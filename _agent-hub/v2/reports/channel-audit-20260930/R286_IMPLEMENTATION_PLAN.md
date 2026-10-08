# R286_IMPLEMENTATION_PLAN.md · R285 audit · 2026-09-30

> One unified channel that **extends** existing `BaseAdapter` and AIOS Hub v2 (file-queue + envelope v1.0) rather than creating another isolated parallel bridge. Plan is **proposal only** in R285; implementation occurs in R286 with explicit user approval per red line.

---

## 1. Goals (carried verbatim from R285 audit brief)

> Design one unified channel that EXTENDS existing BaseAdapter/AIOS v2 rather than creating another isolated parallel bridge. It must target:
> - bidirectional typed envelopes
> - task create/claim/progress/input-request/approval/cancel/final/error lifecycle
> - artifact references and chunked large-text support (no raw binary in queue)
> - trace/correlation/idempotency IDs
> - atomic durable queue + locks + leases + retry/backoff + DLQ
> - acknowledgements separated from business result
> - bounded concurrency/backpressure
> - capabilities negotiation/versioning
> - supervisor visibility and stale-task recovery
> - backward-compatible shims for existing text bridges
> - health/call/trace/handoff tests, plus failure/restart/concurrency tests
> - explicit cutover strategy that avoids duplicate consumers

## 2. Architectural decisions

### 2.1 Extend, do not rebuild

- The v2 envelope v1.0 protocol (`v2/protocols/v1.md`, `v2/schemas/envelope.schema.json`, `v2/schemas/task.schema.json`) is the **SSOT for transport**. R286 must NOT fork it.
- `BaseAdapter` (`aios_tools/aios_adapter_base.py`) is the **SSOT for adapter interface**. R286 must NOT fork it.
- `aiosv2.py` (CLI) is the **SSOT for envelope/queue/state API**. R286 must NOT fork it.

### 2.2 Single consumer per direction (avoid duplicate consumers)

- Currently there are 14 handoff/ polling daemons + 6 MCP launchers all touching v2/inbox indirectly. R286 must **collapse** to:
  - **1 v2 supervisor daemon** (`_aios_v2_supervisor.py`) — runs `aiosv2.py watch` continuously, reaps expired tasks, rebuilds `state.json`, writes `events.ndjson`.
  - **1 v2 inbox consumer daemon** (`_aios_v2_consumer.py`) — one instance per host, claims envelopes from `v2/messages/inbox/{recipient}/`, dispatches to per-agent adapter.
  - **6→1 MCP launcher** — replace per-session `aios_interop_launcher.py` instances with a **single host-wide launcher** that listens on a Windows Mutex / named pipe and serves all CC sessions.
  - **handoff/ polling daemons → DELETE** (or convert to v2 consumers).

### 2.3 Bidirectional typed envelopes

- Every Codex ↔ CC call produces a v2 envelope v1.0 on both sides:
  - **CC → Codex**: input `task` envelope → CC process → output `result` or `error` envelope.
  - **Codex → CC**: input `message`/`task` envelope → Codex process → output `result`/`status` envelope.
- The MCP tool layer is wrapped so the **input** envelope is built from MCP tool args (if user provides `envelope={...}`) and the **output** envelope is built by the MCP tool's response handler and enqueued to `v2/messages/inbox/{sender}/`.

### 2.4 Artifact references + chunked large-text

- Schema extension: `envelope.schema.json` adds:
  - `artifact_refs[].content_type` already exists; add `chunk_id`, `chunk_total`, `is_chunked` to support chunked large-text.
  - `payload.text_chunks` array for long text.
- Queue layer: large envelopes (e.g., >64 KB) are split into chunked envelopes with `chunk_id` linked by `correlation_id`. Receiver assembles and validates `chunk_total == len(chunks)`.
- No raw binary in queue — only artifact refs (path + sha256 + content_type).

### 2.5 Trace / correlation / idempotency

- Use existing `envelope.id`, `correlation_id`, `in_reply_to`, `idempotency_key` fields. R286 does NOT introduce new fields; it uses what is already there.
- `idempotency_key` (sha256 of canonical sender+recipient+message_type+payload) is sufficient. The `idempotency_index.json` sidecar (already implemented, R320.1 hardened) is the dedup SSOT.

### 2.6 Atomic durable queue + locks + leases + retry/backoff + DLQ

- Use existing `v2/src/queue.py` (`enqueue`, `claim`, `ack`, `deadletter`) + `v2/src/lock.py` (`file_lock` msvcrt+fcntl+threading).
- Use existing `v2/src/state_machine.py` (`submit_task`, `transition`, `heartbeat`, `reap_expired`, `cancel`) for lease + retry + DLQ-via-failed.

### 2.7 Acks separated from business result

- Already designed in v1: `message_type=ack` vs `message_type=result`. R320.6 ensured `cmd_ack` writes to inbox by default. R286 ensures **every MCP tool call emits both**:
  - A `result` envelope (business result, async if task)
  - An `ack` envelope (transport ack, immediate)
- The ack envelope has `payload={ack_of: <envelope_id>}` and is NOT a substitute for result.

### 2.8 Bounded concurrency / backpressure

- Per-host `BoundedSemaphore(MAX_CONCURRENT=2)` (env `AIOS_INTEROP_MAX_CONCURRENT`, default 2, max 8).
- Per-host queue `MAX_QUEUE=8` (env `AIOS_INTEROP_MAX_QUEUE`, default 8, max 64).
- v2 queue itself has no concurrency limit; relies on consumer rate.

### 2.9 Capabilities negotiation / versioning

- Add `capabilities` field to MCP `initialize` response: each tool declares `{max_payload_size, supports_chunks, supports_artifacts, supports_progress, supports_cancel, supports_approval, supports_input_request}`.
- Tools can declare multiple `profile` (text-only / artifact / task) and MCP server advertises only the union of registered profiles.
- Envelope schema version remains `1.0`; capability negotiation happens at MCP tool layer, NOT envelope layer.

### 2.10 Supervisor visibility + stale-task recovery

- `_aios_v2_supervisor.py` is the supervisor. Per-tick:
  - `reap_expired()` (lease expiry → `failed` → re-queue if budget left).
  - `build_state_snapshot()` → `save_state_snapshot()`.
  - `probe_all()` → write to `v2/state/state.json`.
  - Append to `v2/logs/events.ndjson`.

### 2.11 Backward-compatible shims

- Existing `codex_query` / `codex_desktop_query` / `claude_code_query` MCP tools MUST continue to accept `prompt` (string) input. R286 adds optional `envelope` parameter; if absent, the tool builds a minimal v1 envelope internally (`{message_type: message, payload: {text: prompt}}`) and proceeds as before.
- Existing `_codex_to_cc_bridge_v2.py`, `_cc_to_openclaw_bridge.py`, etc. handoff/ scripts MUST NOT break during transition. R286 provides a **read-only shim** that watches `handoff/inbox/*` and converts free-form JSON into v2 envelopes.

### 2.12 Health / call / trace / handoff tests + failure / restart / concurrency tests

See `TEST_EVIDENCE_BASELINE.md` §6 and §7 for the 18 new tests. All tests must run from a permitted shell; the existing CC main-session sandbox block is OUT of scope.

### 2.13 Explicit cutover strategy (avoid duplicate consumers)

- **Stage 0 (R286.A · 1 day)**: Deploy `_aios_v2_supervisor.py` + `_aios_v2_consumer.py` as ADDITIVE daemons (no behavior change in existing handoff/ scripts).
- **Stage 1 (R286.B · 1-2 days)**: Add MCP tool wrappers that write v2 envelopes alongside the existing return dict. Verify with `test_10_mcp_to_v2_call.py`.
- **Stage 2 (R286.C · 2-3 days)**: Add new MCP tools (`task_submit`, `task_transition`, `task_heartbeat`, `task_cancel`, `envelope_send`, `envelope_receive`). Verify with `test_05_protocol_loopback.py` extended tests.
- **Stage 3 (R286.D · 2-3 days)**: Cutover handoff/ inbox paths. Each handoff/ daemon's `INBOX_*` path is symlinked (or migrated) to `v2/messages/inbox/{recipient}/`. Verify with `test_06_probes.py` extended.
- **Stage 4 (R286.E · 1 day)**: DELETE sunset handoff/ daemons (after 7-day soak). Verify watchdog state.json has only 1-2 entries.
- **Stage 5 (R286.F · 1 day)**: Collapse 6 launcher instances to 1 host-wide launcher. Verify with new `test_15_idempotency_6writers.py`.

## 3. Implementation plan

### 3.1 New files (R286)

| Path | Purpose | LOC est |
|---|---|---|
| `D:\AIOS\_agent-hub\v2\src\v2_consumer.py` | One-host consumer daemon: claim → dispatch → ack → result | 350 |
| `D:\AIOS\_agent-hub\v2\tests\test_09_v2_consumer_health.py` | 4-level probe evidence | 80 |
| `D:\AIOS\_agent-hub\v2\tests\test_10_mcp_to_v2_call.py` | MCP tool envelope wrapping | 120 |
| `D:\AIOS\_agent-hub\v2\tests\test_11_v2_trace_completeness.py` | events.ndjson coverage | 100 |
| `D:\AIOS\_agent-hub\v2\tests\test_12_mcp_v2_roundtrip.py` | Full bidirectional round-trip | 150 |
| `D:\AIOS\_agent-hub\v2\tests\test_13_mcp_call_killed_midway.py` | Failure: killed-mid-call | 80 |
| `D:\AIOS\_agent-hub\v2\tests\test_14_v2_consumer_restart.py` | Failure: consumer restart | 80 |
| `D:\AIOS\_agent-hub\v2\tests\test_15_idempotency_6writers.py` | Concurrency: 6 writers same key | 80 |
| `D:\AIOS\_agent-hub\v2\tests\test_16_openclaw_proxy_failure.py` | Failure: OpenClaw proxy | 70 |
| `D:\AIOS\_agent-hub\v2\tests\test_17_codex_quota_handoff.py` | Failure: Codex quota | 70 |
| `D:\AIOS\_agent-hub\v2\tests\test_18_codex_desktop_stale_thread.py` | Failure: stale thread | 70 |
| `D:\个人文件\AI\Operator\aios_tools\_aios_v2_supervisor.py` | Wrapper that runs `aiosv2.py watch` and exits non-zero on failure (so watchdog restarts it) | 60 |
| `D:\个人文件\AI\Operator\aios_tools\_aios_v2_consumer_runner.py` | Wrapper that runs `v2_consumer.py --recipient <X>` for each agent in `v2/agents/agents.json` | 80 |

### 3.2 Modified files (R286)

| Path | Change | Risk |
|---|---|---|
| `D:\AIOS\_agent-hub\v2\schemas\envelope.schema.json` | Add `envelope_signature_optional` (HMAC placeholder), `chunk_id`, `chunk_total`, `is_chunked` to artifact_refs; document max payload 64 KB | LOW (additive, optional fields) |
| `D:\AIOS\_agent-hub\v2\src\envelope.py` | Add `envelope_to_chunks(env, max_chunk_size=32768)` + `envelope_from_chunks(chunks)` helpers | LOW |
| `D:\AIOS\_agent-hub\v2\cli\aiosv2.py` | Add `cmd_send --envelope <base64>` flag; add `cmd_send --chunk-size N` flag; add `--correlate-to <env_id>` shortcut | LOW |
| `D:\AIOS\_agent-hub\v2\tests\test_05_protocol_loopback.py` | Add chunked-envelope round-trip test | LOW |
| `D:\个人文件\AI\Operator\aios_tools\aios_interop_mcp.py` | Add `envelope` optional param to `codex_query`, `codex_desktop_query`, `claude_code_query`; build envelope before subprocess, write result envelope after subprocess; add 6 new tools (`task_submit`, `task_transition`, `task_heartbeat`, `task_cancel`, `envelope_send`, `envelope_receive`) | MEDIUM (large change, requires careful review) |
| `D:\个人文件\AI\Operator\aios_tools\aios_interop_launcher.py` | Add Windows Mutex singleton guard so only 1 launcher per host; add MCP `initialize` capability advertisement | MEDIUM (touches 6 live instances) |
| `D:\个人文件\AI\Operator\aios_tools\aios_adapter_base.py` | Add optional `envelope` param to `execute()`; if provided, validate + propagate `correlation_id` | LOW |
| `D:\个人文件\AI\Operator\aios_tools\aios_adapter_codex.py` | Pass `envelope` to subprocess via `--session-id`; emit `result`/`error` envelope | LOW |
| `D:\个人文件\AI\Operator\aios_tools\aios_adapter_codex_desktop.py` | Same | LOW |
| `D:\个人文件\AI\Operator\aios_tools\aios_adapter_claude.py` | Same | LOW |
| `D:\个人文件\AI\Operator\aios_tools\aios_adapter_mcp_bridge.py` | Pass envelope through `call_stdio` | LOW |
| `D:\个人文件\AI\Operator\aios_tools\_aios_daemon_watchdog.py` | Add `DAEMONS` entries for v2 supervisor and v2 consumer wrapper | LOW |
| `D:\AIOS\AIOS_RECONSTRUCTION\03_BRIDGES\AIOS_BRIDGE_REGISTRY.json` | Update `br-claudecode-openclaw` from `loopback_only/unverified` → `loopback_only/built_v2_consumer` once `test_12_mcp_v2_roundtrip.py` passes; update `br-aios-codex-relay` to either `fixed` or `retired` per GAP-P1-07 outcome | LOW |

### 3.3 Deleted files (R286 Stage 4 only)

| Path | When | Why |
|---|---|---|
| `D:\个人文件\AI\Operator\aios_tools\_codex_to_cc_bridge_v2.py` | Stage 4 (after 7-day soak) | superseded by v2_consumer.py |
| `D:\个人文件\AI\Operator\aios_tools\_codex_to_cc_inbox_watcher.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_codex_polling_daemon.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_cc_to_codex_cli_bridge.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_cc_to_codex_cli_polling_daemon.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_codex_cli_to_cc_inbox_watcher.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_cc_to_doubao_bridge.py` | Stage 4 | superseded (per Stage 0 scope decision: out of Codex↔CC scope but sunset for symmetry) |
| `D:\个人文件\AI\Operator\aios_tools\_cc_to_doubao_polling_daemon.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_doubao_to_cc_inbox_watcher.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_cc_to_openclaw_bridge.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_cc_to_openclaw_polling_daemon.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_openclaw_to_cc_inbox_watcher.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_codex_desktop_to_cli_bridge.py` | Stage 4 | superseded (or merged into v2_consumer routing table) |
| `D:\个人文件\AI\Operator\aios_tools\_codex_cli_to_desktop_bridge.py` | Stage 4 | superseded |
| `D:\个人文件\AI\Operator\aios_tools\_handoff_watchdog.py` | Stage 4 | superseded |

### 3.4 Migration order (with checkpoints)

1. **Stage 0** (R286.A) — Deploy additive daemons; no behavior change.
   - Write `_aios_v2_supervisor.py` (calls `aiosv2.py watch --interval 5 --max-ticks 0` and exits on crash).
   - Write `_aios_v2_consumer.py` (one instance; reads `v2/messages/inbox/{recipient}/`; writes `result`/`error` envelope to `v2/messages/inbox/{sender}/`).
   - Add both to `_aios_daemon_watchdog.py::DAEMONS` list.
   - Verify: `v2/state/state.json` exists after 1 minute; `v2/logs/events.ndjson` grows.
   - **STOP POINT 1**: confirm no regression before Stage 1.

2. **Stage 1** (R286.B) — MCP tool envelope wrapping.
   - Modify `aios_interop_mcp.py::codex_query` (and siblings) to:
     - Accept optional `envelope={...}` param; validate against envelope.schema.json; extract `correlation_id` and `idempotency_key`.
     - Write input envelope to `v2/messages/inbox/{recipient}/` BEFORE subprocess call.
     - After subprocess call: write `result` or `error` envelope to `v2/messages/inbox/{original.sender}/` with `correlation_id == input.envelope.id`.
     - On subprocess failure: write `error` envelope with `code=SUBPROCESS_FAILED|TIMEOUT|...`.
   - Run `test_10_mcp_to_v2_call.py`: 1 call → ≥2 envelopes in v2/inbox/{recipient}/ + {sender}/.
   - **STOP POINT 2**: confirm envelope wrapping works for the 3 existing text tools.

3. **Stage 2** (R286.C) — Add new MCP tools.
   - Add `task_submit`, `task_transition`, `task_heartbeat`, `task_cancel`, `envelope_send`, `envelope_receive` to `aios_interop_mcp.py::TOOLS` and `TOOL_HANDLERS`.
   - Each tool's input schema is a strict subset of v1 envelope v1.0; each writes a v2 envelope via `queue.enqueue()`.
   - Run `test_05_protocol_loopback.py` extended tests for chunked envelopes.
   - **STOP POINT 3**: confirm new tools work in isolation.

4. **Stage 3** (R286.D) — Handoff shim.
   - Add `handoff_shim.py` (or inline in `v2_consumer.py`) that watches `handoff/inbox/{cc_to_codex,cc_to_codex_cli,cc_to_openclaw,cc_to_doubao,codex_to_cc,codex_to_codex,codex_cli_to_cc,openclaw_to_cc,doubao_to_cc}/` and converts free-form JSON into v2 envelopes (best-effort mapping: `original_objective` → `payload.text`, `task_id` → envelope `correlation_id`, etc.).
   - Verify shim is read-only (does NOT delete from handoff/inbox) for first 24h.
   - **STOP POINT 4**: confirm shim does not break the existing handoff/ flow.

5. **Stage 4** (R286.E) — Sunset handoff/ daemons.
   - 7-day soak after Stage 3.
   - DELETE 14 handoff/ daemon scripts (see §3.3).
   - Update `_aios_daemon_watchdog.py::DAEMONS` to remove handoff entries.
   - Verify watchdog state.json has only `_aios_v2_supervisor` + `_aios_v2_consumer` (+ legacy daemons not related to Codex↔CC).
   - **STOP POINT 5**: confirm handoff/ inbox empty for 7 days straight; no broken references.

6. **Stage 5** (R286.F) — Collapse 6 launchers to 1.
   - Modify `aios_interop_launcher.py` to:
     - Acquire Windows Mutex `Local\AIOSInteropMcp` at startup.
     - If mutex held, exit immediately (don't respawn).
     - Single launcher serves all CC sessions via shared stdio (Claude Code supports this when configured).
   - Verify `test_15_idempotency_6writers.py`: 6 concurrent sends with same idempotency_key → exactly 1 envelope persisted.
   - **STOP POINT 6**: confirm single launcher handles all CC sessions.

7. **Stage 6** (R286.G) — Bridge registry upgrade.
   - Update `br-claudecode-openclaw` to `built/healthy` once `test_12_mcp_v2_roundtrip.py` passes.
   - Update `br-aios-codex-relay` to either `fixed` or `retired` per GAP-P1-07 outcome.
   - Append CHANGELOG entry to `v2/CHANGELOG.md`.

### 3.5 Backward compatibility shim matrix

| Existing tool / bridge | Post-R286 behaviour |
|---|---|
| `aiosv2.py send --from A --to B --type message --payload '{...}'` | unchanged |
| `aiosv2.py send --from A --to B --type task --payload '{...}' --correlation-id <id> --in-reply-to <id>` | unchanged |
| `aiosv2.py ack <env_id> --actor A` | unchanged (writes to inbox by default per R320.6) |
| `aiosv2.py receive --agent <X> --claim` | unchanged |
| MCP `codex_query({prompt, profile, session_key, timeout, trace})` | unchanged for callers using `prompt`; new optional `envelope` param |
| MCP `codex_desktop_query({prompt, thread_id, timeout, trace})` | unchanged for callers using `prompt`; new optional `envelope` param |
| MCP `claude_code_query({prompt, session_id, timeout, trace})` | unchanged for callers using `prompt`; new optional `envelope` param |
| handoff/ polling daemon | Stage 3 shim converts; Stage 4 daemon deleted |

### 3.6 Capabilities negotiation advertisement

`aios_interop_mcp.py` `initialize` response adds `capabilities`:
```json
{
  "protocolVersion": "2024-11-05",
  "serverInfo": {"name": "aios-interop", "version": "2.0.0-r286"},
  "capabilities": {
    "tools": {
      "envelope": {"max_payload_size": 65536, "supports_chunking": true},
      "task_lifecycle": {"supports_submit": true, "supports_progress": true, "supports_cancel": true, "supports_input_request": true, "supports_approval": true},
      "artifacts": {"max_refs_per_envelope": 16, "supported_content_types": ["text/*", "image/png", "image/jpeg", "application/json", "application/octet-stream"]},
      "correlation": {"supports_correlation_id": true, "supports_in_reply_to": true, "max_correlation_chain": 16},
      "delivery": {"supports_ack": true, "supports_result": true, "supports_error": true, "supports_deadletter": true},
      "concurrency": {"max_concurrent": 2, "max_queue": 8}
    }
  }
}
```

### 3.7 Cutover strategy to avoid duplicate consumers

- **Hard rule**: at most ONE process writes to `v2/messages/inbox/{recipient}/` at a time. Enforced by `_RESULT_CACHE` + `_IDEMPOTENCY_INDEX_LOCK` cross-process lock (already in place from R320.1).
- **Hard rule**: at most ONE v2 supervisor runs. Enforced by `msvcrt LK_NBLCK` on `state/.aios_v2_supervisor.lock` (mirrors `_aios_daemon_watchdog.py` pattern).
- **Hard rule**: at most ONE v2 consumer per recipient. Enforced by per-recipient sidecar lock `state/.aios_v2_consumer.{recipient}.lock`.
- **Soft rule**: during Stage 3-4 transition, handoff/ daemons and v2_consumer both read `handoff/inbox/*`. They must NOT both write to `v2/inbox/*`. handoff/ daemons continue writing their ack files; v2_consumer reads via the shim and does NOT touch handoff/inbox.

## 4. Self-check for the plan

- ✅ Single channel that EXTENDS BaseAdapter + AIOS v2 (does not fork)
- ✅ Bidirectional typed envelopes
- ✅ Task lifecycle (create/claim/progress/input-request/approval/cancel/final/error)
- ✅ Artifact refs + chunked large-text support
- ✅ Trace/correlation/idempotency
- ✅ Atomic durable queue + locks + leases + retry/backoff + DLQ
- ✅ Acks separated from business result
- ✅ Bounded concurrency/backpressure
- ✅ Capabilities negotiation/versioning
- ✅ Supervisor visibility + stale-task recovery
- ✅ Backward-compat shims for text bridges
- ✅ Health/call/trace/handoff tests (test_09..12)
- ✅ Failure/restart/concurrency tests (test_13..18)
- ✅ Explicit cutover strategy with stop points + duplicate-consumer prevention locks

## 5. Out-of-scope items explicitly NOT in R286

- Live re-execution of v2 test suite in CC main session (sandbox blocks `python <script>`)
- Fixing Codex relay 19194 (deferred per GAP-P1-07 — user decision needed)
- Reviving/updating Hermes to upstream HEAD (proxy 7897 dead + DNS hijack; deferred)
- Adding more agent entrypoints beyond the 5 in `v2/agents/agents.json`
- Replacing Codex Desktop queue subcmd with App Server WebSocket adapter (R96 deferred work)

## 6. Open questions requiring user decision (R285 → R286)

| Question | Default if no answer | Where to ask |
|---|---|---|
| Should `br-aios-codex-relay` be revived or retired? | retire (update bridge registry) | next CC session start |
| Should the 7-day soak in Stage 4 be shortened to 3 days? | 7 days | next CC session start |
| Should the chunked-envelope payload limit be 32 KB (default) or 64 KB? | 32 KB | next CC session start |
| Should `_aios_v2_consumer.py` be a single multi-recipient process or one process per recipient? | single multi-recipient process | next CC session start |