#!/usr/bin/env python3
"""
Improved events processor for tax reporting in Spain (Hacienda).
Extracts trade, deposit, and withdrawal data with proper cost basis tracking.

This script processes events using Rotki's EventsAccountant for accurate tax calculations.
"""
from gevent import monkey
monkey.patch_all()  # isort:skip

import json
import logging
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Literal, NamedTuple, Optional, Tuple

import polars as pl

from rotkehlchen.accounting.rules import AccountingRulesManager
from rotkehlchen.chain.evm.accounting.structures import TxAccountingTreatment
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.types import HistoricalPriceOracle
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter, configure_logging, add_logging_level, TRACE
from rotkehlchen.tests.utils.args import default_args
from rotkehlchen.types import EVM_CHAINS_WITH_TRANSACTIONS, Location, Timestamp, SPAM_PROTOCOL
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_iso8601, ts_ms_to_sec
from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.globaldb.manual_price_oracles import ManualCurrentOracle
from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle

from rotkehlchen.externalapis.beaconchain.service import BeaconChain
from rotkehlchen.chain.arbitrum_one.manager import ArbitrumOneManager
from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
from rotkehlchen.chain.avalanche.manager import AvalancheManager
from rotkehlchen.chain.base.manager import BaseManager
from rotkehlchen.chain.base.node_inquirer import BaseInquirer
from rotkehlchen.chain.binance_sc.manager import BinanceSCManager
from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.gnosis.manager import GnosisManager
from rotkehlchen.chain.gnosis.node_inquirer import GnosisInquirer
from rotkehlchen.chain.optimism.manager import OptimismManager
from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
from rotkehlchen.chain.polygon_pos.manager import PolygonPOSManager
from rotkehlchen.chain.polygon_pos.node_inquirer import PolygonPOSInquirer
from rotkehlchen.chain.scroll.manager import ScrollManager
from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
from rotkehlchen.externalapis.etherscan import Etherscan


# Configure logging
add_logging_level('TRACE', TRACE)
configure_logging(default_args(loglevel='info'))

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# Tax year 2024
START_TS = Timestamp(1704067200)  # 2024-01-01
END_TS = Timestamp(1735689599)    # 2024-12-31


class TaxableEvent(NamedTuple):
    """Represents a taxable event for Spanish tax reporting."""
    timestamp: Timestamp
    event_identifier: str
    event_type: str  # Trade, Deposit, Withdrawal
    # Sold/Sent info
    asset_sold: str
    amount_sold: FVal
    price_sold_eur: FVal
    value_sold_eur: FVal
    # Received info
    asset_received: Optional[str]
    amount_received: Optional[FVal]
    price_received_eur: Optional[FVal]
    value_received_eur: Optional[FVal]
    is_fiat_received: bool
    is_fiat_sold: bool
    # Fee info
    fee_amount: Optional[FVal]
    fee_asset: Optional[str]
    fee_value_eur: Optional[FVal]
    # Profit/Loss
    cost_basis_eur: Optional[FVal]
    profit_loss_eur: Optional[FVal]
    location: str


class EventProcessor:
    """Process events for tax reporting with proper cost basis tracking."""
    
    def __init__(self, data_dir: Path, username: str, password: str):
        """Initialize the event processor."""
        self.msg_aggregator = MessagesAggregator()
        self.greenlet_manager = GreenletManager(self.msg_aggregator)
        
        # Initialize global database
        self.globaldb = GlobalDBHandler(
            data_dir=data_dir,
            sql_vm_instructions_cb=0,
            perform_assets_updates=False,
            msg_aggregator=self.msg_aggregator,
        )
        
        # Initialize user database
        self.data = DataHandler(data_dir, self.msg_aggregator, 0)
        self.data.unlock(
            username=username,
            password=password,
            create_new=False,
            resume_from_backup=False,
        )
        
        self.dbevents = DBHistoryEvents(self.data.db)
        
        # Initialize price sources
        self._init_price_sources()
        
        # Initialize cost basis tracking
        self.cost_basis: Dict[Asset, deque[Tuple[FVal, FVal, Timestamp, str]]] = defaultdict(deque)
        # Track: (amount, price_eur, timestamp, event_id)
        
        # Cache for prices
        self.price_cache: Dict[Tuple[str, Timestamp], FVal] = {}
        self.rules = AccountingRulesManager(self.data.db, None, None)
        self.rules._query_db_rules()
    
    def _init_price_sources(self):
        """Initialize price sources and historian."""
        self.cryptocompare = Cryptocompare(database=self.data.db)
        self.coingecko = Coingecko(database=self.data.db)
        self.defillama = Defillama(database=self.data.db)
        self.alchemy = Alchemy(database=self.data.db)

        etherscan = Etherscan(
            database=self.data.db,
            msg_aggregator=self.msg_aggregator,
        )
        self.beaconchain = BeaconChain(database=self.data.db, msg_aggregator=self.msg_aggregator)
        self.etherscan = etherscan



        chain_managers = [
            EthereumManager(
                node_inquirer=(ethereum_inquirer := EthereumInquirer(
                    greenlet_manager=self.greenlet_manager,
                    database=self.data.db,
                    etherscan=etherscan,
                )),
                beacon_chain=self.beaconchain,
            ),
            OptimismManager(OptimismInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            PolygonPOSManager(PolygonPOSInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            ArbitrumOneManager(ArbitrumOneInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            BaseManager(BaseInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            GnosisManager(GnosisInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            ScrollManager(ScrollInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            )),
            BinanceSCManager(BinanceSCInquirer(
                greenlet_manager=self.greenlet_manager,
                database=self.data.db,
                etherscan=etherscan,
            ))
        ]



        self.inquirer = Inquirer(
            data_dir=self.data.db.user_data_dir.parent,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
            defillama=self.defillama,
            alchemy=self.alchemy,
            manualcurrent=ManualCurrentOracle(),
            msg_aggregator=self.msg_aggregator,
        )

        self.inquirer.inject_evm_managers([
            (chain.to_chain_id(), manager)
            for chain, manager in zip(EVM_CHAINS_WITH_TRANSACTIONS, chain_managers)
        ])
        
        self.price_historian = PriceHistorian(
            data_directory=self.data.db.user_data_dir.parent,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
            defillama=self.defillama,
            alchemy=self.alchemy,
            uniswapv2=(uniswap_v2_oracle := UniswapV2Oracle()),
            uniswapv3=(uniswap_v3_oracle := UniswapV3Oracle()),
        )
        
        self.price_historian.set_oracles_order([
            HistoricalPriceOracle.DEFILLAMA,
            HistoricalPriceOracle.CRYPTOCOMPARE,
            HistoricalPriceOracle.ALCHEMY,
        ])
    
    def query_price(self, asset: Asset, timestamp: Timestamp) -> FVal:
        """Query price for an asset at a specific timestamp."""
        cache_key = (asset.identifier, timestamp)
        if cache_key in self.price_cache:
            return self.price_cache[cache_key]
        
        try:
            log.debug(f'Querying price for {asset} at {timestamp}')
            price = self.price_historian.query_historical_price(
                from_asset=asset,
                to_asset=A_EUR,
                timestamp=timestamp,
            )
            self.price_cache[cache_key] = price
            return price
        except NoPriceForGivenTimestamp:
            log.warning(f'No price found for {asset} at {timestamp}')
            self.price_cache[cache_key] = ZERO
            return ZERO
    
    def _group_events_by_identifier(self, events: List[HistoryBaseEntry]) -> Dict[str, List[HistoryBaseEntry]]:
        """Group events by their event_identifier."""
        grouped = defaultdict(list)
        
        for event in events:
            grouped[event.event_identifier].append(event)

        # Sort events within each group by sequence_index
        for event_list in grouped.values():
            event_list.sort(key=lambda e: e.sequence_index)
        
        return grouped
    
    def _is_fiat_asset(self, asset: Asset) -> bool:
        """Check if an asset is fiat currency."""
        return asset.is_fiat()
    
    def _process_swap(
            self,
            out_event: HistoryBaseEntry,
            in_event: HistoryBaseEntry,
            fee_event: HistoryBaseEntry | None = None,
    ) -> Optional[TaxableEvent]:
        """Process a swap transaction (multiple events with same identifier)."""
        # Use the first OUT event as the main event
        timestamp = out_event.get_timestamp_in_sec()

        if (out_asset_id := GlobalDBHandler.get_collection_main_asset(out_event.asset.identifier)) is None:
            out_asset_id = out_event.asset.identifier

        if (in_asset_id := GlobalDBHandler.get_collection_main_asset(in_event.asset.identifier)) is None:
            in_asset_id = in_event.asset.identifier

        out_asset = Asset(out_asset_id).resolve()
        in_asset = Asset(in_asset_id).resolve()

        # Calculate values
        out_price = self.query_price(out_asset, timestamp)
        out_value = out_event.amount * out_price
        
        in_price = self.query_price(in_asset, timestamp)
        in_value = in_event.amount * in_price
        
        # Process fees
        total_fee_value = ZERO
        fee_info = None
        if fee_event:
            if (fee_asset_id := GlobalDBHandler.get_collection_main_asset(fee_event.asset.identifier)) is None:
                fee_asset_id = fee_event.asset.identifier

            fee_price = self.query_price(Asset(fee_asset_id), timestamp)
            fee_value = fee_event.amount * fee_price
            total_fee_value = fee_value
            fee_info = (fee_event.amount, fee_event.asset.resolve().symbol_or_name(), fee_value)
        
        # Update cost basis
        cost_basis = self._process_disposal(out_asset, out_event.amount)
        self._add_to_cost_basis(in_event.asset, in_event.amount, in_price, timestamp, in_event.event_identifier)
        
        # Calculate profit/loss
        profit_loss = out_value - cost_basis - total_fee_value
        return TaxableEvent(
            timestamp=timestamp,
            event_identifier=out_event.event_identifier,
            event_type='Trade',
            asset_sold=out_asset.symbol_or_name(),
            amount_sold=out_event.amount,
            price_sold_eur=out_price,
            value_sold_eur=out_value,
            asset_received=in_asset.symbol_or_name(),
            amount_received=in_event.amount,
            price_received_eur=in_price,
            value_received_eur=in_value,
            is_fiat_received=in_event.asset.is_fiat(),
            is_fiat_sold=out_asset.is_fiat(),
            fee_amount=fee_info[0] if fee_info else None,
            fee_asset=fee_info[1] if fee_info else None,
            fee_value_eur=fee_info[2] if fee_info else None,
            cost_basis_eur=cost_basis,
            profit_loss_eur=profit_loss,
            location=out_event.location.serialize(),
        )

    def _add_to_cost_basis(self, asset: Asset, amount: FVal, price_eur: FVal, timestamp: Timestamp, event_id: str):
        """Add an acquisition to the cost basis."""
        self.cost_basis[asset].append((amount, price_eur, timestamp, event_id))
        #log.info(f'Added {amount} {asset.resolve().symbol_or_name()} to cost basis at {price_eur} EUR/unit')
    
    def _process_disposal(self, asset: Asset, amount: FVal) -> FVal:
        """Process a disposal using FIFO and return the cost basis."""
        remaining = amount
        total_cost_basis = ZERO

        if asset.identifier == 'EUR':
            return amount
        
        while remaining > ZERO and self.cost_basis[asset]:
            oldest_amount, oldest_price, oldest_ts, oldest_event_id = self.cost_basis[asset][0]
            
            if oldest_amount <= remaining:
                # Use entire lot
                used_amount = oldest_amount
                self.cost_basis[asset].popleft()
            else:
                # Use partial lot
                used_amount = remaining
                # Update the lot
                new_lot = (oldest_amount - used_amount, oldest_price, oldest_ts, oldest_event_id)
                self.cost_basis[asset][0] = new_lot
            
            total_cost_basis += used_amount * oldest_price
            remaining -= used_amount
        
        if remaining > ZERO:
            log.warning(f'Insufficient cost basis for {asset.resolve().symbol_or_name()}. Missing {remaining} units')
        
        return total_cost_basis
    
    def process_group(self, events: List[HistoryBaseEntry]) -> List[TaxableEvent]:
        events_iterator = iter(events)
        swaps = []
        gas_event = None
        print(events[0].event_identifier)
        while (event := next(events_iterator, None)) is not None:
            resolved_asset = event.asset.resolve()
            if resolved_asset.is_evm_token() and resolved_asset.protocol == SPAM_PROTOCOL:
                continue

            if (direction := event.maybe_get_direction()) == EventDirection.NEUTRAL:
                continue

            if isinstance(event, EvmEvent) and event.counterparty == CPT_GAS:
                gas_event = event
                self._process_disposal(event.asset, amount=gas_event.amount)
                continue

            timestamp = event.get_timestamp_in_sec()
            rule, callback = self.rules.get_event_settings(event)
            if rule is None:
                log.error(f'Failed to find rule for event {event.serialize()}')
                continue
            
            spend_event, receive_event, fee = None, None, None
            if rule.accounting_treatment == TxAccountingTreatment.SWAP:
                if event.event_type == HistoryEventType.TRADE:
                    if direction == EventDirection.OUT:
                        spend_event = event
                    
                    if (receive_event := next(events_iterator, None)) is None:
                        print("!!!!")
                        return []
                        assert False, [x.serialize() for x in events]

                    fee = next(events_iterator, None)

                    if event.timestamp >= START_TS:
                        swaps.append(self._process_swap(
                            out_event=spend_event,
                            in_event=receive_event,
                            fee_event=fee,
                        ))
            else:
                if direction == EventDirection.IN:
                    self._add_to_cost_basis(
                        asset=event.asset,
                        amount=event.amount,
                        price_eur=self.query_price(event.asset, timestamp),
                        timestamp=timestamp,
                        event_id=event.event_identifier,
                    )
                else:
                    self._process_disposal(event.asset, event.amount)

        return swaps
                

    def process_events(self, all_events: List[HistoryBaseEntry]) -> List[TaxableEvent]:
        """Process all events and return taxable events."""
        taxable_events = []    
        current_event = None
        group_events = []
        for event in all_events:
            if event.event_identifier != current_event:
                if current_event != None:
                    taxable_events.extend(self.process_group(group_events))
                
                # reset the group
                current_event = event.event_identifier
                group_events = [event]
            else:
                group_events.append(event)
        
        # process last group
        taxable_events.extend(self.process_group(group_events))
        
        return taxable_events
    
    def generate_report(self, taxable_events: List[TaxableEvent], output_file: str):
        """Generate CSV report from taxable events."""
        rows = []

        from dataclasses import dataclass

        @dataclass
        class EntryAsset:
            valor_transmision: FVal
            valor_adquisicion: FVal

            def serialize(self):
                return {
                    'valor adquisicion': self.valor_adquisicion,
                    'valor transmision': self.valor_transmision,
                    'ganancia': self.valor_adquisicion - self.valor_transmision
                }

        per_asset: dict[Asset, dict[Literal['fiat', 'crypto'], EntryAsset]] = defaultdict(
            lambda: {'fiat': EntryAsset(ZERO, ZERO), 'crypto': EntryAsset(ZERO, ZERO)}
        )
        
        for event in taxable_events:
            rows.append({
                'Fecha': timestamp_to_iso8601(event.timestamp),
                'Identificador': event.event_identifier,
                'Tipo': event.event_type,
                'Lugar': event.location,
                # Sold/Sent
                'Activo Vendido': event.asset_sold,
                'Cantidad Vendida': float(event.amount_sold) if event.amount_sold else 0,
                'Precio Venta EUR': float(event.price_sold_eur) if event.price_sold_eur else 0,
                'Valor Venta EUR': float(event.value_sold_eur) if event.value_sold_eur else 0,
                # Received
                'Activo Recibido': event.asset_received or '',
                'Cantidad Recibida': float(event.amount_received) if event.amount_received else 0,
                'Precio Compra EUR': float(event.price_received_eur) if event.price_received_eur else 0,
                'Valor Compra EUR': float(event.value_received_eur) if event.value_received_eur else 0,
                'Es Fiat': 'Si' if event.is_fiat_received else 'No',
                # Fee
                'Comision': float(event.fee_amount) if event.fee_amount else 0,
                'Activo Comision': event.fee_asset or '',
                'Valor Comision EUR': float(event.fee_value_eur) if event.fee_value_eur else 0,
                # Profit/Loss
                'Coste Base EUR': float(event.cost_basis_eur) if event.cost_basis_eur else 0,
                'Ganancia/Perdida EUR': float(event.profit_loss_eur) if event.profit_loss_eur else 0,
            })

            if event.is_fiat_received:
                entry = per_asset[event.asset_sold]
                entry['fiat'].valor_transmision += event.cost_basis_eur or ZERO
                entry['fiat'].valor_adquisicion += event.value_received_eur or ZERO
            elif event.is_fiat_sold is False:
                entry = per_asset[event.asset_sold]
                entry['crypto'].valor_transmision += event.cost_basis_eur or ZERO
                entry['crypto'].valor_adquisicion += event.value_received_eur or ZERO
        
        df = pl.DataFrame(rows)
        
        # Summary statistics
        print(f"\n=== Resumen de Eventos Procesados ===")
        print(f"Total eventos: {len(taxable_events)}")
        print(f"Trades: {sum(1 for e in taxable_events if e.event_type == 'Trade')}")
        print(f"Depositos: {sum(1 for e in taxable_events if e.event_type == 'Deposit')}")
        print(f"Retiradas: {sum(1 for e in taxable_events if e.event_type == 'Withdrawal')}")
        
        # Calculate totals
        total_profit = sum(e.profit_loss_eur for e in taxable_events if e.profit_loss_eur and e.profit_loss_eur > 0)
        total_loss = sum(e.profit_loss_eur for e in taxable_events if e.profit_loss_eur and e.profit_loss_eur < 0)
        net_profit_loss = sum(e.profit_loss_eur for e in taxable_events if e.profit_loss_eur)
        
        print(f"\n=== Resumen Fiscal ===")
        print(f"Ganancias totales: {total_profit} EUR")
        print(f"Perdidas totales: {total_loss} EUR")
        print(f"Ganancia/Perdida neta: {net_profit_loss} EUR")
        
        # Save to CSV
        df.write_csv(output_file, separator=';')
        print(f"\nReporte guardado en: {output_file}")

        import pprint
        pprint.pprint([{asset: {'fiat': x['fiat'].serialize(), 'crypto': x['crypto'].serialize()}} for asset, x in per_asset.items()])
        
        return df


def main():
    """Main function to run the event processor."""
    # Configuration
    data_dir = Path('/Users/yabirgb/Library/Application Support/rotki/data')
    username = 'yabirgb'
    password = '}~%-F9qs"TYQH$\/\lg-<:.XHev?=W'
    
    # Initialize processor
    processor = EventProcessor(data_dir, username, password)
    
    # Process events
    print("Procesando eventos...")
    with processor.data.db.conn.read_ctx() as cursor:
            # Get ALL events to build proper cost basis
            all_events = processor.dbevents.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    from_ts=Timestamp(0),  # From beginning for cost basis
                    to_ts=END_TS,
                    # location=Location.COINBASE,
                    order_by_rules=[('timestamp', True), ('sequence_index', True)],
                ),
                has_premium=True,
            )
    taxable_events = processor.process_events(all_events)
    
    # Generate report
    output_file = "hacienda/eventos_fiscales_2024.csv"
    processor.generate_report(taxable_events, output_file)


if __name__ == "__main__":
    main()