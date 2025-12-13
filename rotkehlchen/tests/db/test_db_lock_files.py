from pathlib import Path

from rotkehlchen.constants.misc import DEFAULT_SQL_VM_INSTRUCTIONS_CB
from rotkehlchen.db.drivers.gevent import DBConnection, DBConnectionType


def test_db_connection_creates_lock_file(tmp_path: Path) -> None:
    """Ensure DBConnection keeps a lock file beside the database for IPC writes."""
    db_path = tmp_path / 'global.db'
    conn = DBConnection(
        path=db_path,
        connection_type=DBConnectionType.GLOBAL,
        sql_vm_instructions_cb=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
    )
    try:
        assert db_path.with_suffix('.lock').exists()
    finally:
        conn.close()
