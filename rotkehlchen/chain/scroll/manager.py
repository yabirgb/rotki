from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.manager import EvmManager
from rotkehlchen.history.manager import TaskManager

from .accountant import ScrollAccountingAggregator
from .decoding.decoder import ScrollTransactionDecoder
from .tokens import ScrollTokens
from .transactions import ScrollTransactions

if TYPE_CHECKING:
    from .node_inquirer import ScrollInquirer


class ScrollManager(EvmManager):

    def __init__(self, node_inquirer: 'ScrollInquirer', task_manager: TaskManager) -> None:
        transactions = ScrollTransactions(
            scroll_inquirer=node_inquirer,
            database=node_inquirer.database,
        )
        super().__init__(
            node_inquirer=node_inquirer,
            transactions=transactions,
            tokens=ScrollTokens(
                database=node_inquirer.database,
                scroll_inquirer=node_inquirer,
            ),
            transactions_decoder=ScrollTransactionDecoder(
                database=node_inquirer.database,
                scroll_inquirer=node_inquirer,
                transactions=transactions,
                task_manager=task_manager,
            ),
            accounting_aggregator=ScrollAccountingAggregator(
                node_inquirer=node_inquirer,
                msg_aggregator=transactions.msg_aggregator,
            ),
        )
        self.node_inquirer: ScrollInquirer  # just to make the type specific
