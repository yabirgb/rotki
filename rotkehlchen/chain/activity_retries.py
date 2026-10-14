import json
import logging
from contextlib import contextmanager
from threading import Lock
from typing import TYPE_CHECKING, Final

from rotkehlchen.constants.timing import EVMLIKE_ACCOUNTS_DETECTION_RETRY
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    SUPPORTED_EVM_EVMLIKE_CHAINS,
    SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE,
    ChecksumEvmAddress,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

ActivityCheck = tuple[ChecksumEvmAddress, SUPPORTED_EVM_EVMLIKE_CHAINS_TYPE]
_STATE_KEY: Final = DBCacheStatic.EVM_ACCOUNTS_DETECT_RETRIES
_CHAINS_BY_VALUE: Final = {chain.value: chain for chain in SUPPORTED_EVM_EVMLIKE_CHAINS}


class ActivityRetryTracker:
    """Remembers the (address, chain) account activity checks that failed with a recoverable
    error (e.g. rate limit) so that only those are retried soon, instead of waiting for the
    next full detection. The state is persisted in the user DB so that it survives a restart
    or a logout.

    Each pending check also remembers whether the address was explicitly submitted by the user.
    Such addresses may not be tracked on any chain yet (they were inactive everywhere else), so
    they can't be found by the full detection, which only scans tracked addresses.
    """

    def __init__(self, database: DBHandler) -> None:
        self.database = database
        self._lock = Lock()
        self._pending: dict[ActivityCheck, bool] = {}  # check -> was explicitly submitted
        # None values invalidate responses for checks removed while a retry is running.
        self._in_flight: dict[ActivityCheck, bool | None] | None = None
        self._due_ts: Timestamp = Timestamp(0)
        self._load()

    def _load(self) -> None:
        with self.database.conn.read_ctx() as cursor:
            raw = self.database.get_static_cache(cursor=cursor, name=_STATE_KEY)

        if raw is None:
            return

        try:
            data = json.loads(raw)
            self._pending = {
                (ChecksumEvmAddress(entry['address']), _CHAINS_BY_VALUE[entry['chain']]):
                bool(entry['submitted'])
                for entry in data['checks']
            }
            self._due_ts = Timestamp(int(data['due_ts']))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            log.error('Dropping unreadable pending EVM activity checks %s due to %s', raw, e)
            self._pending = {}
            self._due_ts = Timestamp(0)

    @contextmanager
    def _locked(self, write_cursor: DBCursor | None = None) -> Iterator[DBCursor]:
        """Hold the write transaction and then the lock, always in this order, so that callers
        already inside a write transaction can't deadlock with the ones that open their own."""
        if write_cursor is not None:
            with self._lock:
                yield write_cursor
            return

        with self.database.user_write() as cursor:
            self._lock.acquire()
            try:
                yield cursor
            finally:
                self._lock.release()

    def _write_state(self, write_cursor: DBCursor) -> None:
        checks = {
            check: submitted for check, submitted in (self._in_flight or {}).items()
            if submitted is not None
        } | self._pending
        if len(checks) == 0:
            write_cursor.execute('DELETE FROM key_value_cache WHERE name=?', (_STATE_KEY.value,))
            return

        self.database.set_static_cache(
            write_cursor=write_cursor,
            name=_STATE_KEY,
            value=json.dumps({
                'due_ts': self._due_ts,
                'checks': [
                    {'address': address, 'chain': chain.value, 'submitted': submitted}
                    for (address, chain), submitted in checks.items()
                ],
            }),
        )

    def record_failures(
            self,
            failures: Collection[ActivityCheck],
            submitted: bool = False,
    ) -> None:
        """Remember failed checks and schedule their retry if none is scheduled yet"""
        if len(failures) == 0:
            return

        with self._locked() as write_cursor:
            for check in failures:
                if (
                    self._in_flight is not None and check in self._in_flight and
                    self._in_flight[check] is None
                ):
                    continue  # removed during the request: ignore its late failure
                # a submitted check stays submitted even if a later failure is a detection one
                self._pending[check] = submitted or self._pending.get(check, False) or bool(
                    (self._in_flight or {}).get(check),
                )
            self._schedule_if_needed()
            self._write_state(write_cursor)

    def mark_submitted(self, addresses: Collection[ChecksumEvmAddress]) -> None:
        """Mark the pending checks of explicitly submitted addresses, so that they are
        retried even if the address ends up not being tracked on any chain"""
        with self._locked() as write_cursor:
            if len(marked := [
                check for check, submitted in self._pending.items()
                if not submitted and check[0] in addresses
            ]) == 0:
                return

            for check in marked:
                self._pending[check] = True
            self._write_state(write_cursor)

    def _schedule_if_needed(self) -> None:
        if self._due_ts <= (now := ts_now()):  # no retry is scheduled yet
            self._due_ts = Timestamp(now + EVMLIKE_ACCOUNTS_DETECTION_RETRY)

    def drop_address(
            self,
            write_cursor: DBCursor,
            address: str,
            chain: SupportedBlockchain | None = None,
    ) -> None:
        """Forget the pending checks of an address, e.g. after the user removed it. Only
        the check of the given chain if there is one, otherwise all of its checks."""
        with self._locked(write_cursor):
            dropped = [
                check for check in self._pending
                if check[0] == address and (chain is None or check[1] == chain)
            ]
            for check in dropped:
                del self._pending[check]
            if self._in_flight is not None:
                for check in self._in_flight:
                    if check[0] == address and (chain is None or check[1] == chain):
                        self._in_flight[check] = None
            self._clear_due_if_empty()
            self._write_state(write_cursor)

    def is_due(self) -> bool:
        with self._lock:
            return self._in_flight is None and len(self._pending) != 0 and ts_now() >= self._due_ts

    def has_pending(self) -> bool:
        with self._lock:
            return len(self._pending) != 0 or any(
                submitted is not None for submitted in (self._in_flight or {}).values()
            )

    def is_retry_pending(self, check: ActivityCheck) -> bool:
        """Whether an in-flight retry is still wanted. Check inside the account write
        transaction so that removal cannot land between this check and account addition."""
        with self._lock:
            return self._in_flight is not None and self._in_flight.get(check) is not None

    @contextmanager
    def rechecking(
            self,
            checks: Collection[ActivityCheck] | None = None,
    ) -> Iterator[dict[ActivityCheck, bool]]:
        """Keep checks durable until the operation finishes. On interruption they remain
        pending; on completion only newly recorded failures remain. Removal invalidates
        in-flight checks so neither a late success nor a late failure can add them back."""
        with self._locked():
            if self._in_flight is not None or len(self._pending) == 0:
                pending = {}
            else:
                selected = self._pending.keys() if checks is None else self._pending.keys() & set(checks)  # noqa: E501
                pending = {check: self._pending[check] for check in selected}
                if len(pending) != 0:
                    self._in_flight = dict(pending)
                    for check in pending:
                        del self._pending[check]

        if len(pending) == 0:
            yield {}
            return

        completed = False
        try:
            yield pending
            completed = True
        finally:
            with self._locked() as write_cursor:
                if not completed:
                    for check, submitted in (self._in_flight or {}).items():
                        if submitted is not None:
                            self._pending.setdefault(check, submitted)
                self._in_flight = None
                self._clear_due_if_empty()
                self._write_state(write_cursor)

    def _clear_due_if_empty(self) -> None:
        """Must be called with the lock held"""
        if len(self._pending) == 0 and not any(
            submitted is not None for submitted in (self._in_flight or {}).values()
        ):
            self._due_ts = Timestamp(0)
