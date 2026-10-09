# Cross-session / no-reanimation regression evidence — T01–T18

**Contract**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_CROSS_SESSION_TEST_CONTRACT_20261009.md`

**Executed**: 2026-10-08T17:49:07Z

**Actor**: Claude Code 2.1.285 (MiniMax-M3) — executor

## Totals

- Total tests: **18**
- PASS: **17**
- DEFERRED: **1**
- FAIL: **0**

> DEFERRED is explicit and never reported as PASS. Every DEFERRED case below carries evidence + required user action.

## Per-test matrix

| ID | Name | Verdict | Evidence | Reason |
|---|---|---|---|---|
| T01 | Policy loader produces ACTIVE policy from fresh files | **PASS** | `D:\AIOS\_agent-hub\policy\product_strategy.v1.json` | policy file parses, sidecar hash matches, schema validates, identity fields OK |
| T02 | Policy SHA-256 sidecar matches on-disk content | **PASS** | `D:\AIOS\_agent-hub\policy\product_strategy.v1.sha256` | file hash matches sidecar hash (subprocess-verified) |
| T03 | Strategy gate uses STRUCTURED decision (not bare keyword) | **PASS** | `D:\AIOS\_agent-hub\v2\src\goal_guard_hook.py` | non-structured-field alias hit WARN-only; structured-field alias hit BLOCK |
| T04 | Strategy gate emits all 6 policy.gate_event_types | **PASS** | `D:\AIOS\_agent-hub\v2\tests\test_strategy_gate.py` | all 6 gate_event_types reachable |
| T05 | Scanner source classification is STRUCTURED (not bare keyword) | **PASS** | `D:\AIOS\_agent-hub\policy\contamination_scanner.py` | all 5 sub-path surfaces classified correctly |
| T06 | Scanner content-aware classification emits ACTIVE_VIOLATION | **PASS** | `D:\UsersTemp\cross_session_T06_ee444c03.md` | active loadable file with retired tokens -> ACTIVE_VIOLATION finding |
| T07 | Lifecycle valid transitions PROPOSED→APPROVED→ACTIVE→COMPLETED→ARCHIVED | **PASS** | `in-test` | traversed ['APPROVED', 'ACTIVE', 'COMPLETED', 'ARCHIVED'] ending at ARCHIVED |
| T08 | Lifecycle RETIRED blocks re-activation; ARCHIVED is terminal | **PASS** | `in-test` | RETIRED→ACTIVE rejected; only RETIRED→ARCHIVED allowed; ARCHIVED→ACTIVE rejected |
| T09 | Lifecycle transition table rejects all invalid jumps | **PASS** | `in-test` | 3 invalid jumps correctly rejected (PROPOSED→ACTIVE, APPROVED→COMPLETED, ACTIVE→ARCHIVED) |
| T10 | Quarantine manifest present with correct schema | **PASS** | `D:\AIOS\_quarantine\retired-assets\20261008\quarantine_manifest.json` | manifest has 5 entries, policy_id=GLOBAL_PRODUCT_STRATEGY, DO_NOT_INDEX marker present, ok=True |
| T11 | DO_NOT_INDEX marker exists and is well-formed | **PASS** | `D:\AIOS\_quarantine\retired-assets\20261008\DO_NOT_INDEX.txt` | marker contains all policy markers |
| T12 | submit_task honors strategy gate (fail-closed on retired-id) | **PASS** | `D:\AIOS\_agent-hub\v2\src\state_machine.py` | retired-id envelope blocked (StrategyGateRejected); valid task accepted |
| T13 | AIOSV2Consumer service registration inspectable | **PASS** | `sc qc AIOSV2Consumer` | service registered (START_TYPE=2 AUTO_START DELAYED); runtime START blocked from non-elevated shell per memory log, but registration is the cross-session-relevant artifact |
| T14 | Archived surface AIOS_SOURCE_OF_TRUTH_FINAL exists and is classified | **PASS** | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap` | path exists at root + sub-path classifies as 'read_only' (read_only/archived) |
| T15 | Policy + registry + scanner + gate integration (end-to-end) | **PASS** | `D:\AIOS\_agent-hub\v2\src\goal_guard_hook.py` | deprecated id R-001 blocked with structured risk envelope |
| T16 | Build/deploy paths present in repo | **DEFERRED** | `D:\AIOS\{Dockerfile,docker-compose.yml,Makefile,deployment,deploy,.github}` | no top-level build/deploy artifact found; per R1315 W4.1 SaaS deployment is generated on-demand via _r1315_saas_deployment.py but is not part of the cross-session source policy package. Required action: user-decide whether build/deploy should be materialized as part of the cross-session harness, or remain out-of-scope for cross-session regression. |
| T17 | Quarantine allowlist matches policy entries | **PASS** | `D:\AIOS\_quarantine\retired-assets\20261008\quarantine_manifest.json` | all 5 policy entries accounted for (5 matched / 0 missing / 0 unmatched) |
| T18 | Generic horizontal marketing task acceptance + capability | **PASS** | `D:\AIOS\_agent-hub\policy\product_strategy.v1.json` | horizontal envelope accepted; policy declares HORIZONTAL_MARKETING_SAAS + GENERAL_MARKETING + verticals/presets DISABLED |

## Deferred manifest (require user action)

### T16 — Build/deploy paths present in repo

- **Verdict**: DEFERRED
- **Evidence**: `D:\AIOS\{Dockerfile,docker-compose.yml,Makefile,deployment,deploy,.github}`
- **Reason / required action**: no top-level build/deploy artifact found; per R1315 W4.1 SaaS deployment is generated on-demand via _r1315_saas_deployment.py but is not part of the cross-session source policy package. Required action: user-decide whether build/deploy should be materialized as part of the cross-session harness, or remain out-of-scope for cross-session regression.

## Red lines observed

- AGENTS_md_untouched: ✅
- v2_consumer_py_untouched: ✅
- kernel_models_untouched: ✅
- verifier_untouched: ✅
- no_services_started_or_stopped: ✅
- no_history_rewrites: ✅
- no_user_data_modified: ✅
