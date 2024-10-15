from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import CurveManagerMixin, EvmManager
from rotkehlchen.history.manager import TaskManager

from .accountant import PolygonPOSAccountingAggregator
from .decoding.decoder import PolygonPOSTransactionDecoder
from .tokens import PolygonPOSTokens
from .transactions import PolygonPOSTransactions

if TYPE_CHECKING:

    from .node_inquirer import PolygonPOSInquirer


class PolygonPOSManager(EvmManager, CurveManagerMixin):

    def __init__(
            self,
            node_inquirer: 'PolygonPOSInquirer',
            task_manager: TaskManager,
    ) -> None:
        transactions = PolygonPOSTransactions(
            polygon_pos_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=PolygonPOSTokens(
                database=node_inquirer.database,
                polygon_pos_inquirer=node_inquirer,
            ),
            transactions_decoder=PolygonPOSTransactionDecoder(
                database=node_inquirer.database,
                polygon_pos_inquirer=node_inquirer,
                transactions=transactions,
                task_manager=task_manager,
            ),
            accounting_aggregator=PolygonPOSAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: PolygonPOSInquirer  # just to make the type specific
