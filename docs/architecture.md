# AIOS Kernel Architecture (T0031 scaffold)

> Frozen intent for Phase A. Implementation detail lives in T0032–T0037.

## 1. Mission

Wrap (not rewrite) the existing AIOS services running under `D:\AIOS\` so
that the VNext spec's six conceptual surfaces — Goal, Plan, Task, State,
Worker, Verifier — become first-class objects inside an isolated runtime.

## 2. Module Map

| Module | Card | Role |
|--------|------|------|
| `aios_kernel.domain` | T0032 | Pydantic schemas for Goal / State / Task / Plan |
| `aios_kernel.persistence` | T0032 | SQLAlchemy ORM models + Alembic migrations |
| `aios_kernel.workflows` | T0033 | Durable execution (PG checkpointer vs Temporal) |
| `aios_kernel.workers` | T0034 | Worker Adapter registration + 4 interface stubs |
| `aios_kernel.verifier` | T0035 | Independent Verifier process + protocol |
| `aios_kernel.api` | T0035/T0036 | FastAPI surface (HTTP + WebSocket) |
| `aios_kernel.cli` | T0031 | Operator console entry point |

## 3. Wrap-not-Rewrite Principle (Spec §100)

The kernel **never** imports `D:\AIOS\aios_tools\` or `_agent-hub/` modules
directly. It only talks to them over the boundaries defined in the Phase A
acceptance spec (T0030 §3 boundary table). All wrap targets are listed in
`docs/acceptance_criteria.md` §2.

## 4. Runtime Surfaces (Phase A)

- **HTTP API** — FastAPI on uvicorn
- **Background workers** — Temporal (durable) or asyncio (sim)
- **Persistence** — PostgreSQL 16 (docker-compose service)
- **Verifier** — Separate process; shared DB only

## 5. Non-goals (Phase A)

- ❌ Multi-tenant auth (Phase B)
- ❌ Sharded workers (Phase B)
- ❌ Production rollout hooks (Phase C)
