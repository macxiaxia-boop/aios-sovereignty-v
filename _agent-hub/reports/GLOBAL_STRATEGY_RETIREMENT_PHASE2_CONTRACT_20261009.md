# AIOS Global Product Strategy Retirement — Phase 2 Construction Contract

## Executor and authority
Claude Code is the executor. Codex is supervisor and independent verifier. Read `D:\AIOS\_agent-hub\AGENTS.md` and memory logs for 2026-10-08 and 2026-10-09 before editing. The audit of record is `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008.md/.json` plus the three partial audit pairs in `GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008`.

## Authorized objective
Implement the safe, reversible portion of the user's product-strategy retirement. CloudTech / 灵策智算 is a horizontal, general marketing SaaS. Do not let cancelled vertical/industry-specific direction re-enter active planning, task generation, dispatch, prompt context, or RAG sources. Preserve reusable generic marketing capabilities. Do not invent retired IDs; use only evidence-backed R-001..R-020 in the audit (R-021 is sensitive and must not be expanded into secret contents).

## Hard red lines
- Do not edit `D:\AIOS\_agent-hub\AGENTS.md` or duplicate the strategy policy. The single machine-readable Product Strategy Policy must be the one registered SSOT.
- Do not rewrite the existing Goal/Plan/Task/Trace/Evidence models. Do not modify `kernel/src/aios_kernel/verifier/deterministic.py`. Keep `v2_consumer.py` diff <= 10 lines.
- Do not stop/delete Windows services, kill the live CloudTech gateway, unregister scheduled tasks, delete cloud backups, delete E:\AI_Backup, delete personal files, or alter git history in this phase. Record these as deferred high-impact operations with exact paths.
- Do not use keyword-only blocking. The gate must use policy version/hash, retired requirement IDs, component identity, source classification, and dependency/data-source evidence. Keyword matches are auxiliary only.
- Do not change the user-owned model policy (`model-policy.v1.yaml`) or existing sovereignty-v work.

## Required implementation
1. Create one machine-readable policy SSOT under `D:\AIOS\_agent-hub\policy\` (JSON plus JSON Schema and SHA-256 sidecar) with exactly: policy_id `GLOBAL_PRODUCT_STRATEGY`, policy_version `2026-10-08`, product `CloudTech`, positioning `HORIZONTAL_MARKETING_SAAS`, business_scope `GENERAL_MARKETING`, vertical_product_strategy `DISABLED`, industry_presets `DISABLED`, deprecated_requirement_ids R-001..R-020, prohibited_active_assets derived from the audit (no secret paths/contents), owner `USER`, change_authority `EXPLICIT_USER_APPROVAL`, status `ACTIVE`. Include explicit scope note: horizontal marketing does not mean all-industry business management software; customer-supplied materials may customize workers without restoring official industry presets.
2. Add a policy loader/validator with hash and explicit-user-approval enforcement. Missing, malformed, hash-mismatched, or unapproved policy must fail closed for task creation and dispatch.
3. Add a requirements lifecycle module/schema supporting PROPOSED, APPROVED, ACTIVE, COMPLETED, SUPERSEDED, RETIRED, REJECTED, ARCHIVED and valid transitions. This is a requirement registry, not a rewrite of the existing task aggregate/state machine.
4. Add a Strategy Gate that checks new task creation and dispatch for policy compliance, retired IDs, deprecated assets, vertical strategy, unauthorized product direction changes, and historical-source reactivation. Reject/isolate with event types `STRATEGY_DRIFT_DETECTED`, `RETIRED_REQUIREMENT_REACTIVATED`, `DEPRECATED_ASSET_REFERENCED`, `INVALID_TASK_GENERATED`, `ARCHIVE_LEAK_DETECTED`, `POLICY_GATE_REJECTED`. Integrate through the existing goal_guard_hook without changing the v2 consumer main loop beyond the red-line budget; also protect v2 task submission if possible.
5. Add a structured contamination scanner with classifications `ACTIVE_VIOLATION`, `ARCHIVED_REFERENCE`, `FALSE_POSITIVE`, `UNVERIFIED`. It must emit machine-readable evidence and block active violations. Do not treat every keyword hit as a violation.
6. Quarantine only these confirmed active/dormant WorkBuddy assets by reversible move to `D:\AIOS\_quarantine\retired-assets\20261008\` (never delete): the exact memory profile `C:\Users\xinzh\.workbuddy\memory\45e357fa-c2ec-4bd0-b734-9b016a2759d7_memory.md`; the exact home cache under `C:\Users\xinzh\.workbuddy\storage\user-45e357fa-c2ec-4bd0-b734-9b016a2759d7-personal\scoped\c7389fe09fa872c0\home-first-screen-cache.json`; the exact skills-installed-store under the same scoped directory; the exact `C:\Users\xinzh\.workbuddy\plugins\marketplaces\workbuddy-connector-plugins-official\connectors\zxygj-business-data\` directory; and `C:\Users\xinzh\.workbuddy\sessions\23852.json` if its content is confirmed old strategy. Preserve a manifest with source path, SHA-256, reason, quarantine path, timestamp, and restore instructions. Put a `DO_NOT_INDEX.txt` marker in quarantine and exclude it from scanner/indexers. If a path differs, has changed hash, or is not confirmed by the audit, do not touch it; record UNVERIFIED.
7. Update only active AIOS governance/registry indexes needed to register the policy, lifecycle, gate, scanner, and quarantine manifest. Do not rewrite historical registries. Keep historical references classified ARCHIVED_REFERENCE and out of active loaders.
8. Add focused unit/integration tests for policy load/hash/approval, lifecycle transitions, retired-ID blocking, deprecated-asset blocking, source-based archive leak detection, quarantine allowlist, and gate events. Add a machine-readable test evidence file.
9. Build a deferred-high-impact manifest for (without executing): live CloudTech gateway/service, 5 CloudTech scheduled tasks, CloudTech service/monitor XML, root installer scripts, E:\AI_Backup mirror, cloud backups, and any personal/session files not on the explicit allowlist. Include exact paths, current process/task/service evidence, and the authorization needed.
10. Write implementation evidence and diff summary to `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PHASE2_20261009_EVIDENCE.md/.json`.

## Verification required before completion
- `python -m pytest` for the new strategy/lifecycle/scanner tests plus existing v2 tests that cover goal guard and task submission.
- Validate policy JSON/schema/hash and all JSON evidence files parse.
- Demonstrate a valid horizontal marketing task is accepted and a task referencing R-001/R-009/industry preset or deprecated asset is rejected before dispatch.
- Demonstrate quarantine manifest hashes and `DO_NOT_INDEX` marker, and that scanner classifies quarantine entries as ARCHIVED_REFERENCE/UNVERIFIED rather than ACTIVE_VIOLATION.
- Demonstrate no v2_consumer.py diff exceeds 10 lines and no existing Goal/Plan/Task/Trace/Evidence model or verifier was rewritten.
- Do not claim live gateway teardown, scheduled-task removal, backup purge, or full-disk zero residue; list them as deferred.

Return ACK with changed paths, tests, and unresolved high-impact operations.
