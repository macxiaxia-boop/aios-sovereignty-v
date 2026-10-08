#!/usr/bin/env bash
# Run the AIOS Kernel FastAPI process (T0031 scaffold — uvicorn only).
# Real config wiring arrives in T0033/T0035.
set -euo pipefail

HOST="${AIOS_KERNEL_HOST:-127.0.0.1}"
PORT="${AIOS_KERNEL_PORT:-8080}"

cd "$(dirname "$0")/.."

exec python -m uvicorn aios_kernel.api:app \
  --host "$HOST" \
  --port "$PORT" \
  --reload
