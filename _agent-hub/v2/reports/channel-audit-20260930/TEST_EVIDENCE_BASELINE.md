# TEST_EVIDENCE_BASELINE.md · R285 · 2026-09-30

> Baseline of the four required evidence classes (health-check, call, trace, handoff) for the Codex ↔ Claude Code channel BEFORE R286 changes. Audit-only — no new live tests run in this round; baseline is composed from existing artifacts + this session's read-only observations.

## 1. health-check evidence

| Layer | Live probe (this session) | Existing artifact | Status |
|---|---|---|---|
| v2 supervisor health | `aiosv2.py health` not runnable in this session (sandbox blocks `python <script>`) | `v2/reports/health.json` (last updated 2026-09-29T05:19:02Z, final R320.6 probe) | 4-level model: Hermes/OpenClaw `healthy=true`; Codex/CC/WorkBuddy `present=true, reachable=false, healthy=false` |
| aios-interop MCP | `cross_entrypoint_health` MCP tool exists; live invocation blocked in CC main session | n/a | tool registered, 22 tools listed |
| aios_interop_launcher.py | not directly probed | per-launcher process state | 6 instances alive |
| AIOS_Autonomy_Daemon.exe | not probed | tasklist snapshot | 7 instances alive (no health probe) |
| OpenClaw gateway | `openclaw_health` MCP tool exists; live invocation blocked in CC main session | `aios_status::probe_openclaw` returns `port_open=true, healthz=200 body={"ok":true,"status":"live"}` (R320.6 final probe) | healthy |
| 14 handoff/ daemons | watchdog status file `_aios_daemon_watchdog_state.json` last update 2026-09-30T00:51:27Z, cycle=353, all 14 alive | n/a | all alive |
| _aios_daemon_watchdog | watchdog self-PID = PID file `_aios_daemon_watchdog.pid` (5 bytes, updated 2026-09-29T21:55Z) | watchdog singleton lock held | alive |

**Acceptance baseline for R286**: R286 must add **call-time evidence** that every R286-introduced code path emits the same 4-level probe snapshot, and the probe must run in `v2_consumer.py` tick (one entry per tick in `v2/state/state.json`).

## 2. call evidence

| Path | Last observed call | Source | Notes |
|---|---|---|---|
| `aiosv2.py send` | 2026-09-29T05:14:43Z | v2/idempotency_index.json entry `e13b03ff...` (claudecode → codex, result) | R320.6 verification |
| `aiosv2.py receive` | 2026-09-29T05:14Z (approx) | claim files (not currently visible) | R320.6 verification |
| `aiosv2.py ack` | 2026-09-29T05:15:32Z | v2/idempotency_index.json entry `cd54b5ce...` (codex → claudecode, ack) | R320.6 verification |
| `codex_query` MCP | not observed | n/a | CC main session blocked |
| `codex_desktop_query` MCP | not observed | n/a | CC main session blocked |
| `claude_code_query` MCP | not observed | n/a | CC main session blocked |
| `_codex_to_cc_bridge_v2.main_loop` | continuously (15s cycle) | heartbeat file 2026-09-30T00:50Z | idle (inbox empty) |
| `_handoff_watchdog` | continuously | handoff_watchdog.log | not inspected in this audit |
| `AIOS_Autonomy_Daemon.exe` | continuously | service-managed | singleton lock not enforced |
| openclaw_delegate subprocess via MCP | not observed in this session | n/a | in tool list |

**Acceptance baseline for R286**: R286 must add `v2_consumer.py` that performs a `receive --claim` cycle per tick and records the result in `v2/logs/events.ndjson`. The audit window of "no observed MCP live calls in this session" must END post-R286 (CC main-session permission gate aside).

## 3. trace evidence

| Layer | Existing log | Last line in this audit | Notes |
|---|---|---|---|
| `aios_tasks/evidence/adapter_trace.jsonl` | per-call JSONL | not inspected (may not exist for this session) | emit_trace called by every BaseAdapter.call() |
| `v2/logs/events.ndjson` | envelope lifecycle NDJSON | 0 lines | no supervisor running |
| `_aios_daemon_watchdog_alert.log` | watchdog events (1.37 MB) | "R207 VERIFY_FAIL" / "RESTART" / "THROTTLE" / "DETECTED DEAD" entries | rich history |
| `bridge_v2.log` | per-cycle text log | alive | not sampled |
| `handoff_watchdog.log` | per-cycle text log | alive | not sampled |
| `codex_cli_chat.log` | per-call text log | alive | not sampled |
| `Langfuse` (local stub `_aios_langfuse_trace_stub.py`) | per-call NDJSON | alive | not sampled |

**Acceptance baseline for R286**: post-R286, `v2/logs/events.ndjson` MUST grow by ≥1 line per envelope lifecycle event (enqueue, claim, ack, deadletter, reap_expired, state transition). Trace schema for events:
```json
{"ts": "<iso8601>", "actor": "<agent_id>", "event": "envelope.enqueue|task.transition|task.heartbeat|...", "envelope_id|task_id": "<uuid>", "from?": "<state>", "to?": "<state>", "note?": "..."}
```

## 4. handoff evidence

| Path | Existing handoff file (sample) | Last mtime |
|---|---|---|
| `D:/demo/notifications/cc_processed_*.json` | 20+ files from 2026-09-24 to 2026-09-27 | 2026-09-27T20:00Z (old test traffic) |
| `handoff/inbox/codex_to_cc/ack_*.json` | None in this audit | n/a |
| `handoff/inbox/cc_to_codex/STR-CODEX-AUDIT-*.json` | 9+ STR-CODEX-AUDIT files from 2026-09-27 (history) | 2026-09-27 |
| v2 envelope round-trip evidence (R320.6) | `v2/messages/{inbox,outbox}/*.json` | 2026-09-29T13:07–13:15 |

**Acceptance baseline for R286**: post-R286, every MCP call to `codex_query`/`codex_desktop_query`/`claude_code_query` MUST write a v2 envelope with the same `correlation_id` into `v2/messages/inbox/{recipient}/`. R286 acceptance test: send N envelopes, observe N+1 envelopes in v2/inbox (N inputs + N ack outputs if `--dest=inbox`).

## 5. Test suite baseline

**Location**: `D:\AIOS\_agent-hub\v2\tests\`

**Modules** (read 2026-09-30T00:55Z):
- `test_01_envelope_schema.py` (8 tests; R320.1 no `import pytest`)
- `test_02_queue_concurrency.py` (6 tests; R320.1 worker-exception collection + exact-count)
- `test_03_state_machine.py` (8 tests; R320.1 no `import pytest`)
- `test_04_heartbeat_timeout_retry.py` (4 tests)
- `test_05_protocol_loopback.py` (10 tests; R320.6 added 4 for ack-routing + correlation)
- `test_06_probes.py` (6 tests; 4-level honest model)
- `test_07_healthcheck.py` (11 tests; R320.6 added 4 subprocess CLI tests)
- `test_08_supervisor_watch.py` (2 tests)
- `run_all_tests.py` (R320.1 polyfill-first; per-module load failures recorded)
- `conftest.py` (pytest config)
- `run_all_tests.cmd` (wrapper)

**Total**: 55 test functions. Per `IMPLEMENTATION_REPORT.md` (R320.6): 55 PASS / 0 FAIL when run by Codex from a permitted shell on 2026-09-29T05:13:31Z–05:13:46Z. **Current session execution blocked** by CC main-session Bash sandbox (`python <script>` requires approval).

**Reports persisted**:
- `v2/reports/test-output.txt` (per-test PASS lines with durations)
- `v2/reports/test_run.json` (total_pass=55, total_fail=0, all_pass=true)
- `v2/reports/health.json` (4-level probe snapshot)

**What these tests prove**:
- Envelope schema round-trips through file queue (test_01)
- Concurrent writes are safe (test_02)
- State machine transitions are correct (test_03)
- Heartbeat + lease expiry + retry work (test_04)
- Ack routing lands in inbox (test_05 R320.6)
- Probes return 4 honest levels (test_06)
- CLI subprocess calls succeed (test_07)
- Supervisor can `tick()` and `watch()` (test_08)

**What these tests do NOT prove** (carried over from IMPLEMENTATION_REPORT.md §3.1(d)):
- Hermes / OpenClaw / WorkBuddy consume v2 envelopes end-to-end
- aios-interop MCP transports envelopes in a regular CC main session
- Multiple `aios_interop_launcher.py` instances do NOT race on the idempotency index (because they don't share state)
- v2 supervisor runs long enough to observe >1 reap cycle
- Hermes queue-consumer round-trip

## 6. Required evidence classes — required new tests for R286

The R285 audit establishes the following four classes MUST be evidenced by R286 with tests:

| Class | Test | Required file | Acceptance |
|---|---|---|---|
| **health-check** | `_aios_v2_consumer.py::tick()` writes probe snapshot to `v2/state/state.json` and `v2/logs/events.ndjson` | `tests/test_09_v2_consumer_health.py` | 4-level probe evidence present for all 5 agents after 1 tick |
| **call** | MCP `codex_query` writes a v2 envelope before+after the subprocess call | `tests/test_10_mcp_to_v2_call.py` | `v2/messages/inbox/{recipient}/*.json` increases by ≥2 per call (input envelope + output result envelope) |
| **trace** | All v2 envelope lifecycle events append to `v2/logs/events.ndjson` with `actor`, `event`, `envelope_id` | `tests/test_11_v2_trace_completeness.py` | For each envelope enqueued, ≥3 trace lines exist (enqueue, claim, ack) |
| **handoff** | A full bidirectional MCP call → v2 envelope → v2 consumer → MCP tool → v2 envelope round-trip works end-to-end with correlation | `tests/test_12_mcp_v2_roundtrip.py` | 1 envelope sent → 2 envelopes received (result + ack) with matching correlation_id |

## 7. Failure / restart / concurrency test requirements (R286)

| Failure mode | Test | Acceptance |
|---|---|---|
| CC main session dies mid-MCP-call | `tests/test_13_mcp_call_killed_midway.py` | claimed envelope must be reaped to `failed` state by supervisor within lease expiry; idempotency index must NOT be corrupted |
| v2 inbox consumer dies | `tests/test_14_v2_consumer_restart.py` | watchdog restarts within 60s; envelopes in inbox remain unclaimed (no data loss) |
| 6 launchers write same idempotency_key simultaneously | `tests/test_15_idempotency_6writers.py` | exactly 1 envelope persisted; 5 duplicate IDs deduped (no file lock contention) |
| OpenClaw gateway dies mid-delegate | `tests/test_16_openclaw_proxy_failure.py` | MCP tool returns `OK=False` with `error.code=SUBPROCESS_FAILED`; v2 envelope with `message_type=error` written to inbox |
| Codex CLI returns quota_exhausted | `tests/test_17_codex_quota_handoff.py` | MCP tool detects signal; writes `error` envelope with `code=quota_exhausted`; handoff flag recorded |
| Codex Desktop thread_id is stale | `tests/test_18_codex_desktop_stale_thread.py` | MCP tool returns `error.code=THREAD_NOT_FOUND`; v2 envelope reflects failure |

## 8. Baseline summary

- **Total live bridge-related processes (Python + Node + exe)**: 7 claude.exe + 6 launcher + 6 in-process MCP + 7 daemon + 14 polling + 1 supervisor + 1 workbuddy + 2 openclaw + 1 cua_node + ~45 npx-cli's (playwright/github/filesystem/memory/sequential-thinking/atlascloud MCP servers, mostly CC-scoped) = **~90 bridge-related processes**.
- **Live v2 envelopes in flight**: 3 (1 inbox stuck, 2 outbox stranded).
- **Live handoff/ envelopes in flight**: 0 (all inboxes empty).
- **Test suite**: 55/55 PASS per R320.6 Codex verification (2026-09-29T05:13Z). Not re-executed in this audit (CC sandbox blocks).
- **Watcher coverage gaps**: v2 supervisor NOT covered; aios_interop_launcher NOT covered; MCP servers NOT covered.