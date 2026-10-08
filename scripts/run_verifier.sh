#!/usr/bin/env bash
# Run the AIOS Verifier as a standalone process (T0035).
# Usage:
#   ./scripts/run_verifier.sh                       # foreground, default 127.0.0.1:9001
#   PORT=9100 ./scripts/run_verifier.sh             # custom port via env
#
# The Verifier runs in its own OS process, so the PID differs from the
# Kernel process that talks to it. The Kernel reaches it at
# $VERIFIER_HOST:$VERIFIER_PORT (defaults 127.0.0.1:9001).
set -euo pipefail

cd "$(dirname "$0")/.."

HOST="${VERIFIER_HOST:-127.0.0.1}"
PORT="${VERIFIER_PORT:-9001}"
VERIFIER_ID="${VERIFIER_ID:-deterministic-verifier}"

exec python scripts/run_verifier.py \
  --host "$HOST" \
  --port "$PORT" \
  --verifier-id "$VERIFIER_ID"
