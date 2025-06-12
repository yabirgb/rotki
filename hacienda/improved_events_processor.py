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
from typing import Dict, List, NamedTuple, Optional, Tuple

import polars as pl

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.constants.misc import ZERO
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
from rotkehlchen.types import Location, Timestamp, SPAM_PROTOCOL
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_iso8601, ts_ms_to_sec

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
    
    def _init_price_sources(self):
        """Initialize price sources and historian."""
        self.cryptocompare = Cryptocompare(database=self.data.db)
        self.coingecko = Coingecko(database=self.data.db)
        self.defillama = Defillama(database=self.data.db)
        
        self.inquirer = Inquirer(
            data_dir=self.data.db.user_data_dir.parent,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
            defillama=self.defillama,
            alchemy=None,
            manualcurrent=None,
            msg_aggregator=self.msg_aggregator,
        )
        
        self.price_historian = PriceHistorian(
            data_directory=self.data.db.user_data_dir.parent,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
            defillama=self.defillama,
            alchemy=None,
            uniswapv2=None,
            uniswapv3=None,
        )
        
        self.price_historian.set_oracles_order([
            HistoricalPriceOracle.DEFILLAMA,
            HistoricalPriceOracle.CRYPTOCOMPARE,
            HistoricalPriceOracle.COINGECKO,
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
            if event.event_identifier:
                grouped[event.event_identifier].append(event)
            else:
                # Single events without identifier
                grouped[f'single_{event.timestamp}_{id(event)}'] = [event]
        
        # Sort events within each group by sequence_index
        for event_id, event_list in grouped.items():
            event_list.sort(key=lambda e: (e.timestamp, getattr(e, 'sequence_index', 0)))
        
        return grouped
    
    def _is_fiat_asset(self, asset: Asset) -> bool:
        """Check if an asset is fiat currency."""
        fiat_symbols = {'EUR', 'USD', 'GBP', 'JPY', 'CHF', 'CAD', 'AUD'}
        return asset.resolve().symbol in fiat_symbols
    
    def _process_swap(self, events: List[HistoryBaseEntry]) -> Optional[TaxableEvent]:
        """Process a swap transaction (multiple events with same identifier)."""
        out_events = []
        in_events = []
        fee_events = []
        
        for event in events:
            # Skip spam assets
            if hasattr(event, 'asset') and event.asset.is_evm_token():
                token = event.asset.resolve_to_evm_token()
                if token.protocol == SPAM_PROTOCOL:
                    continue
            
            direction = event.maybe_get_direction()
            if direction is None or direction == EventDirection.NEUTRAL:
                continue
            
            if hasattr(event, 'event_subtype') and event.event_subtype == HistoryEventSubType.FEE:
                fee_events.append(event)
            elif direction == EventDirection.OUT:
                out_events.append(event)
            elif direction == EventDirection.IN:
                in_events.append(event)
        
        # Must have at least one OUT and one IN for a valid swap
        if not out_events or not in_events:
            return None
        
        # Use the first OUT event as the main event
        main_out = out_events[0]
        main_in = in_events[0]
        
        timestamp = ts_ms_to_sec(main_out.timestamp)
        
        # Calculate values
        out_price = self.query_price(main_out.asset, timestamp)
        out_value = main_out.amount * out_price
        
        in_price = self.query_price(main_in.asset, timestamp)
        in_value = main_in.amount * in_price
        
        # Process fees
        total_fee_value = ZERO
        fee_info = None
        if fee_events:
            fee_event = fee_events[0]
            fee_price = self.query_price(fee_event.asset, timestamp)
            fee_value = fee_event.amount * fee_price
            total_fee_value = fee_value
            fee_info = (fee_event.amount, fee_event.asset.resolve().symbol_or_name(), fee_value)
        
        # Update cost basis
        cost_basis = self._process_disposal(main_out.asset, main_out.amount, timestamp, main_out.event_identifier)
        self._add_to_cost_basis(main_in.asset, main_in.amount, in_price, timestamp, main_in.event_identifier)
        
        # Calculate profit/loss
        profit_loss = out_value - cost_basis - total_fee_value
        
        return TaxableEvent(
            timestamp=timestamp,
            event_identifier=main_out.event_identifier,
            event_type='Trade',
            asset_sold=main_out.asset.resolve().symbol_or_name(),
            amount_sold=main_out.amount,
            price_sold_eur=out_price,
            value_sold_eur=out_value,
            asset_received=main_in.asset.resolve().symbol_or_name(),
            amount_received=main_in.amount,
            price_received_eur=in_price,
            value_received_eur=in_value,
            is_fiat_received=self._is_fiat_asset(main_in.asset),
            fee_amount=fee_info[0] if fee_info else None,
            fee_asset=fee_info[1] if fee_info else None,
            fee_value_eur=fee_info[2] if fee_info else None,
            cost_basis_eur=cost_basis,
            profit_loss_eur=profit_loss,
            location=main_out.location.serialize(),
        )
    
    def _process_deposit(self, event: HistoryBaseEntry) -> Optional[TaxableEvent]:
        """Process a deposit event."""
        timestamp = ts_ms_to_sec(event.timestamp)
        price = self.query_price(event.asset, timestamp)
        value = event.amount * price
        
        # Add to cost basis if it's an acquisition
        self._add_to_cost_basis(event.asset, event.amount, price, timestamp, event.event_identifier)
        
        return TaxableEvent(
            timestamp=timestamp,
            event_identifier=event.event_identifier,
            event_type='Deposit',
            asset_sold='',
            amount_sold=ZERO,
            price_sold_eur=ZERO,
            value_sold_eur=ZERO,
            asset_received=event.asset.resolve().symbol_or_name(),
            amount_received=event.amount,
            price_received_eur=price,
            value_received_eur=value,
            is_fiat_received=self._is_fiat_asset(event.asset),
            fee_amount=None,
            fee_asset=None,
            fee_value_eur=None,
            cost_basis_eur=None,
            profit_loss_eur=None,
            location=event.location.serialize(),
        )
    
    def _process_withdrawal(self, event: HistoryBaseEntry) -> Optional[TaxableEvent]:
        """Process a withdrawal event."""
        timestamp = ts_ms_to_sec(event.timestamp)
        price = self.query_price(event.asset, timestamp)
        value = event.amount * price
        
        # Process disposal from cost basis
        cost_basis = self._process_disposal(event.asset, event.amount, timestamp, event.event_identifier)
        profit_loss = value - cost_basis
        
        return TaxableEvent(
            timestamp=timestamp,
            event_identifier=event.event_identifier,
            event_type='Withdrawal',
            asset_sold=event.asset.resolve().symbol_or_name(),
            amount_sold=event.amount,
            price_sold_eur=price,
            value_sold_eur=value,
            asset_received='',
            amount_received=None,
            price_received_eur=None,
            value_received_eur=None,
            is_fiat_received=False,
            fee_amount=None,
            fee_asset=None,
            fee_value_eur=None,
            cost_basis_eur=cost_basis,
            profit_loss_eur=profit_loss,
            location=event.location.serialize(),
        )
    
    def _add_to_cost_basis(self, asset: Asset, amount: FVal, price_eur: FVal, timestamp: Timestamp, event_id: str):
        """Add an acquisition to the cost basis."""
        self.cost_basis[asset].append((amount, price_eur, timestamp, event_id))
        log.info(f'Added {amount} {asset.resolve().symbol_or_name()} to cost basis at {price_eur} EUR/unit')
    
    def _process_disposal(self, asset: Asset, amount: FVal, timestamp: Timestamp, event_id: str) -> FVal:
        """Process a disposal using FIFO and return the cost basis."""
        remaining = amount
        total_cost_basis = ZERO
        
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
    
    def process_events(self) -> List[TaxableEvent]:
        """Process all events and return taxable events."""
        taxable_events = []
        
        with self.data.db.conn.read_ctx() as cursor:
            # Get ALL events to build proper cost basis
            all_events = self.dbevents.get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    from_ts=Timestamp(0),  # From beginning for cost basis
                    to_ts=END_TS,
                    order_by_rules=[('timestamp', True), ('sequence_index', True)],
                ),
                has_premium=True,
            )
        
        # Group events by identifier
        grouped_events = self._group_events_by_identifier(all_events)
        
        # Process each group chronologically
        sorted_groups = sorted(grouped_events.items(), key=lambda x: x[1][0].timestamp)
        
        for event_id, events in sorted_groups:
            # Skip events before tax year unless they affect cost basis
            first_ts = ts_ms_to_sec(events[0].timestamp)
            
            if len(events) > 1:
                # Multi-event transaction (likely a swap)
                taxable_event = self._process_swap(events)
                if taxable_event and first_ts >= START_TS:
                    taxable_events.append(taxable_event)
            else:
                # Single event
                event = events[0]
                
                # Skip spam
                if hasattr(event, 'asset') and event.asset.is_evm_token():
                    token = event.asset.resolve_to_evm_token()
                    if token.protocol == SPAM_PROTOCOL:
                        continue
                
                # Determine event type
                if event.event_type == HistoryEventType.DEPOSIT:
                    taxable_event = self._process_deposit(event)
                    if taxable_event and first_ts >= START_TS:
                        taxable_events.append(taxable_event)
                elif event.event_type == HistoryEventType.WITHDRAWAL:
                    taxable_event = self._process_withdrawal(event)
                    if taxable_event and first_ts >= START_TS:
                        taxable_events.append(taxable_event)
                elif event.event_type == HistoryEventType.TRADE:
                    # Single event trade (shouldn't happen normally)
                    log.warning(f'Found single event trade: {event.event_identifier}')
        
        return taxable_events
    
    def generate_report(self, taxable_events: List[TaxableEvent], output_file: str):
        """Generate CSV report from taxable events."""
        rows = []
        
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
        print(f"Ganancias totales: {total_profit:.2f} EUR")
        print(f"Perdidas totales: {total_loss:.2f} EUR")
        print(f"Ganancia/Perdida neta: {net_profit_loss:.2f} EUR")
        
        # Save to CSV
        df.write_csv(output_file, separator=';')
        print(f"\nReporte guardado en: {output_file}")
        
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
    taxable_events = processor.process_events()
    
    # Generate report
    output_file = "hacienda/eventos_fiscales_2024.csv"
    processor.generate_report(taxable_events, output_file)


if __name__ == "__main__":
    main()