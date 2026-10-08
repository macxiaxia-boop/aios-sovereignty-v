# PROCESS_AND_QUEUE_AUDIT.md · R285 · 2026-09-30

> Direct evidence-first snapshot of every Codex/Claude/CC bridge-related process and every queue/state/log location. Observations at 2026-09-30T00:50Z–00:55Z (read-only).

## 1. Process inventory (Python interpreters only, bridge-related)

### 1.1 aios_interop_launcher.py claude (one per Claude Code session)

| PID | Parent PID | PPID process | Boot ts (PID file approximate) | Status |
|---|---|---|---|---|
| 12044 | 14732 | claude.exe | unknown (no individual PID file; 1 per session) | alive |
| 26580 | 32432 | claude.exe | sibling | alive |
| 32036 | 32496 | claude.exe | sibling | alive |
| 26924 | 28992 | claude.exe | sibling | alive |
| 3924 | 30340 | claude.exe | sibling | alive |
| 25848 | 15252 | claude.exe | sibling | alive |

**Interpreter**: `C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe`

**Issue (fact)**: 6 instances exist; each spawns its own `_mtime_watchdog` daemon thread and its own `aios-daemon-watchdog` thread (which may start a separate AIOS_Autonomy_Daemon.exe per launcher if none found). See `_aios_daemon_watchdog.py` line 145 for the standard single-instance pattern; the launcher does NOT use this pattern.

### 1.2 r306_dashboard_supervisor.py

| PID | Parent PID | Status |
|---|---|---|
| 1644 | 1748 | alive |

**Interpreter**: `D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe` (different from aios_tools venv!)

**Issue (fact)**: supervisor uses the **WorkBuddy Python**, NOT the aios_venv Python. If `r306_dashboard_supervisor.py` ever tries to import from `aios_tools`, it may pick up the wrong stdlib or wrong venv-relative paths.

### 1.3 AIOS_Autonomy_Daemon.exe ×7

| PID | Parent PID | PPID command | Likely source |
|---|---|---|---|
| 18508 | 18452 (python r306_dashboard_supervisor) | supervisor-launched | r306 supervisor |
| 9112 | 18508 (daemon) | parent-child | spawned by 18508 |
| 19400 | 1000 (system, WinSW service) | AIOS_Autonomy_Daemon-svc.exe wrapper | WinSW service |
| 21160 | 19400 (svc daemon) | service-child | spawned by 19400 |
| 21356 | 21160 (daemon) | grandchild | spawned by 21160 |
| 3400 | 20496 (interactive console) | manual launch | user / schedule |
| 21336 | 3400 (daemon) | console-child | spawned by 3400 |

**Issue (fact)**: at least 3 distinct launch sources + inherent parent→child chain = 7 instances. The watchdog singleton lock (`_aios_daemon_watchdog.py:506-552`) only protects the **watchdog**, not the daemon. No source-visible daemon-level singleton lock exists in this audit window.

### 1.4 OpenClaw gateway ×2

| PID | Parent PID | Command |
|---|---|---|
| 5920 | 4472 | `node openclaw/dist/index.js gateway --port 18792 --task-supervisor --ambient-channels` |
| 6336 | 8080 | `node openclaw/dist/index.js gateway --port 18792 --ambient-channels --task-supervisor-child=641906982` |

**Issue (fact)**: 2 gateway instances. The MCP probe (`aios_interop_mcp.py:76-107`) uses `socket.create_connection((127.0.0.1, 18792))` which returns success if ANY process is listening. The probe does NOT enumerate gateway instances.

### 1.5 14 handoff/ polling daemons (per `_aios_daemon_watchdog_state.json` 2026-09-30T00:51:27Z, cycle=353)

| Daemon | Current PID | Last boot | Source file |
|---|---|---|---|
| `_codex_polling_daemon` | 31912 | 2026-09-29T20:13 | `_codex_polling_daemon.py` |
| `_codex_to_cc_inbox_watcher` | 23800 | 2026-09-30T00:19 | `_codex_to_cc_inbox_watcher.py` |
| `_codex_to_cc_bridge_v2` | 32020 | 2026-09-29T20:08 | `_codex_to_cc_bridge_v2.py` |
| `_cc_to_codex_cli_bridge` | 32612 | 2026-09-29T20:08 | `_cc_to_codex_cli_bridge.py` |
| `_cc_to_codex_cli_polling_daemon` | 31456 | 2026-09-29T20:23 | `_cc_to_codex_cli_polling_daemon.py` |
| `_codex_cli_to_cc_inbox_watcher` | 31492 | 2026-09-29T20:07 | `_codex_cli_to_cc_inbox_watcher.py` |
| `_cc_to_doubao_bridge` | 30464 | 2026-09-29T21:49 | `_cc_to_doubao_bridge.py` |
| `_cc_to_doubao_polling_daemon` | 6568 | 2026-09-30T00:31 | `_cc_to_doubao_polling_daemon.py` |
| `_doubao_to_cc_inbox_watcher` | 31124 | 2026-09-29T22:27 | `_doubao_to_cc_inbox_watcher.py` |
| `_cc_to_openclaw_bridge` | 32528 | 2026-09-29T20:41 | `_cc_to_openclaw_bridge.py` |
| `_cc_to_openclaw_polling_daemon` | 31232 | 2026-09-29T23:56 | `_cc_to_openclaw_polling_daemon.py` |
| `_openclaw_to_cc_inbox_watcher` | 27064 | 2026-09-29T23:56 | `_openclaw_to_cc_inbox_watcher.py` |
| `_codex_desktop_to_cli_bridge` | 31248 | 2026-09-29T23:28 | `_codex_desktop_to_cli_bridge.py` |
| `_codex_cli_to_desktop_bridge` | 31324 | 2026-09-29T20:59 | `_codex_cli_to_desktop_bridge.py` |

**Issue (fact)**: 31 restart events between 2026-09-29T21:10Z and 2026-09-30T00:31Z (~4h) per `_aios_daemon_watchdog_restart_history.json`. The 4 most-restarted daemons are `_codex_to_cc_inbox_watcher` (6), `_codex_desktop_to_cli_bridge` (6), `_doubao_to_cc_inbox_watcher` (4), `_openclaw_to_cc_inbox_watcher` (3).

### 1.6 Claude Code processes (claude.exe ×7)

| PID | PPID | Memory (K) |
|---|---|---|
| 14732 | (unknown parent) | 249,676 |
| 32432 | unknown | 259,880 |
| 32496 | unknown | 263,396 |
| 28992 | unknown | 310,336 |
| 30340 | unknown | 297,448 |
| 15252 | unknown | 247,052 |
| 18840 | unknown | 239,936 |

**Issue (inference)**: 7 claude.exe instances = 7 concurrent Claude Code sessions (likely multiple VSCode windows + CLI processes). Each spawned its own `aios_interop_launcher.py claude`; the 6:1 ratio suggests 1 of the 7 is the parent of an MCP-less child (perhaps a daemon process).

### 1.7 Codex processes

| PID | Memory | Role |
|---|---|---|
| 15336 | 251,072 KB | codex.exe (Codex Desktop Electron UI) |
| 29872 | 47,592 KB | codex-code-mode-host.exe (Codex Desktop mode host) |

**Issue (fact)**: Codex Desktop is alive. The relay 19194 is DOWN (per probe). The CLI base profile uses direct API to MiniMax-M3, not relay.

## 2. Queue inventory

### 2.1 v2 file-queue (envelope v1.0)

| Path | Files | Sizes (B) | Last mtime | Notes |
|---|---|---|---|---|
| `v2/messages/inbox/` | 1 | 563 | 2026-09-29T13:15 | Stuck ack (12h old, never claimed) |
| `v2/messages/outbox/` | 2 | 559, 582 | 2026-09-29T13:07, 13:08 | Stranded pre-R320.6 acks |
| `v2/messages/deadletter/` | 0 | n/a | n/a | Empty |
| `v2/tasks/` | 0 | n/a | n/a | Empty (state machine never exercised in production) |
| `v2/runs/` | 0 | n/a | n/a | Empty |
| `v2/state/state.json` | MISSING | n/a | n/a | Supervisor never ran |
| `v2/state/idempotency_index.json` | 9 entries | 2.6 KB | 2026-09-29T05:15Z | Locked under sidecar; last write at end of R320.6 verification |
| `v2/state/idempotency_index.json.lock` | 1 | 0 | 2026-09-29T05:15Z | Sidecar lock file |
| `v2/logs/events.ndjson` | 0 lines | 0 | n/a | Empty |

### 2.2 handoff/ legacy queues

| Path | Files | Last mtime |
|---|---|---|
| `handoff/inbox/cc_to_codex/` | 0 | n/a |
| `handoff/inbox/cc_to_codex_cli/` | 0 | n/a |
| `handoff/inbox/cc_to_doubao/` | 0 | n/a |
| `handoff/inbox/cc_to_openclaw/` | 0 | n/a |
| `handoff/inbox/codex_cli_to_cc/` | 0 | n/a |
| `handoff/inbox/codex_to_cc/` | 0 | n/a |
| `handoff/inbox/codex_to_codex/` | 0 | n/a |
| `handoff/inbox/doubao_to_cc/` | 0 | n/a |
| `handoff/inbox/openclaw_to_cc/` | 0 | n/a |
| `handoff/processed/` | 3 demo entries | 2026-09-27 (5d old) |
| `handoff/watchdog/*.pid` | 17 files | 2026-09-29T20:08Z to 2026-09-30T00:31Z |
| `handoff/.heartbeat_*.json` | 11 files | 2026-09-30T00:50Z to 00:51Z (alive within 5 min) |
| `D:/demo/notifications/` | 20+ | 2026-09-24 to 2026-09-27 (old test traffic) |

### 2.3 v2 envelopes — actual content observed

**`inbox/41afc2c3-...__codex__claudecode__ack.json`** (563 B, ts 2026-09-29T13:15Z):
```json
{
  "id": "41afc2c3-8fd3-4c80-80f2-62943eea25fd",
  "schema_version": "1.0",
  "message_type": "ack",
  "sender": "codex",
  "recipient": "claudecode",
  "timestamp": "2026-09-29T05:15:32Z",
  "idempotency_key": "cd54b5ce08efb879437e758d7f23a47d3f1f558dacd7021f449fc164717be433",
  "payload": {"ack_of": "3a9d9f27-...", "note": "r3206-result-verified"},
  "correlation_id": "3a9d9f27-...",
  "in_reply_to": "3a9d9f27-...",
  "retry_count": 0,
  "ttl_ms": 300000
}
```
✅ Valid v1.0 envelope. Schema-conformant. Stuck because no CC session has run `receive --agent claudecode --claim`.

**`outbox/19334d04-...__claudecode__codex__ack.json`** (582 B, ts 2026-09-29T13:07Z):
```json
{
  "id": "19334d04-08f8-4d3d-9f94-4eab28d336ce",
  ...
  "message_type": "ack",
  "sender": "claudecode",
  "recipient": "codex",
  "payload": {"ack_of": "d12a944d-...", "note": "received-and-processed-by-independent-cc"},
  ...
}
```
✅ Valid v1.0 envelope. Pre-R320.6 `cmd_ack` default `dest=outbox`; stranded per protocol §10.

### 2.4 idempotency_index.json content

9 entries (all R320.6 verification window 2026-09-29T05:06:28Z to 2026-09-29T05:15:32Z):

| Key (idempotency_key[:16]) | envelope_id | sender → recipient | message_type | location |
|---|---|---|---|---|
| 055b49423d8737d8 | d8c5884b-... | claudecode → codex | ack | inbox/ |
| 20692ef8d722a49c | 19334d04-... | claudecode → codex | ack | outbox/ |
| 64e1f4a75e9de92f | 0fbf6f33-... | codex → claudecode | ack | outbox/ |
| ad4b6105cb749885 | 37531663-... | codex → claudecode | task | inbox/ |
| bb70f79cebf31cba | d12a944d-... | codex → claudecode | task | inbox/ |
| cd54b5ce08efb879 | 41afc2c3-... | codex → claudecode | ack | inbox/ |
| de5cbd8bb4b162a8 | da0d4385-... | claudecode → codex | result | inbox/ |
| e13b03ff005c906c | 3a9d9f27-... | claudecode → codex | result | inbox/ |

Note: 2 task envelopes (ad4b6, bb70f) and 2 result envelopes (de5c, e13b) **exist in the index** but their envelope files are NOT in `v2/messages/inbox/` or `v2/messages/outbox/` today — they were either consumed and moved out, or never persisted to the directory. The index points to inbox/outbox paths that no longer exist.

## 3. Lock & contention observation

- `v2/state/idempotency_index.json.lock` exists; no active writer at audit time (last write 2026-09-29T05:15Z).
- `_aios_daemon_watchdog.py::WD_LOCK` is held by PID 1748 → 1644 (supervisor) chain (read `_aios_daemon_watchdog.pid` = the supervisor's PID 5-byte value, not the actual watchdog PID — minor data quality issue).
- No file-queue contention observed (idempotency index has been quiet for ~20 hours).

## 4. Lifecycle ownership

| Layer | Watchdog covers it? | Restart policy | Singleton lock? |
|---|---|---|---|
| v2 supervisor | ❌ not in DAEMONS list | none | none |
| v2 inbox consumer (proposed) | ❌ not in DAEMONS list | none | none |
| AIOS_Autonomy_Daemon.exe | n/a (binary service) | WinSW service-supervised; manual console start; supervisor-launched | none at daemon level |
| aios_interop_launcher.py | ❌ not in DAEMONS list | spawned per CC session by Claude Code stdio bootstrap | none at launcher level |
| aios_interop_mcp.py | n/a (in-process) | relaunched on launcher restart or `os.execv` mtime-watchdog | per-launcher |
| openclaw gateway | n/a (Node.js binary) | launched by supervisor / console | none observed |
| 14 handoff/ daemons | ✅ in DAEMONS list | PID file + alive_pid + restart with throttle (`MAX_RESTART_PER_HOUR=3`, `MIN_RESTART_INTERVAL_SECONDS=300`) | per-daemon PID file |

## 5. Findings table

| ID | Finding | Severity | Evidence |
|---|---|---|---|
| PROC-01 | 7 AIOS_Autonomy_Daemon.exe instances with no daemon-level singleton lock | P1 | §1.3 |
| PROC-02 | 6 aios_interop_launcher.py claude with cascading mtime-watchdog | P1 | §1.1 |
| PROC-03 | 2 openclaw gateway instances bound to port 18792 | P2 | §1.4 |
| PROC-04 | r306_dashboard_supervisor uses WorkBuddy Python (3.13.12), not aios_venv Python (3.12.13) | P2 | §1.2 |
| PROC-05 | handoff/ polling daemons flap (31 restart events in 4h) | P1 | §1.5 |
| PROC-06 | 14 handoff/ daemons read empty inboxes | P1 | §2.2 |
| PROC-07 | v2 inbox has 1 stuck ack 12h old | P0 | §2.1 |
| PROC-08 | v2 outbox has 2 stranded acks (pre-R320.6) | P0 | §2.1 |
| PROC-09 | v2 state.json MISSING; events.ndjson empty; tasks/runs empty | P0 | §2.1 |
| PROC-10 | 2 of 9 idempotency entries point to inbox paths that no longer have files | P2 | §2.4 |
| PROC-11 | watchdog does NOT cover v2 supervisor or MCP launchers | P1 | §4 |
| PROC-12 | 7 claude.exe instances for 6 launchers (orphan process?) | P3 | §1.6 |
| PROC-13 | 14 daemons' watchdog PID file dates span 2026-09-29 20:08 to 2026-09-30 00:31, indicating the watchdog does not restart dead daemons promptly | P2 | §1.5 |