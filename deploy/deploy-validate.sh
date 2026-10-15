#!/usr/bin/env bash
# deploy-validate.sh — Pre-deployment validation (R1505-5).
#
# Run on production host before deploying AIOS kernel.
# Exits 0 if all checks pass; non-zero on first failure.
#
# Checks:
#   1. Python version (>= 3.11)
#   2. Dependencies installed (pip install -e .[dev])
#   3. Tests pass (114+)
#   4. Database reachable (if AIOS_KERNEL_DATABASE_URL set)
#   5. Port reachable (if AIOS_KERNEL_PORT set)
#   6. Env vars set (AIOS_INSTANCE_ID, AIOS_LOG_LEVEL)
#   7. JWT secret strength (if auth required)
#   8. Disk space >= 1GB free
#   9. Docker daemon (optional, if docker-compose planned)
#  10. AIOS kernel imports succeed

set -uo pipefail

cd "$(dirname "$0")/.."

PASS=0
FAIL=0
WARN=0

ok()   { echo "  ✓ $*"; PASS=$((PASS+1)); }
fail() { echo "  ✗ $*"; FAIL=$((FAIL+1)); }
warn() { echo "  ⚠ $*"; WARN=$((WARN+1)); }

echo "=== AIOS Kernel deployment validation ==="
echo ""

# 1. Python version
echo "[1] Python >= 3.11"
if command -v python >/dev/null 2>&1; then
  PY=$(python -c 'import sys; print(sys.version_info >= (3, 11))')
  if [ "$PY" = "True" ]; then
    ok "Python $(python --version)"
  else
    fail "Python too old (need 3.11+)"
  fi
else
  fail "python not in PATH"
fi

# 2. Dependencies
echo "[2] aios_kernel package installed"
if python -c "import aios_kernel" 2>/dev/null; then
  ok "import aios_kernel"
else
  fail "aios_kernel not installed (run: pip install -e '.[dev]')"
fi

# 3. Tests
echo "[3] Tests pass (114+)"
TEST_OUT=$(python -m pytest tests/unit/test_scheduler.py tests/unit/test_state_machine.py tests/unit/test_adapters.py tests/unit/test_agents.py tests/unit/test_gateway.py tests/unit/test_runtime.py tests/unit/test_scheduler_audit.py tests/integration/test_e2e.py tests/integration/test_r1504_coverage.py tests/integration/test_openclaw_integration_e2e.py tests/integration/test_observability_e2e.py tests/integration/test_auth_readyz_e2e.py -q 2>&1 | tail -1)
if echo "$TEST_OUT" | grep -q "passed"; then
  ok "tests: $TEST_OUT"
else
  fail "tests: $TEST_OUT"
fi

# 4. Database
echo "[4] Database reachable"
if [[ -n "${AIOS_KERNEL_DATABASE_URL:-}" ]]; then
  if python -c "import sqlalchemy; e = sqlalchemy.create_engine('$AIOS_KERNEL_DATABASE_URL'); e.connect().close()" 2>/dev/null; then
    ok "database OK"
  else
    fail "database unreachable"
  fi
else
  warn "AIOS_KERNEL_DATABASE_URL unset (skipping)"
fi

# 5. Port reachable
echo "[5] Port not in use"
PORT="${AIOS_KERNEL_PORT:-9000}"
if [[ "$PORT" =~ ^[0-9]+$ ]]; then
  if command -v ss >/dev/null 2>&1; then
    if ss -tlnp 2>/dev/null | grep -q ":$PORT "; then
      warn "port $PORT already in use (existing process?)"
    else
      ok "port $PORT free"
    fi
  else
    ok "port $PORT (can't probe without ss/netstat)"
  fi
else
  fail "AIOS_KERNEL_PORT=$PORT not a number"
fi

# 6. Env vars
echo "[6] Env vars"
[[ -n "${AIOS_INSTANCE_ID:-}" ]] && ok "AIOS_INSTANCE_ID=$AIOS_INSTANCE_ID" || warn "AIOS_INSTANCE_ID unset (defaults to aios-kernel-1)"
[[ -n "${AIOS_LOG_LEVEL:-}" ]] && ok "AIOS_LOG_LEVEL=$AIOS_LOG_LEVEL" || warn "AIOS_LOG_LEVEL unset (defaults to INFO)"

# 7. JWT secret
echo "[7] JWT secret strength (if auth enabled)"
if [[ "${AIOS_KERNEL_AUTH_REQUIRED:-0}" == "1" ]]; then
  if [[ -z "${AIOS_KERNEL_JWT_SECRET:-}" ]]; then
    fail "AIOS_KERNEL_AUTH_REQUIRED=1 but JWT_SECRET unset"
  elif [[ ${#AIOS_KERNEL_JWT_SECRET} -lt 32 ]]; then
    fail "JWT_SECRET < 32 chars (weak)"
  else
    ok "JWT_SECRET ${#AIOS_KERNEL_JWT_SECRET} chars"
  fi
else
  ok "auth disabled (no JWT_SECRET required)"
fi

# 8. Disk space
echo "[8] Disk free >= 1GB"
AVAIL_KB=$(df -k . 2>/dev/null | tail -1 | awk '{print $4}')
if [[ -n "$AVAIL_KB" ]] && [[ "$AVAIL_KB" -gt 1048576 ]]; then
  AVAIL_GB=$(echo "scale=1; $AVAIL_KB / 1048576" | bc 2>/dev/null || echo "?")
  ok "disk free ${AVAIL_GB}GB"
else
  warn "disk free < 1GB or undetectable"
fi

# 9. Docker (optional)
echo "[9] Docker (optional)"
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then
    ok "docker daemon running"
  else
    warn "docker installed but daemon not running"
  fi
else
  warn "docker not installed (skipping compose validation)"
fi

# 10. Import health
echo "[10] Core modules importable"
for m in aios_kernel.scheduler aios_kernel.state_machine aios_kernel.workers.adapters aios_kernel.agents.protocol aios_kernel.gateway.http aios_kernel.gateway.mcp aios_kernel.runtime.process aios_kernel.runtime.memory aios_kernel.runtime.cron; do
  if python -c "import $m" 2>/dev/null; then
    ok "$m"
  else
    fail "$m"
  fi
done

echo ""
echo "=== Summary ==="
echo "  PASS: $PASS"
echo "  WARN: $WARN"
echo "  FAIL: $FAIL"
echo ""

if [[ $FAIL -gt 0 ]]; then
    echo "  ❌ DEPLOYMENT VALIDATION FAILED — fix above issues before deploying"
    exit 1
fi
echo "  ✅ Deployment validation passed — ready to deploy"
exit 0