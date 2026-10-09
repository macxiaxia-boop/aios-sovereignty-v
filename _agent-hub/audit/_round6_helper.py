"""R6 audit dimensions helper."""
import json, subprocess, sys, os
sys.path.insert(0, r'D:\AIOS\kernel\src')
sys.path.insert(0, r'D:\AIOS\_agent-hub\policy')
sys.path.insert(0, r'D:\AIOS\_agent-hub\policy\adapters')

# D3 adapter status
print("=== D3 ===")
import __init__ as ad
statuses = ad.list_adapters_status()
for s in statuses:
    mark = "OK" if (s["loaded"] and s["signature_ok"]) else "FAIL"
    print(f"  [{mark}] {s['name']:24s} sig_ok={s['signature_ok']} info={s['signature_info']}")
ok = sum(1 for s in statuses if s["loaded"] and s["signature_ok"])
print(f"summary: {ok}/{len(statuses)}")

# D4 Adapter stdin deepseek deny
print()
print("=== D4 Adapter stdin DENY ===")
req = json.dumps({"model": "deepseek-v3", "provider": "deepseek", "request_id": "r6-deny"})
proc = subprocess.run(
    [sys.executable, "-c", "import sys; sys.path.insert(0, r'D:\\AIOS\\_agent-hub\\policy'); from codex_adapter import main; main()"],
    input=req, capture_output=True, text=True,
    cwd=r'D:\AIOS\kernel',
    env={**os.environ, "PYTHONPATH": r"D:\AIOS\kernel\src;D:\AIOS\_agent-hub\policy"}
)
print(f"  exit code: {proc.returncode}")
print(f"  stderr: {proc.stderr[:300]}")

# D11 24 files presence
print()
print("=== D11 _agent-hub 24 files ===")
must = [
    'policy/model-policy.v1.yaml','policy/model-policy.v1.sha256',
    'policy/adapter-contract.md','policy/adapter-spec.v1.md',
    'policy/codex_adapter.py','policy/drift-event.schema.json',
    'policy/reconciler-spec.md','policy/RUNBOOK.md',
    'policy/reconciler/reconciler.py','policy/reconciler/register_reconciler.cmd',
    'policy/reconciler/last_run.log','policy/adapters/__init__.py',
    'policy/adapters/codex_runtime.py','policy/adapters/claude_code_runtime.py',
    'policy/adapters/openclaw_runtime.py','policy/adapters/hermes_runtime.py',
    'audit/drift-events.log','audit/adapter-rejects.log',
    'audit/regression-tests.md','audit/sovereignty-audit-checklist.md',
    'memory/2026-10-09.md','AGENTS.md','README.md','CLAUDE.md',
]
missing = [f for f in must if not os.path.exists(f"D:\AIOS\_agent-hub\\{f}")]
print(f"  {len(must) - len(missing)}/{len(must)} present" + (f" · missing: {missing}" if missing else " · PASS"))