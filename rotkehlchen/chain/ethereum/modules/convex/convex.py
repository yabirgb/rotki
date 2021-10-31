from collections import defaultdict
from typing import Any, Dict, List, NamedTuple, Optional, TYPE_CHECKING

import more_itertools as mit

from rotkehlchen.accounting.structures import AssetBalance, Balance
from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.defi.convex_pools import get_convex_pools
from rotkehlchen.chain.ethereum.contracts import EthereumContract
from rotkehlchen.chain.ethereum.graph import (
    SUBGRAPH_REMOTE_ERROR_MSG,
    Graph,
    format_query_indentation,
)
from rotkehlchen.chain.ethereum.utils import multicall, token_normalized_value_decimals
from rotkehlchen.constants.ethereum import LUSD_CONVEC_REWARDS, CURVE_LUSD_FACTORY
from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.premium.premium import Premium
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.typing import ChecksumEthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

from .graph import QUERY_EVENTS


CONTRACTS_PER_CHUNK = 15
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ConvexBalance(NamedTuple):
    pool_balances: List[AssetBalance]

    def serialize(self) -> Dict[str, Any]:
        return {
            'pool_balances': [x.serialize() for x in self.pool_balances]
        }

class ConvexEvent(NamedTuple):
    event_type: Literal['deposit', 'withdrawals']
    pool_id: int
    amount: FVal
    timestamp: Timestamp
    def serialize(self) -> Dict[str, Any]:
        return {
            'event_type': self.event_type,
            'pool_name': self.pool_id,
            'amount': self.amount,
            'timestamp': self.timestamp,
        }


class Convex(EthereumModule):

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.premium = premium
        self.msg_aggregator = msg_aggregator
        self.virtual_prices_mapping = {}

        try:
            self.graph = Graph(
                'https://api.thegraph.com/subgraphs/name/convex-community/curve-pools',
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(
                SUBGRAPH_REMOTE_ERROR_MSG.format(protocol='Convex', error_msg=str(e)),
            )
            raise ModuleInitializationFailure('Liquity Subgraph remote error') from e

    def get_virtual_price(self, address: ChecksumEthAddress, is_v2: bool = False) -> FVal:
        # TODO: When the curve module is integrated this should be generalized
        virtual_price = self.virtual_prices_mapping.get(address)
        if virtual_price is None:
            if not is_v2:
                virtual_price_raw = CURVE_LUSD_FACTORY.call(
                    ethereum=self.ethereum,
                    method_name='get_virtual_price',
                )
                virtual_price = FVal(virtual_price_raw*10**-18)
                self.virtual_prices_mapping[address] = virtual_price
        return virtual_price

    def get_balances(
        self,
        addresses: List[ChecksumEthAddress],
    ) -> Dict[ChecksumEthAddress, List[AssetBalance]]:
        """
        Query information for amount locked, pending rewards and time until unlock
        for Pickle's dill.
        """
        convex_pools = get_convex_pools()
        rewards_addresses = [(x.crv_rewards, pid) for pid, x in convex_pools.items()]
        balances_result = {}
        for address in addresses:
            # Split calls in chuncks since requests are too big. Getting Request URL Too Long   
            chunked_rewards_addresses = mit.chunked(rewards_addresses, CONTRACTS_PER_CHUNK)
            pool_balances = []
            for chunk in chunked_rewards_addresses:
                balances = multicall(
                    ethereum=self.ethereum,
                    calls=[(
                        reward_contract[0],
                        LUSD_CONVEC_REWARDS.encode(method_name='balanceOf', arguments=[address])
                    ) for reward_contract in chunk],
                )
                for idx, balance_encoded in enumerate(balances):
                    balance = FVal(LUSD_CONVEC_REWARDS.decode(balance_encoded, 'balanceOf', arguments=[address])[0]/10**18)
                    if balance != 0:
                        lp_token = convex_pools[chunk[idx][1]].lp
                        amount = FVal(balance)*self.get_virtual_price(lp_token)
                        pool_balances.append(
                            AssetBalance(
                                asset=EthereumToken(lp_token),
                                balance=Balance(
                                    amount=amount,
                                    usd_value=FVal(0),
                                )
                            )
                        )
            balances_result[address] = ConvexBalance(
                pool_balances=pool_balances,
            )
        return balances_result

    def _get_raw_history(self, addresses: List[ChecksumEthAddress]) -> Dict[str, Any]:
        param_types = {
            '$addresses': '[Bytes!]',
        }
        param_values = {
            'addresses': [addr.lower() for addr in addresses],
        }
        querystr = format_query_indentation(QUERY_EVENTS)
        return self.graph.query(
            querystr=querystr,
            param_types=param_types,
            param_values=param_values,
        )

    def get_history(self, addresses: List[ChecksumEthAddress]) -> Dict[ChecksumEthAddress, List[ConvexEvent]]:
        history: Dict[ChecksumEthAddress, Dict[str, List[ConvexEvent]]] = defaultdict(lambda: defaultdict(list))
        for address in addresses:
            raw_data = self._get_raw_history(address)
            for event_type in ['withdrawals', 'deposits']:
                for entry in raw_data[event_type]:
                    try:
                        event = ConvexEvent(
                            event_type=event_type,
                            pool_id=entry['poolid']['id'],
                            amount=FVal(raw_data['amount']),
                            timestamp=raw_data['timestamp']
                        )
                        history[address][event_type],append(event)
                    except KeyError as e:
                        log.debug(f'Failed to ready entry {entry} from convex due to missing key {str(e)}')
        return history

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> Optional[List['AssetBalance']]:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        pass
