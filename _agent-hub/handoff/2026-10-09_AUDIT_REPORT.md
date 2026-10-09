# Audit Report 2026-10-09 (Codex Supervisor)

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
- `restart delay 15 sec` + `onfailure action=restart` in `D:\AIOS\daemons_v2\winsw\v2-consumer\AIOSV2Consumer.xml`.

### C3. 221 git dirty files (uncommitted working tree)
- Most are scratch files (`_*`, `*.bak`, `__pycache__`). Real work in D:\AIOS is committed.

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
2. `git -C D:\AIOS add _agent-hub/v2/src/queue.py` to commit the shim
3. `python D:\AIOS\_agent-hub\v2\cli\aiosv2.py status` to verify CLI works
4. `python D:\AIOS\_agent-hub\v2\cli\aiosv2.py receive --agent codex` to drain inbox

— Codex Supervisor, 2026-10-09
