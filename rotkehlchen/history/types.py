from typing import TYPE_CHECKING, NamedTuple, Tuple, Union

from rotkehlchen.assets.asset import Asset
from rotkehlchen.types import OracleSource, Price, Timestamp
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn

from .deserialization import deserialize_price

if TYPE_CHECKING:
    from rotkehlchen.externalapis.coingecko import Coingecko
    from rotkehlchen.externalapis.cryptocompare import Cryptocompare
    from rotkehlchen.externalapis.defillama import Defillama
    from rotkehlchen.globaldb.manual_price_oracles import ManualPriceOracle

HistoricalPriceOracleInstance = Union['Coingecko', 'Cryptocompare', 'ManualPriceOracle', 'Defillama']  # noqa: E501


class HistoricalPriceOracle(DBEnumMixIn, OracleSource):
    """Supported oracles for querying historical prices"""
    MANUAL = 1
    COINGECKO = 2
    CRYPTOCOMPARE = 3
    XRATESCOM = 4
    MANUAL_CURRENT = 5
    DEFILLAMA = 6


NOT_EXPOSED_SOURCES = (
    HistoricalPriceOracle.XRATESCOM,
)

DEFAULT_HISTORICAL_PRICE_ORACLES_ORDER = [
    HistoricalPriceOracle.MANUAL,
    HistoricalPriceOracle.CRYPTOCOMPARE,
    HistoricalPriceOracle.COINGECKO,
    HistoricalPriceOracle.DEFILLAMA,
]


class HistoricalPrice(NamedTuple):
    """A historical price entry"""
    from_asset: Asset
    to_asset: Asset
    source: HistoricalPriceOracle
    timestamp: Timestamp
    price: Price

    def __str__(self) -> str:
        return (
            f'Price entry {str(self.price)} of {self.from_asset} -> {self.to_asset} '
            f'at {self.timestamp} from {str(self.source)}'
        )

    def serialize_for_db(self) -> Tuple[str, str, str, int, str]:
        return (
            self.from_asset.identifier,
            self.to_asset.identifier,
            self.source.serialize_for_db(),
            self.timestamp,
            str(self.price),
        )

    @classmethod
    def deserialize_from_db(cls, value: Tuple[str, str, str, int, str]) -> 'HistoricalPrice':
        """Deserialize a HistoricalPrice entry from the DB.

        May raise:
        - DeserializationError
        - UnknownAsset
        """
        return cls(
            from_asset=Asset(value[0]).check_existence(),
            to_asset=Asset(value[1]).check_existence(),
            source=HistoricalPriceOracle.deserialize_from_db(value[2]),
            timestamp=Timestamp(value[3]),
            price=deserialize_price(value[4]),
        )
