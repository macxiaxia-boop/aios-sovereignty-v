# Cross-session / no-reanimation regression contract

Claude Code, read D:\AIOS\_agent-hub\AGENTS.md and memory 2026-10-08/09. Implement a deterministic, machine-readable cross-session regression harness for T01–T18 using the existing policy/gate/scanner/lifecycle and actual local task/config/quarantine evidence. Do not use model-only assertions.

Required:
- Add a supported test module under `D:\AIOS\_agent-hub\v2\tests\test_strategy_cross_session.py` (or equivalent) that covers T01–T18 and records PASS/DEFERRED/FAIL with evidence path and reason. A DEFERRED result must be explicit and must never be reported as PASS.
- T01/T02/T03/T04/T05/T06/T07/T08/T09/T12/T14/T15/T17: exercise the actual policy loader, structured StrategyGate, scanner source classification, lifecycle/task submission, and quarantine/archive manifests using fresh inputs without historical chat context. For task-generation scenarios, inspect the generated/accepted/rejected structured task decision, not just model wording.
- T10/T11/T13/T16: inspect actual local runtime/config evidence (service/task state, source paths, quarantine marker/manifests, build/deploy paths). If OS permissions or external CloudTech runtime prevent a PASS, record DEFERRED with exact evidence and required elevated action; do not silently pass.
- T18: verify generic horizontal marketing task acceptance and a minimal generic marketing capability check. If no generic marketing API/UI contract is available in the current source, record DEFERRED with exact reason rather than claiming functional completeness.
- Add a reusable supported harness under `D:\AIOS\_agent-hub\policy\` only if needed; do not add ad-hoc scripts outside the policy/test package.
- Write `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_CROSS_SESSION_20261009_EVIDENCE.md/.json`, run all strategy tests plus the new matrix, and return ACK with counts and all DEFERRED cases. Do not touch services, backups, user data, AGENTS.md, model-policy, or git history.
