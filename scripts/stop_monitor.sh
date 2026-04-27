#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT_DIR/logs/liquidity_monitor.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Monitor is not running (pid file missing)."
  exit 0
fi

PID="$(cat "$PID_FILE")"
if ps -p "$PID" >/dev/null 2>&1; then
  kill "$PID"
  echo "Stopped monitor PID=$PID"
else
  echo "No running process found for PID=$PID"
fi

rm -f "$PID_FILE"
