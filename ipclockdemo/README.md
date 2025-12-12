# IPC Lock Demo

This proof of concept shows how a Python process (using `fasteners`) and a Rust process (using `fs2::FileExt`) can coordinate access to the same SQLite database while WAL mode is enabled. Both processes share a small lock file (`demo.db.lock`) so only one writer holds the lock at a time, which eliminates `database is locked` failures even though they run concurrently.

## Requirements
- Python 3.11+ with [`fasteners`](https://pypi.org/project/fasteners/) installed (e.g. `uv pip install fasteners`)
- Rust toolchain (stable) for running the included Cargo project

## Running the demo
1. **Start the Python writer** (terminal A):
   ```bash
   uv run python ipclockdemo/python_writer.py --name py --iterations 10 --delay 1.0
   ```
   Flags are optional; defaults are 8 iterations, one second delay, and name `python`.

2. **Start the Rust writer** (terminal B):
   ```bash
   cd ipclockdemo
   cargo run --quiet -- --name rust --iterations 10 --delay-ms 1000
   ```
   Arguments are optional; see `cargo run -- --help` for details.

Both writers will print the rows they see after every insert. You should observe each process reading the other one's rows without SQLITE_BUSY errors, demonstrating that the shared lock gate keeps concurrent writers.

### Stress test
To hammer the database with rapid writes from both processes, run the helper script from the repository root:

```bash
./ipclockdemo/run_stress.sh
```

This launches both writers with 200 iterations and sub-100ms delays, making it much more likely to surface locking errors if the coordination were missing.

## Files
- `python_writer.py` — Python script using `fasteners.InterProcessLock`
- `Cargo.toml`, `src/main.rs` — Rust binary using `fs2::FileExt` for locking
- `run_stress.sh` — convenience script that runs both writers in a tight loop

The SQLite database (`demo.db`) and the WAL/shm files are ignored from version control.
