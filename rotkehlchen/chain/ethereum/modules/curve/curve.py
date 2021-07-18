import logging

from rotkehlchen.premium.premium import Premium
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.user_messages import MessagesAggregator


if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.defi.structures import GIVEN_ETH_BALANCES
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


log = logging.getLogger(__name__)
SUBGRAPH_REMOTE_ERROR_MSG = (
    "Failed to request the Curve Finance subgraph due to {error_msg}. "
    "All the deposits and withdrawals history queries are not functioning until this is fixed. "  # noqa: E501
    "Probably will get fixed with time. If not report it to rotki's support channel"  # noqa: E501
)


class CurveFinance(EthereumModule):

    def __init__(
        self,
        ethereum_manager: 'EthereumManager',
        database: 'DBHandler',
        premium: Optional[premium],
        msg_aggregator: MessagesAggregator,
    ):
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.history_lock = Semaphore()

        try:
            self.graph_inquirer: CurveFiGraph = CurveFiGraph(
                ethereum_manager=ethereum_manager,
                database=database,
                premium=premium,
                msg_aggregator=msg_aggregator,
            )
        except RemoteError as e:
            self.msg_aggregator.add_error(SUBGRAPH_REMOTE_ERROR_MSG.format(error_msg=str(e)))
            raise ModuleInitializationFailure('Curve Finance subgraph remote error') from e