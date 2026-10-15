#!/usr/bin/env bash
# start-prod.sh - R1505-2: one-shot production startup for AIOS kernel.
#
# Usage:
#   bash start-prod.sh              # foreground (Ctrl-C to stop)
#   bash start-prod.sh status       # check liveness / readiness
#   bash start-prod.sh metrics      # dump Prometheus metrics
#   bash start-prod.sh tail         # tail scheduler log
#   bash start-prod.sh stop         # SIGTERM the running daemon
#
# Environment:
#   AIOS_KERNEL_PORT        (default 9000)
#   AIOS_KERNEL_AUTH_REQUIRED (0 or 1; default 0)
#   AIOS_KERNEL_RATELIMIT_ENABLED (0 or 1; default 0)
#   AIOS_KERNEL_JWT_SECRET   (required only when AUTH_REQUIRED=1)
#
# Co-Authored-By: Claude Code via AIOS R1505-2
set -euo pipefail

cd "$(dirname "$0")"

PYTHON="${PYTHON:-python}"
if [[ -f ".venv/Scripts/python.exe" ]]; then
    PYTHON=".venv/Scripts/python.exe"
elif [[ -f ".venv/bin/python" ]]; then
    PYTHON=".venv/bin/python"
fi

PORT="${AIOS_KERNEL_PORT:-9000}"
LOG="/var/log/aios-kernel/kernel.log"
PIDFILE="/var/run/aios-kernel.pid"

cmd="${1:-run}"

case "$cmd" in
    run)
        echo "[start-prod] starting AIOS kernel scheduler on :$PORT (foreground)"
        exec "$PYTHON" -m aios_kernel.cli scheduler run
        ;;
    background)
        echo "[start-prod] starting AIOS kernel daemon on :$PORT"
        if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "  already running PID=$(cat "$PIDFILE")"
            exit 1
        fi
        mkdir -p "$(dirname "$LOG")" 2>/dev/null || LOG="/tmp/aios-kernel.log"
        nohup "$PYTHON" -m aios_kernel.cli scheduler run > "$LOG" 2>&1 &
        echo $! > "$PIDFILE"
        sleep 3
        echo "  PID=$(cat "$PIDFILE"), log=$LOG"
        ;;
    status)
        echo "[start-prod] health probe :$PORT"
        for path in /health /healthz /readyz /metrics; do
            code=$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$PORT$path" || echo "000")
            echo "  $path -> $code"
        done
        ;;
    metrics)
        curl -s "http://127.0.0.1:$PORT/metrics"
        ;;
    tail)
        tail -n 50 -f "${LOG:-/tmp/aios-kernel.log}"
        ;;
    stop)
        if [[ -f "$PIDFILE" ]]; then
            PID=$(cat "$PIDFILE")
            echo "[start-prod] stopping PID=$PID"
            kill -TERM "$PID" 2>/dev/null || true
            rm -f "$PIDFILE"
        else
            echo "[start-prod] no PIDFILE"
        fi
        ;;
    test)
        echo "[start-prod] running 114+ tests"
        exec "$PYTHON" -m pytest tests/unit/ tests/integration/test_e2e.py \
            tests/integration/test_r1504_coverage.py \
            tests/integration/test_openclaw_integration_e2e.py \
            tests/integration/test_observability_e2e.py \
            tests/integration/test_auth_readyz_e2e.py -q
        ;;
    *)
        echo "Usage: $0 {run|background|status|metrics|tail|stop|test}"
        exit 1
        ;;
esac