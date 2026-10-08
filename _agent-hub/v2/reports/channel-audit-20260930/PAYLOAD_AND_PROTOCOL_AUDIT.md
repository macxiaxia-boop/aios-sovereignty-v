# PAYLOAD_AND_PROTOCOL_AUDIT.md · R285 · 2026-09-30

> Per-direction audit of the payload carried by every active Codex ↔ Claude Code path, with size, schema-conformance, truncation, atomicity, ordering, dedupe, ack, retry, and observability findings. Compares what each path does versus what the v2 envelope v1.0 protocol defines.

## 1. Protocol reference (SSOT)

- **`v2/protocols/v1.md`** (read 2026-09-30T00:55Z): defines 7 message_types, requires `id` (UUID4), `schema_version` (const `"1.0"`), `message_type`, `sender`, `recipient`, `timestamp` (ISO8601 UTC), `idempotency_key` (sha256 hex 64 chars), `payload`. Optional: `correlation_id`, `in_reply_to`, `artifact_refs[]`, `retry_count`, `ttl_ms`.
- **`v2/schemas/envelope.schema.json`** (read): defines structure with `additionalProperties: false`; `idempotency_key` pattern `^[0-9a-f]{64}$`; `correlation_id` and `in_reply_to` must be UUID4 if present.
- **`v2/src/envelope.py::verify_envelope`** (read): checks schema + recomputes `idempotency_key` to ensure payload has not been tampered.
- **`v2/src/queue.py::enqueue`** (read): idempotency dedup inside `file_lock(IDEMPOTENCY_INDEX_LOCK)` with 30s timeout. Write path uses unique tmp filename (`uuid.uuid4().hex+pid`) + `os.replace` for atomicity.
- **`v2/src/queue.py::claim`** (read): atomic rename `<env>.json` → `<env>.claimed.<host>.<pid>.<nonce>.json`. Returns None on race-loss.
- **`v2/src/queue.py::ack`** (read): `os.remove(claimed)`; if missing → return False.
- **`v2/src/queue.py::deadletter`** (read): renames `claimed.*` → `<env>.dead.*` + writes `.reason.json` sidecar.

## 2. Payload — per path

### 2.1 handoff/ polling paths (legacy, R200/V15)

**Schema**: free-form JSON, not AIOS envelope. Observed shapes in `handoff/inbox/cc_to_codex/STR-*.json`:
```json
{
  "task_id": "STR-CODEX-AUDIT-20260927-A",        // STRING, not UUID
  "handoff_type": "codex_supervisor_trigger" | "openclaw_response" | "codex_cli_response" | "...",
  "ts": "2026-09-27T18:23:00",                    // ISO local time, no UTC marker
  "from": "CC (Claude Code · minimax self-ref)",
  "to": "Codex (Codex Desktop · gpt-5-codex)",
  "original_objective": "...",                    // free-form text
  "files_context": ["path1", "path2"],
  "what_i_need_from_codex": "polling_ack",
  "do_not": ["rewrite_response"]
}
```

| Aspect | Status | Evidence |
|---|---|---|
| Plain text payload | ✅ `original_objective`, `current_error_or_observation` | observed in `handoff/inbox/cc_to_codex/*.json` |
| Structured task | ❌ no AIOS task.schema conformance; `task_id` is STRING | `_codex_supervisor.py:89` uses `SUP-<ts>-<hex>` |
| File / artifact refs | 🟡 `files_context` is string list, not `{path,sha256,content_type}` | `_codex_supervisor.py:135-137` |
| Batch | ❌ one handoff per file | n/a |
| Binary metadata | ❌ | n/a |
| Progress | ❌ no `progress_pct` | n/a |
| Approval / input request | ❌ no in-band support | n/a |
| Cancellation | 🟡 `--task-id` cancel handled by separate `cancel_task.py` (not a daemon) | not observed |
| Final result | 🟡 as a separate `*_response.json` file in codex_cli_to_cc/ | `_cc_to_codex_cli_bridge.py:99-119` |
| Error | ❌ no canonical error shape | n/a |
| Max payload size observed | 4 KB max (largest file in `handoff/` is `STR-20260924-195715-cbd255` @ ~3 KB) | `ls -la` |
| Truncation | None — entire file written verbatim | `_codex_supervisor.py:126` |
| Atomicity | ❌ `open(...).write(json.dump(...))` — not atomic; concurrent writers can leave torn files | `_codex_to_cc_bridge_v2.py:147-150` |
| Ordering | 🟡 filename-prefix sort; concurrent writers race on `<msg_id>.json` | `_codex_to_cc_bridge_v2.py:213-225` |
| Correlation IDs | 🟡 `task_id` string (not UUID); no `in_reply_to`; no `correlation_id` envelope field | `_codex_supervisor.py:89` |
| Dedupe / idempotency | 🟡 `.seen_ids_v2.json` (last 1000 IDs) — only blocks re-ack of same message_id | `_codex_to_cc_bridge_v2.py:81-87` |
| Ack semantics | at-most-once (no separate envelope); ack = file presence | `_codex_to_cc_bridge_v2.py:119-122` |
| Delivery state | at-most-once (no re-queue / DLQ) | `_codex_to_cc_bridge_v2.py:165-167` |
| Retry / backoff | None (no in-band retry); `MIN_RESTART_INTERVAL_SECONDS=300` only restarts the daemon process | `_aios_daemon_watchdog.py:193` |
| DLQ | `handoff/processed/` (all moves, success or fail) | filesystem |
| Concurrency / backpressure | None | n/a |
| Auth | None | n/a |
| Observability — log | `bridge_v2.log` (text, line per cycle) | `_codex_to_cc_bridge_v2.py:74-81` |
| Observability — handoff evidence | `D:/demo/notifications/cc_processed_*.json` | `_codex_to_cc_bridge_v2.py:159-178` |
| Observability — trace / handoff | `_aios_daemon_watchdog_alert.log` (text) | `_aios_daemon_watchdog.py:349-360` |

### 2.2 v2 file-queue (envelope v1.0)

| Aspect | Status | Evidence |
|---|---|---|
| Plain text payload | ✅ `payload.text` (message_type=message) | envelope.schema.json |
| Structured task | ✅ `payload={task_id, title, ...}` + `tasks/<uuid>.json` | task.schema.json + state_machine.py |
| File / artifact refs | ✅ `artifact_refs[i] = {path, sha256?, content_type?}` | envelope.schema.json lines 61-73 |
| Batch | ❌ one envelope per send | queue.enqueue single-message |
| Binary metadata | ✅ via `artifact_refs[].content_type` (e.g., `image/png`) but no raw bytes (correct design) | envelope.schema.json |
| Progress | ✅ `message_type=status` `payload={task_id, state, progress_pct, note}` | protocols/v1.md line 53 |
| Approval / input request | ❌ no canonical message_type | protocols/v1.md table |
| Cancellation | ✅ `state_machine.cancel(task_id, actor)` writes task state; corresponding envelope not standardized but extensible | state_machine.py:197-198 |
| Final result | ✅ `message_type=result` `payload={task_id, output_payload}` | protocols/v1.md line 54 |
| Error | ✅ `message_type=error` `payload={code, message, details?}` | envelope.schema.json |
| Max payload size | ❌ NO EXPLICIT MAX in envelope.schema.json (only `MAX_MESSAGE_LENGTH = 12000` in `aios_interop_mcp.py:33` for MCP tool inputs, not envelope size) | aios_interop_mcp.py:33 |
| Truncation | None for envelopes; atomic write of entire envelope | queue.enqueue |
| Atomicity | ✅ `os.replace(tmp, target)` under `file_lock(IDEMPOTENCY_INDEX_LOCK, timeout_s=30)` | queue.py:74-99 |
| Ordering | FIFO by `timestamp`; concurrent writes use unique tmp filename `uuid.uuid4().hex+pid` | queue.py:84-87 |
| Correlation IDs | ✅ `correlation_id` (UUID4), `in_reply_to` (UUID4) | envelope.schema.json |
| Dedupe / idempotency | ✅ `idempotency_key = sha256(sender|recipient|message_type|payload)`; index sidecar + cross-process lock | queue.py:38-99 |
| Ack semantics | ✅ `message_type=ack` built via `reply_envelope`; `cmd_ack` default `dest=inbox` (R320.6) | aiosv2.py:163-215 |
| Delivery state | at-least-once (claim → ack or deadletter) | queue.claim / queue.ack / queue.deadletter |
| Retry / backoff | ✅ lease-based: `reap_expired()` → `failed` → re-queue if retry budget left; `min_restart_interval` only for watchdog | state_machine.py:167-194 |
| DLQ | ✅ `v2/messages/deadletter/` (empty in this audit) | queue.deadletter |
| Concurrency / backpressure | none on queue itself; aios-interop MCP has `BoundedSemaphore(2)` + `MAX_QUEUE=8` | aios_interop_mcp.py:46-47 |
| Auth | envelope unsigned (no signature field); relies on OS ACL | design choice |
| Observability — trace | ✅ `v2/logs/events.ndjson` (currently 0 lines because no supervisor running) | state_machine._log_event |
| Observability — handoff evidence | ✅ `v2/state/state.json` rebuilt by `supervisor.tick()` (currently MISSING) | supervisor.py |

### 2.3 aios-interop MCP tools (codex_query / codex_desktop_query / claude_code_query)

**Schema**: tool input schemas accept only flat scalar fields (`prompt`, `profile`, `thread_id`, `session_key`, `session_id`, `timeout`, `trace`); `trace` itself is `{request_id, parent_request_id, depth, visited, idempotency_key}`. No envelope field.

| Aspect | Status | Evidence |
|---|---|---|
| Plain text | ✅ `prompt` | schemas lines 152-199 |
| Structured task | ❌ no payload structure; `prompt` is a single string | schemas |
| File / artifact refs | ❌ | n/a |
| Batch | ❌ | n/a |
| Binary metadata | ❌ | n/a |
| Progress | ❌ | n/a |
| Approval / input request | ❌ | n/a |
| Cancellation | ❌ no cancel tool; `interrupt` would be exposed by Codex/CC CLI but not added to MCP | n/a |
| Final result | 🟡 `output` field (string) or `queued_message_id` (UUID string) — NOT an envelope | codex_query / codex_desktop_query return dicts |
| Error | ✅ `{"ok": false, "error": {"code": ..., "message": ...}}` | aios_interop_mcp.py:63-64 |
| Max payload size | 12000 chars (MAX_MESSAGE_LENGTH) | aios_interop_mcp.py:33 |
| Truncation | None; validation rejects >12000 chars | aios_interop_mcp.py:489-493 |
| Atomicity | in-process only; no FS writes | n/a |
| Ordering | FIFO via Codex session; no inter-tool ordering | n/a |
| Correlation IDs | `trace.request_id` (string, ≤128 chars); `trace.parent_request_id`; `trace.idempotency_key` (≤128 chars) | TRACE_SCHEMA lines 113-123 |
| Dedupe / idempotency | ✅ `_RESULT_CACHE` LRU 256 keyed on `principal:name:idempotency_key`; rejects IDEMPOTENCY_CONFLICT if fingerprint differs | aios_interop_mcp.py:51-54 + 1974-1980 |
| Ack semantics | NONE — tool call returns result synchronously; no separate ack envelope | n/a |
| Delivery state | at-least-once (subprocess re-call replays) | n/a |
| Retry / backoff | None at MCP level; subprocess-level: `timeout` 15-600s; tool returns TIMEOUT on subprocess exit 124 | aios_interop_mcp.py:479-486 |
| DLQ | None | n/a |
| Concurrency | ✅ `BoundedSemaphore(MAX_CONCURRENT=2)` + queue `MAX_QUEUE=8` (raises QUEUE_FULL/BUSY) | aios_interop_mcp.py:46-47, 563-580 |
| Auth | ✅ HMAC-SHA256(principal|authorities|host) + authority ladder (N<C<O<P<A) | aios_interop_mcp.py:441-467 |
| Observability — trace | ✅ `aios_tasks/evidence/adapter_trace.jsonl` (per-call) + Langfuse stub (R294) | aios_interop_mcp.py:1989-1998 |
| Observability — call lifecycle | ✅ `_RESULT_CACHE` exposes fingerprint; cache hit/miss tracked | aios_interop_mcp.py:1974-1981 |

### 2.4 Codex Desktop queue subcmd (`codex queue --thread --message`)

| Aspect | Status | Evidence |
|---|---|---|
| Plain text | ✅ `--message` | aios_adapter_codex_desktop.py:91 |
| Structured task | ❌ no payload | n/a |
| File / artifact refs | ❌ | n/a |
| Batch | ❌ | n/a |
| Binary metadata | ❌ | n/a |
| Progress | ❌ | n/a |
| Approval / input request | ❌ | n/a |
| Cancellation | ❌ no cancel; Codex Desktop has its own interrupt | n/a |
| Final result | ❌ queue subcmd is one-way; reply requires human reading Desktop UI | per aios_adapter_codex_desktop.py comment lines 22-25 |
| Error | ✅ `{"ok": false, "error": ...}` | aios_adapter_codex_desktop.py:127-141 |
| Max payload size | `prompt_len` only logged; no observed max | aios_adapter_codex_desktop.py:121 |
| Truncation | None | n/a |
| Atomicity | subprocess only | n/a |
| Ordering | FIFO via Codex Desktop queue | Codex Desktop internal |
| Correlation IDs | `queued_message_id` (UUID) | aios_adapter_codex_desktop.py:108-111 |
| Dedupe / idempotency | None | n/a |
| Ack semantics | NONE | n/a |
| Delivery state | at-least-once (subprocess re-call replays) | n/a |
| Retry / backoff | None | n/a |
| DLQ | None | n/a |
| Concurrency | None | n/a |
| Auth | Codex Desktop session OAuth | Codex Desktop |
| Observability — trace | ✅ `adapter_trace.jsonl` via `emit_trace` | aios_adapter_codex_desktop.py:113-124 |
| Observability — handoff evidence | None | n/a |

## 3. Mismatch between actual channel and v2 envelope v1.0

The v2 envelope v1.0 protocol expects a typed, validated, idempotent envelope with correlation, ack, retry, and DLQ. **None of the live paths produce v2 envelopes**. Specifically:

1. **aios-interop MCP tools** produce dict results with `output` text or `queued_message_id`; no envelope validation, no write to v2/messages/inbox/.
2. **handoff/ polling daemons** produce free-form JSON; no envelope validation, no schema, no correlation.
3. **Codex Desktop queue subcmd** produces only a `queued_message_id` UUID; no envelope.

Only the `aiosv2.py send` CLI command produces v2 envelopes — and there is **no daemon** that consumes v2 envelopes to call Codex/CC. The v2 layer is **structurally correct but operationally dormant** at the channel boundary.

## 4. Findings

| ID | Finding | Severity | Evidence |
|---|---|---|---|
| PAY-01 | Channel is narrow text-only; no envelopes produced by live MCP/handoff paths | P0 | §2.3, §2.4 |
| PAY-02 | v2 envelope layer dormant (1 stuck inbox, 2 stranded outbox, no consumer) | P0 | GAP-P0-02, GAP-P0-03 |
| PAY-03 | aios-interop MCP tools lack cancellation, progress, approval, artifact-ref, batch, structured result, input-request | P0 | §2.3 |
| PAY-04 | handoff/ has no schema validation; free-form JSON observed | P1 | §2.1 |
| PAY-05 | No in-band retry/backoff in MCP or handoff/ | P1 | §2.1, §2.3 |
| PAY-06 | DLQ only exists in v2 layer (empty); handoff/ uses `processed/` for everything | P2 | §2.1, §2.2 |
| PAY-07 | aios-interop MCP has fingerprint-based dedup but no envelope-level dedup | P1 | §2.3 + queue.py |
| PAY-08 | `_RESULT_CACHE` is per-process LRU; not shared across the 6 launcher instances | P2 | aios_interop_mcp.py:51-54 |
| PAY-09 | envelope idempotency_key is sha256(canonical sender+recipient+message_type+payload); payload hash ignores `artifact_refs` (which live at envelope level); consequence: same payload + different artifact_refs = same key | P2 | envelope.py:35 vs envelope.schema.json |
| PAY-10 | `MAX_MESSAGE_LENGTH = 12000` is enforced only at the aios-interop MCP layer; the v2 envelope schema does NOT enforce a max payload size — a 1 MB envelope would be allowed in principle | P1 | envelope.schema.json (no maxLength on payload) |

## 5. Recommended (R286) protocol extensions

These are described in `R286_IMPLEMENTATION_PLAN.md` §3.4. Summarized here:

- Add envelope-wrapping to `codex_query` / `codex_desktop_query` / `claude_code_query` MCP tools.
- Add new MCP tools `task_submit`, `task_transition`, `task_heartbeat`, `task_cancel`, `envelope_send`, `envelope_receive`.
- Add `envelope_max_size` and `envelope_chunked_send` to envelope.schema.json so large text payloads can be split across multiple envelopes with `correlation_id` linking.
- Add `signature` (HMAC of canonical envelope) to envelope.schema.json to authenticate the writer (currently unauthenticated).
- Add a consumer daemon `_aios_v2_consumer.py` that drains v2/messages/inbox/{recipient}/ and dispatches per agent registry.