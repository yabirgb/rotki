#!/usr/bin/env python3
"""Simple SQLite writer guarded by a fasteners IPC lock."""

from __future__ import annotations

import argparse
import sqlite3
import time
from pathlib import Path

from fasteners import InterProcessLock

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "demo.db"
LOCK_PATH = BASE_DIR / "demo.db.lock"


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            iteration INTEGER NOT NULL,
            inserted_at REAL NOT NULL
        )
        """,
    )


def insert_row(conn: sqlite3.Connection, source: str, iteration: int) -> None:
    conn.execute(
        "INSERT INTO messages (source, iteration, inserted_at) VALUES (?, ?, ?)",
        (source, iteration, time.time()),
    )


def read_recent(limit: int = 5) -> list[sqlite3.Row]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        ensure_schema(conn)
        cursor = conn.execute(
            "SELECT id, source, iteration, inserted_at FROM messages ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cursor.fetchall()


def run_writer(name: str, iterations: int, delay: float) -> None:
    lock = InterProcessLock(str(LOCK_PATH))
    for iteration in range(iterations):
        with lock:
            with sqlite3.connect(DB_PATH) as conn:
                ensure_schema(conn)
                insert_row(conn, name, iteration)
                conn.commit()
        rows = read_recent()
        pretty_rows = ", ".join(
            f"#{row['id']}:{row['source']}@{row['iteration']}" for row in rows
        )
        print(f"[{name}] inserted iteration {iteration}. Recent rows: {pretty_rows}")
        time.sleep(delay)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Python fasteners SQLite writer")
    parser.add_argument("--name", default="python", help="label stored in the DB")
    parser.add_argument(
        "--iterations",
        type=int,
        default=8,
        help="number of writes to perform",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="delay (seconds) between writes",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    run_writer(args.name, args.iterations, args.delay)


if __name__ == "__main__":
    main()
