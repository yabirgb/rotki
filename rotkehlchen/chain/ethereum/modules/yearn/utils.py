import logging

from rotkehlchen.constants.assets import A_USD
from rotkehlchen.assets.asset import Asset, EthereumToken
from rotkehlchen.chain.ethereum.modules.yearn.vaults import get_usd_price_zero_if_error
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.history.typing import HistoricalPrice, HistoricalPriceOracle
from rotkehlchen.history.price import query_usd_price_zero_if_error
from rotkehlchen.typing import Timestamp, Price
from rotkehlchen.user_messages import MessagesAggregator


log = logging.getLogger(__name__)


def get_usd_price_yearnv2_zero_if_error(
        asset: EthereumToken,
        time: Timestamp,
        price_per_share: int,
        location: str,
        msg_aggregator: MessagesAggregator,
) -> Price:
    # Query price in case we have it saved
    price = query_usd_price_zero_if_error(
        asset=asset,
        time=time,
        location=location,
        msg_aggregator=msg_aggregator,
    )
    # If not use the price_per_share provided
    if price == ZERO:
        maybe_underlying_token = GlobalDBHandler().fetch_underlying_tokens(asset.ethereum_address)
        if maybe_underlying_token is None or len(maybe_underlying_token) != 1:
            log.error(f'Yearn vault token {asset} without an underlying asset')
            return Price(ZERO)
        underlying_token = EthereumToken(maybe_underlying_token[0].address)
        underlying_token_price = Inquirer().find_usd_price(underlying_token)
        if underlying_token != ZERO:
            price = Price(price_per_share * 10**-asset.decimals * underlying_token_price)
            # Now that we have a price lets save it
            historical_price = HistoricalPrice(
                from_asset=asset,
                to_asset=A_USD,
                source=HistoricalPriceOracle.MANUAL,
                timestamp=time,
                price=price,
            )
            GlobalDBHandler().add_single_historical_price(historical_price)
            return price
    # This will return ZERO also if we failed to calculate price with the undelying asset
    return price
