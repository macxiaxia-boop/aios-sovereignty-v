# AIOS Kernel

> **Wrap-not-rewrite** runtime for the AIOS VNext Phase A program.

This repository hosts the new kernel that wraps (does not fork) the existing
AIOS services surfaced from `D:\AIOS`. See `docs/architecture.md` for the
architectural intent and `docs/acceptance_criteria.md` for the Phase A exit
gate (frozen by T0030).

## Status

- **Phase**: A — Scaffold (T0031)
- **Owner**: Claude Code (executor), Codex (supervisor)
- **Cards**: T0031 (this repo init) → T0032–T0037 (implementation)

## Layout

```
src/aios_kernel/
  domain/        # Pydantic models (Goal, State, Task, Plan) — T0032
  persistence/   # SQLAlchemy ORM + Alembic — T0032
  workflows/     # Durable execution adapter — T0033
  workers/       # Worker Adapter registry — T0034
  verifier/      # Independent Verifier process — T0035
  api/           # FastAPI surface
  cli.py         # `aios-kernel` console script
tests/{unit,integration,sim}/
scripts/         # Operator scripts (run_kernel, run_verifier, seed)
docs/            # architecture.md, acceptance_criteria.md
```

## Quickstart

```bash
# Editable install (uses pyproject.toml)
pip install -e ".[dev]"

# Smoke check
python -c "import aios_kernel; print(aios_kernel.__version__)"

# Run CLI
aios-kernel --version
```

## CI

Local `scripts/ci.sh` mirrors `.github/workflows/ci.yml` so the kernel can be
verified without a GitHub remote (per T0031 Out-of-scope).
