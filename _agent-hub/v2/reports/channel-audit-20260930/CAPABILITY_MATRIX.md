# CAPABILITY_MATRIX.md · R285 · 2026-09-30

> Capability matrix for the Codex ↔ Claude Code channel and adjacent paths, separated by direction and by Codex surface (Desktop vs CLI vs relay) and Claude surface (CC CLI/VSCode vs aios-interop MCP).
> Schema reference: AIOS v2 `envelope.schema.json` v1.0 (`message|task|status|result|ack|heartbeat|error`).
> Each cell is **FACT** (live-evidenced by file/process inspection at capture time) or **INFERENCE** (best-effort deduction, never executed). **NOT-VERIFIED** = no live evidence in this audit window.

Legend: ✅ = live evidence observed · 🟡 = implementation present but not exercised in this session · ❌ = absent · ⚠️ = partial / risky

## 1. Direction: CC → Codex (write path; the "narrow text polling" scope)

| Capability | handoff/ inbox polling (legacy) | v2 file-queue (envelope v1.0) | aios-interop MCP (codex_query) | aios-interop MCP (codex_desktop_query) | Codex Desktop queue subcmd |
|---|---|---|---|---|---|
| Producer entrypoint | CC writes JSON file to `handoff/inbox/cc_to_codex/` (manual / via `_codex_supervisor.py`) | `aiosv2.py::cmd_send` or `queue.enqueue()` | MCP tool `codex_query` (in-process) | MCP tool `codex_desktop_query` | manual / via `aios_adapter_codex_desktop.py` |
| Transport | filesystem write | filesystem write + atomic tmp+replace | stdio MCP → subprocess `codex_cli_chat.py` → `node codex.js exec` | stdio MCP → subprocess `aios_adapter_codex_desktop.py` → `codex queue --thread --message` | native subprocess |
| Schema | free-form JSON (no schema validation; observed shapes: `{task_id, handoff_type, original_objective, current_error_or_observation, what_i_need_from_codex, do_not}`) | envelope v1.0 mandatory | tool `prompt` only (no envelope payload structure) | tool `prompt` + `thread_id` only | tool `prompt` only |
| Payload — plain text | ✅ in `handoff_type=message` JSON | ✅ `payload.text` (message_type=message) | ✅ `prompt` string | ✅ `prompt` string | ✅ `prompt` string |
| Payload — structured task | 🟡 `{task_id, handoff_type, original_objective, ...}` not AIOS task.schema | ✅ `payload={task_id, ...}` + separate `tasks/<uuid>.json` via `state_machine.submit_task` | ❌ no task lifecycle (just a one-shot prompt) | ❌ same | ❌ same |
| Payload — file/artifact refs | ❌ (paths embedded in `do_not` / `original_objective` text) | ✅ envelope `artifact_refs[]` (`{path, sha256?, content_type?}`) | ❌ | ❌ | ❌ |
| Payload — batch | ❌ | ❌ (single envelope per send) | ❌ | ❌ | ❌ |
| Payload — binary metadata | ❌ | 🟡 schema allows `artifact_refs[i].content_type` but no raw bytes (correct design) | ❌ | ❌ | ❌ |
| Payload — progress | ❌ | ✅ `message_type=status` + `payload={task_id, state, progress_pct, note}` | ❌ | ❌ | ❌ |
| Payload — approval / input request | ❌ | ⚠️ schema allows it (`payload` is open object) but no canonical approval/input-request message_type | ❌ | ❌ | ❌ |
| Payload — cancellation | ❌ | ✅ `state_machine.cancel()` writes task state `cancelled`; corresponding envelope `message_type=task` with `payload.cancel_requested` is not defined but `payload.reason` is open | ❌ | ❌ | ❌ |
| Payload — final result | 🟡 `{response_file, response_summary}` JSON in `handoff/inbox/codex_cli_to_cc/` | ✅ `message_type=result` + `payload={task_id, output_payload}` | 🟡 returns Codex CLI stdout as `output` string | 🟡 returns `queued_message_id` only (one-way, no reply) | 🟡 same |
| Payload — error | ❌ | ✅ `message_type=error` + `payload={code, message, details?}` | 🟡 surfaced as `{"error": ..., "exit_code": N}` | 🟡 surfaced as `{"ok": false, "error": ...}` | 🟡 surfaced as `{"ok": false, "error": ...}` |
| Max payload size observed | 1.2 KB (small JSON handoff files) | `MAX_MESSAGE_LENGTH = 12000` chars in aios-interop; envelope `ttl_ms` default 300000; no explicit max envelope size | 12000 chars (`MAX_MESSAGE_LENGTH = 12000`) | 12000 chars | `prompt_len` truncated by parent caller; observed Code MCP max = 12000 |
| Truncation behaviour | None — entire file written verbatim | None (atomic write entire envelope) | None — validated minLength=1 maxLength=12000 | None | None |
| Atomicity / locking | None — direct `open(...).write(json.dump(...))`; no `os.replace`; PID-level only | ✅ `os.replace(tmp, target)` under `file_lock(IDEMPOTENCY_INDEX_LOCK)` (R320.1 hardened) | in-process only | in-process only | in-process only |
| Ordering | FIFO via filename prefix | FIFO by `timestamp` field; concurrent writers use unique tmp filename (uuid+pid) | FIFO via Codex CLI session | FIFO via Codex Desktop queue | FIFO via Codex Desktop queue |
| Correlation / task / trace IDs | `{task_id}` is a STRING (not UUID); not validated; e.g. `STR-CODEX-AUDIT-20260927-A` | ✅ `correlation_id`, `in_reply_to` (UUID4), envelope `id` (UUID4) | `trace.request_id` (UUID-like, ≤128 chars) | `trace.request_id` (≤128 chars) | none — Codex CLI `--session-id` is opaque Codex-managed |
| Dedupe / idempotency | None — name collisions overwrote earlier files | ✅ `idempotency_key = sha256(canonical(sender|recipient|message_type|payload))`; index sidecar + `IDEMPOTENCY_INDEX_LOCK` (R320.1) | 🟡 `cache_key = principal:name:idempotency_key`; per-process LRU 256 entries | same | ❌ none |
| Ack semantics | File presence = ack (no separate ack envelope) | ✅ `message_type=ack` envelope built via `reply_envelope`; `cmd_ack` default `dest=inbox` (R320.6) | 🟡 returns `output` text; not an envelope ack | 🟡 returns `queued_message_id`; not an envelope ack | 🟡 same |
| Delivery state | at-most-once (file deletion not enforced) | at-least-once (claim → ack → deadletter) via `queue.claim`/`ack`/`deadletter` | at-least-once via `idempotency_key` cache | at-least-once (subprocess re-call replays) | at-least-once |
| Retry / backoff / timeout | None — daemon polls every 15s and re-emits | ✅ `state_machine.heartbeat()` + `reap_expired()` auto-retry on lease expiry; `transition(... failed → queued)` if retry_count < max_retries | `timeout` (15-600s) enforced in `aios_interop_mcp.py::_validate_timeout`; no retry | same | `self.timeout=30` default; no retry |
| DLQ | `handoff/processed/` (all moves, success or fail) | `v2/messages/deadletter/` (empty in this audit) | none | none | none |
| Concurrency / backpressure / rate limit | None | `BoundedSemaphore(MAX_CONCURRENT=2)` + `MAX_QUEUE=8` (aios-interop MCP only); v2 queue itself has no concurrency limit | ✅ bounded | ✅ bounded | ❌ none |
| Auth / authz / trust | None — anyone with FS write access | envelope unsigned (no signature field); file-queue relies on OS ACL | ✅ HMAC + principal authorities | ✅ same | ❌ relies on Codex Desktop session |
| Lifecycle ownership / watchdog | ✅ `_aios_daemon_watchdog.py` PID files + restart (msvcrt singleton lock) | ❌ no v2-supervisor daemon — only CLI subprocess | in-process only | in-process only | in-process only |
| Singleton protection | per-daemon: PID file in `handoff/watchdog/*.pid` | none — multiple CLI `aiosv2.py` instances can be launched | per-claude.exe (1:1 stdio) | same | Codex Desktop only |
| Backwards-compat shim | n/a | none — v2 is additive (R320 §9) | ❌ none — only speaks v1.0 envelopes via `payload` | ❌ same | ❌ same |
| Compatibility with `BaseAdapter` | ❌ (handoff/ scripts do not extend `aios_adapter_base.BaseAdapter`) | ❌ (v2 CLI is separate from adapter layer; uses `BaseAdapter.execute()` only when an adapter wraps it, e.g. `MCPBridgeAdapter` for HTTP→stdio) | 🟡 uses `BaseAdapter.execute()` indirectly via `codex_query` invoking `codex_cli_chat.py` which is NOT a BaseAdapter subclass | 🟡 same | ✅ `CodexDesktopAdapter(BaseAdapter)` directly |
| Compatibility with v2 SSOT | ❌ | ✅ reference impl | 🟡 payloads must conform to envelope.schema.json but current MCP call sites don't build envelopes | ❌ | ❌ |

## 2. Direction: Codex → CC (read/consume path)

| Capability | handoff/ inbox watcher (legacy) | v2 file-queue (envelope v1.0) | aios-interop MCP (claude_code_query) |
|---|---|---|---|
| Consumer entrypoint | `_codex_to_cc_bridge_v2.py::main_loop` (15s poll) | `aiosv2.py::cmd_receive --claim` (CLI invocation) | MCP tool `claude_code_query` in-process |
| Transport | filesystem scan | filesystem scan + atomic claim | stdio MCP → subprocess `claude -p` |
| Schema | free-form JSON observed in `handoff/inbox/codex_to_cc/*.json` (history shows `STR-CODEX-AUDIT-2026-09-27-*`, `T-R*` task shapes) | envelope v1.0 | `prompt` + `session_id` only |
| Auto-claim / dedup | ✅ `seen` set persisted to `.seen_ids_v2.json` (last 1000 IDs) | ✅ `queue.claim` renames `<env>.json` → `<env>.claimed.<host>.<pid>.<nonce>.json` via `os.replace` | 🟡 per-process LRU result cache (256 entries) keyed on `principal:name:idempotency_key` |
| Cross-process dedup | 🟡 `seen` is local; multiple bridge instances would race | ✅ `IDEMPOTENCY_INDEX_LOCK` under cross-process `file_lock` (msvcrt + fcntl + threading fallback) | ❌ per-process only |
| Stale-task recovery | ❌ (seen grows forever; restart loses pending set in memory) | ✅ `state_machine.reap_expired()` + supervisor watchdog | ❌ |
| Concurrency / backpressure | None | none | ✅ `BoundedSemaphore(2)` + queue `MAX_QUEUE=8` (raises `QUEUE_FULL`) |
| Cancellation | ❌ | ✅ `cancel(task_id, actor)` → `transition → cancelled` | ❌ |
| Heartbeat | ❌ | ✅ `state_machine.heartbeat()` + lease-based reap | ❌ |
| Observability — trace | `bridge_v2.log` file | ✅ `aios_tasks/evidence/adapter_trace.jsonl` + Langfuse stub | ✅ Langfuse `aios_interop.tool_call.{done,error}` events + local fallback |
| Observability — handoff evidence | `_aios_daemon_watchdog_alert.log` (1.37 MB; observed events: RESTART, VERIFY_FAIL, THROTTLE) | empty (no v2 supervisor running) | none |
| Health snapshot | ✅ top-level `aiosv2.py::cmd_health` (4-level honest model) | ✅ same | ✅ `cross_entrypoint_health` aggregate |

## 3. Direction: Codex Desktop ↔ Codex CLI (sub-channel)

| Capability | Routing bridge | Direct path |
|---|---|---|
| Schema | `_v16_routing` metadata overlay `{source, routed_to, routed_at, router}` | none |
| File mechanism | `shutil.copy2` + metadata injection | none — they share OAuth but separate inboxes |
| Loop prevention | none | n/a |
| FIFO | filename sorted | n/a |
| Atomicity | `copy2` not atomic; no `os.replace` | n/a |

## 4. LLM-provider capability ceiling

| Capability | Codex CLI (base=MiniMax-M3) | Codex CLI (ollama=qwen2.5:3b-64k) | Codex Desktop (gpt-5-codex) | Claude Code (Sonnet 5 / Opus 5.5) |
|---|---|---|---|---|
| Multi-turn persistence | ✅ `codex --session-id` (R293 session_key pool) | ✅ same | ✅ (Codex Desktop session UUID) | ✅ `--session-id` (R295) |
| Sandbox | `--sandbox {read-only,workspace-write,danger-full-access}` | same | per-Codex-Desktop-config | ❌ (CC always uses `--tools ""` in MCP calls) |
| Approval gate | `--ask-for-approval {untrusted,on-failure,on-request,never}` | same | per-Codex-Desktop | none (analysis-only) |
| Context preamble (RAG) | ✅ `_build_context_preamble` injects `[AIOS_CONTEXT_PACKET]` up to 8000 chars | same | ❌ (Codex Desktop has its own context) | ✅ `_build_context_preamble` same path |
| Trace propagation | `AIOS_INTEROP_TRACE` env (request_id, parent_request_id, depth, visited) | same | ❌ | same |

## 5. Coverage gaps (see GAP_REGISTER.json for evidence & acceptance)

| Gap | Direction | Severity |
|---|---|---|
| v2 outbox has 2 stranded acks (no dispatcher; manual recovery needed) | CC → Codex | P0 |
| v2 inbox has 1 stuck ack 12h old (CC `receive --claim` not running in main session) | Codex → CC | P0 |
| 6 aios_interop_launcher.py instances cause mtime-watchdog cascade | system-wide | P1 |
| 7 AIOS_Autonomy_Daemon.exe instances — no daemon-level singleton lock | system-wide | P1 |
| 2 openclaw gateway instances on port 18792 | system-wide | P2 |
| handoff/ polling daemons flap (31 restarts in 4h per restart_history) | CC → Codex and reverse | P1 |
| `_aios_daemon_watchdog.py` is not wired to the v2 envelope layer | system-wide | P1 |
| No v2 supervisor running in production (state.json missing, events.ndjson empty) | system-wide | P1 |
| No file-queue consumer for Hermes/OpenClaw/WorkBuddy at v2 layer | various | P1 |
| aios-interop MCP live invocation blocked by CC main-session sandbox | both directions | P2 |
| Codex relay 19194 DOWN (TCP CLOSED) | both directions | P2 |
| Only the narrow text payload (`prompt`) is supported by the MCP tools — no envelopes, no task lifecycle, no cancellation, no progress | both directions | P0 (the central R285 problem) |