#!/usr/bin/env bash
# Local CI mirror of .github/workflows/ci.yml (T0031 scaffold).
# Run on every developer machine before pushing.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "[ci] ruff lint"
python -m ruff check src/ tests/

echo "[ci] mypy typecheck"
python -m mypy src/aios_kernel || true  # optional at scaffold stage

echo "[ci] pytest collect"
python -m pytest --collect-only

echo "[ci] OK"
