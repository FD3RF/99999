#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT_DIR/logs/liquidity_monitor.pid"
LOG_FILE="$ROOT_DIR/logs/liquidity_monitor.log"

if [[ -f "$PID_FILE" ]]; then
  OLD_PID="$(cat "$PID_FILE")"
  if ps -p "$OLD_PID" >/dev/null 2>&1; then
    echo "Monitor already running with PID $OLD_PID"
    exit 0
  fi
fi

cd "$ROOT_DIR"
nohup python -u liquidity_monitor.py >> "$LOG_FILE" 2>&1 &
NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

echo "Monitor started. PID=$NEW_PID"
echo "Log: $LOG_FILE"
