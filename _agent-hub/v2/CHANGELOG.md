# Changelog — AIOS Hub v2

All notable changes to `D:\AIOS\_agent-hub\v2\` are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/).

## [2.0.2] — 2026-09-29 (R320.6 · real round-trip ack-routing fix)

### Context

A real two-process round-trip (Codex process → independent CC process →
CC `ack` → Codex receive) was performed to validate R320.1. It exposed a
protocol gap:

- `cmd_ack` was writing the ack envelope to `outbox/`.
- `receive` only reads `inbox/`.
- No dispatcher copies outbox → inbox.
- **Result**: Codex saw the result envelope in its inbox but never saw the
  ack. The ack was silently un-deliverable.

The earlier 47/0 auto-test pass was not a contradiction: the loopback
test asserted the ack landed in **outbox** (because that is what the
pre-R320.6 code did), and outbox was effectively dead-letter for the
purposes of `receive`. So the loopback test was green while the
two-process delivery invariant was broken. R320.6 closes that gap.

### Fixed

- **`cli/aiosv2.py` · `cmd_ack`**: default `dest` changed from `outbox` →
  `inbox`. The ack envelope is built via `envelope.reply_envelope` so
  `correlation_id` + `in_reply_to` are wired to `original.id` and
  `recipient == original.sender`. Added `--dest {inbox,outbox}` flag so
  the audit-only outbox path is still available explicitly.
- **`cli/aiosv2.py` · `cmd_send`**: added optional `--correlation-id` and
  `--in-reply-to` flags. Both propagate to `build_envelope`. Omission
  preserves R320 / R320.1 envelope shape (no `correlation_id` /
  `in_reply_to` field). CLI stdout now echoes `correlation_id`,
  `in_reply_to`, and `dest`.
- **`cli/aiosv2.py` · argparse**: `ack` learned `--dest`; `send` learned
  `--correlation-id` + `--in-reply-to`.

### Added

- **Tests** in `tests/test_05_protocol_loopback.py`:
  - `test_r3206_ack_default_lands_in_inbox_not_outbox`
  - `test_r3206_build_envelope_propagates_correlation_id_and_in_reply_to`
  - `test_r3206_ack_of_ack_does_not_create_loop`
  - `test_r3206_correlation_id_filter_isolates_replies_per_original`
- **Tests** in `tests/test_07_healthcheck.py` (subprocess CLI):
  - `test_cli_send_with_correlation_id_and_in_reply_to_writes_them`
  - `test_cli_ack_default_writes_to_inbox_receivable_by_sender`
  - `test_cli_ack_correlation_id_and_in_reply_to_match_original`
  - `test_cli_ack_of_ack_does_not_create_loop`

### Documentation

- `protocols/v1.md`: added §10 Ack Routing (R320.6), pinning the
  inbox=delivery / outbox=audit-only contract and the no-ack-of-ack
  invariant.
- `README.md`: added explicit "inbox vs outbox — read this first"
  section; updated Quick Start and round-trip examples to show
  `--correlation-id` / `--in-reply-to` on `send` and the new ack default.
- `reports/IMPLEMENTATION_REPORT.md`: added R320.6 section; honest
  PENDING CODEX VERIFICATION status (test count NOT inflated, no claim
  that new tests passed in this CC session).

### Pending Codex verification

This CC session's Bash sandbox denies `python <script>` invocations
(see R320.1 blocker B1). The new R320.6 tests are written and
source-audited but **NOT executed** in this session. Codex is asked to
run `python D:\AIOS\_agent-hub\v2\tests\run_all_tests.py` from a
permitted shell and confirm the prior 47/0 + 8 new R320.6 tests = 55/55
(or report any failures).

### R320.6 test-only patch (after Codex verification round 1)

Codex re-ran the suite and reported **54 pass / 1 fail**. The single
failure was
`tests.test_05_protocol_loopback.test_r3206_build_envelope_propagates_correlation_id_and_in_reply_to`
because the test passed pseudo strings (`"abc-123"`) that the schema
correctly rejected (`correlation_id must be uuid4 format` per
`schemas/envelope.schema.json::properties.correlation_id.pattern`,
which enforces the uuid4 8-4-4-4-12 hex shape).

**Test-only fix**:
- The test now uses real `uuid.uuid4()` values (plus a sanity guard
  that the generated strings match the 8-4-4-4-12 hex shape, so a
  schema-regression bug cannot silently hide).
- Added the realistic case: pass an actual `build_envelope(...)`
  envelope's `id` as both `correlation_id` and `in_reply_to` — this
  mirrors what `envelope.reply_envelope(...)` does.
- The omission branch (no `correlation_id` / no `in_reply_to`) is
  preserved to keep the R320 / R320.1 backwards-compat guarantee.

**Production code NOT touched**: `src/envelope.py`, `src/queue.py`,
`cli/aiosv2.py`, `schemas/envelope.schema.json` are unchanged. The
schema is correct as-is — pseudo strings like `"abc-123"` MUST be
rejected.

**Awaiting Codex verification round 2**: 55/55 expected.

### R320.6 test-only patch round 3 (sanity-guard hyphen position)

Codex round 2 still 54/1. Root cause: the sanity guard in the same test
used the wrong hyphen index. Standard uuid4 hex string has hyphens at
indices **8, 13, 18, 23** (not 8, 14, 18, 23), so `cid[14] == "-"`
fails for any real `uuid.uuid4()` value.

**Test-only fix**: changed `cid[14]` → `cid[13]` and `irt[14]` → `irt[13]`
in the two sanity-guard assertions. No other line touched. Production
code and schema remain unchanged.

**Awaiting Codex verification round 3**: 55/55 expected.

### Backwards compatibility

- Envelopes produced by R320 / R320.1 have no `correlation_id` /
  `in_reply_to` field. R320.6 readers (validation, queue) accept this
  unchanged.
- Old callers of `cmd_ack` that depended on the ack landing in `outbox`
  must either pass `--dest outbox` explicitly or read the new
  `ack_dest` field in the CLI stdout.
- `cli/aiosv2.py send` without `--correlation-id` / `--in-reply-to`
  produces an envelope identical to R320 / R320.1.

### Unchanged

- `inbox/` and `outbox/` directories on disk keep the same names.
- `envelope.schema.json` — no schema change (correlation_id /
  in_reply_to were already optional in v1.0).
- All other 47 prior tests are unchanged.

## [2.0.3] — 2026-09-29 (R320.6 VERIFIED · live test pass + two-process round-trip)

### Status change

R320.6 (previously [2.0.2] PENDING CODEX VERIFICATION) is now
**VERIFIED** by both automated test execution and a real two-process
round-trip. No production code or test code was touched in this
verification step — only documentation/log updates.

### Live automated test (Codex re-ran in a permitted shell)

- Executed: `python D:\AIOS\_agent-hub\v2\tests\run_all_tests.py`
- When: 2026-09-29T05:13:31Z–05:13:46Z
- Python: 3.13.14 (main, Jun 11 2026, 04:04:46) [MSC v.1944 64 bit (AMD64)]
- Platform: win32
- **Result**: TOTAL pass=55 / fail=0, all 8 modules PASS, `all_pass=true`
- Report files written:
  - `v2/reports/test_run.json` — full module/test breakdown, `total_pass=55, total_fail=0, failed_modules=0`
  - `v2/reports/test-output.txt` — human-readable pass log with per-test durations
- All 8 R320.6-specific tests are in the pass list:
  - `test_r3206_ack_default_lands_in_inbox_not_outbox` (25 ms)
  - `test_r3206_ack_of_ack_does_not_create_loop` (33 ms)
  - `test_r3206_build_envelope_propagates_correlation_id_and_in_reply_to` (0 ms)
  - `test_r3206_correlation_id_filter_isolates_replies_per_original` (0 ms)
  - `test_cli_ack_correlation_id_and_in_reply_to_match_original` (509 ms)
  - `test_cli_ack_default_writes_to_inbox_receivable_by_sender` (665 ms)
  - `test_cli_ack_of_ack_does_not_create_loop` (498 ms)
  - `test_cli_send_with_correlation_id_and_in_reply_to_writes_them` (168 ms)

### Live two-process round-trip (Codex process ↔ independent CC process)

Performed by Codex in a permitted shell against an independent Claude
Code process in a strict-permission bypass session. Envelope IDs and
correlation wiring captured from real CLI output (no mock).

| Step | Actor | CLI | Result envelope_id | Notes |
|---|---|---|---|---|
| 1 | Codex | `aiosv2.py send --from codex --to claudecode --type task --payload {...}` | `37531663-c742-4c95-939b-905c47ba86c4` | source task envelope, task_id `rt2-0473a55a-93a7-4a9a-80a2-6b786d0bb490` |
| 2 | CC | `aiosv2.py receive --agent claudecode --limit 1000 --claim` | (claim file `37531663-...task.claimed.DESKTOP-0JKD1FQ.23340.ef5add35.json`) | `count=1`, target found |
| 3 | CC | `aiosv2.py ack 37531663-... --actor claudecode --note r3206-cc-received` | `d8c5884b-1454-422c-8be9-a3843c4bc4c8` | `correlation_id == in_reply_to == source.id`, `ack_recipient=codex`, `ack_dest=inbox`, `deduped=false` |
| 4 | CC | `aiosv2.py send --from claudecode --to codex --type result --correlation-id ... --in-reply-to ... --payload {task_id,status,source_envelope_id}` | `3a9d9f27-aa0e-4171-a855-3883f80a2491` | payload `status=received_by_cc_r3206`, task_id matches source |
| 5 | Codex | `aiosv2.py receive --agent codex` | ack + result both visible | both envelopes show `correlation_id == in_reply_to == source task id` |
| 6 | Codex | `aiosv2.py ack 3a9d9f27-... --actor codex` | `41afc2c3-8fd3-4c80-80f2-62943eea25fd` | original CC ack consumed without ack-of-ack (invariant holds in real shell) |

### Still NOT verified (kept honest — no `completed`/`healthy` claim without live evidence)

Status correction 2026-09-29T05:19:02Z · Codex ran `aiosv2.py health`
and got the following 4-level per-agent snapshot. This supersedes any
earlier "Hermes exec denied / OpenClaw healthz non-200 / all five
present ceiling" wording in this changelog or in
`_agent-hub/memory/2026-09-29.md`.

| Agent | configured | present | reachable | healthy |
|---|---|---|---|---|
| Hermes | true | true | true | true |
| OpenClaw | true | true | true | true |
| Codex | true | true | **false** | **false** |
| Claude Code | true | true | **false** | **false** |
| WorkBuddy | true | true | **false** | **false** |

Hermes evidence: `hermes.exe v0.15.1`, `hermes --version` exit=0.
OpenClaw evidence: `127.0.0.1:18792` `port_open=true`, GET `/healthz`
returns 200 body=`{"ok":true,"status":"live"}`. Codex `reachable=false`
because relay 19194 is still CLOSED; `ChatGPT.exe` alive only proves
`present`. Claude Code `reachable=false` because the regular CC main
session has no live `mcp__aios-interop__*` call — the R320.6
two-process round-trip ran from a strictly-scoped temporary CC bypass
session that only allowed three non-destructive `aiosv2.py`
subcommands, which is **not** a permanent relaxation. WorkBuddy
`reachable=false` because no live CLI invocation or HTTP health
endpoint was hit in this verification round.

Items below are the **only** non-completion items still tracked — none
of them is a service-health gap (Hermes and OpenClaw self-probes are
now `healthy`); they are v2-queue-integration gaps:

- **WorkBuddy ↔ v2 wiring**: no live CLI/HTTP probe and no v2 envelope
  consumer. NOT completed.
- **Claude Code main-session shell freedom**: the R320.6 round-trip's
  strict-permission bypass does not relax the CC main-session gate.
  NOT completed as a permanent state.
- **Hermes / OpenClaw ↔ v2 queue real bidirectional consumption**:
  self-probes are `healthy`; no Hermes/OpenClaw daemon has been
  observed draining v2 `inbox/` and emitting `ack`/`result` back.
  Bridge registry row `br-claudecode-openclaw` therefore remains
  `loopback_only / unverified` — no upgrade in R320.6. The remaining
  bridge-upgrade gate is the v2-queue consumer round-trip, **not**
  service health.

### Documentation updates (this round)

- `v2/reports/IMPLEMENTATION_REPORT.md` — R320.6 section flipped from
  PENDING to VERIFIED; added live-test table (8 modules, 55/0) and live
  round-trip envelope-id table; honest non-completion notes for
  WorkBuddy / CC main session / Hermes / OpenClaw.
- `v2/CHANGELOG.md` — this `[2.0.3]` entry.
- `_agent-hub/memory/2026-09-29.md` — new "R320.6 闭环验收" section
  with same evidence and same non-completion notes.
- No source, test, schema, registry, watchdog, or daemon was modified.

## [2.0.1] — 2026-09-29 (R320.1 · Codex independent audit)

### Fixed (Codex-mandated)
- **P0-1** `src/queue.py` concurrency: enqueue now under cross-process file lock; all tmp filenames unique per call.
- **P0-1** NEW `src/lock.py`: cross-platform file lock (msvcrt.locking on Win, fcntl.flock on POSIX, threading.Lock fallback).
- **P0-2** `tests/test_02_queue_concurrency.py`: worker exceptions now collected and re-raised after join; exact-count assertions on files + index.
- **P0-3** `tests/run_all_tests.py`: pytest polyfill (only `pytest.raises`) installed into `sys.modules` BEFORE importing any test module — driver now runs without pytest installed.
- **P0-3** `tests/test_01_envelope_schema.py`, `tests/test_03_state_machine.py`: removed `import pytest` / `pytest.raises`; replaced with try/except ValueError.
- **P0-4** `src/state_machine.py`: added `import uuid` (was missing — NameError on `_atomic_write_json`).
- **P1-5** Renamed `test_05_codex_cc_roundtrip.py` → `test_05_protocol_loopback.py` with explicit DISCLAIMER that this is a single-process loopback, NOT a real CC↔OpenClaw/Codex round-trip. Updated IMPLEMENTATION_REPORT.md to say so.
- **P1-6** `src/probes.py`: rewrote with 4-level model (configured / present / reachable / healthy). Only upgrade `reachable`/`healthy` after a live call. Removed hardcoded `session_is_cc_main=True` from claudecode probe. Removed file-presence-based "healthy" claim from workbuddy probe.
- **P1-6** `reports/health.json`: rewritten with 4-level model. claudecode / workbuddy are honest `present` only, not `healthy`.
- **P1-7** `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json`: `br-claudecode-openclaw` rolled back from `built/partial` (R320 overclaim) to `loopback_only/unverified` with honest evidence text.
- **P1-8** Documentation self-consistency: removed "11/11" claims from `v2/README.md`, `_agent-hub/README.md`. Removed broken `receive --claimpython` example. `IMPLEMENTATION_REPORT.md` rewritten as factual state.
- **P1-9** `reports/test-output.txt` + `reports/test_run.json`: created as honest "NOT EXECUTED — Bash sandbox blocks `python <script>` in this CC session" placeholders. Will be overwritten on first real run.

### Unchanged (still BLOCKED in this CC session)
- Bash tool in this Claude Code main session denies every `python <script>` invocation. Only `python --version` is permitted. **Real test execution is up to Codex** to run from a permitted shell.
- aios-interop MCP tools (`mcp__aios-interop__*`) denied in this session → real CC→Codex/Hermes/OpenClaw MCP-direct round-trip remains BLOCKED_EXTERNAL.

## [2.0.0] — 2026-09-29 (R320)

### Added
- Bidirectional protocol v1 (`protocols/v1.md`) with versioned JSON Schema (`schemas/envelope.schema.json`, `task.schema.json`, `state.schema.json`).
- 7 message types: `message`, `task`, `status`, `result`, `ack`, `heartbeat`, `error`.
- File-based queue with `enqueue` / `claim` (atomic rename) / `ack` / `deadletter` + idempotency dedup.
- Task state machine: `queued`/`running`/`waiting`/`succeeded`/`failed`/`cancelled` with retry budget and `reap_expired` auto-timeout.
- Supervisor: periodic tick (reap + snapshot) + `watch` loop.
- Real probes for all 5 agents (`claudecode` / `codex` / `workbuddy` / `hermes` / `openclaw`).
- CLI `aiosv2.py` with: `init` / `status` / `health` / `send` / `receive` / `ack` / `submit-task` / `update-task` / `watch` / `tick`.
- 8-module test suite (42 test cases after R320.1 rename) covering schema, concurrency, state machine, heartbeat/timeout/retry, protocol loopback, probes, CLI smoke, supervisor.
- Agent registry (`agents/agents.json`) with `codex` / `claudecode` / `workbuddy` / `hermes` / `openclaw`.
- Event log (`logs/events.ndjson`) for audit.

### R320 overclaim (rolled back in R320.1)
- Bridge registry: `br-claudecode-openclaw` was set to `status=built, health=partial`. That was an overclaim because no real two-runtime round-trip was proven. Rolled back in R320.1 to `loopback_only/unverified`.