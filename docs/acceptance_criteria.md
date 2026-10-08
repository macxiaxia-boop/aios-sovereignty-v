# AIOS Kernel — Phase A Acceptance Criteria

> This document **references** T0030 `Phase A Acceptance Spec v0.1` (frozen).
> Do NOT redefine acceptance here — only mirror the scope of T0031's exit gate.

## 1. Source-of-Truth

- Spec ID: `AIOS_VNEXT_PHASE_A_ACCEPTANCE_v0.1`
- Owner: Codex (supervisor)
- Frozen in: T0030
- Reference path: `D:\AIOS\aios_tasks\aios_vnext\cards\T0030_*.md`

## 2. T0031 Exit Criteria (mirrored from card)

1. `D:\AIOS\kernel\` exists and is an independent git repo on branch `main`.
2. Directory tree matches `cards/T0031_kernel_repo_init.md` §Scope 2.
3. `pip install -e .` exits 0.
4. `python -c "import aios_kernel"` prints version.
5. `pytest --collect-only` exits 0 (0 tests collected is acceptable at scaffold stage).
6. `ruff check src/` reports 0 issues.
7. `git log --oneline` shows ≥ 1 commit on `main`.

## 3. Downstream Cards (will tighten this)

- T0032 — domain + persistence contracts
- T0033 — durable execution
- T0034 — worker registry
- T0035 — verifier
- T0036 — 100-task closed-loop
- T0037 — crash recovery
- T0038 — Phase A 综合验收 (Codex 独立签字)
