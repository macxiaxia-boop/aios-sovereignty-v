# Phase-2 correction: task creation gate

Claude Code, read D:\AIOS\_agent-hub\AGENTS.md and memory 2026-10-08/09. The Phase-2 strategy gate currently protects dispatch through goal_guard_hook, but independent inspection found `D:\AIOS\_agent-hub\v2\src\state_machine.py::submit_task` has no strategy/policy gate. Correct this gap.

Requirements:
- Add a small, explicit strategy-policy check at the start of v2 `submit_task`, before any task JSON is written. Use the existing `policy.strategy_gate.StrategyGate`; evaluate task title/description/input_payload and reject retired IDs, prohibited active assets, vertical/industry-preset direction, and policy load/hash/approval failures. Do not keyword-only block; use the structured gate decision.
- Rejected submissions must create no task file and must log an event containing `POLICY_GATE_REJECTED` plus the underlying event type. Raise a clear exception for CLI callers. Valid horizontal marketing submissions must continue unchanged.
- Do not rewrite existing task/goal models, do not modify v2_consumer.py, AGENTS.md, model-policy, or any product code outside this v2 governance path.
- Add focused tests that call `state_machine.submit_task` with a temporary `AIOS_V2_ROOT`/policy setup and prove valid accept, retired/deprecated reject, no task file on reject, and event evidence. Keep existing 59 strategy tests passing.
- Verify policy loader and SHA sidecar using its own public API; do not change the sidecar format unless necessary.
- Write `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PHASE2_CORRECTION_20261009_EVIDENCE.md/.json` with diff, tests, and any unresolved issue.
- Return ACK only after tests pass and evidence files exist.
