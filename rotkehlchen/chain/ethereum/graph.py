import json
import logging
import re
from typing import Any, Dict, Optional, Tuple, List, TYPE_CHECKING

import gevent
import requests
from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport
from typing_extensions import Literal

from rotkehlchen.constants.timing import QUERY_RETRY_TIMES
from rotkehlchen.errors import RemoteError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, Timestamp, ExternalService

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


GRAPH_QUERY_LIMIT = 1000
GRAPH_QUERY_SKIP_LIMIT = 5000
RE_MULTIPLE_WHITESPACE = re.compile(r'\s+')
RETRY_BACKOFF_FACTOR = 0.2
SUBGRAPH_REMOTE_ERROR_MSG = (
    "Failed to request the {protocol} subgraph due to {error_msg}. "
    "All the deposits and withdrawals history queries are not functioning until this is fixed. "  # noqa: E501
    "Probably will get fixed with time. If not report it to rotki's support channel"  # noqa: E501
)
THEGRAPH_GATEWAY_PREFIX = 'https://gateway.thegraph.com/api/'


def format_query_indentation(querystr: str) -> str:
    """Format a triple quote and indented GraphQL query by:
    - Removing returns
    - Replacing multiple inner whitespaces with one
    - Removing leading and trailing whitespaces
    """
    return RE_MULTIPLE_WHITESPACE.sub(' ', querystr).strip()


def get_common_params(
        from_ts: Timestamp,
        to_ts: Timestamp,
        address: ChecksumEthAddress,
        address_type: Literal['Bytes!', 'String!'] = 'Bytes!',
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    param_types = {
        '$start_ts': 'Int!',
        '$end_ts': 'Int!',
        '$address': address_type,
    }
    param_values = {
        'start_ts': from_ts,
        'end_ts': to_ts,
        'address': address.lower(),
    }
    return param_types, param_values


class Graph(ExternalServiceWithApiKey):

    def __init__(self, urls: List[str], database: 'DBHandler') -> None:
        """
        - May raise requests.RequestException if there is a problem connecting to the subgraph"""
        super().__init__(database=database, service_name=ExternalService.THEGRAPH)
        own_key = self._get_api_key()
        self.clients, gateway_api = [], False
        for url in urls:
            if url.startswith(THEGRAPH_GATEWAY_PREFIX):
                gateway_api = True
                if not own_key:
                    continue
                url = url.format(api_key=own_key)
            transport = RequestsHTTPTransport(url=url)
            try:
                self.clients.append(Client(transport=transport, fetch_schema_from_transport=False))
            except (requests.exceptions.RequestException) as e:
                raise RemoteError(
                    f'Failed to connect to the graph at {url} due to {str(e)}',
                ) from e
        if len(self.clients) == 0 and gateway_api:
            raise RemoteError('Tryied to use TheGraph gateway without an API key.')
        self.current_client_index = 0

    def _get_client(self, use_next: bool = False) -> Client:
        if use_next:
            if self.current_client_index == len(self.clients) - 1:
                return None
            self.current_client_index += 1
        return self.clients[self.current_client_index]

    def _execute_query(
        self,
        querystr: str,
        param_values: Optional[Dict[str, Any]],
        client: Client,
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        retries_left = QUERY_RETRY_TIMES
        result, exc_msg = None, ''
        while retries_left > 0 and result is None:
            try:
                result = client.execute(gql(querystr), variable_values=param_values)
            # need to catch Exception here due to stupidity of gql library
            except (requests.exceptions.RequestException, Exception) as e:  # pylint: disable=broad-except  # noqa: E501
                # NB: the lack of a good API error handling by The Graph combined
                # with gql v2 raising bare exceptions doesn't allow us to act
                # better on failed requests. Currently all trigger the retry logic.
                # TODO: upgrade to gql v3 and amend this code on any improvement
                # The Graph does on its API error handling.
                exc_msg = str(e)
                retries_left -= 1
                base_msg = f'The Graph query to {querystr} failed due to {exc_msg}'
                if retries_left:
                    sleep_seconds = RETRY_BACKOFF_FACTOR * pow(2, QUERY_RETRY_TIMES - retries_left)
                    retry_msg = (
                        f'Retrying query after {sleep_seconds} seconds. '
                        f'Retries left: {retries_left}.'
                    )
                    log.error(f'{base_msg}. {retry_msg}')
                    gevent.sleep(sleep_seconds)
            else:
                break
        return result, exc_msg

    def query(
            self,
            querystr: str,
            param_types: Optional[Dict[str, Any]] = None,
            param_values: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Queries The Graph for a particular query

        May raise:
        - RemoteError: If there is a problem querying the subgraph and there
        are no retries left.
        """
        prefix = ''
        if param_types is not None:
            prefix = 'query '
            prefix += json.dumps(param_types).replace('"', '').replace('{', '(').replace('}', ')')
            prefix += '{'

        querystr = prefix + querystr
        log.debug(f'Querying The Graph for {querystr}')
        client, result, error = self._get_client(), None, ''
        while client is not None:
            result, error = self._execute_query(
                querystr=querystr,
                param_values=param_values,
                client=client,
            )
            if result is not None:
                break
            client = self._get_client(use_next=True)
        if result is None:
            raise RemoteError(
                f'Failed to query subgraph with {querystr} due to {error}. No retries left.',
            )
        log.debug('Got result from The Graph query')
        return result
