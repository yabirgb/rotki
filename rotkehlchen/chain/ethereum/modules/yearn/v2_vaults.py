from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Optional

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.modules.yearn.vaults import YearnVaultHistory, YearnVaultBalance
from rotkehlchen.chain.ethereum.modules.yearn.graph import YearnV2Inquirer
from rotkehlchen.chain.ethereum.structures import YearnVault, YearnVaultEvent
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.chain.ethereum.modules.yearn.vaults import get_usd_price_zero_if_error
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress, EthAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.defi.structures import (
        GIVEN_DEFI_BALANCES,
        DefiProtocolBalances,
    )
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler


class YearnV2Vaults(EthereumModule):

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.premium = premium
        self.history_lock = Semaphore()

        try:
            self.graph_inquirer: Optional[YearnV2Inquirer] = YearnV2Inquirer(
                ethereum_manager=ethereum_manager,
                database=database,
                premium=premium,
                msg_aggregator=msg_aggregator,
            )
        except RemoteError as e:
            self.graph_inquirer = None
            self.msg_aggregator.add_error(
                f'Could not initialize the Yearn V2 subgraph due to {str(e)}.',
            )

    def _process_vault_events(self, events: List[YearnVaultEvent]) -> Balance:
        """Process the events for a single vault and returns total profit/loss after all events"""
        total = Balance()
        profit_so_far = Balance()
        for event in events:
            if event.event_type == 'deposit':
                total -= event.from_value
            else:  # withdraws
                profit_amount = total.amount + event.to_value.amount - profit_so_far.amount
                profit: Optional[Balance]
                if profit_amount >= 0:
                    usd_price = get_usd_price_zero_if_error(
                        asset=event.to_asset,
                        time=event.timestamp,
                        location='yearn vault event processing',
                        msg_aggregator=self.msg_aggregator,
                    )
                    profit = Balance(profit_amount, profit_amount * usd_price)
                    profit_so_far += profit
                else:
                    profit = None

                event.realized_pnl = profit
                total += event.to_value

        return total

    def _get_single_addr_balance(
            self,
            defi_balances: List['DefiProtocolBalances'],
            roi_cache: Dict[str, FVal],
    ) -> Dict[str, YearnVaultBalance]:
        pass

    def _get_vault_deposit_events(
            self,
            vault: YearnVault,
            address: ChecksumEthAddress,
            from_block: int,
            to_block: int,
    ) -> List[YearnVaultEvent]:
        pass

    def _get_vault_withdraw_events(
            self,
            vault: YearnVault,
            address: ChecksumEthAddress,
            from_block: int,
            to_block: int,
    ) -> List[YearnVaultEvent]:
        pass

    def get_vaults_history(
            self,
            defi_balances: List['DefiProtocolBalances'],
            address: ChecksumEthAddress,
            from_block: int,
            to_block: int,
    ) -> Optional[Dict[str, YearnVaultHistory]]:

        if self.graph_inquirer is None:
            return None

        new_events = self.graph_inquirer.get_all_events(
            address=EthAddress(address.lower()),
            from_block=from_block,
            to_block=to_block,
        )

        # Dict that stores vault token symbol and their events + total pnl
        vaults: Dict[str, Dict[str, List[YearnVaultEvent]]] = defaultdict(
            lambda: defaultdict(list),
        )

        # Vaults histories
        vaults_histories: Dict[str, YearnVaultHistory] = {}

        # Flattern the data into an unique list
        events = list(new_events['deposits'])
        events.extend(new_events['withdrawals'])

        for event in events:
            if event.event_type == 'deposit':
                vault_token_symbol = event.to_asset.identifier
                underlying_token = event.from_asset
            else:
                vault_token_symbol = event.from_asset.identifier
                underlying_token = event.to_asset

            vaults[vault_token_symbol]['events'].append(event)

        # Sort events in each vault
        for key in vaults.keys():
            vaults[key]['events'].sort(key=lambda x: x.timestamp)
            total_pnl = self._process_vault_events(vaults[key]['events'])

            current_balance = None
            for balance in defi_balances:
                found_balance = (
                    balance.protocol.name == 'yearn.finance • Vaults' and
                    balance.base_balance.token_symbol == vault_token_symbol
                )
                if found_balance:
                    current_balance = balance.underlying_balances[0].balance
                    total_pnl += current_balance
                    break

                # Due to the way we calculate usd prices for vaults we need to get the current
                # usd price of the actual pnl amount at this point
                if total_pnl.amount != ZERO:
                    usd_price = get_usd_price_zero_if_error(
                        asset=underlying_token,
                        time=ts_now(),
                        location='yearn vault history',
                        msg_aggregator=self.msg_aggregator,
                    )
                    total_pnl.usd_value = usd_price * total_pnl.amount

            vaults_histories[key] = YearnVaultHistory(
                events=vaults[key]['events'],
                profit_loss=total_pnl,
            )

        return vaults_histories

    def get_history(
            self,
            given_defi_balances: 'GIVEN_DEFI_BALANCES',
            addresses: List[ChecksumEthAddress],
            reset_db_data: bool,
            from_timestamp: Timestamp,  # pylint: disable=unused-argument
            to_timestamp: Timestamp,  # pylint: disable=unused-argument
    ) -> Dict[ChecksumEthAddress, Dict[str, YearnVaultHistory]]:
        with self.history_lock:

            # TODO: Skip entries in DB already queried. Since is a graph query
            # it doesn't have a huge performance effect but is less data we have
            # to process

            if reset_db_data is True:
                self.database.delete_yearn_vaults_data()

            if isinstance(given_defi_balances, dict):
                defi_balances = given_defi_balances
            else:
                defi_balances = given_defi_balances()

            from_block = self.ethereum.get_blocknumber_by_time(from_timestamp)
            to_block = self.ethereum.get_blocknumber_by_time(to_timestamp)
            history: Dict[ChecksumEthAddress, Dict[str, YearnVaultHistory]] = {}

            for address in addresses:
                history[address] = {}
                vaults_histories = self.get_vaults_history(
                    defi_balances=defi_balances.get(address, []),
                    address=address,
                    from_block=from_block,
                    to_block=to_block,
                )

                if vaults_histories is not None:
                    for vault_name, vault_history in vaults_histories.items():
                        history[address][vault_name] = vault_history

                if len(history[address]) == 0:
                    del history[address]

            return history

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        pass

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        pass

    def deactivate(self) -> None:
        self.database.delete_yearn_vaults_data()
