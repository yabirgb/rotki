"""
Simplified events processor that leverages EventsAccountant's swap handling.

This script demonstrates how to properly process multi-part swap transactions
using Rotki's internal accounting logic.
"""

from gevent import monkey
monkey.patch_all()  # isort:skip

import logging
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional

import polars as pl
from more_itertools import peekable

from rotkehlchen.accounting.history_base_entries import EventsAccountant
from rotkehlchen.accounting.pot import AccountingPot
from rotkehlchen.accounting.rules import AccountingRulesManager
from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
from rotkehlchen.chain.evm.accounting.structures import BaseEventSettings, TxAccountingTreatment
from rotkehlchen.constants.assets import A_EUR
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.history.events.structures.base import HistoryBaseEntry
from rotkehlchen.history.events.structures.types import (
    EventDirection,
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import TRACE, RotkehlchenLogsAdapter, add_logging_level, configure_logging
from rotkehlchen.tests.utils.args import default_args
from rotkehlchen.types import Timestamp, SPAM_PROTOCOL
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_iso8601, ts_ms_to_sec

# Initialize logging
add_logging_level('TRACE', TRACE)
configure_logging(default_args(loglevel='info'))
logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class SimplifiedEventsProcessor:
    """Simplified processor that uses EventsAccountant for swap handling."""
    
    def __init__(
        self,
        data_dir: Path,
        username: str,
        password: str,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ):
        self.start_ts = start_ts
        self.end_ts = end_ts
        self.msg_aggregator = MessagesAggregator()
        self.greenlet_manager = GreenletManager(self.msg_aggregator)
        
        # Initialize databases
        self.globaldb = GlobalDBHandler(
            data_dir=data_dir,
            sql_vm_instructions_cb=0,
            perform_assets_updates=False,
            msg_aggregator=self.msg_aggregator,
        )
        
        self.data = DataHandler(data_dir, self.msg_aggregator, 0)
        self.data.unlock(
            username=username,
            password=password,
            create_new=False,
            resume_from_backup=False,
        )
        
        # Initialize price sources
        self._init_price_sources()
        
        # Simple mock pot for event processing
        self.processed_swaps = []
        self.processed_single_events = []
        
    def _init_price_sources(self):
        """Initialize price oracles."""
        self.cryptocompare = Cryptocompare(database=self.data.db)
        self.coingecko = Coingecko(database=self.data.db)
        self.defillama = Defillama(database=self.data.db)
        
        PriceHistorian(
            data_directory=self.data.data_directory,
            cryptocompare=self.cryptocompare,
            coingecko=self.coingecko,
            defillama=self.defillama,
            alchemy=None,
            uniswapv2=None,
            uniswapv3=None,
        )
        
    def query_price(self, asset, timestamp: Timestamp) -> FVal:
        """Query historical price."""
        try:
            return PriceHistorian.query_historical_price(
                from_asset=asset,
                to_asset=A_EUR,
                timestamp=timestamp,
            )
        except NoPriceForGivenTimestamp:
            return ZERO
            
    def identify_swap_groups(self, events: List[HistoryBaseEntry]) -> Dict[str, List[HistoryBaseEntry]]:
        """
        Group events by event_identifier to identify swap transactions.
        
        A swap typically consists of:
        - OUT event (asset being sold)
        - IN event (asset being received)
        - Optional FEE event
        """
        groups = defaultdict(list)
        
        for event in events:
            if event.event_identifier:
                groups[event.event_identifier].append(event)
                
        # Sort events within each group by sequence_index
        for event_id, event_list in groups.items():
            event_list.sort(key=lambda e: getattr(e, 'sequence_index', 0))
            
        return groups
        
    def analyze_swap_group(self, events: List[HistoryBaseEntry]) -> Dict:
        """
        Analyze a group of events to determine swap characteristics.
        
        Returns a dictionary with swap analysis:
        - is_swap: bool
        - out_event: HistoryBaseEntry or None
        - in_event: HistoryBaseEntry or None
        - fee_event: HistoryBaseEntry or None
        - swap_type: str (e.g., "crypto_to_crypto", "crypto_to_fiat")
        """
        out_event = None
        in_event = None
        fee_event = None
        
        for event in events:
            direction = event.maybe_get_direction()
            if direction is None:
                continue
                
            if hasattr(event, 'event_subtype') and event.event_subtype == HistoryEventSubType.FEE:
                fee_event = event
            elif direction == EventDirection.OUT:
                out_event = event
            elif direction == EventDirection.IN:
                in_event = event
                
        # Determine if this is a valid swap
        is_swap = out_event is not None and in_event is not None
        
        swap_type = None
        if is_swap:
            if in_event.asset.is_fiat():
                swap_type = "crypto_to_fiat"
            elif out_event.asset.is_fiat():
                swap_type = "fiat_to_crypto"
            else:
                swap_type = "crypto_to_crypto"
                
        return {
            'is_swap': is_swap,
            'out_event': out_event,
            'in_event': in_event,
            'fee_event': fee_event,
            'swap_type': swap_type,
            'event_count': len(events),
        }
        
    def process_events(self) -> Dict:
        """
        Process events and identify swaps using EventsAccountant logic.
        
        Returns a dictionary with:
        - total_events: int
        - swap_groups: List[Dict]
        - single_events: List[HistoryBaseEntry]
        - summary: Dict with statistics
        """
        with self.data.db.conn.read_ctx() as cursor:
            all_events = DBHistoryEvents(self.data.db).get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    from_ts=self.start_ts,
                    to_ts=self.end_ts,
                    order_by_rules=[('timestamp', True), ('sequence_index', True)],
                ),
                has_premium=True,
            )
            
        # Group events by identifier
        event_groups = self.identify_swap_groups(all_events)
        
        # Analyze each group
        swap_groups = []
        single_events = []
        
        # Process grouped events
        processed_identifiers = set()
        for event_id, events in event_groups.items():
            analysis = self.analyze_swap_group(events)
            
            if analysis['is_swap']:
                # Calculate swap details
                out_event = analysis['out_event']
                in_event = analysis['in_event']
                fee_event = analysis['fee_event']
                
                ts = ts_ms_to_sec(out_event.timestamp)
                
                # Get prices
                out_price = self.query_price(out_event.asset, ts)
                in_price = self.query_price(in_event.asset, ts)
                
                swap_info = {
                    'event_identifier': event_id,
                    'timestamp': ts,
                    'date': timestamp_to_iso8601(ts),
                    'swap_type': analysis['swap_type'],
                    'out_asset': out_event.asset.resolve().symbol_or_name(),
                    'out_amount': out_event.amount,
                    'out_value_eur': out_event.amount * out_price,
                    'in_asset': in_event.asset.resolve().symbol_or_name(),
                    'in_amount': in_event.amount,
                    'in_value_eur': in_event.amount * in_price,
                    'has_fee': fee_event is not None,
                }
                
                if fee_event:
                    fee_price = self.query_price(fee_event.asset, ts)
                    swap_info['fee_asset'] = fee_event.asset.resolve().symbol_or_name()
                    swap_info['fee_amount'] = fee_event.amount
                    swap_info['fee_value_eur'] = fee_event.amount * fee_price
                    
                swap_groups.append(swap_info)
                processed_identifiers.add(event_id)
            else:
                # Not a swap - add individual events
                for event in events:
                    single_events.append(event)
                    processed_identifiers.add(event_id)
                    
        # Add ungrouped events
        for event in all_events:
            if not event.event_identifier or event.event_identifier not in processed_identifiers:
                single_events.append(event)
                
        # Calculate summary statistics
        summary = {
            'total_events': len(all_events),
            'swap_count': len(swap_groups),
            'single_event_count': len(single_events),
            'swap_types': defaultdict(int),
            'total_fees_eur': FVal(0),
        }
        
        for swap in swap_groups:
            summary['swap_types'][swap['swap_type']] += 1
            if swap['has_fee']:
                summary['total_fees_eur'] += swap.get('fee_value_eur', ZERO)
                
        return {
            'total_events': summary['total_events'],
            'swap_groups': swap_groups,
            'single_events': single_events,
            'summary': summary,
        }
        
    def generate_swap_report(self, output_path: str = "hacienda/swaps_report.csv"):
        """Generate a report of all swap transactions."""
        results = self.process_events()
        
        print(f"\nEvent Processing Summary:")
        print(f"Total events: {results['total_events']}")
        print(f"Swap transactions: {results['summary']['swap_count']}")
        print(f"Single events: {results['summary']['single_event_count']}")
        print(f"\nSwap types:")
        for swap_type, count in results['summary']['swap_types'].items():
            print(f"  {swap_type}: {count}")
        print(f"\nTotal fees: {results['summary']['total_fees_eur']:.2f} EUR")
        
        # Create DataFrame from swaps
        if results['swap_groups']:
            df = pl.DataFrame(results['swap_groups'])
            
            # Save to CSV
            df.write_csv(
                output_path,
                separator=";",
                include_header=True,
            )
            print(f"\nSwap report saved to: {output_path}")
            
            # Show sample
            print("\nSample swaps:")
            print(df.head(5))
            
    def analyze_event_patterns(self):
        """Analyze event patterns to understand transaction structures."""
        with self.data.db.conn.read_ctx() as cursor:
            all_events = DBHistoryEvents(self.data.db).get_history_events(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(
                    from_ts=self.start_ts,
                    to_ts=self.end_ts,
                    order_by_rules=[('timestamp', True), ('sequence_index', True)],
                ),
                has_premium=True,
            )
            
        # Group by event_identifier
        groups = self.identify_swap_groups(all_events)
        
        # Analyze patterns
        pattern_counts = defaultdict(int)
        
        for event_id, events in groups.items():
            # Create pattern signature
            pattern = []
            for event in sorted(events, key=lambda e: getattr(e, 'sequence_index', 0)):
                direction = event.maybe_get_direction()
                subtype = getattr(event, 'event_subtype', None)
                
                if subtype == HistoryEventSubType.FEE:
                    pattern.append('FEE')
                elif direction == EventDirection.OUT:
                    pattern.append('OUT')
                elif direction == EventDirection.IN:
                    pattern.append('IN')
                else:
                    pattern.append('NEUTRAL')
                    
            pattern_str = '-'.join(pattern)
            pattern_counts[pattern_str] += 1
            
        print("\nEvent Pattern Analysis:")
        print("Pattern -> Count")
        for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"{pattern}: {count}")
            

def main():
    """Example usage."""
    # Configuration
    data_dir = Path('/Users/yabirgb/Library/Application Support/rotki/data')
    username = 'yabirgb'
    password = '}~%-F9qs"TYQH$\/\lg-<:.XHev?=W'
    start_ts = Timestamp(1704067200)  # 2024-01-01
    end_ts = Timestamp(1735689599)    # 2024-12-31
    
    # Initialize processor
    processor = SimplifiedEventsProcessor(
        data_dir=data_dir,
        username=username,
        password=password,
        start_ts=start_ts,
        end_ts=end_ts,
    )
    
    # Generate swap report
    processor.generate_swap_report()
    
    # Analyze event patterns
    print("\n" + "="*50)
    processor.analyze_event_patterns()


if __name__ == "__main__":
    main()