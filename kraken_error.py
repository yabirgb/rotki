from pathlib import Path

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.exchanges.bitpanda import Bitpanda
from rotkehlchen.externalapis.coingecko import Coingecko
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.globaldb import GlobalDBHandler
from rotkehlchen.history.price import PriceHistorian
from rotkehlchen.history.typing import DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER
from rotkehlchen.inquirer import DEFAULT_CURRENT_PRICE_ORACLES_ORDER, Inquirer
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.exchanges.kraken import Kraken
from rotkehlchen.typing import Location

data_dir = Path('/home/yabirgb/.local/share/rotki/data')
GlobalDBHandler(data_dir=data_dir)

from rotkehlchen.constants.assets import A_ETH, A_BTC
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.exchanges import check_saved_events_for_exchange
from rotkehlchen.tests.utils.exchanges import create_test_binance, create_test_poloniex, create_test_kraken
from rotkehlchen.typing import (
    Location,
    AssetAmount,
    Fee,
    Price,
    Timestamp,
    TradeType,
)

# initialize the price historian singleton
msg_aggregator = MessagesAggregator()

username = 'yabirgb'
db = DBHandler(
    user_data_dir=data_dir / username,
    password='',
    msg_aggregator=msg_aggregator,
    initial_settings=None,
)

cryptocompare = Cryptocompare(data_directory=data_dir, database=db)
coingecko = Coingecko()
price_historian = PriceHistorian(
    data_directory=data_dir,
    cryptocompare=cryptocompare,
    coingecko=coingecko,
)
PriceHistorian().set_oracles_order(DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER)
inquirer = Inquirer(
    data_dir=data_dir,
    cryptocompare=cryptocompare,
    coingecko=coingecko,
)
Inquirer().set_oracles_order(DEFAULT_CURRENT_PRICE_ORACLES_ORDER)


kraken = Kraken(
    name='kraken',
    api_key='',
    secret=b'',
    database=db,
    msg_aggregator=msg_aggregator,
)

print(kraken.api_query('Ledgers'))
print(kraken.api_query('Staking/Transactions'))