#!/usr/bin/env bash
# Run both writers with aggressive settings to stress-test the lock coordination.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY_CMD="${PY_CMD:-uv run python}"
RUST_CMD="${RUST_CMD:-cargo run --quiet}"

cd "$SCRIPT_DIR"

tmp_fifo="$(mktemp)"
rm -f "$tmp_fifo"
mkfifo "$tmp_fifo"
trap 'rm -f "$tmp_fifo"' EXIT

(
  $PY_CMD python_writer.py --name py --iterations 200 --delay 0.25
  echo py_done > "$tmp_fifo"
) &
PY_PID=$!

(
  $RUST_CMD -- --name rust --iterations 200 --delay-ms 50
  echo rust_done > "$tmp_fifo"
) &
RUST_PID=$!

# Wait for both processes by reading completion markers from fifo.
for _ in 1 2; do
  cat "$tmp_fifo"
done

wait $PY_PID
wait $RUST_PID
