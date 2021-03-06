from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors import DeserializationError
from rotkehlchen.history.deserialization import deserialize_price
from rotkehlchen.serialization.deserialize import (
    deserialize_asset_amount,
    deserialize_location_from_db,
    deserialize_optional,
    deserialize_timestamp,
)
from rotkehlchen.typing import AssetAmount, Location, Price, Timestamp, Tuple


class LedgerActionType(Enum):
    INCOME = 1
    EXPENSE = 2
    LOSS = 3
    DIVIDENDS_INCOME = 4
    DONATION_RECEIVED = 5
    AIRDROP = 6
    GIFT = 7
    GRANT = 8

    def serialize(self) -> str:
        return str(self)

    def __str__(self) -> str:
        if self == LedgerActionType.INCOME:
            return 'income'
        if self == LedgerActionType.EXPENSE:
            return 'expense'
        if self == LedgerActionType.LOSS:
            return 'loss'
        if self == LedgerActionType.DIVIDENDS_INCOME:
            return 'dividends income'
        if self == LedgerActionType.DONATION_RECEIVED:
            return 'donation received'
        if self == LedgerActionType.AIRDROP:
            return 'airdrop'
        if self == LedgerActionType.GIFT:
            return 'gift'
        if self == LedgerActionType.GRANT:
            return 'grant'

        # else
        raise RuntimeError(f'Corrupt value {self} for LedgerActionType -- Should never happen')

    @classmethod
    def deserialize(cls, symbol: str) -> 'LedgerActionType':
        """Takes a string and attempts to turn it into a LedgerActionType

        Can throw DeserializationError if the symbol is not as expected
        """
        if not isinstance(symbol, str):
            raise DeserializationError(
                f'Failed to deserialize ledger action type symbol from {type(symbol)} entry',
            )

        value = LEDGER_ACTION_TYPE_MAPPING.get(symbol, None)
        if value is None:
            raise DeserializationError(
                f'Failed to deserialize ledger action symbol. Unknown symbol '
                f'{symbol} for ledger action',
            )

        return value

    def serialize_for_db(self) -> str:
        if self == LedgerActionType.INCOME:
            return 'A'
        if self == LedgerActionType.EXPENSE:
            return 'B'
        if self == LedgerActionType.LOSS:
            return 'C'
        if self == LedgerActionType.DIVIDENDS_INCOME:
            return 'D'
        if self == LedgerActionType.DONATION_RECEIVED:
            return 'E'
        if self == LedgerActionType.AIRDROP:
            return 'F'
        if self == LedgerActionType.GIFT:
            return 'G'
        if self == LedgerActionType.GRANT:
            return 'H'

        # else
        raise RuntimeError(f'Corrupt value {self} for LedgerActionType -- Should never happen')

    @classmethod
    def deserialize_from_db(cls, symbol: str) -> 'LedgerActionType':
        """Takes a string from the DB and attempts to turn it into a LedgerActionType

        Can throw DeserializationError if the symbol is not as expected
        """
        if not isinstance(symbol, str):
            raise DeserializationError(
                f'Failed to deserialize ledger action type symbol from {type(symbol)} entry',
            )

        if symbol == 'A':
            return LedgerActionType.INCOME
        if symbol == 'B':
            return LedgerActionType.EXPENSE
        if symbol == 'C':
            return LedgerActionType.LOSS
        if symbol == 'D':
            return LedgerActionType.DIVIDENDS_INCOME
        if symbol == 'E':
            return LedgerActionType.DONATION_RECEIVED
        if symbol == 'F':
            return LedgerActionType.AIRDROP
        if symbol == 'G':
            return LedgerActionType.GIFT
        if symbol == 'H':
            return LedgerActionType.GRANT
        # else
        raise DeserializationError(
            f'Failed to deserialize ledger action type symbol. Unknown DB '
            f'symbol {symbol} for ledger action type',
        )

    def is_profitable(self) -> bool:
        return self in (
            LedgerActionType.INCOME,
            LedgerActionType.DIVIDENDS_INCOME,
            LedgerActionType.DONATION_RECEIVED,
            LedgerActionType.AIRDROP,
            LedgerActionType.GIFT,
            LedgerActionType.GRANT,
        )


LEDGER_ACTION_TYPE_MAPPING = {str(x): x for x in LedgerActionType}


LedgerActionDBTuple = Tuple[
    int,  # timestamp
    str,  # action_type
    str,  # location
    str,  # amount
    str,  # asset
    Optional[str],  # rate
    Optional[str],  # rate_asset
    Optional[str],  # link
    Optional[str],  # notes
]


LedgerActionDBTupleWithIdentifier = Tuple[
    int,  # identifier
    int,  # timestamp
    str,  # action_type
    str,  # location
    str,  # amount
    str,  # asset
    Optional[str],  # rate
    Optional[str],  # rate_asset
    Optional[str],  # link
    Optional[str],  # notes
]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class LedgerAction:
    """Represents an income/loss/expense for accounting purposes"""
    identifier: int  # the unique id of the action and DB primary key
    timestamp: Timestamp
    action_type: LedgerActionType
    location: Location
    amount: AssetAmount
    asset: Asset
    rate: Optional[Price]
    rate_asset: Optional[Asset]
    link: Optional[str]
    notes: Optional[str]

    def serialize(self) -> Dict[str, Any]:
        return {
            'identifier': self.identifier,
            'timestamp': self.timestamp,
            'action_type': str(self.action_type),
            'location': str(self.location),
            'amount': str(self.amount),
            'asset': self.asset.identifier,
            'rate': str(self.rate) if self.rate else None,
            'rate_asset': self.rate_asset.identifier if self.rate_asset else None,
            'link': self.link,
            'notes': self.notes,
        }

    def serialize_for_db(self) -> LedgerActionDBTuple:
        """Serializes an action for writing in the DB. Identifier is ignored"""
        return (
            self.timestamp,
            self.action_type.serialize_for_db(),
            self.location.serialize_for_db(),
            str(self.amount),
            self.asset.identifier,
            str(self.rate) if self.rate else None,
            self.rate_asset.identifier if self.rate_asset else None,
            self.link,
            self.notes,
        )

    @classmethod
    def deserialize_from_db(cls, data: LedgerActionDBTupleWithIdentifier) -> 'LedgerAction':
        """May raise:
        - DeserializationError
        - UnknownAsset
        """
        return cls(
            identifier=data[0],
            timestamp=deserialize_timestamp(data[1]),
            action_type=LedgerActionType.deserialize_from_db(data[2]),
            location=deserialize_location_from_db(data[3]),
            amount=deserialize_asset_amount(data[4]),
            asset=Asset(data[5]),
            rate=deserialize_optional(data[6], deserialize_price),
            rate_asset=deserialize_optional(data[7], Asset),
            link=data[8],
            notes=data[9],
        )

    def is_profitable(self) -> bool:
        return self.action_type.is_profitable()
