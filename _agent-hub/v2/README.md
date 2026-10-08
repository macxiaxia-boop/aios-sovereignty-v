# AIOS Hub v2 · Multi-Agent Bidirectional Workspace

> **Status**: ACTIVE — R320.1 (Codex independent audit applied)
> **SSOT scope**: `D:\AIOS\_agent-hub\v2\`
> **Complement to**: `D:\AIOS\_agent-hub\` (v1 markdown sync, unchanged)

This is the **canonical, versioned, machine-validated** extension of the AIOS shared
workspace. It addresses the v1 limitations (no live sync, no bidirectional, no schema,
no state machine) without touching the existing markdown hub or any agent's home dir.

> **R320.1 honesty note**: this README no longer claims 11/11 complete. See
> `v2/reports/IMPLEMENTATION_REPORT.md` §1 for the current factual state.

## What's Inside

```
D:\AIOS\_agent-hub\v2\
├── README.md              ← this file
├── CHANGELOG.md
├── agents/agents.json     ← canonical agent registry (SSOT)
├── protocols/v1.md        ← bidirectional protocol spec
├── schemas/
│   ├── envelope.schema.json   ← versioned message envelope (v1.0)
│   ├── task.schema.json       ← task lifecycle
│   └── state.schema.json      ← aggregate state snapshot
├── messages/
│   ├── inbox/      ← envelopes awaiting processing — DELIVERY QUEUE
│   ├── outbox/     ← envelopes produced locally — AUDIT ONLY, NO DISPATCHER
│   └── deadletter/ ← envelopes that exceeded retry or schema-failed
├── tasks/    ← one <task_id>.json per task
├── runs/     ← per (task_id, ts) run record
├── logs/events.ndjson    ← every state-changing call is appended
├── state/state.json       ← aggregate snapshot
├── reports/
│   ├── health.json        ← latest probe results (5 agents, 4 levels each)
│   ├── status.json
│   ├── test_run.json      ← last test run output (or NOT_EXECUTED placeholder)
│   ├── test-output.txt    ← plaintext console log of last test run
│   └── IMPLEMENTATION_REPORT.md
├── src/
│   ├── paths.py           ← path constants + ensure_dirs()
│   ├── id.py              ← uuid/sha256/timestamp helpers
│   ├── lock.py            ← cross-process file lock (msvcrt + fcntl)
│   ├── envelope.py        ← build/reply/verify envelopes
│   ├── validation.py      ← JSON Schema validation (no external deps)
│   ├── queue.py           ← file queue (enqueue/claim/ack/deadletter + idempotency)
│   ├── state_machine.py   ← task lifecycle + reap_expired + heartbeat
│   ├── probes.py          ← real probes, 4 honest levels (configured/present/reachable/healthy)
│   └── supervisor.py      ← periodic watcher (reap + snapshot)
├── cli/
│   ├── aiosv2.py          ← CLI entry (init/status/send/receive/ack/submit-task/update-task/watch/health/tick)
│   └── aiosv2.cmd         ← Windows wrapper
└── tests/
    ├── conftest.py
    ├── run_all_tests.py   ← driver (polyfill-first; runs without pytest)
    ├── run_all_tests.cmd  ← pytest alternative
    ├── test_01_envelope_schema.py
    ├── test_02_queue_concurrency.py
    ├── test_03_state_machine.py
    ├── test_04_heartbeat_timeout_retry.py
    ├── test_05_protocol_loopback.py   ← single-process loopback + R320.6 inbox routing
    ├── test_06_probes.py
    ├── test_07_healthcheck.py          ← CLI subprocess smoke incl. R320.6 ack round-trip
    └── test_08_supervisor_watch.py
```

## inbox vs outbox — read this first

| dir | role | deliverable? | when to write |
|---|---|---|---|
| `inbox/` | delivery queue | **YES** — `receive --agent X` reads here | `send` (default), `ack` (default since R320.6) |
| `outbox/` | audit trail | **NO** — no dispatcher; nothing reads it | `send --dest outbox`, `ack --dest outbox` (explicit audit-only) |

**There is no daemon that moves outbox → inbox.** Anything written to outbox
is not visible to `receive` from another process. R320.6 made this explicit
after a real two-process round-trip exposed the gap (Codex → CC ack was
un-deliverable because it was written to outbox).

## Quick Start

```powershell
# 0) One-time: ensure dirs + initial state
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py init

# 1) Health check (real probes of all 5 agents; reports 4 levels)
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py health

# 2) Submit a task
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py submit-task `
    --title "diagnose openclaw" `
    --assignee codex --owner claudecode `
    --timeout-ms 15000

# 3) Update task state
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py update-task `
    --task-id <uuid> --action transition `
    --state running --actor claudecode

# 4) Send a message envelope (R320.6: optional --correlation-id / --in-reply-to)
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py send `
    --from codex --to claudecode `
    --type message --payload '{"text":"hi v2"}' `
    [--correlation-id <env_id>] [--in-reply-to <env_id>]

# 5) Receive + claim (R320.3: --agent filters BEFORE limit)
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py receive --limit 1000 --agent claudecode --claim

# 6) Ack by envelope id (R320.6: default --dest inbox; recipient=original.sender)
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py ack <envelope_id> `
    --actor claudecode --note "received"
# Add `--dest outbox` only for explicit audit (NOT delivered to sender).

# 7) Watch loop (default 5s interval)
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py watch
```

## Real Two-Process Round-Trip (Codex-CC ↔ CC)

The CLI is the transport-layer-agnostic surface; the **same envelope contract**
works for in-process loopback, file-queue (default), and aios-interop MCP.

```powershell
# --- SENDER (e.g. Codex) ---
# 1) Codex sends a task to CC (default --dest inbox; recipient=claudecode)
$ENV = python D:\AIOS\_agent-hub\v2\cli\aiosv2.py send `
    --from codex --to claudecode `
    --type task `
    --payload '{"task_id":"demo-1","instruction":"diagnose openclaw"}' | ConvertFrom-Json
$ENV_ID = $ENV.envelope_id

# 2) Codex waits for an ack envelope addressed to itself (now in INBOX, R320.6).
#    poll inbox for envelope whose correlation_id == $ENV_ID.
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py receive `
    --limit 1000 --agent codex

# --- RECEIVER (independent CC process / session) ---
# 3) CC receives only envelopes addressed to itself (filter BEFORE limit)
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py receive `
    --limit 1000 --agent claudecode --claim

# 4) CC does the work, then sends a result envelope back to codex.
#    R320.6: --correlation-id + --in-reply-to wire the result to the original.
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py send `
    --from claudecode --to codex `
    --type result `
    --payload '{"task_id":"demo-1","output":{"port":"closed"}}' `
    --correlation-id $ENV_ID --in-reply-to $ENV_ID

# 5) CC acks the original task envelope. Default --dest=inbox so the ack
#    lands in codex's inbox (recipient=codex). The ack envelope carries
#    correlation_id + in_reply_to == original.id automatically.
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py ack $ENV_ID `
    --actor claudecode --note "result-sent"

# --- SENDER (Codex) ---
# 6) Codex receives (now BOTH result and ack envelopes are addressable)
python D:\AIOS\_agent-hub\v2\cli\aiosv2.py receive `
    --limit 1000 --agent codex --claim
# (find the result + ack envelopes; ack them as needed)
```

**Invariants verified by `tests/test_05_protocol_loopback.py` + `tests/test_07_healthcheck.py`:**
- `receive --agent X` filters by `recipient == X` (or `broadcast`) BEFORE the
  `--limit` cap is applied — so an agent never misses its own messages when
  the queue is large.
- `ack <envelope_id>` works ONLY if that envelope was previously claimed
  (`receive --claim`). The command globs `inbox/<id>__*.claimed.*.json`
  directly, parses it, and removes it.
- R320.6: `ack` writes the ack envelope to `inbox/` by default with
  `recipient=original.sender` and `correlation_id == in_reply_to == original.id`.
  The original sender can `receive --agent <sender>` and claim the ack.
  Outbox is audit-only; no dispatcher copies outbox → inbox.
- R320.6: `send --correlation-id X --in-reply-to Y` propagates both fields
  into the on-disk envelope JSON, so result/status/error can be wired to
  their originating task envelope without going through `reply_envelope`.

**NOT verified yet** (pending Codex two-process verification):
- That a Codex process and a CC process actually drain the queue in the
  same wall-clock window when invoked from separate shells (R320.6 added
  tests for this; awaiting Codex re-run).
- That aios-interop MCP transports these envelopes when allowed.
  → See `reports/IMPLEMENTATION_REPORT.md` §5 for the honest state.

## Run the Test Suite

```powershell
# Driver (no pytest required)
python D:\AIOS\_agent-hub\v2\tests\run_all_tests.py
# Output: console + D:\AIOS\_agent-hub\v2\reports\test-output.txt
#         + D:\AIOS\_agent-hub\v2\reports\test_run.json
```

The driver auto-creates a temp AIOS_V2_ROOT so tests do NOT touch the real v2 dirs.
8 modules, 42 test cases across envelope schema, queue concurrency, state machine,
heartbeat/timeout/retry, protocol loopback (NOT real round-trip), probes, CLI smoke,
and supervisor/watch.

## Bidirectional Protocol

See `protocols/v1.md`. Key invariants:

1. Every envelope has `schema_version: "1.0"` + sha256 `idempotency_key`.
2. Sender → recipient are agent ids (or `broadcast`).
3. Replies (`status`/`result`/`ack`/`error`) MUST carry `correlation_id` = `original.id`.
4. Idempotency: same `(sender, recipient, message_type, payload)` ⇒ same idempotency_key ⇒
   second enqueue is deduped (returns existing envelope_id).

## State Machine

```
queued → running → succeeded
  ↓        ↓
cancelled  failed → (retry if retry_count < max_retries) → queued
```

A running task must heartbeat every `timeout_ms/3` seconds. The supervisor scans all
running tasks and reaps any whose `lease_expires_at < now()` (→ failed → auto-retry or
final-failed).

## Concurrency (R320.1 hardened)

- File-based queue with `os.replace` for atomic claim (Windows + POSIX).
- **Cross-process file lock** (`src/lock.py`) wraps every `enqueue` so the
  read-check-write of `idempotency_index.json` is atomic.
- All tmp filenames are unique per call (`uuid.uuid4().hex + pid`) — no more
  WinError 32 sharing violations.
- In-process thread serialization via per-path `threading.Lock` inside `file_lock`.

## Probes (R320.1 honest 4-level model)

Every probe returns these four boolean levels, only upgraded when justified:

| level | requires |
|---|---|
| `configured` | appears in `agents/agents.json` |
| `present` | required file/binary exists on disk |
| `reachable` | a live call returned a non-error response |
| `healthy` | the live call returned the SPECIFIC 2xx success criterion |

No live call → max level = `present`. No file-only "healthy" claims.

## What This Does NOT Touch

- `~/.claude.json` (aios-interop MCP config) — unchanged
- `D:\个人文件\AI\Operator\aios_tools\` — unchanged
- `C:\Users\xinzh\.workbuddy\A2-path-launcher.sh` — unchanged
- Any daemon / watchdog / scheduled task — unchanged
- `D:\AIOS\_agent-hub\*.md` (v1 hub) — unchanged (v2 is additive)
- `D:\AIOS\AIOS_RECONSTRUCTION\` — only `br-claudecode-openclaw` row was touched, then rolled back to honest state

## See Also

- `protocols/v1.md` — full protocol spec
- `agents/agents.json` — agent identity registry
- `reports/IMPLEMENTATION_REPORT.md` — delivery report + completion matrix (factual, R320.1)
- `reports/health.json` — latest probe results (4 levels per agent)
- `reports/test_run.json` — last test run output (or `NOT_EXECUTED` placeholder)