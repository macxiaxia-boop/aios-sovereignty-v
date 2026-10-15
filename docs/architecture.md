# AIOS Kernel Architecture (R1503 FINAL · 2026-10-12)

> **R1503**: 4 modules, 12 tasks, 91 tests · **DONE**

## 1. Mission

Wrap (not rewrite) the existing AIOS services surfaced from `D:\AIOS\` so
the VNext spec's six conceptual surfaces — Goal, Plan, Task, State,
Worker, Verifier — become first-class objects inside an isolated runtime.

## 2. R1503 Module Map (4 modules · 12 tasks)

| Module | Tasks | Role | Test Count |
|---|---|---|---|
| `aios_kernel.scheduler` | R1503-001 | High-level task scheduler (priority queue + circuit breaker + retry + DLQ + metrics) | 10 + 4 audit |
| `aios_kernel.state_machine` | R1503-002 | Generic FSM primitive + workflow_fsm + task_fsm factories | 13 |
| `aios_kernel.workers.adapters` | R1503-003 | CLI/HTTP adapter templates + register_four_agent_team() | 9 |
| `aios_kernel.agents` | R1503-004+005 | AgentMessage + AgentProtocol (send/recv/broadcast/request/respond) + AgentRegistry + capability discovery | 15 |
| `aios_kernel.gateway` | R1503-007+008+009 | FastAPI HTTP REST + JSON-RPC 2.0 MCP + JWT HS256 auth + token-bucket RateLimiter | 15 |
| `aios_kernel.runtime` | R1503-010+011+012 | ProcessManager + MemoryPersistence (JSONL + atomic fsync) + CronManager (5-field cron) | 16 |
| `aios_kernel.cli` | (CLI bridge) | `scheduler run`, `scheduler status` | n/a |

## 3. Wrap-not-Rewrite Principle (Spec §100)

The kernel **never** imports `D:\AIOS\aios_tools\` or `_agent-hub/` modules
directly. It only talks to them over the boundaries defined in the Phase A
acceptance spec (T0030 §3 boundary table). All wrap targets are listed in
`docs/acceptance_criteria.md` §2.

## 4. Runtime Surfaces (R1503)

- **HTTP API** — FastAPI on uvicorn (port 8080 default, configurable)
- **MCP Server** — JSON-RPC 2.0 over HTTP (4 tools)
- **Background workers** — ProcessManager spawns subprocesses
- **Persistence** — MemoryPersistence (JSONL ledger + JSON state.db) at
  configurable paths
- **Scheduler** — Asyncio-based dispatch loop (60s tick), CI-tested with 91 PASS

## 5. 4-Agent Team Architecture

Each module corresponds to one Agent in the 4-Agent parallel team:

| Module | Worker Adapter | Default Provider | Default Host |
|---|---|---|---|
| `kernel/` | ClaudeCodeAdapter | claude-code (MiniMax-M3) | VSCode extension |
| `agents/` | CodexAdapter | gpt-5.1 Codex (OAuth) | CLI |
| `gateway/` | OpenClawAdapter | lingceAI / multi-provider | Node daemon :18792 |
| `runtime/` | HermesAdapter | in-process CIO | embedded in kernel |

R1503 was implemented by Claude Code (Agent 1) which also acted as fallback
for Agents 2/3/4 since their respective tools (Codex CLI / OpenClaw Node /
Hermes in-proc) were either unavailable or failed during execution.

## 6. Phase Status

| Phase | Status | Acceptance |
|---|---|---|
| A — T0031 scaffold | ✅ DONE | importable package, CLI --version |
| B — T0032-T0070 modules | ✅ DONE | 87 unit + integration tests PASS |
| C — R1503 4-module | ✅ DONE | scheduler + state_machine + adapters + agents + gateway + runtime |
| D — R1503-FINAL gap-fill | ✅ DONE | scheduler audit ledger + pre-commit hook + GATE/RESOLVER Python impl |

## 8. Future Work (Post-R1503)

- Phase D: R1504 production rollout (Docker compose + supervisor daemon)
- Phase E: Multi-tenant auth + sharded workers
- Phase F: Cross-module integration with real 4-Agent worker adapters
  (Codex CLI, OpenClaw daemon, Hermes query)

## 9. Non-goals

- ❌ Multi-tenant auth (Phase D)
- ❌ Sharded workers (Phase E)
- ❌ Production rollout hooks (Phase D)
- ❌ Per-module versioning beyond `__version__`