# CHANNEL_TOPOLOGY.md · R285 · 2026-09-30

> **Audit-only snapshot of every active Codex ↔ Claude Code channel path in this Windows host.** No source, config, service, MCP registration, credential, launcher, or PID file was modified. All facts below come from Read of source files + wmic/tasklist + filesystem listing at capture time. **Observation window**: 2026-09-30T00:50Z–00:55Z. **Mode**: read-only.

---

## 1. Top-level diagram

```
┌───────────────────────────── HOST (Windows 10 10.0.19045) ─────────────────────────────┐
│                                                                                       │
│  ┌────────── Claude Code (CLI/VSCode) ──────────┐    ┌────── Codex Desktop ────────┐ │
│  │ 7× claude.exe  PIDs 14732 32432 32496 28992  │    │ codex.exe          PID 15336 │ │
│  │              30340 15252 18840                │    │ codex-code-mode-host PID 29872│ │
│  └──────────────────┬───────────────────────────┘    └─────────────┬───────────────┘ │
│                     │ stdio MCP (1:1 per claude.exe)               │ Electron + WS    │
│                     ▼                                                ▼                  │
│  ┌────────── aios_interop_launcher.py claude ─────┐    ┌────── Codex App Server ────┐  │
│  │ 6× running:  PIDs 12044 26580 32036            │    │  (in-proc, queue subcmd)   │  │
│  │                  26924 3924 25848              │    └─────────────┬───────────────┘  │
│  │ parent = each claude.exe                        │                  │                 │
│  │ AIOS daemon watchdog inner thread + mtime wd    │                  │                 │
│  └──────────────────┬─────────────────────────────┘                  │                 │
│                     ▼                                                │                 │
│  ┌──────────────────────── aios_interop_mcp.py (RESTRICTED) ─────────────────────┐   │
│  │  1 process per CC session (in-process import). 22 tools listed; host-allowlist │   │
│  │  applied per `AIOS_MCP_HOST`. Auth = HMAC-SHA256(principal|authorities|host). │   │
│  │  Slot semaphore MAX_CONCURRENT=2 · MAX_QUEUE=8 · TTL bounded 15–600s.        │   │
│  └─────────┬──────────────────────────────┬─────────────────────────┬────────────┘   │
│            │                              │                         │                │
│            ▼                              ▼                         ▼                │
│   ┌──────────────────┐          ┌────────────────────┐   ┌────────────────────┐     │
│   │ codex_query →    │          │ codex_desktop_query │   │ claude_code_query  │     │
│   │ codex_cli_chat.py│          │ → aios_adapter_     │   │ → claude CLI -p     │     │
│   │ → node codex.js  │          │   codex_desktop.py │   │   (max-turns=1)     │     │
│   │ (base=MiniMax-M3)│          │ → codex queue --    │   │ session_id passthru │     │
│   │ + ollama fallback│          │   thread --message  │   │ tools=""           │     │
│   └──────────────────┘          └────────────────────┘   └────────────────────┘     │
│                                                                                       │
│  ┌───────────────────── PARALLEL FILE-QUEUE STACK (handoff/) ─────────────────────┐  │
│  │ 14 polling daemons alive (per _aios_daemon_watchdog_state.json 2026-09-30):    │  │
│  │   _codex_polling_daemon                   PID 31912  (started 2026-09-29 20:13) │  │
│  │   _codex_to_cc_inbox_watcher              PID 23800  (started 2026-09-30 00:19) │  │
│  │   _codex_to_cc_bridge_v2                  PID 32020  (started 2026-09-29 20:08) │  │
│  │   _cc_to_codex_cli_bridge                 PID 32612  (started 2026-09-29 20:08) │  │
│  │   _cc_to_codex_cli_polling_daemon         PID 31456  (started 2026-09-29 20:23) │  │
│  │   _codex_cli_to_cc_inbox_watcher          PID 31492  (started 2026-09-29 20:07) │  │
│  │   _cc_to_doubao_bridge                    PID 30464  (started 2026-09-29 21:49) │  │
│  │   _cc_to_doubao_polling_daemon            PID 6568   (started 2026-09-30 00:31) │  │
│  │   _doubao_to_cc_inbox_watcher             PID 31124  (started 2026-09-29 22:27) │  │
│  │   _cc_to_openclaw_bridge                  PID 32528  (started 2026-09-29 20:41) │  │
│  │   _cc_to_openclaw_polling_daemon          PID 31232  (started 2026-09-29 23:56) │  │
│  │   _openclaw_to_cc_inbox_watcher           PID 27064  (started 2026-09-29 23:56) │  │
│  │   _codex_desktop_to_cli_bridge            PID 31248  (started 2026-09-29 23:28) │  │
│  │   _codex_cli_to_desktop_bridge            PID 31324  (started 2026-09-29 20:59) │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                       │
│  ┌────────────── PARALLEL v2 FILE-QUEUE STACK (envelope v1.0) ───────────────────┐  │
│  │ D:\AIOS\_agent-hub\v2\                                                          │  │
│  │   messages\inbox\    1 stuck ack (12h old, never claimed)                       │  │
│  │   messages\outbox\   2 stranded acks (R320.6 verified flow leftovers)          │  │
│  │   messages\deadletter\  empty                                                   │  │
│  │   tasks\ runs\       empty (state machine NEVER executed outside R320.6 test)  │  │
│  │   state\             idempotency_index.json only (9 entries)                   │  │
│  │                      state.json MISSING (supervisor never ran in prod)         │  │
│  │   logs\events.ndjson 0 lines                                                    │  │
│  └──────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                       │
│  ┌────────── SUPPORTING DAEMONS ──────────┐                                          │
│  │ 7× AIOS_Autonomy_Daemon.exe (parent chain = WinSW + watchdog + console)        │ │
│  │   PIDs 18508 9112 19400 21160 21356 3400 21336                                  │ │
│  │   → 2× of these are required (1 service + 1 watchdog-launched); 5 are EXTRA     │ │
│  │ 2× openclaw gateway (port 18792) PIDs 5920 + 6336 → 2nd cannot bind successfully│ │
│  │ 1× r306_dashboard_supervisor.py PID 1644 (parent PID 1748)                     │ │
│  └────────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Channel inventory (per direction)

### 2.1 Codex → Claude Code

| # | Path | Transport | Code | Live evidence |
|---|---|---|---|---|
| C1 | aios-interop MCP `claude_code_query` | stdio MCP → `claude -p` | `aios_interop_mcp.py::claude_code_query` lines 881–901 | tool registered; **live invocation not observed in this session** (CC sandbox denies `mcp__aios-interop__*`) |
| C2 | handoff `_codex_to_cc_bridge_v2.py` | filesystem poll (15s) of `D:/个人文件/AI/Operator/handoff/inbox/codex_to_cc/` | `_codex_to_cc_bridge_v2.py` lines 1–284 | PID 32020 alive; inbox dir empty (2026-09-30T00:55Z) |
| C3 | handoff `_codex_to_cc_inbox_watcher.py` | filesystem poll (15s) of `D:/个人文件/AI/Operator/handoff/inbox/cc_to_codex/` (Codex-driven task/question) | `_codex_to_cc_inbox_watcher.py` lines 1–152 | PID 23800 alive; dir empty |
| C4 | Codex Desktop queue → Codex App Server → Codex Desktop → human echo | Electron UI; Codex "queue --thread --message" | `aios_adapter_codex_desktop.py` lines 73–149 | codex.exe + codex-code-mode-host.exe alive; **direction CC→Codex Desktop is the only Codex Desktop path actively codex-side** |
| C5 | v2 inbox envelope `codex → claudecode` task | file-queue (envelope v1.0) | `aiosv2.py::cmd_send` + `queue.enqueue` | 1 ack `41afc2c3-...` stuck in v2/inbox 12h old |
| C6 | OpenClaw-delegated → CC inbox | file poll + MCP | `_openclaw_to_cc_inbox_watcher.py` + `aios_interop_mcp.py::openclaw_delegate` | PID 27064 alive; handoff/inbox/openclaw_to_cc empty |
| C7 | Doubao-delegated → CC inbox | file poll | `_doubao_to_cc_inbox_watcher.py` | PID 31124 alive; handoff/inbox/doubao_to_cc empty |

### 2.2 Claude Code → Codex

| # | Path | Transport | Code | Live evidence |
|---|---|---|---|---|
| X1 | aios-interop MCP `codex_query` | stdio MCP → `codex_cli_chat.py` → `node codex.js exec` | `aios_interop_mcp.py::codex_query` lines 801–845 | tool registered, fallback chain base→ollama; **live invocation not observed** |
| X2 | aios-interop MCP `codex_desktop_query` | stdio MCP → `aios_adapter_codex_desktop.py` → `codex queue --thread` | `aios_interop_mcp.py::codex_desktop_query` lines 848–878 | tool registered; requires `thread_id` (UUID) |
| X3 | handoff `_cc_to_codex_cli_bridge.py` | file poll (15s) → call openclaw-style delegate | `_cc_to_codex_cli_bridge.py` lines 137–199 | PID 32612 alive; not currently driving `codex_cli_chat.py` (R70 refactor notes Codex CLI is one-shot) |
| X4 | handoff `_codex_supervisor.py` (one-shot) | one-shot trigger file write | `_codex_supervisor.py::write_supervisor_trigger` lines 79–172 | not a daemon) |
| X5 | v2 envelope `claudecode → codex` | file-queue envelope v1.0 | `aiosv2.py::cmd_send` | 2 acks stranded in v2/outbox (no dispatcher) |
| X6 | openclaw relay → codex via MCP | file-poll + MCP subprocess | `_cc_to_openclaw_bridge.py::call_openclaw_delegate` lines 111–147 | PID 32528 alive; calls `aios_interop_mcp.py --invoke openclaw_delegate` |

### 2.3 Codex Desktop ↔ Codex CLI (sub-channel)

| # | Path | Code | Evidence |
|---|---|---|---|
| XCD1 | Desktop → CLI routing bridge | `_codex_desktop_to_cli_bridge.py` (PID 31248) | copies `handoff/inbox/codex_to_cc/*.json` → `handoff/inbox/codex_cli_to_cc/*.json` + adds `_v16_routing` metadata |
| XCD2 | CLI → Desktop routing bridge | `_codex_cli_to_desktop_bridge.py` (PID 31324) | reverse direction; same metadata convention |

### 2.4 Codex Desktop ↔ Claude Code (via queue/UI)

| # | Path | Code | Evidence |
|---|---|---|---|
| XC1 | Codex Desktop → CC: Codex user reads in Electron UI, copies to chat, then CC `aios_status` reads | out-of-band (human-mediated) | No in-process code path |
| XC2 | CC → Codex Desktop: `codex_desktop_query` MCP tool + `aios_adapter_codex_desktop.py::CodexDesktopAdapter.execute` (subprocess `codex queue --thread <UUID> --message <text>`) | `aios_adapter_codex_desktop.py` lines 73–149 | adapter available, not invoked in this session |

---

## 3. Duplicate-process inventory (for P0 race/duplicate analysis)

### 3.1 aios_interop_launcher.py (claude) — 6 instances

| PID | Parent PID | PPID command | Boot ts (heartbeat-derived) |
|---|---|---|---|
| 12044 | 14732 (claude.exe) | CC session 1 | ~2026-09-29 or earlier |
| 26580 | 32432 (claude.exe) | CC session 2 | sibling |
| 32036 | 32496 (claude.exe) | CC session 3 | sibling |
| 26924 | 28992 (claude.exe) | CC session 4 | sibling |
| 3924 | 30340 (claude.exe) | CC session 5 | sibling |
| 25848 | 15252 (claude.exe) | CC session 6 | sibling |

**Verdict (inference, not kill)**: each launcher is dedicated to one CC session; stdio MCP is 1:1 with the host process. They do NOT race on a single MCP socket because each Claude.exe holds its own stdio. However, **all 6 share `_RESULT_CACHE`** (module-level OrderedDict in `aios_interop_mcp.py`) ONLY within their own process; no shared cross-process cache exists. **Different concern**: they all call `_mtime_watchdog()` for `SERVER_PATH`, which fires an `os.execv` of the launcher → relaunches both the launcher AND the in-process server when ANY one launcher detects a change. With 6 launchers all watching the same mtime, an `mtime` bump will trigger 6 cascading `os.execv` cycles (each one re-runs and re-watches). This is **confirmed design behaviour** (R299 E 治本 comment in `aios_interop_launcher.py` line 71–90) but **amplifies restart churn** for the active host.

### 3.2 AIOS_Autonomy_Daemon.exe — 7 instances

| PID | Parent PID | PPID command line | Likely owner |
|---|---|---|---|
| 18508 | 18452 (python r306_dashboard_supervisor) | watchdog | supervisor-launched |
| 9112 | 18508 (daemon) | parent-child | spawned by 18508 |
| 19400 | 1000 (system, WinSW service) | AIOS_Autonomy_Daemon-svc.exe parent | WinSW service |
| 21160 | 19400 (service-launched daemon) | service-child | spawned by 19400 |
| 21356 | 21160 (daemon) | grandchild | spawned by 21160 |
| 3400 | 20496 (interactive console) | console-started | manual / schedule |
| 21336 | 3400 (daemon) | console-child | spawned by 3400 |

**Verdict (inference)**: at least 3 distinct launch sources (WinSW service, supervisor, manual console) plus the inherent parent→child chain. The daemon binary is 7.7 MB (read 2026-09-27) — likely a daemon that takes a job anchor and spawns workers. **If each root daemon writes to a shared state file**, race conditions are possible. **State evidence**: `D:/个人文件/AI/Operator/aios_tools/_aios_daemon_watchdog_state.json` last modified 2026-09-30T00:50Z (≈5 min before this audit) — suggests watchdog is the dominant writer (good). However, the **watchdog itself uses a single `_WD_LOCK` msvcrt NBLCK lock** (`_aios_daemon_watchdog.py:506–552`) so duplicate watchdogs are blocked at startup — the duplicate protection exists at the **watchdog** layer, NOT at the **daemon** layer. So multiple daemon processes are expected by the supervisor's design but **they will all try to acquire the same msvcrt lock-protected shared state** (the watchdog lock) only if they themselves start child watchdogs — currently only ONE watchdog is alive (PID 1748 → PID 1644 supervisor → PID 18508 daemon). The extra 6 daemons are **operationally redundant but not currently conflicting** because only ONE watchdog is writing to the singleton state. **Risk is in restart scenarios**: if a daemon dies and another watchdog/console-restart tool starts a NEW watchdog without honouring the singleton lock, races occur.

### 3.3 openclaw gateway (port 18792) — 2 instances

| PID | Parent | Command |
|---|---|---|
| 5920 | 4472 | `node openclaw/dist/index.js gateway --port 18792 --task-supervisor --ambient-channels` |
| 6336 | 8080 | `node openclaw/dist/index.js gateway --port 18792 --ambient-channels --task-supervisor-child=641336958728373` (different supervisor-child token) |

**Verdict**: Only one can bind TCP 18792. The second one either binds a different port (gateway may listen on 18792 + internal WS on a sibling port) OR fails fast. **MCP `aios_status::openclaw_gateway`** uses TCP `connect_ex` to 18792 (`aios_interop_mcp.py:998-1012`) which succeeds for the alive listener. **If both are actually listening on 18792** (gateway allows multiple instances sharing port via SO_REUSEADDR or because one is the parent and one is the child), there is **no MCP-visible problem**; but if WebSocket sessions get fanned across two gateway instances, message_id drift can occur.

### 3.4 v2 inbox has 1 stuck ack from 12h ago

- File: `D:\AIOS\_agent-hub\v2\messages\inbox\41afc2c3-8fd3-4c80-80f2-62943eea25fd__codex__claudecode__ack.json` (563 B, ts 2026-09-29T13:15)
- Payload: `{ack_of: 3a9d9f27-..., note: "r3206-result-verified"}`
- The corresponding CC side run was: `aiosv2.py receive --agent claudecode` was NOT called in any subsequent session to claim this ack; CC main session has not run `receive --agent claudecode --claim` since 2026-09-29T13:15Z.

### 3.5 v2 outbox has 2 stranded acks

- `0fbf6f33-...__codex__claudecode__ack.json` (559 B, ts 2026-09-29T13:08)
- `19334d04-...__claudecode__codex__ack.json` (582 B, ts 2026-09-29T13:07)

Both predate the R320.6 source-level fix (R320.6 switched `cmd_ack` default `dest` to `inbox`); they were written to `outbox/` under the previous (broken) routing rule. R320.6 protocol §10 documents that **outbox has no dispatcher**. They will never be consumed unless manually moved into `inbox/`.

---

## 4. AIOS v2 envelope layer — current operational state

| Asset | State (R285 capture) | Notes |
|---|---|---|
| `v2/messages/inbox/` | 1 unclaimed ack, **12 h stale** | No auto-prune, no auto-claim |
| `v2/messages/outbox/` | 2 stranded acks, **17 h stale** | No dispatcher per protocol §10 |
| `v2/messages/deadletter/` | empty | DLQ never invoked |
| `v2/tasks/` | empty | State machine never exercised in production |
| `v2/runs/` | empty | Run-attempt logger never invoked |
| `v2/state/idempotency_index.json` | 9 entries (all from R320.6 verification window 2026-09-29T05:06Z–05:15Z) | Index sidecar lockfile present, no contention observed |
| `v2/state/state.json` | **MISSING** | `supervisor.tick()` never ran in production |
| `v2/logs/events.ndjson` | **0 lines** | `_log_event` never invoked in production |
| `v2/agents/agents.json` | present | 5 agents: codex, claudecode, workbuddy, hermes, openclaw |
| `v2/reports/health.json` + `status.json` | present | last written by R320.6 health probe |

---

## 5. AIOS handoff/ legacy layer — current operational state

| Asset | State (R285 capture) |
|---|---|
| `handoff/.heartbeat_*.json` | 11 files, latest 2026-09-30T00:51Z (alive within last 9 min) |
| `handoff/inbox/cc_to_codex/` | empty |
| `handoff/inbox/cc_to_codex_cli/` | empty |
| `handoff/inbox/cc_to_doubao/` | empty |
| `handoff/inbox/cc_to_openclaw/` | empty |
| `handoff/inbox/codex_cli_to_cc/` | empty |
| `handoff/inbox/codex_to_cc/` | empty |
| `handoff/inbox/codex_to_codex/` | empty (Codex Desktop ↔ Codex CLI routing) |
| `handoff/inbox/doubao_to_cc/` | empty |
| `handoff/inbox/openclaw_to_cc/` | empty |
| `handoff/watchdog/*.pid` | 17 pid files; ages 2026-09-29T20:08Z to 2026-09-30T00:31Z |
| `handoff/processed/` | last entries 2026-09-27 (5-day-old) |
| `D:/demo/notifications/` | 20+ entries 2026-09-27 — old test traffic, no new since |

**Verdict**: the handoff/ polling stack is **structurally alive** (all 14 daemons running per watchdog state), but **the inbox directories are empty** for 9 distinct paths. This means the polling daemons are spinning idle, scanning 0 files every 15s. Their restart-history file shows **31 restart events in the past ~4 hours** (most-recent: 2026-09-30T00:31Z for `_cc_to_doubao_polling_daemon`) — these daemons are FLAPPING and getting restarted by the watchdog repeatedly.

---

## 6. Process-to-file mapping

| Process | File or socket it writes | File or socket it reads |
|---|---|---|
| aios_interop_launcher.py claude ×6 | child watchdog (AIOS_Autonomy_Daemon), in-memory only | `mcp_credentials.env`, `aios_interop_mcp.py` (mtime) |
| aios_interop_mcp.py ×6 | `aios_tasks/evidence/adapter_trace.jsonl` (via `emit_trace`), Langfuse stub | `_aios_shared_truth`, `_aios_langfuse_trace_stub`, `_aios_model_router`, `r293_cross_entrypoint_rag`, `aios_adapter_hermes`, `aios_task_lifecycle` |
| 14 handoff/ daemons | `handoff/.heartbeat_*.json`, `D:/demo/notifications/*.json`, `handoff/inbox/*/ack_*.json`, `handoff/processed/`, `_aios_daemon_watchdog_*` | `handoff/inbox/*/*.json` |
| AIOS_Autonomy_Daemon.exe ×7 | logs in `aios_tools/_aios_daemon_watchdog_alert.log` (1.37M bytes) | shared resources held by WinSW job-anchor |
| openclaw gateway ×2 | openclaw internal state | 127.0.0.1:18792 |

---

## 7. Trust boundary summary (no secrets read)

| Boundary | Mechanism |
|---|---|
| aios-interop MCP ↔ host | HMAC-SHA256 of `(principal|authorities|host)` using `AIOS_MCP_AUTH_SECRET` (loaded from `mcp_credentials.env`, never printed) |
| host allowlist | `HOST_TOOL_ALLOW` dict in `aios_interop_mcp.py:427–434` restricts tools per host |
| Tool authority | `_authorise()` (`aios_interop_mcp.py:470–476`) requires P-grade principal for non-aios_status tools |
| Codex CLI OAuth | Codex 0.149.1+ uses OAuth token; no API key passed |
| Codex relay 19194 | Down per `probes.py::probe_codex` and `netstat` (19194 CLOSED) |
| aios_adapter_codex.py | No key handling; relies on Codex CLI OAuth token auto-management |
| OpenClaw models | Whitelist `ALLOWED_OPENCLAW_MODELS` (3 entries) |
| Codex profiles | Whitelist `ALLOWED_CODEX_PROFILES` (2 entries: base, ollama; deepseek/deepseek-pro/qwen25 removed R329) |

---

## 8. ASCII art process tree (top 4 levels)

```
claude.exe (14732)
└── aios_interop_launcher.py claude (12044) [started by 14732]
    └── aios_interop_mcp.py (in-process import)
        └── aios_interop_launcher.py child threads
            ├── aios-mtime-watchdog (5s poll)
            └── aios-daemon-watchdog (10s poll → starts AIOS_Autonomy_Daemon.exe)

r306_dashboard_supervisor.py (1644)
└── AIOS_Autonomy_Daemon.exe (18508)  [supervisor-spawned]

AIOS_Autonomy_Daemon-svc.exe (19400)  [WinSW service, parent = system 1000]
├── AIOS_Autonomy_Daemon.exe (21160)  [service-spawned]
│   └── AIOS_Autonomy_Daemon.exe (21356)  [grandchild]
└── (also hosts job anchor)

(cmd console, parent 20496) AIOS_Autonomy_Daemon.exe (3400)
└── AIOS_Autonomy_Daemon.exe (21336)

node.exe (5920) openclaw gateway port 18792 (parent 4472)
└── node.exe (10460) service-child-windows-job-anchor.js

node.exe (6336) openclaw gateway port 18792 (parent 8080)
└── node.exe (32336) service-child-windows-job-anchor.js
└── node.exe (8164) task-supervisor-child=641906982
    └── node.exe (6064) sqlite-readonly-location.worker

pythonw (31912) _codex_polling_daemon.py
pythonw (23800) _codex_to_cc_inbox_watcher.py
pythonw (32020) _codex_to_cc_bridge_v2.py
pythonw (32612) _cc_to_codex_cli_bridge.py
pythonw (31456) _cc_to_codex_cli_polling_daemon.py
pythonw (31492) _codex_cli_to_cc_inbox_watcher.py
pythonw (30464) _cc_to_doubao_bridge.py
pythonw (6568)  _cc_to_doubao_polling_daemon.py
pythonw (31124) _doubao_to_cc_inbox_watcher.py
pythonw (32528) _cc_to_openclaw_bridge.py
pythonw (31232) _cc_to_openclaw_polling_daemon.py
pythonw (27064) _openclaw_to_cc_inbox_watcher.py
pythonw (31248) _codex_desktop_to_cli_bridge.py
pythonw (31324) _codex_cli_to_desktop_bridge.py
```