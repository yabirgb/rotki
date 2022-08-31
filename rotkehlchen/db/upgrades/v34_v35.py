from typing import TYPE_CHECKING

from rotkehlchen.constants.resolver import ETHEREUM_DIRECTIVE, strethaddress_to_identifier
from rotkehlchen.globaldb.upgrades.v2_v3 import OTHER_EVM_CHAINS_ASSETS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor


def _refactor_time_columns(write_cursor: 'DBCursor') -> None:
    """
    The tables that contained time instead of timestamp as column names and need
    to be changed were:
    - timed_balances
    - timed_location_data
    - ethereum_accounts_details
    - trades
    - asset_movements
    """
    write_cursor.execute('ALTER TABLE timed_balances RENAME COLUMN time TO timestamp')
    write_cursor.execute('ALTER TABLE timed_location_data RENAME COLUMN time TO timestamp')
    write_cursor.execute('ALTER TABLE ethereum_accounts_details RENAME COLUMN time TO timestamp')
    write_cursor.execute('ALTER TABLE trades RENAME COLUMN time TO timestamp')
    write_cursor.execute('ALTER TABLE asset_movements RENAME COLUMN time TO timestamp')


def _create_new_tables(write_cursor: 'DBCursor') -> None:
    write_cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_notes(
        identifier INTEGER NOT NULL PRIMARY KEY,
        title TEXT NOT NULL,
        content TEXT NOT NULL,
        location TEXT NOT NULL,
        last_update_timestamp INTEGER NOT NULL,
        is_pinned INTEGER NOT NULL CHECK (is_pinned IN (0, 1))
    );
    """)


def _rename_assets_identifiers(write_cursor: 'DBCursor') -> None:
    """Version 1.26 includes the migration for the global db and the references to assets
    need to be updated also in this database.
    We need to update the rows instead of just deleting and inserting because the rows are
    referenced and this triggers an update in cascade.
    """
    write_cursor.execute('SELECT identifier FROM assets')
    old_id_to_new = {}
    for (identifier,) in write_cursor:
        if identifier.startswith(ETHEREUM_DIRECTIVE):
            old_id_to_new[identifier] = strethaddress_to_identifier(identifier[6:])
        elif identifier in OTHER_EVM_CHAINS_ASSETS:
            old_id_to_new[identifier] = OTHER_EVM_CHAINS_ASSETS[identifier]
    sqlite_tuples = [(new_id, old_id) for old_id, new_id in old_id_to_new.items()]
    # Make sure that the new ids don't exist already in the user db
    write_cursor.executemany('DELETE FROM assets WHERE identifier=?', [(x,) for x in old_id_to_new.values()])  # noqa: E501
    write_cursor.executemany('UPDATE OR IGNORE assets SET identifier=? WHERE identifier=?', sqlite_tuples)  # noqa: E501


def upgrade_v34_to_v35(db: 'DBHandler') -> None:
    """Upgrades the DB from v34 to v35
    - Change tables where time is used as column name to timestamp
    - Add user_notes table
    - Renames the asset identifiers to use CAIPS
    """
    with db.user_write() as write_cursor:
        _rename_assets_identifiers(write_cursor)
        _refactor_time_columns(write_cursor)
        _create_new_tables(write_cursor)
