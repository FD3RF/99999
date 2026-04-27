#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PID_FILE="$ROOT_DIR/logs/liquidity_monitor.pid"
LOG_FILE="$ROOT_DIR/logs/liquidity_monitor.log"

if [[ ! -f "$PID_FILE" ]]; then
  echo "Monitor status: STOPPED"
  exit 0
fi

PID="$(cat "$PID_FILE")"
if ps -p "$PID" >/dev/null 2>&1; then
  echo "Monitor status: RUNNING (PID=$PID)"
  echo "Log: $LOG_FILE"
else
  echo "Monitor status: STOPPED (stale pid file: $PID)"
fi
