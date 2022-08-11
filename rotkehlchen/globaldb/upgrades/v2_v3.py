import logging
from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants.resolver import (
    ETHEREUM_DIRECTIVE,
    ETHEREUM_DIRECTIVE_LENGTH,
    ChainID,
    EvmTokenKind,
    evm_address_to_identifier,
    strethaddress_to_identifier,
)
from rotkehlchen.globaldb.schema import (
    DB_CREATE_ASSETS,
    DB_CREATE_COMMON_ASSET_DETAILS,
    DB_CREATE_ETHEREUM_TOKENS_LIST,
    DB_CREATE_EVM_TOKENS,
    DB_CREATE_MULTIASSETS,
    DB_CREATE_USER_OWNED_ASSETS,
)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBConnection, DBCursor

log = logging.getLogger(__name__)


COMMON_ASSETS_INSERT = """INSERT OR IGNORE INTO common_asset_details(
    identifier, name, symbol, coingecko, cryptocompare, forked
    ) VALUES(?, ?, ?, ?, ?, ?)
"""
ASSETS_INSERT = """INSERT OR IGNORE INTO assets(
        identifier, type, started, swapped_for
    )VALUES(?, ?, ?, ?);
"""
EVM_TOKEN_INSERT = """INSERT OR IGNORE INTO evm_tokens(
        identifier, token_kind, chain, address, decimals, protocol
    ) VALUES(?, ?, ?, ?, ?, ?)
"""
UNDERLYING_TOKEN_INSERT = """INSERT OR IGNORE INTO
    underlying_tokens_list(identifier, weight, parent_token_entry)
    VALUES (?, ?, ?)
"""
OWNED_ASSETS_INSERT = 'INSERT OR IGNORE INTO user_owned_assets(asset_id) VALUES (?);'


EVM_TUPLES_CREATION_TYPE = (
    Tuple[
        List[Tuple[str, str, str, str, Any, Any]],
        List[Tuple[Any, str, Any, Optional[str]]],
        List[Tuple[Any, Any, Any, Any, Any, None]],
    ]
)

ASSET_CREATION_TYPE = (
    Tuple[
        List[Tuple[Any, Any, Any, Any]],
        List[Tuple[Any, Any, Any, Any, Any, Any]],
    ]
)


def upgrade_ethereum_assets(query: List[Any]) -> EVM_TUPLES_CREATION_TYPE:
    old_ethereum_data = []
    old_ethereum_id_to_new = {}
    evm_tuples = []
    assets_tuple = []
    common_asset_details = []

    for entry in query:
        new_id = evm_address_to_identifier(
            address=entry[0],
            chain=ChainID.ETHEREUM,
            token_type=EvmTokenKind.ERC20,
            collectible_id=None,
        )
        old_ethereum_id_to_new[entry[3]] = new_id
        old_ethereum_data.append((new_id, *entry))

    for entry in old_ethereum_data:
        evm_tuples.append((
            str(entry[0]),  # identifier
            EvmTokenKind.ERC20.serialize_for_db(),  # token type
            ChainID.ETHEREUM.serialize_for_db(),  # chain
            str(entry[1]),  # address
            entry[2],  # decimals
            entry[3],  # protocol
        ))
        new_swapped_for = old_ethereum_id_to_new.get(entry[8])
        if new_swapped_for is not None:
            new_swapped_for = evm_address_to_identifier(
                address=entry[8][ETHEREUM_DIRECTIVE_LENGTH:],
                chain=ChainID.ETHEREUM,
                token_type=EvmTokenKind.ERC20,
            )
            old_ethereum_id_to_new[entry[8]] = new_swapped_for

        assets_tuple.append((
            entry[0],  # identifier
            AssetType.EVM_TOKEN.serialize_for_db(),  # type
            entry[7],  # started
            new_swapped_for,  # swapped for
        ))
        common_asset_details.append((
            entry[0],  # identifier
            entry[5],  # name
            entry[6],  # symbol
            entry[9],  # coingecko
            entry[10],  # cryptocompare
            None,  # forked, none for eth
        ))

    return (
        evm_tuples,
        assets_tuple,
        common_asset_details,
    )


def upgrade_ethereum_asset_ids_v3(cursor: 'DBCursor') -> EVM_TUPLES_CREATION_TYPE:
    """Query all the information available from ethereum tokens in
    the v2 schema to be used in v3"""
    result = cursor.execute(
        'SELECT A.address, A.decimals, A.protocol, B.identifier, B.name, B.symbol, B.started, '
        'B.swapped_for, B.coingecko, B.cryptocompare FROM assets '
        'AS B JOIN ethereum_tokens '
        'AS A ON A.address = B.details_reference WHERE B.type="C";',
    )  # noqa: E501

    return upgrade_ethereum_assets(result.fetchall())


def upgrade_other_assets(cursor: 'DBCursor') -> ASSET_CREATION_TYPE:
    """Create the bindings typle for the assets and common_asset_details tables using the
    information from the V2 tables for non ethereum assets"""
    chains = ",".join([f'"{x}"' for x in ('C',)])
    result = cursor.execute(
        f'SELECT A.identifier, A.type, A.name, A.symbol, A.started, A.swapped_for, A.coingecko, '
        f'A.cryptocompare, B.forked FROM assets as A JOIN common_asset_details AS B '
        f'ON B.asset_id=A.identifier WHERE A.type NOT IN ({chains})',
    )  # noqa: E501

    assets_tuple = []
    common_asset_details = []
    for entry in result:
        assets_tuple.append((
            entry[0],  # identifier
            entry[1],  # type
            entry[4],  # started
            entry[5],  # swapped for
        ))
        common_asset_details.append((
            entry[0],  # identifier
            entry[2],  # name
            entry[3],  # symbol
            entry[6],  # coingecko
            entry[7],  # cryptocompare
            entry[8],  # forked
        ))

    return (
        assets_tuple,
        common_asset_details,
    )


def translate_underlying_table(cursor: 'DBCursor') -> List[Tuple[str, str, str]]:
    """Get information about the underlying tokens and upgrade it to the V3 schema from the
    information in the v2 schema"""
    query = cursor.execute(
        'SELECT address, weight, parent_token_entry FROM underlying_tokens_list;',
    )
    mappings = []
    for row in query:
        new_address = evm_address_to_identifier(
            address=row[0],
            chain=ChainID.ETHEREUM,
            token_type=EvmTokenKind.ERC20,
            collectible_id=None,
        )
        new_parent = evm_address_to_identifier(
            address=row[2],
            chain=ChainID.ETHEREUM,
            token_type=EvmTokenKind.ERC20,
            collectible_id=None,
        )
        mappings.append((new_address, row[1], new_parent))
    return mappings


def translate_owned_assets(cursor: 'DBCursor') -> List[Tuple[str]]:
    """Collect and update assets in the user_owned_assets tables to use the new id format"""
    cursor.execute('SELECT asset_id from user_owned_assets;')
    owned_assets = []
    for (asset_id,) in cursor:
        new_id = asset_id
        if asset_id.startswith(ETHEREUM_DIRECTIVE):
            new_id = strethaddress_to_identifier(asset_id[ETHEREUM_DIRECTIVE_LENGTH:])
        owned_assets.append((new_id,))
    return owned_assets


def migrate_to_v3(connection: 'DBConnection') -> None:
    """Upgrade assets information and migrate globaldb to version 3"""

    with connection.read_ctx() as cursor:
        # Obtain information for ethereum assets
        evm_tuples, assets_tuple, common_asset_details = upgrade_ethereum_asset_ids_v3(cursor)
        # Underlying tokens mappings
        mappings = translate_underlying_table(cursor)
        assets_tuple_others, common_asset_details_others = upgrade_other_assets(cursor)
        owned_assets = translate_owned_assets(cursor)

    with connection.write_ctx() as cursor:
        # Purge or delete tables with outdated information
        cursor.executescript("""
        PRAGMA foreign_keys=off;
        DROP TABLE IF EXISTS user_owned_assets;
        DROP TABLE IF EXISTS assets;
        DROP TABLE IF EXISTS ethereum_tokens;
        DROP TABLE IF EXISTS evm_tokens;
        DROP TABLE IF EXISTS common_asset_details;
        DROP TABLE IF EXISTS underlying_tokens_list;
        PRAGMA foreign_keys=on;
        """)

        # Create new tables
        cursor.execute(DB_CREATE_COMMON_ASSET_DETAILS)
        cursor.execute(DB_CREATE_ASSETS)
        cursor.execute(DB_CREATE_EVM_TOKENS)
        cursor.execute(DB_CREATE_MULTIASSETS)
        cursor.execute(DB_CREATE_USER_OWNED_ASSETS)
        cursor.execute(DB_CREATE_ETHEREUM_TOKENS_LIST)

        cursor.executescript('PRAGMA foreign_keys=off;')
        cursor.executemany(COMMON_ASSETS_INSERT, common_asset_details)
        cursor.executemany(COMMON_ASSETS_INSERT, common_asset_details_others)
        cursor.executemany(ASSETS_INSERT, assets_tuple)
        cursor.executemany(ASSETS_INSERT, assets_tuple_others)
        cursor.executemany(OWNED_ASSETS_INSERT, owned_assets)
        cursor.executescript('PRAGMA foreign_keys=on;')
        cursor.executemany(EVM_TOKEN_INSERT, evm_tuples)
        cursor.executemany(UNDERLYING_TOKEN_INSERT, mappings)

        connection.commit()
