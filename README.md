# AIOS Kernel

> **Wrap-not-rewrite** runtime for the AIOS VNext Phase A program.
>
> **R1503**: 4 modules, 12 tasks, 87 tests · see [R1503 Final Report](../R1503_FINAL_REPORT.md)

[![AIOS Kernel CI](https://github.com/macxiaxia-boop/aios-sovereignty-v/actions/workflows/aios-kernel-ci.yml/badge.svg)](https://github.com/macxiaxia-boop/aios-sovereignty-v/actions/workflows/aios-kernel-ci.yml)

This repository hosts the AIOS kernel — a Python package that wraps (does not
fork) the existing AIOS services surfaced from `D:\AIOS`. R1503 (2026-10-12)
delivered the 4-module architecture in one pass:

```
src/aios_kernel/
  scheduler.py       (R1503-001)  high-level task scheduler (priority queue + circuit breaker + retry + DLQ + metrics)
  state_machine.py   (R1503-002)  generic FSMachine[S, E] + workflow_fsm() + task_fsm()
  workers/adapters.py (R1503-003)  cli_subprocess_adapter + http_adapter + 4-Agent registry
  agents/            (R1503-004+005)  AgentProtocol + AgentRegistry + capability discovery
  gateway/           (R1503-007+008+009)  FastAPI HTTP + JSON-RPC MCP + JWT auth + RateLimiter
  runtime/           (R1503-010+011+012)  ProcessManager + MemoryPersistence + CronManager
  cli.py             4-Agent CLI bridge (`scheduler run`, `scheduler status`)
```

See `docs/architecture.md` for the architectural intent and
`docs/acceptance_criteria.md` for the Phase A exit gate.

## Status

- **Phase**: A — Scaffold complete + R1503 modules shipped
- **Tests**: 87 PASS (78 unit + 9 integration) — `pytest tests/`
- **CI**: `.github/workflows/aios-kernel-ci.yml` (pytest 3.11/3.12/3.13 + ruff + mypy)
- **Coverage**: see CI artifact `coverage-xml`
- **Owner**: Claude Code (executor + 4-Agent delegation)
- **Audit**: `D:/个人文件/AI/Operator/aios-r1503-4agent/R1503_FINAL_REPORT.md`

## Layout

```
src/aios_kernel/
  domain/        Pydantic models (Goal, State, Task, Plan)
  persistence/   SQLAlchemy ORM + Alembic
  workflows/     Durable execution adapter (PGCheckpointerEngine)
  workers/       Worker Adapter registry + 4-interface stubs (R1503-003 enhanced)
  verifier/      Independent Verifier process
  api/           FastAPI surface
  cli.py         Operator console + 4-Agent CLI bridge
  scheduler.py   (R1503-001)
  state_machine.py (R1503-002)
  agents/        (R1503-004+005)
  gateway/       (R1503-007+008+009)
  runtime/       (R1503-010+011+012)

tests/
  unit/          78 tests
  integration/   9 e2e tests (4-module integration)

docs/            architecture.md, acceptance_criteria.md
scripts/         Operator scripts
.github/workflows/aios-kernel-ci.yml
```

## Quickstart

```bash
# Install
pip install -e ".[dev]"

# Smoke check
python -c "import aios_kernel; print(aios_kernel.__version__)"

# Run the 4-Agent scheduler (foreground, blocks until Ctrl-C)
python -m aios_kernel.cli scheduler run

# Print metrics snapshot
python -m aios_kernel.cli scheduler status

# Run all tests
pytest tests/ -v

# Run only integration tests (4-module e2e)
pytest tests/integration/ -v
```

## 4-Agent Team (R1503)

| Module | Worker Adapter | Default Provider |
|---|---|---|
| `kernel/` (scheduler) | ClaudeCodeAdapter | claude-code (MiniMax-M3) |
| `agents/` (protocol) | CodexAdapter | gpt-5.1 Codex (OAuth) |
| `gateway/` (http/mcp) | OpenClawAdapter | lingceAI / multi-provider |
| `runtime/` (process/mem/cron) | HermesAdapter | in-process CIO |

See `src/aios_kernel/workers/adapters.py::register_four_agent_team`.

## API Endpoints (R1503-007)

```
GET  /health        liveness
GET  /metrics       scheduler.metrics()
POST /tasks         submit Task (returns 202 + run_id)
GET  /tasks/{id}    query task status

MCP tools (R1503-008, JSON-RPC):
  aios_submit_task, aios_get_task_status, aios_get_metrics, aios_get_health
```

## CI

`.github/workflows/aios-kernel-ci.yml` runs on push to main:

- **test job** — pytest 3.11/3.12/3.13 + coverage (Ubuntu)
- **lint job** — ruff + mypy
- **quality-gate** — aggregate pass

Local equivalent: `scripts/ci.sh` (no remote required for pre-flight).

## Acceptance

- ✅ 87/87 tests PASS (R1503 modules)
- ✅ AIOS kernel full suite: 579 passed · 6 historical unrelated fails
- ✅ 5 commits pushed to `macxiaxia-boop/aios-sovereignty-v/main`
- ✅ OpenClaw daemon live at `:18792` (real HTTP e2e validated)
- ✅ memory-bank SSOT synchronized across `D:/AIOS/memory-bank/`