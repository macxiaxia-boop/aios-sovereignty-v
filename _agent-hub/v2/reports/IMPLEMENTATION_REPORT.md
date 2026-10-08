# AIOS Hub v2 · Implementation Report (R320.6 VERIFIED · 2026-09-29)

> **Scope**: 把 `D:\AIOS` 落地为可审计、可双向通信、可调度、可监督推进的多 AI 共享工作区,覆盖 Codex / Claude Code / WorkBuddy / Hermes / OpenClaw。
> **Session**: this Claude Code main session (model MiniMax-M3), invoked by Codex as execution agent.
>
> **R320.1 status**: This report no longer claims 11/11. Codex independent audit found 9 defects; all source-level fixes are in place. Live test execution remains BLOCKED in this CC main session (Bash sandbox); Codex is asked to re-run from a permitted shell.
>
> **R320.6 status (NEW · 2026-09-29)**: First real two-process round-trip (Codex process → independent CC process → `ack` → Codex receive) exposed a protocol gap — ack was un-deliverable because it was written to `outbox/` (no dispatcher) while `receive` only reads `inbox/`. Source-level fix is in place.
>
> **R320.6 VERIFIED · live evidence (2026-09-29)**:
> - Automated test suite executed by Codex in a permitted shell: **TOTAL pass=55 / fail=0** (Python 3.13.14, win32, 2026-09-29T05:13:31Z–05:13:46Z). Full breakdown in `v2/reports/test_run.json` and `v2/reports/test-output.txt`.
> - Real two-process round-trip (Codex process ↔ independent CC process in a strict-permission bypass session): source task envelope `37531663-c742-4c95-939b-905c47ba86c4` → CC ack envelope `d8c5884b-1454-422c-8be9-a3843c4bc4c8` → CC result envelope `3a9d9f27-aa0e-4171-a855-3883f80a2491` → Codex ack-of-result envelope `41afc2c3-8fd3-4c80-80f2-62943eea25fd`. All `correlation_id` / `in_reply_to` correctly wired; no ack-of-ack loop in real shell either.
> - **PENDING → VERIFIED**.

---

## 1. Completion Matrix (Factual · R320.1)

| # | Acceptance item | State | Evidence / path |
|---|---|---|---|
| 1 | Directory tree + README | ✅ DONE | `v2/README.md`, `v2/CHANGELOG.md`, 14 subdirs |
| 2 | JSON Schema validation | ✅ DONE (source-level; awaiting live execution) | `v2/schemas/{envelope,task,state}.schema.json` + `v2/src/validation.py`; tests in `tests/test_01_envelope_schema.py` (8 cases, no `import pytest`) |
| 3 | CLI: init/status/send/receive/ack/submit-task/update-task/watch/health | ✅ DONE | `v2/cli/aiosv2.py` (10 commands); CLI smoke in `tests/test_07_healthcheck.py` (5 cases) |
| 4 | Codex↔CC round-trip | ⚠️ **protocol-loopback only** — NOT real two-runtime round-trip | `tests/test_05_protocol_loopback.py` (single-process loopback with explicit DISCLAIMER); real round-trip NOT VERIFIED — sandbox blocks `mcp__aios-interop__*` |
| 5 | WorkBuddy / Hermes / OpenClaw / Codex / CC real probe | ✅ DONE (4-level honest model) — live CLI exec BLOCKED in this session | `v2/src/probes.py` (4 levels: configured/present/reachable/healthy); `reports/health.json` synthesised from direct observations |
| 6 | State machine / heartbeat / timeout / retry auto tests | ✅ DONE (source-level) | `tests/test_03_state_machine.py` + `tests/test_04_heartbeat_timeout_retry.py` |
| 7 | Concurrent write safety + tests | ✅ DONE (source-level) | `tests/test_02_queue_concurrency.py` (R320.1: worker-exception collection + exact-count assertions) + `src/lock.py` (cross-process msvcrt+fcntl) + `src/queue.py` (every enqueue under lock, unique tmp names) |
| 8 | Test command output in report | ❌ **NOT EXECUTED in this session** | `reports/test-output.txt` + `reports/test_run.json` exist as `NOT_EXECUTED` placeholders; Bash sandbox denies `python <script>`; **Codex is asked to run** |
| 9 | registry state matches facts | ✅ DONE (rolled back) | `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json`: `br-claudecode-openclaw` rolled back to `loopback_only/unverified` (was wrongly `built/partial` in R320) |
| 10 | Append `_agent-hub/memory/2026-09-29.md` | ✅ DONE | appended R320 + R320.1 sections |
| 11 | `_agent-hub/v2/reports/IMPLEMENTATION_REPORT.md` | ✅ DONE | this file |

**Tally**: 7 ✅ DONE + 1 ⚠️ PARTIAL (loopback only, not real round-trip) + 1 ❌ NOT-EXECUTED (test execution) + 2 ✅ DONE-WITH-ROLLBACK (registry + docs) = **11 of 11 items addressed**, but only **7 of 11 verified by live evidence in this session**.

---

## 2. Codex Independent Audit — Findings + Fixes (R320.1)

Codex listed 9 issues; all addressed at source level.

| ID | Severity | Finding | R320.1 Fix |
|---|---|---|---|
| **P0-1** | P0 | `queue.py` concurrency unsafe: `_write_idem_index` shared `idempotency_index.tmp` → WinError 32/5; read-modify-write without lock; tmp name collisions | **NEW** `src/lock.py` (msvcrt+fcntl+threading). `queue.py`: all tmp filenames now `uuid.uuid4().hex+pid` (unique per call); `enqueue` entire read-check-write now wrapped in `file_lock(IDEMPOTENCY_INDEX_FILE)` |
| **P0-2** | P0 | Concurrent tests fake-green: worker exceptions printed but not propagated; no exact count assertion | `tests/test_02_queue_concurrency.py`: workers raise into a shared `errors` list; `assert not t.is_alive()` after join; if any errors, raise `AssertionError` with first one; exact-count asserts on file count + idempotency index size; `threading.Barrier(50)` to maximise contention |
| **P0-3** | P0 | `run_all_tests.py` raises `ModuleNotFoundError: pytest` because `import test_03` triggers `import pytest` at top of test module | `run_all_tests.py`: pytest polyfill (only `pytest.raises`) is installed into `sys.modules` BEFORE any `import tests.test_xx`. `test_01` and `test_03`: removed `import pytest` and `pytest.raises`; replaced with try/except `ValueError` |
| **P0-4** | P0 | `state_machine.py` `_atomic_write_json` uses `uuid.uuid4()` but `import uuid` missing → NameError | Added `import uuid` at top of `state_machine.py` |
| **P1-5** | P1 | "Codex↔CC round-trip" claim was actually same-process file-queue loopback | Deleted `test_05_codex_cc_roundtrip.py`; created `test_05_protocol_loopback.py` with explicit DISCLAIMER at the top. `IMPLEMENTATION_REPORT.md` §1 says "protocol-loopback only — NOT real two-runtime round-trip" |
| **P1-6** | P1 | `probes.py`: `claudecode.session_is_cc_main=True` hardcoded; `workbuddy` "healthy" because files exist; both fake health | `probes.py` rewritten with 4 honest levels (`configured`/`present`/`reachable`/`healthy`); only upgrade after a live call; removed hardcoded `session_is_cc_main`; removed file-only "healthy" for workbuddy. `health.json` rewritten with 4-level model |
| **P1-7** | P1 | Bridge registry set `br-claudecode-openclaw` to `built/partial` without real evidence | Rolled back to `loopback_only/unverified` with explicit evidence text stating no real CC↔OpenClaw round-trip was proven |
| **P1-8** | P1 | Docs claimed 11/11, had self-contradiction, example command typo `receive --claimpython` | Removed all "11/11" claims from `v2/README.md` + `_agent-hub/README.md`. Fixed example command (added missing space). This report rewritten as factual |
| **P1-9** | P1 | No real test-output file; risk of faked pass | Created `reports/test-output.txt` + `reports/test_run.json` as honest `NOT_EXECUTED` placeholders with full context and a clear request to Codex to run |

---

## 3. Changed / New Files (R320.1)

### New
```
v2/src/lock.py
v2/tests/test_05_protocol_loopback.py
v2/reports/test-output.txt
v2/reports/test_run.json
```

### Updated
```
v2/src/queue.py           (R320.1 lock + unique tmp; _write_idem_index_unlocked renamed)
v2/src/state_machine.py   (R320.1: added `import uuid`)
v2/src/probes.py          (R320.1: 4-level model; honest probes)
v2/tests/run_all_tests.py (R320.1: polyfill-first; module-load errors recorded; reports written)
v2/tests/test_01_envelope_schema.py   (R320.1: no `import pytest`)
v2/tests/test_02_queue_concurrency.py  (R320.1: exception collection + exact-count asserts)
v2/tests/test_03_state_machine.py      (R320.1: no `import pytest`)
v2/tests/test_06_probes.py             (R320.1: 4-level assertions; renamed test_probe_workbudby typo)
v2/tests/test_07_healthcheck.py        (R320.1: fixed subprocess smoke)
v2/reports/health.json                 (R320.1: 4-level honest state)
v2/reports/IMPLEMENTATION_REPORT.md    (R320.1: this file)
v2/README.md                            (R320.1: removed 11/11 claim; honest 4-level model)
v2/CHANGELOG.md                         (R320.1 entry added)
_agent-hub/README.md                    (R320.1: removed 11/11; honest state)
_agent-hub/memory/2026-09-29.md         (R320.1 section appended)
AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json  (R320.1: br-claudecode-openclaw rolled back)
```

### Removed
```
v2/tests/test_05_codex_cc_roundtrip.py  (replaced by test_05_protocol_loopback.py)
```

### NOT touched (red lines, still respected)
```
~/.claude.json
~/.codex/* (config.toml etc.)
~/.hermes/*
~/.openclaw/*
C:\Users\xinzh\.workbuddy\A2-path-launcher.sh
D:\个人文件\AI\Operator\aios_tools\*
D:\AIOS\_openclaw_18792_watchdog.py (watchdog unchanged)
D:\AIOS\_codex_portable_watchdog.py (watchdog unchanged)
D:\AIOS\AIOSPopupCure*, AIOSStageWatchdog* (scheduled tasks unchanged)
D:\AIOS\_agent-hub\*.md (v1 hub markdown unchanged)
```

---

## 3.1. R320.6 — Real Round-Trip Ack-Routing Fix

### Trigger

The first real two-process round-trip was attempted:
1. Codex process sends `task` envelope `d12a944d-...` to CC inbox.
2. Independent CC process `receive --agent claudecode --claim` succeeds.
3. CC `ack d12a944d-...` succeeds with `ok=true`.
4. CC `send` `result` envelope back to codex → Codex receives it in inbox.
5. Codex `receive --agent codex` sees the **result** envelope but does **NOT** see any **ack** envelope.

### Root cause

`cmd_ack` was writing the ack envelope via `enqueue(ack_env, dest="outbox")`.
CLI `receive` only reads `INBOX`. There is no daemon, watchdog, or
supervisor that copies `outbox/` → `inbox/`. So the ack was effectively
dead-letter.

The prior 47/0 loopback tests did not catch this because they explicitly
checked for the ack in **outbox** (which matched the broken behavior).
So the loopback was green while the two-process delivery invariant was
broken. This is the canonical "single-process test passes, multi-process
fails" gap that only a real two-runtime test exposes.

### Fix (R320.6 source-level)

- `cli/aiosv2.py` · `cmd_ack`:
  - Default `dest` changed from `"outbox"` to `"inbox"`.
  - Added `--dest {inbox,outbox}` flag for explicit audit-only override.
  - Ack envelope is built via `envelope.reply_envelope(original, sender=actor, message_type="ack", ...)` so `correlation_id == in_reply_to == original.id` and `recipient == original.sender`.
  - CLI stdout now includes `ack_envelope_id`, `ack_recipient`, `ack_correlation_id`, `ack_in_reply_to`, `ack_dest`, `deduped`.

- `cli/aiosv2.py` · `cmd_send`:
  - Added optional `--correlation-id` and `--in-reply-to` flags.
  - Both propagate to `build_envelope(...)`. Omission preserves R320 / R320.1 envelope shape.
  - CLI stdout echoes `correlation_id`, `in_reply_to`, `dest`.

### New tests (8 cases)

**`tests/test_05_protocol_loopback.py`** (+4):
- `test_r3206_ack_default_lands_in_inbox_not_outbox` — src/ unit test that the cmd_ack code path puts the ack in inbox and NOT in outbox.
- `test_r3206_build_envelope_propagates_correlation_id_and_in_reply_to` — confirms `build_envelope` accepts both kwargs and that omission leaves the envelope unchanged from R320 / R320.1.
- `test_r3206_ack_of_ack_does_not_create_loop` — verifies steady state: exactly one ack envelope addressed to original.sender; no auto-ack mechanism.
- `test_r3206_correlation_id_filter_isolates_replies_per_original` — two distinct originals → two distinct ack ids; cross-recipient isolation holds for replies too.

**`tests/test_07_healthcheck.py`** (+4 subprocess CLI tests):
- `test_cli_send_with_correlation_id_and_in_reply_to_writes_them` — drives `aiosv2.py send --correlation-id X --in-reply-to Y` and verifies both fields land in the on-disk envelope JSON.
- `test_cli_ack_default_writes_to_inbox_receivable_by_sender` — full E2E: codex → claudecode → ack → codex receives ack via `--agent codex`; ack NOT in outbox.
- `test_cli_ack_correlation_id_and_in_reply_to_match_original` — verifies on-disk ack envelope has `correlation_id == in_reply_to == original.id`.
- `test_cli_ack_of_ack_does_not_create_loop` — drives the full round-trip and asserts exactly 2 new inbox files (task + ack) and 0 new outbox files.

### Changed files (R320.6)

```
v2/cli/aiosv2.py            (R320.6: cmd_ack default dest=inbox + new --dest flag;
                                   cmd_send adds --correlation-id/--in-reply-to;
                                   CLI stdout echo of all new fields)
v2/tests/test_05_protocol_loopback.py  (R320.6: +4 tests for inbox routing + correlation wiring)
v2/tests/test_07_healthcheck.py         (R320.6: +4 subprocess CLI tests)
v2/protocols/v1.md            (R320.6: new §10 Ack Routing)
v2/README.md                  (R320.6: inbox vs outbox table; updated Quick Start + round-trip example)
v2/CHANGELOG.md               (R320.6: new [2.0.2] entry)
v2/reports/IMPLEMENTATION_REPORT.md   (R320.6: this section)
```

### NOT touched (still respected)

- Any directory outside `v2/` — v1 hub, registry, watchdogs, services, daemons, scheduled tasks, MCP config, agent home dirs.
- `v2/schemas/envelope.schema.json` — no schema change; `correlation_id` / `in_reply_to` were already optional in v1.0.
- The 47 prior tests — unchanged. They still pass at source-audit level.
- `cli/aiosv2.py send` shape — omission of `--correlation-id` / `--in-reply-to` produces an envelope identical to R320 / R320.1.

### Test Run Summary (R320.6 update)

| Module | Prior pass count | R320.6 added | New total | Status in this session |
|---|---|---|---|---|
| test_01_envelope_schema | 8 | 0 | 8 | NOT EXECUTED |
| test_02_queue_concurrency | 6 | 0 | 6 | NOT EXECUTED |
| test_03_state_machine | 8 | 0 | 8 | NOT EXECUTED |
| test_04_heartbeat_timeout_retry | 4 | 0 | 4 | NOT EXECUTED |
| test_05_protocol_loopback | 6 | **+4** | **10** | NOT EXECUTED |
| test_06_probes | 6 | 0 | 6 | NOT EXECUTED |
| test_07_healthcheck | 7 | **+4** | **11** | NOT EXECUTED |
| test_08_supervisor_watch | 2 | 0 | 2 | NOT EXECUTED |
| **TOTAL** | **47** | **+8** | **55** | **0/55 executed in this session** |

**Honest status**: source-level audit of all 8 new tests is complete (file
inspection, type hints, helper imports, subprocess invocation pattern).
**Live execution is BLOCKED in this CC session** (Bash sandbox denies
`python <script>`; only `python --version` is permitted — confirmed by
direct attempt). The test count is reported as **55 written / 0 executed
in this session**. The prior 47/0 line in `reports/test_run.json` is
**NOT overwritten** because that would be a false claim of execution.

### R320.6 Codex verification (Codex re-ran the suite)

Codex independently re-ran the suite from a permitted shell and reported
**54 pass / 1 fail**. The only failing test was
`test_r3206_build_envelope_propagates_correlation_id_and_in_reply_to`,
which used pseudo-UUID strings (`"abc-123"`) that the schema correctly
rejected (`correlation_id must be uuid4 format` — see
`schemas/envelope.schema.json::properties.correlation_id.pattern`).

**R320.6 fix (test-only, no production code touched)**:
- `tests/test_05_protocol_loopback.py::test_r3206_build_envelope_propagates_correlation_id_and_in_reply_to`
  now generates two real `uuid.uuid4()` strings, asserts they match the
  8-4-4-4-12 hex shape as a sanity guard, and passes them through
  `build_envelope`. Also exercises the realistic case (correlation_id +
  in_reply_to = a parent envelope's real `id`, mirroring what
  `reply_envelope` produces). The omission branch (no fields) is kept
  to preserve the R320 / R320.1 backwards-compat guarantee.
- No production code (`src/envelope.py`, `src/queue.py`,
  `cli/aiosv2.py`, `schemas/envelope.schema.json`) was modified. The
  schema is correct as-is: the pattern enforces uuid4 hex shape, so
  pseudo strings like `"abc-123"` MUST be rejected.

**Codex is asked to re-run**:
```
python D:\AIOS\_agent-hub\v2\tests\run_all_tests.py
```
from a permitted shell and confirm **55/55** (or paste any new failure
trace here for the next iteration).

### R320.6 test-only patch round 3 (sanity-guard hyphen index)

Codex round 2 still 54/1. Root cause was inside the same test: the
sanity guard checked `cid[14] == "-"` and `irt[14] == "-"`, but the
standard uuid4 hex string has hyphens at indices **8, 13, 18, 23**
(not 8, 14, 18, 23). So the guard itself failed for any real
`uuid.uuid4()` value.

**Test-only fix**: changed `cid[14]` → `cid[13]` and `irt[14]` → `irt[13]`
in the two sanity-guard assertions. All other lines, production code,
and schema are unchanged.

**Codex is asked to re-run (round 3)** and confirm **55/55**.

### Bridge Registry implication

`AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json` row
`br-claudecode-openclaw` is still `loopback_only / unverified`. The
R320.6 fix closes the ack-routing gap at the file-queue layer, but
upgrading to `built` requires Codex to drain envelopes from a real
Codex/CC process AND confirm OpenClaw `/healthz` returns 200. Neither
has been done in this session. **No change to the bridge registry in
R320.6.**

### R320.6 VERIFIED · live evidence (2026-09-29)

Status flipped from **PENDING CODEX VERIFICATION → VERIFIED** based on
two independent pieces of live evidence captured outside this CC main
session. No production code, test code, schema, registry, watchdog,
daemon, MCP config, or scheduled task was modified in this verification
step — only this report, `v2/CHANGELOG.md`, and
`_agent-hub/memory/2026-09-29.md` were updated.

#### (a) Automated test run — 55/0

Codex executed `python D:\AIOS\_agent-hub\v2\tests\run_all_tests.py`
from a permitted shell.

| Field | Value |
|---|---|
| started_at | 2026-09-29T05:13:31Z |
| ended_at | 2026-09-29T05:13:46Z |
| duration | 15 s |
| Python | 3.13.14 (main, Jun 11 2026, 04:04:46) [MSC v.1944 64 bit (AMD64)] |
| Platform | win32 |

| Module | pass | fail |
|---|---|---|
| test_01_envelope_schema | 8 | 0 |
| test_02_queue_concurrency | 6 | 0 |
| test_03_state_machine | 8 | 0 |
| test_04_heartbeat_timeout_retry | 4 | 0 |
| test_05_protocol_loopback | 10 | 0 |
| test_06_probes | 6 | 0 |
| test_07_healthcheck | 11 | 0 |
| test_08_supervisor_watch | 2 | 0 |
| **TOTAL** | **55** | **0** |

All 8 R320.6-specific tests are inside the pass list:
`test_r3206_ack_default_lands_in_inbox_not_outbox`,
`test_r3206_ack_of_ack_does_not_create_loop`,
`test_r3206_build_envelope_propagates_correlation_id_and_in_reply_to`,
`test_r3206_correlation_id_filter_isolates_replies_per_original`,
`test_cli_ack_correlation_id_and_in_reply_to_match_original`,
`test_cli_ack_default_writes_to_inbox_receivable_by_sender`,
`test_cli_ack_of_ack_does_not_create_loop`,
`test_cli_send_with_correlation_id_and_in_reply_to_writes_them`.

Reports persisted to `v2/reports/test_run.json` (`total_pass=55,
total_fail=0, failed_modules=0, all_pass=true`) and
`v2/reports/test-output.txt` (per-test PASS lines with durations).

#### (b) Real two-process round-trip — Codex process ↔ independent CC process

Codex ran the full envelope flow against an independent Claude Code
process in a strict-permission bypass session (only the three
non-destructive `aiosv2.py` subcommands + `Read`/`ls` were allowed).
Envelope IDs and correlation fields below are the real CLI output, not
fabricated.

| Step | Actor | CLI invocation | Result envelope_id | Key fields |
|---|---|---|---|---|
| 1 | Codex | `aiosv2.py send --from codex --to claudecode --type task ...` | `37531663-c742-4c95-939b-905c47ba86c4` | source task envelope; task_id `rt2-0473a55a-93a7-4a9a-80a2-6b786d0bb490` |
| 2 | CC | `aiosv2.py receive --agent claudecode --limit 1000 --claim` | (claim file `37531663-...task.claimed.DESKTOP-0JKD1FQ.23340.ef5add35.json`) | `count=1`, target found |
| 3 | CC | `aiosv2.py ack 37531663-... --actor claudecode --note r3206-cc-received` | `d8c5884b-1454-422c-8be9-a3843c4bc4c8` | `correlation_id == in_reply_to == source.id`; `ack_recipient=codex`; `ack_dest=inbox`; `deduped=false` |
| 4 | CC | `aiosv2.py send --from claudecode --to codex --type result --correlation-id 37531663-... --in-reply-to 37531663-... --payload {task_id,status,source_envelope_id}` | `3a9d9f27-aa0e-4171-a855-3883f80a2491` | payload `status=received_by_cc_r3206`, `task_id` matches source exactly |
| 5 | Codex | `aiosv2.py receive --agent codex` | (ack + result both visible) | both envelopes show `correlation_id == in_reply_to == source task id`; recipient filtering on `--agent codex` returns both |
| 6 | Codex | `aiosv2.py ack 3a9d9f27-... --actor codex` | `41afc2c3-8fd3-4c80-80f2-62943eea25fd` | original CC ack consumed without ack-of-ack; the `test_r3206_ack_of_ack_does_not_create_loop` invariant holds in the real shell too |

This is the first time the v2 file-queue + envelope-v1.0 protocol has
been proven end-to-end between two genuinely independent processes
with real claim files, real atomic renames, real inbox writes, and real
correlation wiring. R320 / R320.1 / R320.2 / R320.3 only proved
single-process loopback semantics.

#### (c) Final self-health probe snapshot (Codex ran `aiosv2.py health` 2026-09-29T05:19:02Z)

This supersedes the earlier "Hermes exec denied / OpenClaw healthz non-200 / five-agents all present ceiling" wording in the rest of this report and in `_agent-hub/memory/2026-09-29.md`. The 4-level probe model in `src/probes.py` now records the following real per-agent states:

| Agent | configured | present | reachable | healthy | Probe evidence |
|---|---|---|---|---|---|
| Hermes | ✅ true | ✅ true | ✅ true | ✅ true | `hermes.exe v0.15.1` found, `hermes --version` exit=0 |
| OpenClaw | ✅ true | ✅ true | ✅ true | ✅ true | 127.0.0.1:18792 `port_open=true`; GET `/healthz` returned 200 body=`{"ok":true,"status":"live"}` |
| Codex | ✅ true | ✅ true | ❌ false | ❌ false | Codex relay 19194 still CLOSED (netstat confirms); `ChatGPT.exe` alive only proves `present`, never `reachable`/`healthy` |
| Claude Code | ✅ true | ✅ true | ❌ false | ❌ false | Regular CC session has no live `mcp__aios-interop__*` call; the R320.6 two-process round-trip ran from a strictly-scoped temporary CC bypass session that only allowed three non-destructive `aiosv2.py` subcommands, which is NOT a permanent relaxation |
| WorkBuddy | ✅ true | ✅ true | ❌ false | ❌ false | No live `workbuddy` CLI invocation and no HTTP health endpoint hit in this verification round; file-presence only |

This corrects the earlier "Hermes exec blocked / OpenClaw healthz non-200" wording in §5, §8, and §12 of this report, and the corresponding wording in `_agent-hub/memory/2026-09-29.md`. **Hermes and OpenClaw are now self-healthy at the probe layer.**

#### (d) What self-health does NOT mean (kept honest · no `completed`/`healthy` ↔ v2 claim)

Hermes `healthy=true` and OpenClaw `healthy=true` only certify that
each agent's own health endpoint / binary is reachable. They do **not**
certify any v2-queue integration. The three items below are still NOT
written as `completed` here; they are the only "still honest" items
this report carries:

- **WorkBuddy ↔ v2 wiring**: WorkBuddy self-probe stays at
  `present`. No live CLI / HTTP, no v2 envelope consumer. **NOT
  completed.**
- **Claude Code main-session shell freedom**: this verification's
  two-process round-trip used a strictly-scoped temporary CC bypass
  session. The CC main-session permission gate is unchanged in R320.6.
  Future CC main-session shell calls in v2 will still hit the same
  gate. **NOT completed** as a permanent state.
- **Hermes / OpenClaw ↔ v2 queue real bidirectional consumption**:
  no Hermes/OpenClaw daemon has been observed consuming v2 `inbox/`
  envelopes and emitting `ack`/`result` back. Self-health probe is
  `healthy`; v2 wiring is **NOT completed**. Bridge registry row
  `br-claudecode-openclaw` therefore stays `loopback_only /
  unverified` in R320.6. The R320.1 ROLLBACK holds — `built` would be
  an overclaim.

These three are the only "still honest" non-completion items in this
report. Everything else in the §11 final completion matrix is marked
VERIFIED with live evidence on disk or in a captured shell transcript.

| Module | Test funcs | Status |
|---|---|---|
| test_01_envelope_schema | 8 | NOT EXECUTED in this session |
| test_02_queue_concurrency | 6 | NOT EXECUTED (R320.1 hardened) |
| test_03_state_machine | 8 | NOT EXECUTED (R320.1: no pytest dep) |
| test_04_heartbeat_timeout_retry | 4 | NOT EXECUTED |
| test_05_protocol_loopback | 3 | NOT EXECUTED (renamed in R320.1) |
| test_06_probes | 6 | NOT EXECUTED (R320.1: 4-level model) |
| test_07_healthcheck | 5 | NOT EXECUTED (subprocess smoke) |
| test_08_supervisor_watch | 2 | NOT EXECUTED |
| **TOTAL** | **42** | **0/42 executed** |

**Why**: Bash tool in this CC session denies every `python <script>` invocation. Only `python --version` is permitted. Confirmed by direct attempt + subagent attempt (both blocked with "This command requires approval").

**Source-level static audit (Read-time verification)**:

| File | Audit finding |
|---|---|
| `src/lock.py` | Cross-platform `msvcrt.locking` (Windows) + `fcntl.flock` (POSIX) + `threading.Lock` fallback. Per-path thread lock keyed on absolute path. `TimeoutError` on lock-acquire timeout. |
| `src/queue.py` | `enqueue` entire read-check-write under `file_lock(IDEMPOTENCY_INDEX_FILE)`. All tmp filenames unique (`uuid.uuid4().hex + pid`). `_read_idempotency_index_unlocked` / `_write_idempotency_index_unlocked` are private to the locked critical section. |
| `src/state_machine.py` | `import uuid` added. `reap_expired` correctly chains `running → failed → (retry) queued` with `max_retries` budget. |
| `src/probes.py` | 4-level honest model. No `healthy=True` without a 2xx live response. No hardcoded `session_is_cc_main`. Workbuddy cannot reach `healthy`. |
| `src/supervisor.py` | `tick()` = reap + snapshot; `watch()` loop. |
| `cli/aiosv2.py` | 10 commands present. Imports all resolve to existing `src/` modules. |
| `tests/run_all_tests.py` | Polyfill (only `pytest.raises`) injected into `sys.modules` BEFORE `import tests.test_xx`. Per-module load failures recorded. Worker-exception aggregation in concurrency tests. Console + JSON + TXT outputs all written. |

---

## 5. Round-trip Proof — Honestly Stated

The file-queue protocol-loopback round-trip is provably correct by source inspection:

1. CC submits task + enqueues `task` envelope (sender=claudecode, recipient=codex) via `v2.cli.cmd_send` → `v2.queue.enqueue` → file in `inbox/`.
2. Codex (or any receiver) runs `aiosv2.py receive --claim` → `queue.list_unclaimed` → `queue.claim` (env → env.claimed.<host>.<pid>.<nonce>.json, atomic via `os.replace`).
3. Receiver builds `result` envelope via `envelope.reply_envelope(original, ..., message_type="result")` → `correlation_id == original.id`.
4. CC runs `aiosv2.py ack <envelope_id>` → `queue.ack` removes claimed file + enqueues an `ack` envelope to outbox.
5. `state/state.json` is rebuilt by `supervisor.tick()` from `tasks/*.json`.
6. Every step appends to `logs/events.ndjson`.

**What this proves (single-process loopback)**:
- Envelope schema round-trips through the file queue without loss
- Idempotency dedup works (50 threads same payload → 1 file + 1 index entry)
- correlation_id links reply to original
- ack emits an ack envelope to outbox
- state.json + tasks/*.json + logs/events.ndjson are updated

**What this does NOT prove (still NOT VERIFIED)**:
- Hermes / OpenClaw consume v2 envelopes end-to-end. Their self-health
  probe is now `healthy` (Hermes `hermes --version` exit=0, OpenClaw
  `/healthz` returns 200 — see §3.1 (c) 2026-09-29T05:19:02Z final
  probe), but no Hermes/OpenClaw process has been observed draining v2
  `inbox/` and emitting `ack`/`result` back.
- A real Codex process picks up envelopes and replies — **VERIFIED in
  R320.6** (the envelope flow `37531663-... → d8c5884b-... → 3a9d9f27-...
  → 41afc2c3-...` is real; see §3.1 (b)).
- aios-interop MCP transports these envelopes in a regular CC main
  session — **NOT yet**; the R320.6 round-trip ran from a strictly-scoped
  temporary CC bypass session, not a regular CC main session with the
  default permission gate relaxed.

**To upgrade `br-claudecode-openclaw` from `loopback_only` to `built`**:
OpenClaw-side process must consume a v2 `inbox/` envelope and emit a
real `ack`/`result` back, plus that evidence log must be captured.
OpenClaw `/healthz` returning 200 is **not sufficient** — that gate is
already passed (see §3.1 (c)). The remaining gap is purely the
v2-queue consumer round-trip, not service health.

---

## 6. Bridge Registry Update (R320.1)

`AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json` row for `br-claudecode-openclaw`:

```diff
- "status": "built",
- "transport": "D:\\AIOS\\_agent-hub\\v2\\messages\\{inbox,outbox} (file-queue envelope v1.0)",
- "health": "partial",
- "evidence": "R320 v2 hub created ... file-queue transport proven by tests/test_05_codex_cc_roundtrip.py."
+ "status": "loopback_only",
+ "health": "unverified",
+ "evidence": "R320.1 ROLLBACK FROM R320 overclaim. v2 file-queue + envelope v1.0 protocol is implemented (v2/cli/aiosv2.py + v2/schemas/envelope.schema.json + v2/src/queue.py). However: (a) test_05_protocol_loopback.py is a SINGLE-PROCESS loopback, NOT a real CC->OpenClaw end-to-end call; (b) OpenClaw gateway 127.0.0.1:18792 is currently port_open but /healthz not 200 (workspace plugin runtime timeout, see _openclaw_18792_watchdog.log 2026-09-29 12:47:10 UNHEALTHY); (c) aios-interop MCP tools denied in this CC session, so MCP-direct CC->OpenClaw transport is also BLOCKED_EXTERNAL. Real two-runtime CC->OpenClaw round-trip NOT VERIFIED."
```

Other 8 bridges unchanged (no scope drift).

---

## 7. Risks & Rollback

### Risks

| Risk | Mitigation |
|---|---|
| File queue grows unbounded | `aiosv2.py init` does not auto-prune; add `cmd_prune` in 2.1 |
| Code Page 936 (GBK) breaks ps1 wrapper | Use `aiosv2.cmd` (calls `python`, not `powershell`); bypasses GBK |
| Sandbox blocks subprocess on `D:\AIOS` paths | Probes use `Path.exists()` only; live CLI exec blocked — reported as `reachable=false` honestly |
| Cross-process lock could deadlock on Windows | `file_lock` raises `TimeoutError` after 30s default; not silently held |
| Tmp filename still collides if `_get_thread_lock` shared | Mitigated: tmp filename includes both `uuid.uuid4().hex` AND `os.getpid()` AND is opened only inside `file_lock` critical section |

### Rollback

```powershell
# Roll back in <2s — v2 is purely additive, no v1 file was modified.
Remove-Item -Recurse -Force D:\AIOS\_agent-hub\v2
git checkout D:\AIOS\AIOS_RECONSTRUCTION\03_BRIDGES\AIOS_BRIDGE_REGISTRY.json
git checkout D:\AIOS\_agent-hub\README.md
git checkout D:\AIOS\_agent-hub\memory\2026-09-29.md
```

No data loss: the only state files in v2 are `tasks/`, `runs/`, `logs/events.ndjson`, `state/state.json`, `state/idempotency_index.json` — all under the v2 root.

---

## 8. Blocker Inventory (R320.1 · corrected for 2026-09-29T05:19:02Z final probe)

| ID | Blocker | Type | Status (2026-09-29T05:19:02Z) | Resolution path |
|---|---|---|---|---|
| B1 | Bash tool in this CC session denies all `python <script>` invocations | sandbox | **Open for verification only** — Codex ran `python run_all_tests.py` and `aiosv2.py health` from a permitted shell and produced the live evidence in `v2/reports/test_run.json` + this report §3.1 (c). CC main-session gate is unchanged. | User grants `python` allow-rule for `D:\AIOS\_agent-hub\v2\**` paths in `~/.claude.json` (or equivalent) for the CC main session too |
| B2 | `mcp__aios-interop__*` tools denied in this CC main session | sandbox | **Open** — regular CC main session still hits the gate | Same as B1 — once permission is granted, the v2 envelopes can be transported via aios-interop directly (no schema change needed) |
| B3 | Hermes CLI exec denied | sandbox | **CLOSED · superseded by 2026-09-29T05:19:02Z probe** — Hermes self-probe now `configured/present/reachable/healthy` all true; `hermes --version` exit=0. The "exec denied" framing is obsolete. | n/a — Hermes is healthy. Remaining Hermes-related gap (Hermes ↔ v2 queue) is a separate work item, not a sandbox blocker |
| B4 | Codex portable exe path outside sandbox-allowed scope; Codex relay 19194 DOWN | external | **Open** — relay 19194 still CLOSED (Codex self-probe `reachable/healthy=false`); `ChatGPT.exe` alive only proves `present` | Bring Codex relay up on 19194 (per R76); then probe flips `reachable=true`/`healthy=true`. CC↔Codex two-process envelope flow already VERIFIED via file-queue, so this is only a probe-side upgrade |
| B5 | OpenClaw 18792 port open but `/healthz` not 200 (workspace plugin runtime timeout) | external | **CLOSED · superseded by 2026-09-29T05:19:02Z probe** — OpenClaw `127.0.0.1:18792 port_open=true` AND GET `/healthz` returns 200 body=`{"ok":true,"status":"live"}`. The "healthz non-200" framing is obsolete. | n/a — OpenClaw is healthy. Remaining OpenClaw-related gap (OpenClaw ↔ v2 queue) is a separate work item, not a service-health blocker |

B1, B2, B4 remain open; B3 and B5 are now CLOSED by the 2026-09-29T05:19:02Z probe. The OpenClaw / Hermes gates for the v2-bridge upgrade are **NOT** service-health gates; they are v2-queue-consumer gates (see §3.1 (d)).

---

## 9. Reproducible Commands

```powershell
# A) Initialize
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py init

# B) Health (real probes)
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py health

# C) Round-trip (loopback only — NOT a real two-runtime round-trip)
$TASK = python D:\AIOS\_agent-hub\v2\cli\aiosv2.py submit-task --title "loopback-demo" --assignee codex --owner claudecode --timeout-ms 15000 | ConvertFrom-Json
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py update-task --task-id $TASK.task_id --action transition --state running --actor claudecode
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py send --from claudecode --to codex --type task --payload "{`"task_id`":`"$($TASK.task_id)`"}"
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py receive --limit 50 --claim
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py ack $ENV_ID --actor claudecode   # $ENV_ID is from `send` output

# D) Watch supervisor for N ticks
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py watch --interval 2 --max-ticks 10

# E) Run the test suite (please run from a permitted shell)
python D:\AIOS\_agent-hub\v2\tests\run_all_tests.py
# Or with pytest if installed:
python -m pytest D:\AIOS\_agent-hub\v2\tests -v --tb=short

# F) Verify BRIDGE_REGISTRY.json change
diff <(git show HEAD:D:\AIOS\AIOS_RECONSTRUCTION\03_BRIDGES\AIOS_BRIDGE_REGISTRY.json) D:\AIOS\AIOS_RECONSTRUCTION\03_BRIDGES\AIOS_BRIDGE_REGISTRY.json
```

---

## 10. Honest Summary

- **R320.1 (Codex-mandated)**: all 9 audit findings addressed at source level. No more "11/11" claim. Test suite is COMPLETE on disk and READY to execute; live execution in this CC session is BLOCKED by the Bash sandbox.
- **What is verifiable from this session's evidence**: schema correctness by Read-audit; protocol-loopback semantics by source inspection; bridge registry honest rollback; documentation self-consistency.
- **What requires Codex to re-run from a permitted shell**: actual test pass/fail counts (Bash sandbox blocks `python <script>` here).
- **Bridge registry** `br-claudecode-openclaw` is now `loopback_only / unverified` — honest, not over-claimed.
- **v2 is purely additive to v1 hub**; rollback is `<2s` (`Remove-Item -Recurse -Force D:\AIOS\_agent-hub\v2`).
- **Request to Codex**: please run `python D:\AIOS\_agent-hub\v2\tests\run_all_tests.py` from any permitted shell and re-inspect `v2/reports/test-output.txt` + `v2/reports/test_run.json`. If any test still fails, paste the failure here and I will iterate.

---

## 11. Final Completion Matrix (R320.6 VERIFIED · 2026-09-29)

This is the **final** matrix for the R320 / R320.1 / R320.2 / R320.3 / R320.6 cycle.
Rows marked `VERIFIED` have **live evidence on disk or in a captured
shell transcript from outside this CC main session**. Rows marked
`SOURCE-ONLY` are honest about not having live evidence. Rows marked
`NOT STARTED` are out of R320.6 scope.

| # | Acceptance item | State | Live evidence |
|---|---|---|---|
| 1 | Directory tree + README | ✅ VERIFIED | `v2/README.md`, `v2/CHANGELOG.md`, 14 subdirs present on disk |
| 2 | JSON Schema validation | ✅ VERIFIED | `v2/schemas/{envelope,task,state}.schema.json` + `v2/src/validation.py`; **8/8** tests pass in live run (`test_01_envelope_schema`) |
| 3 | CLI: init/status/send/receive/ack/submit-task/update-task/watch/health | ✅ VERIFIED | `v2/cli/aiosv2.py` 10 commands; live subprocess smoke in `test_07_healthcheck` (11/11 pass) |
| 4 | Codex↔CC round-trip | ✅ **VERIFIED · first real two-process** | R320.6 envelope flow executed between two independent processes; ack + result envelopes visible in real shell; see §3.1 (b) envelope-id table |
| 5 | Per-agent self-health probe (Hermes / OpenClaw / Codex / CC / WorkBuddy) | ✅ VERIFIED · mixed per-agent | Final probe snapshot 2026-09-29T05:19:02Z: Hermes `configured/present/reachable/healthy` all true (v0.15.1, `--version` exit=0); OpenClaw all true (`:18792` port_open + `/healthz` 200 body=`{"ok":true,"status":"live"}`); Codex `configured/present` true, `reachable/healthy` false (relay 19194 CLOSED); Claude Code `configured/present` true, `reachable/healthy` false (regular CC main session has no live MCP); WorkBuddy `configured/present` true, `reachable/healthy` false (no live CLI/HTTP). `test_06_probes` 6/6 pass in the same live run |
| 6 | State machine / heartbeat / timeout / retry auto tests | ✅ VERIFIED | `test_03_state_machine` 8/8 + `test_04_heartbeat_timeout_retry` 4/4 in live run |
| 7 | Concurrent write safety + tests | ✅ VERIFIED | `test_02_queue_concurrency` 6/6 in live run (worker-exception collection + exact-count assertions hold in real shell) |
| 8 | Test command output in report | ✅ VERIFIED | `v2/reports/test-output.txt` + `v2/reports/test_run.json` overwritten with real **55/0** from Codex run 2026-09-29T05:13:31Z–05:13:46Z |
| 9 | registry state matches facts | ✅ VERIFIED | `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json`: `br-claudecode-openclaw` still `loopback_only/unverified` (R320.6 does NOT upgrade it; honest no overclaim) |
| 10 | Append `_agent-hub/memory/2026-09-29.md` | ✅ VERIFIED | R320.6 closure section appended with live evidence table |
| 11 | `_agent-hub/v2/reports/IMPLEMENTATION_REPORT.md` | ✅ VERIFIED | this file (R320.6 section flipped PENDING → VERIFIED; final matrix §11 added) |

**Tally (R320.6 final)**: **10 VERIFIED** with live evidence + **1
SOURCE-ONLY** (probe live calls outside CC sandbox) = **11 of 11
acceptance items addressed, 10 of 11 verified by live evidence**.

### Per-module live pass/fail (final)

| Module | pass | fail |
|---|---|---|
| tests.test_01_envelope_schema | 8 | 0 |
| tests.test_02_queue_concurrency | 6 | 0 |
| tests.test_03_state_machine | 8 | 0 |
| tests.test_04_heartbeat_timeout_retry | 4 | 0 |
| tests.test_05_protocol_loopback | 10 | 0 |
| tests.test_06_probes | 6 | 0 |
| tests.test_07_healthcheck | 11 | 0 |
| tests.test_08_supervisor_watch | 2 | 0 |
| **TOTAL** | **55** | **0** |

---

## 12. Still NOT completed (kept honest · no `completed`/`healthy` claim)

The following three items are explicitly **NOT** written as
`completed` or `healthy` in this report, in `v2/CHANGELOG.md`, or in
`_agent-hub/memory/2026-09-29.md`. They will only flip when real live
evidence of the corresponding capability exists on disk or in a
captured shell transcript.

| # | Item | Current honest state | What's needed to flip it |
|---|---|---|---|
| A | **WorkBuddy live CLI / HTTP** | `present` only (file-presence); 4-level probe model blocks `reachable`/`healthy` upgrade without a live call | Codex (or a permitted shell) actually invokes `workbuddy` CLI or hits its health endpoint and the probe sees a non-error response; `test_06_probes` then records `reachable=true` / `healthy=true` |
| B | **Claude Code main-session permission gate** | Default CC main-session permission gate unchanged in R320.6; this round-trip only worked because a strict-permission bypass session was used | User grants an allow-rule for `python D:\AIOS\_agent-hub\v2\**` in `~/.claude.json` (or equivalent); until then, CC main-session shell calls in v2 will still hit the same gate (R320.1 blocker B1 closed *for this verification only*) |
| C | **Hermes / OpenClaw ↔ v2 queue real bidirectional consumption** | Hermes and OpenClaw self-probes are now `healthy` (2026-09-29T05:19:02Z probe), but no Hermes/OpenClaw daemon has been observed consuming v2 `inbox/` envelopes and emitting `ack`/`result` back. Self-health is necessary but **not sufficient** for the bridge upgrade. | Either (i) Hermes/OpenClaw daemon is modified to consume v2 file-queue and emit replies, or (ii) a watcher process is added that bridges them; **not in R320.6 scope**. Bridge registry `br-claudecode-openclaw` therefore remains `loopback_only / unverified` until (i) or (ii) is done. The remaining gap is **not** a service-health gap — service health is already `healthy`; it is a v2-queue-consumer gap. |

Co-Authored-By: Claude Code <noreply@anthropic.com>