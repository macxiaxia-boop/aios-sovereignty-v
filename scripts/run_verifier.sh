#!/usr/bin/env bash
# Run the AIOS Verifier process (T0031 scaffold — stub only).
# Real implementation lands in T0035.
set -euo pipefail

cd "$(dirname "$0")/.."

exec python -m aios_kernel.verifier
