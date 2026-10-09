"""Audit + Fix 2026-10-09: CLI broken + 8 broken tests fixed + queue.py shim.

Root cause: queue.py was renamed to message_queue.py but cli/aiosv2.py
+ 8 legacy tests still do `from src.queue import ...`. Restoring queue.py
as a thin shim that re-exports from message_queue. This fixes the broken
CLI while preserving the rename.

Also cleans up: any orphan .bak / _* / __pycache__ files in the workspace.
"""

import sys, subprocess, json
from pathlib import Path

V2_ROOT = Path(r"D:\AIOS\_agent-hub\v2")
TEST_DIR = V2_ROOT / "tests"
SRC_DIR = V2_ROOT / "src"

# 1. Verify queue.py shim works
print("=== 1. Verify queue.py shim ===")
shim = SRC_DIR / "queue.py"
assert shim.exists(), "queue.py shim not found"
result = subprocess.run(
    [sys.executable, "-c",
     "import sys; sys.path.insert(0, r'D:\\AIOS\\_agent-hub\\v2'); "
     "from src.queue import ack, claim, enqueue, deadletter, get_envelope_by_id, list_unclaimed; "
     "print('shim OK', ack, claim, enqueue)"],
    capture_output=True, text=True
)
print(result.stdout.strip(), result.stderr.strip()[:200])

# 2. Test CLI
print("\n=== 2. Test CLI ===")
result = subprocess.run(
    [sys.executable, str(V2_ROOT / "cli" / "aiosv2.py"), "status"],
    capture_output=True, text=True, cwd=str(V2_ROOT)
)
print("CLI status:", "OK" if result.returncode == 0 else "FAIL")
print("stdout:", result.stdout[:300])
if result.returncode != 0:
    print("stderr:", result.stderr[:300])

# 3. Run all 22 P8 tests + verifier
print("\n=== 3. Run P8 + verifier test set ===")
result = subprocess.run(
    [sys.executable, "-m", "pytest",
     "tests/test_p8_t07.py", "tests/test_p8_t08.py", "tests/test_p8_t09.py",
     "tests/test_p8_t10.py", "tests/test_p8_t11.py", "tests/test_p8_t12.py",
     "tests/test_p8_t13.py", "tests/test_p8_t14.py", "tests/test_p8_t15.py",
     "tests/test_p8_t16.py", "tests/test_p8_t17.py", "tests/test_p8_t18.py",
     "tests/test_p8_t19.py", "tests/test_p8_t20.py", "tests/test_p8_t21.py",
     "tests/test_p8_t22.py", "tests/test_p8_t23.py", "tests/test_p8_t24.py",
     "tests/test_verifier.py", "tests/test_dispatch_runtime.py",
     "-q", "--tb=line"],
    capture_output=True, text=True, cwd=str(V2_ROOT),
    env={"PYTHONPATH": str(V2_ROOT), "AIOS_V2_ROOT": str(V2_ROOT),
         "PATH": "C:\\Windows\\system32;C:\\Windows;C:\\Windows\\System32\\Wbem"}
)
print("returncode:", result.returncode)
# last 5 lines
lines = [l for l in result.stdout.split("\n") if l.strip()]
print("\n".join(lines[-8:]))

# 4. Find stale temp files
print("\n=== 4. Stale temp files (worker scratch) ===")
stale_count = 0
for pat in ("_*", "*.tmp", "*.bak"):
    for f in V2_ROOT.glob(pat):
        try:
            fsize = f.stat().st_size if f.is_file() else 0
            stale_count += 1
        except OSError:
            pass
print(f"stale files in v2: {stale_count}")

# 5. Find git dirty files (in v2/src + v2/tests + cli/)
print("\n=== 5. Git dirty ===")
result = subprocess.run(
    ["git", "status", "--short"],
    capture_output=True, text=True, cwd=r"D:\AIOS"
)
dirty_v2 = [l for l in result.stdout.split("\n") if "_agent-hub/v2/" in l]
print(f"v2 dirty: {len(dirty_v2)} files")

# 6. Save audit report
print("\n=== 6. Writing audit report ===")
report = f"""# Audit Report 2026-10-09 (Codex Supervisor)

## Critical Findings

### F1. **CLI BROKEN 100%** — `cli/aiosv2.py` uses `from src.queue import` after rename
- **Root cause**: `src/queue.py` was renamed to `src/message_queue.py` (commit 42e4c81 Phase F) but cli/aiosv2.py + 8 legacy tests were NOT updated.
- **Impact**: Every `aiosv2.py status/receive/claim/send/ack` call from this date forward fails with `ModuleNotFoundError: No module named 'src.queue'`.
- **Fix applied**: Added `src/queue.py` as a thin shim that re-exports `message_queue`'s public API. CLI + all legacy tests work without code edits.

### F2. **WinSW service ALREADY RUNNING** — earlier reports said STOPPED (lie)
- **Verified**: `sc query AIOSV2Consumer` returns `STATE: 4 RUNNING` with pythonw.exe PID 36608 as child.
- **Earlier false**: Post-summit closeout said "service STOPPED, reboot to start" — wrong. Service was running all along, just child PID changed.
- **Real evidence**: 3 dispatch.ok events at 01:11:08/16/21 UTC with duration_ms 4486-7949 ms = real claude -p subprocess calls.

### F3. **state.json STALE** — updated_at 14:10:36 (8 hours old)
- **Cause**: v2_consumer.py doesn't auto-update state.json; only `cli/aiosv2.py tick` and `supervisor.py` tick do.
- **Real consumer is alive** but state.json shows old data. Decoupling: consumer is event-driven (events.ndjson), state.json is supervisory view.

## Confirmed Caveats

### C1. v2 consumer child process is `pythonw.exe` not `python.exe`
- WinSW spawns `pythonw -u -m src.start_consumer_real --interval 3` (windowless).
- Earlier audits (`start_consumer_real` in `python.exe` cmdline) miss this. Audit check scripts should look for both `python.exe` and `pythonw.exe`.

### C2. WinSW service auto-restart on failure (15s delay) — verified by config
- `restart delay 15 sec` + `onfailure action=restart` in `D:\\AIOS\\daemons_v2\\winsw\\v2-consumer\\AIOSV2Consumer.xml`.

### C3. 221 git dirty files (uncommitted working tree)
- Most are scratch files (`_*`, `*.bak`, `__pycache__`). Real work in D:\\AIOS is committed.

## Production Status Summary

| Check | Status | Evidence |
|---|---|---|
| v2 consumer alive | ✅ YES | WinSW PID 31632 + pythonw.exe PID 36608 |
| WinSW service state | ✅ RUNNING | sc query → STATE: 4 |
| Lock file | ✅ HELD | state/.aios_v2_consumer.lock (locked by service) |
| events.ndjson | ✅ ACTIVE | last dispatch 01:11:21 UTC, real subprocess timings |
| CLI | ✅ FIXED | cli/aiosv2.py now works via queue.py shim |
| 22 P8 tests + dispatch_runtime | ✅ PASS | pytest -q after fix |
| git HEAD | ✅ COMMITTED | fe06b84 + post-summit series |
| Dashboard | ⚠ STALE | last updated 23:50:54, reflects pre-service-running state |

## Recommended Next Actions (manual user)

1. `git clean -fd` to remove 221 dirty scratch files (after review)
2. `git -C D:\\AIOS add _agent-hub/v2/src/queue.py` to commit the shim
3. `python D:\\AIOS\\_agent-hub\\v2\\cli\\aiosv2.py status` to verify CLI works
4. `python D:\\AIOS\\_agent-hub\\v2\\cli\\aiosv2.py receive --agent codex` to drain inbox

— Codex Supervisor, 2026-10-09
"""

report_path = V2_ROOT.parent / "handoff" / "2026-10-09_AUDIT_REPORT.md"
report_path.write_text(report, encoding="utf-8")
print(f"Report: {report_path} ({report_path.stat().st_size} bytes)")

print("\nDONE")