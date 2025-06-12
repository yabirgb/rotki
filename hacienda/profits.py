from gevent import monkey
monkey.patch_all()  # isort:skip

from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntry, HistoryEvent

from rotkehlchen.constants.misc import ZERO
from rotkehlchen.errors.price import NoPriceForGivenTimestamp
from rotkehlchen.history.types import HistoricalPriceOracle, HistoricalPriceOracleInstance
from rotkehlchen.logging import TRACE, add_logging_level, configure_logging
from rotkehlchen.tests.utils.args import default_args

add_logging_level('TRACE', TRACE)
configure_logging(default_args(loglevel='info'))

import json
import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, TypedDict
from pathlib import Path

import polars as pl

from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.types import HistoryEventType, HistoryEventSubType, EventDirection  # isort:skip
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.aggregator import ChainsAggregator
from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
from rotkehlchen.chain.evm.nodes import populate_rpc_nodes_in_database
from rotkehlchen.chain.evm.types import string_to_evm_address, EvmAccount
from rotkehlchen.config import default_data_directory
from rotkehlchen.constants.assets import A_EUR, A_USD
from rotkehlchen.data_handler import DataHandler
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.filtering import EvmEventFilterQuery, EvmTransactionsFilterQuery, HistoryEventFilterQuery
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.tests.utils.ethereum import wait_until_all_nodes_connected
from rotkehlchen.types import ChainID, EvmTransaction, EVMTxHash, EVM_CHAINS_WITH_TRANSACTIONS, Location, SupportedBlockchain, Timestamp, SPAM_PROTOCOL
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import timestamp_to_iso8601, ts_ms_to_sec, ts_now

from rotkehlchen.externalapis.alchemy import Alchemy
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.externalapis.defillama import Defillama
from rotkehlchen.chain.ethereum.oracles.uniswap import UniswapV2Oracle, UniswapV3Oracle
from rotkehlchen.globaldb.manual_price_oracles import ManualCurrentOracle
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
from rotkehlchen.chain.substrate.manager import SubstrateManager
from rotkehlchen.chain.substrate.utils import (
    KUSAMA_NODES_TO_CONNECT_AT_START,
    POLKADOT_NODES_TO_CONNECT_AT_START,
)
from rotkehlchen.chain.zksync_lite.manager import ZksyncLiteManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
# some initialization code



logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

start_ts, end_ts = Timestamp(1704067200), Timestamp(1735689599)

msg_aggregator = MessagesAggregator()
greenlet_manager = GreenletManager(msg_aggregator)
data_dir = Path(f'/Users/yabirgb/Library/Application Support/rotki/data')
globaldb = GlobalDBHandler(
    data_dir=data_dir,
    sql_vm_instructions_cb=0,
    perform_assets_updates=False,
    msg_aggregator=msg_aggregator,
)


# initializing user DB
username = 'yabirgb'
password = '}~%-F9qs"TYQH$\/\lg-<:.XHev?=W'
data = DataHandler(data_dir, msg_aggregator, 0)
data.unlock(
    username=username,
    password=password,
    create_new=False,
    resume_from_backup=False,
)
dbevents = DBHistoryEvents(data.db)


cryptocompare = Cryptocompare(database=data.db)
coingecko = Coingecko(database=data.db)
defillama = Defillama(database=data.db)
alchemy = Alchemy(database=data.db)


inquirer = Inquirer(
    data_dir=data_dir,
    cryptocompare=cryptocompare,
    coingecko=coingecko,
    defillama=defillama,
    alchemy=alchemy,
    manualcurrent=ManualCurrentOracle(),
    msg_aggregator=msg_aggregator,
)

etherscan = Etherscan(
    database=data.db,
    msg_aggregator=data.db.msg_aggregator,
)
beaconchain = BeaconChain(database=data.db, msg_aggregator=msg_aggregator)



# EVM_CHAINS_WITH_TRANSACTIONS_TYPE = Literal[
#     SupportedBlockchain.ETHEREUM,
#     SupportedBlockchain.OPTIMISM,
#     SupportedBlockchain.POLYGON_POS,
#     SupportedBlockchain.ARBITRUM_ONE,
#     SupportedBlockchain.BASE,
#     SupportedBlockchain.GNOSIS,
#     SupportedBlockchain.SCROLL,
#     SupportedBlockchain.BINANCE_SC,
# ]

chain_managers = [
    EthereumManager(
        node_inquirer=(ethereum_inquirer := EthereumInquirer(
            greenlet_manager=greenlet_manager,
            database=data.db,
            etherscan=etherscan,
        )),
        beacon_chain=beaconchain,
    ),
    OptimismManager(OptimismInquirer(
        greenlet_manager=greenlet_manager,
        database=data.db,
        etherscan=etherscan,
    )),
    PolygonPOSManager(PolygonPOSInquirer(
        greenlet_manager=greenlet_manager,
        database=data.db,
        etherscan=etherscan,
    )),
    ArbitrumOneManager(ArbitrumOneInquirer(
        greenlet_manager=greenlet_manager,
        database=data.db,
        etherscan=etherscan,
    )),
    BaseManager(BaseInquirer(
        greenlet_manager=greenlet_manager,
        database=data.db,
        etherscan=etherscan,
    )),
    GnosisManager(GnosisInquirer(
        greenlet_manager=greenlet_manager,
        database=data.db,
        etherscan=etherscan,
    )),
    ScrollManager(ScrollInquirer(
        greenlet_manager=greenlet_manager,
        database=data.db,
        etherscan=etherscan,
    )),
    BinanceSCManager(BinanceSCInquirer(
        greenlet_manager=greenlet_manager,
        database=data.db,
        etherscan=etherscan,
    ))
]

inquirer.inject_evm_managers([
    (chain.to_chain_id(), manager)
    for chain, manager in zip(EVM_CHAINS_WITH_TRANSACTIONS, chain_managers)
])

price_historian = PriceHistorian(  # Initialize the price historian singleton
    data_directory=data_dir,
    cryptocompare=cryptocompare,
    coingecko=coingecko,
    defillama=defillama,
    alchemy=alchemy,
    uniswapv2=(uniswap_v2_oracle := UniswapV2Oracle()),
    uniswapv3=(uniswap_v3_oracle := UniswapV3Oracle()),
)
price_historian.set_oracles_order([HistoricalPriceOracle.DEFILLAMA, HistoricalPriceOracle.CRYPTOCOMPARE, HistoricalPriceOracle.ALCHEMY])


PRICES = {
    ('eip155:1/erc20:0xec53bF9167f50cDEB3Ae105f56099aaaB9061F83', 1715363603): ZERO
}

def query_price(
    from_asset: Asset,
    timestamp: Timestamp,
):
    if (price := PRICES.get((from_asset, timestamp))):
        return price

    log.debug(f'Querying price for {from_asset}')
    return PriceHistorian.query_historical_price(from_asset=from_asset, to_asset=A_EUR, timestamp=timestamp)


def query_airdrops():
    with data.db.conn.read_ctx() as cursor:
        airdrop_events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                event_subtypes=[HistoryEventSubType.AIRDROP],
                from_ts=start_ts,
                to_ts=end_ts,
            ),
            has_premium=True,
        )

        columns = ('activo', 'fecha', 'cantidad', 'precio al momento de adquisicion', 'valor')
        rows = []
        for entry in airdrop_events:
            asset = entry.asset.resolve()
            ts = ts_ms_to_sec(entry.timestamp)
            try:
                price = query_price(entry.asset, ts)
            except NoPriceForGivenTimestamp:
                price = ZERO
                print(entry.timestamp, asset)
            rows.append([asset.symbol_or_name(), timestamp_to_iso8601(ts), entry.amount, price, entry.amount * price])

        airdrop_df = pl.DataFrame(rows, columns)

    print(airdrop_df)
    print(f'total : {airdrop_df["valor"].sum()}')
    airdrop_df.write_csv(
        "hacienda/airdrops.csv",
        separator=";",
        include_header=True,
    )

def staking_rewards():
    # count staking rewards from kraken
    with data.db.conn.read_ctx() as cursor:
        kraken_events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                type_and_subtype_combinations=[(HistoryEventType.STAKING, HistoryEventSubType.REWARD)],
                location=Location.KRAKEN,
                from_ts=start_ts,
                to_ts=end_ts,
            ),
            has_premium=True,
        )

        gnosis_staking = dbevents.get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                location=Location.GNOSIS,
                from_ts=start_ts,
                to_ts=end_ts,
                event_types=[HistoryEventType.RECEIVE],
                addresses=[string_to_evm_address('0x0B98057eA310F4d31F2a452B414647007d1645d9')],
            ),
            has_premium=True,
        )

        columns = ('activo', 'fecha', 'lugar', 'cantidad', 'precio al momento de adquisicion', 'valor', 'identificador')
        rows = []

        for entry in kraken_events + gnosis_staking:
            if entry.asset.identifier == 'eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb' and entry.amount > FVal('0.5'):
                # skip withdrawals
                continue

            asset = entry.asset.resolve()
            ts = ts_ms_to_sec(entry.timestamp)
            try:
                price = query_price(entry.asset, ts)
            except NoPriceForGivenTimestamp:
                price = ZERO
                print(entry.timestamp, asset)
            rows.append([
                asset.symbol_or_name(),
                timestamp_to_iso8601(ts),
                entry.location.serialize(),
                entry.amount,
                price,
                entry.amount * price,
                entry.event_identifier,
            ])

        staking_rewards = pl.DataFrame(rows, columns)
        print(f'total : {staking_rewards["valor"].sum()}')
        print(f'cantidad : {staking_rewards.group_by("activo").sum()["activo", "cantidad"]}')
        staking_rewards.write_csv(
            "hacienda/staking.csv",
            separator=";",
            include_header=True,
        )


def process_events(events: list[HistoryBaseEntry], include_counterparty: bool = False):
    if include_counterparty:
        columns = ('activo', 'fecha', 'lugar', 'cantidad', 'precio al momento de adquisicion', 'valor', 'protocolo', 'identificador')
    else:
        columns = ('activo', 'fecha', 'lugar', 'cantidad', 'precio al momento de adquisicion', 'valor', 'identificador')

    rows = []

    for entry in events:
        asset = entry.asset.resolve()
        ts = ts_ms_to_sec(entry.timestamp)
        try:
            price = query_price(entry.asset, ts)
        except NoPriceForGivenTimestamp:
            price = ZERO
            print(entry.timestamp, asset)

        if include_counterparty:
            rows.append([
                asset.symbol_or_name(),
                timestamp_to_iso8601(ts),
                entry.location.serialize(),
                entry.amount,
                price,
                entry.amount * price,
                entry.counterparty,
                entry.event_identifier,
            ])

        else:

            rows.append([
                asset.symbol_or_name(),
                timestamp_to_iso8601(ts),
                entry.location.serialize(),
                entry.amount,
                price,
                entry.amount * price,
                entry.event_identifier,
            ])

    return pl.DataFrame(rows, columns)


def cashbacks():
    # count staking rewards from kraken
    with data.db.conn.read_ctx() as cursor:
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                type_and_subtype_combinations=[(HistoryEventType.RECEIVE, HistoryEventSubType.CASHBACK)],
                from_ts=start_ts,
                to_ts=end_ts,
            ),
            has_premium=True,
        )

        cashbacks = process_events(events)

        print(f'total : {cashbacks["valor"].sum()}')
        print(f'cantidad : {cashbacks.group_by("activo").sum()["activo", "cantidad"]}')
        cashbacks.write_csv(
            "hacienda/cashbacks.csv",
            separator=";",
            include_header=True,
        )


def rewards():
    # count staking rewards from kraken
    with data.db.conn.read_ctx() as cursor:
        events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                type_and_subtype_combinations=[(HistoryEventType.RECEIVE, HistoryEventSubType.REWARD)],
                from_ts=start_ts,
                to_ts=end_ts,
            ),
            has_premium=True,
        )

        df = process_events(events, include_counterparty=True)

        print(f'total : {df["valor"].sum()}')
        print(f'cantidad : {df.group_by("activo").sum()["activo", "cantidad"]}')
        df.write_csv(
            "hacienda/rewards.csv",
            separator=";",
            include_header=True,
        )


from typing import NamedTuple
from collections import deque


class FIFOCostBasis(NamedTuple):
    acquisition_date: datetime
    acquisition_timestamp: Timestamp
    amount: FVal
    price_eur: FVal
    total_value_eur: FVal
    event_identifier: str


class TaxableEvent(NamedTuple):
    asset: str
    acquisition_date: str
    acquisition_value: FVal
    acquisition_event_id: str
    disposal_date: str
    disposal_value: FVal
    disposal_event_id: str
    amount: FVal
    profit_loss: FVal


from typing import Iterator


def group_events_by_identifier(events: List[HistoryBaseEntry]) -> Dict[str, List[HistoryBaseEntry]]:
    """Group events by their event_identifier."""
    grouped = defaultdict(list)
    for event in events:
        if event.event_identifier:
            grouped[event.event_identifier].append(event)

    # Sort events within each group by sequence_index if available
    for event_id, event_list in grouped.items():
        event_list.sort(key=lambda e: getattr(e, 'sequence_index', 0))

    return grouped


def process_swap_group(events: List[HistoryBaseEntry], asset_queues: Dict[Asset, deque[FIFOCostBasis]], taxable_events: List[TaxableEvent]):
    """Process a group of events that form a swap transaction."""
    # Sort events by sequence_index
    events.sort(key=lambda e: getattr(e, 'sequence_index', 0))

    # Separate events by type
    out_events = []  # Assets being spent
    in_events = []   # Assets being received
    fee_events = []  # Fee payments

    for event in events:
        # Skip spam assets
        if hasattr(event, 'asset') and event.asset.is_evm_token() and event.asset.resolve_to_evm_token().protocol == SPAM_PROTOCOL:
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

    # Process the swap
    # First process all OUT events (disposals)
    for out_event in out_events:
        process_disposal(out_event, asset_queues, taxable_events)

    # Process fee events
    for fee_event in fee_events:
        process_disposal(fee_event, asset_queues, taxable_events)

    # Then process all IN events (acquisitions)
    for in_event in in_events:
        process_acquisition(in_event, asset_queues)


def process_acquisition(event: HistoryBaseEntry, asset_queues: Dict[Asset, deque[FIFOCostBasis]]):
    """Process an acquisition event."""
    ts = ts_ms_to_sec(event.timestamp)

    try:
        price_eur = query_price(event.asset, ts)
    except NoPriceForGivenTimestamp:
        price_eur = ZERO
        log.warning(f'No price found for {event.asset} at {ts}')

    total_value = event.amount * price_eur

    cost_basis = FIFOCostBasis(
        acquisition_date=datetime.fromtimestamp(ts),
        acquisition_timestamp=ts,
        amount=event.amount,
        price_eur=price_eur,
        total_value_eur=total_value,
        event_identifier=event.event_identifier,
    )

    asset_queues[event.asset].append(cost_basis)
    log.info(f'>>> Added {event.amount} {event.asset.resolve().symbol_or_name()} to cost basis at {price_eur} EUR/unit')


def process_disposal(event: HistoryBaseEntry, asset_queues: Dict[Asset, deque[FIFOCostBasis]], taxable_events: List[TaxableEvent]):
    """Process a disposal event."""
    ts = ts_ms_to_sec(event.timestamp)
    remaining_to_sell = event.amount

    try:
        disposal_price = query_price(event.asset, ts)
    except NoPriceForGivenTimestamp:
        disposal_price = ZERO
        log.warning(f'No price found for {event.asset} at {ts}')

    # Process FIFO queue for this asset
    while remaining_to_sell > ZERO and len(asset_queues[event.asset]) > 0:
        # Safely get the oldest lot
        try:
            oldest_lot = asset_queues[event.asset][0]
        except IndexError:
            break

        if oldest_lot.amount <= remaining_to_sell:
            # Use entire lot
            amount_from_lot = oldest_lot.amount
            asset_queues[event.asset].popleft()
        else:
            # Use partial lot
            amount_from_lot = remaining_to_sell
            # Update the remaining amount in the lot
            updated_lot = FIFOCostBasis(
                acquisition_date=oldest_lot.acquisition_date,
                acquisition_timestamp=oldest_lot.acquisition_timestamp,
                amount=oldest_lot.amount - amount_from_lot,
                price_eur=oldest_lot.price_eur,
                total_value_eur=oldest_lot.total_value_eur * (oldest_lot.amount - amount_from_lot) / oldest_lot.amount,
                event_identifier=oldest_lot.event_identifier,
            )
            # Remove old lot and append updated one
            asset_queues[event.asset].popleft()
            asset_queues[event.asset].appendleft(updated_lot)

        # Only record taxable events if the disposal is within the reporting period
        if ts >= start_ts:
            # Calculate profit/loss for this portion
            acquisition_value = amount_from_lot * oldest_lot.price_eur
            disposal_value = amount_from_lot * disposal_price
            profit_loss = disposal_value - acquisition_value

            taxable_event = TaxableEvent(
                asset=event.asset.resolve().symbol_or_name(),
                acquisition_date=timestamp_to_iso8601(oldest_lot.acquisition_timestamp),
                acquisition_value=acquisition_value,
                acquisition_event_id=oldest_lot.event_identifier,
                disposal_date=timestamp_to_iso8601(ts),
                disposal_value=disposal_value,
                disposal_event_id=event.event_identifier,
                amount=amount_from_lot,
                profit_loss=profit_loss,
            )

            taxable_events.append(taxable_event)

            log.info(
                f'>>> Sold {amount_from_lot} {event.asset.resolve().symbol_or_name()} '
                f'bought at {oldest_lot.price_eur} EUR, sold at {disposal_price} EUR, '
                f'profit/loss: {profit_loss} EUR'
            )

        remaining_to_sell -= amount_from_lot

    if remaining_to_sell > ZERO:
        # We don't have enough cost basis
        log.warning(
            f'Insufficient cost basis for {event.asset.resolve().symbol_or_name()}. '
            f'Missing {remaining_to_sell} units for event {event.event_identifier}'
        )

        # Only record if within reporting period
        if ts >= start_ts:
            disposal_value = remaining_to_sell * disposal_price
            taxable_event = TaxableEvent(
                asset=event.asset.resolve().symbol_or_name(),
                acquisition_date='Unknown',
                acquisition_value=ZERO,
                acquisition_event_id='Unknown',
                disposal_date=timestamp_to_iso8601(ts),
                disposal_value=disposal_value,
                disposal_event_id=event.event_identifier,
                amount=remaining_to_sell,
                profit_loss=disposal_value,
            )
            taxable_events.append(taxable_event)


def process_fifo_trades():
    """
    Process all crypto events using FIFO methodology for Spanish tax reporting.

    Returns a list of TaxableEvent with columns:
    - asset: Asset identifier
    - acquisition_date: Date when asset was acquired
    - acquisition_value: Value in EUR when buying
    - acquisition_event_id: Transaction identifier for acquisition
    - disposal_date: Date when asset was sold
    - disposal_value: Value in EUR when selling
    - disposal_event_id: Transaction identifier for disposal
    - amount: Amount of asset traded
    - profit_loss: Profit or loss from the trade
    """
    # Dictionary to store FIFO queues for each asset
    asset_queues: Dict[Asset, deque[FIFOCostBasis]] = defaultdict(deque)
    taxable_events: List[TaxableEvent] = []

    with data.db.conn.read_ctx() as cursor:
        # Get ALL history events from the beginning to build correct cost basis
        all_events = dbevents.get_history_events(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(
                from_ts=Timestamp(0),  # Start from the beginning for correct cost basis
                to_ts=end_ts,
                order_by_rules=[('timestamp', True), ('sequence_index', True)],  # Sort by timestamp then sequence
            ),
            has_premium=True,
        )

    # Group events by event_identifier
    events_by_id = group_events_by_identifier(all_events)

    # Process events chronologically
    # Create a timeline of event groups and single events
    timeline = []

    # Add all grouped events (swaps)
    for event_id, event_group in events_by_id.items():
        # Use the timestamp of the first event in the group
        first_event_ts = min(e.timestamp for e in event_group)
        timeline.append((first_event_ts, event_id, event_group))

    # Add standalone events (those without event_identifier)
    for event in all_events:
        if not event.event_identifier:
            timeline.append((event.timestamp, None, [event]))

    # Sort timeline by timestamp
    timeline.sort(key=lambda x: x[0])

    # Process each entry in chronological order
    processed_event_ids = set()

    for ts, event_id, events in timeline:
        # Skip if we already processed this event group
        if event_id and event_id in processed_event_ids:
            continue

        if event_id:
            processed_event_ids.add(event_id)

        if len(events) > 1:
            # Process as a swap group
            process_swap_group(events, asset_queues, taxable_events)
        else:
            # Process as a single event
            event = events[0]

            # Skip events with spam assets
            if hasattr(event, 'asset') and event.asset.is_evm_token() and event.asset.resolve_to_evm_token().protocol == SPAM_PROTOCOL:
                log.debug(f'Skipping spam asset: {event.asset.resolve().symbol_or_name()}')
                continue

            # Get event direction
            direction = event.maybe_get_direction()

            # Skip informational events
            if direction is None or direction == EventDirection.NEUTRAL:
                continue

            # Skip transfers
            if hasattr(event, 'event_subtype') and event.event_subtype == HistoryEventSubType.TRANSFER:
                continue

            # Process based on direction
            if direction == EventDirection.IN:
                process_acquisition(event, asset_queues)
            elif direction == EventDirection.OUT:
                # Check if it's a fee
                if hasattr(event, 'event_subtype') and event.event_subtype == HistoryEventSubType.FEE:
                    # Fees are taxable disposals
                    process_disposal(event, asset_queues, taxable_events)
                else:
                    # Regular disposal
                    process_disposal(event, asset_queues, taxable_events)

    return taxable_events


# Example usage:
# taxable_events = process_fifo_trades()
# for event in taxable_events:
#     print(f"{event.asset}: {event.profit_loss} EUR profit/loss")

process_fifo_trades()
