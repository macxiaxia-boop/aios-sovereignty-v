# Strategy Gate Self-Audit — 2026-10-09

- **Audit scope:** `D:\AIOS\_agent-hub\policy\strategy_gate.py`, `strategy_policy.py`, `product_strategy.v1.json`, and both requested strategy-gate test modules.
- **Auditor:** Codex worker.
- **Captured:** 2026-10-09T09:56:00+08:00
- **Baseline repository status:** 194 `git status --short` lines at audit start (pre-existing shared-worktree state; not treated as owned by this worker).

## 1. Fresh test run

Command:

```text
pytest -vv D:\AIOS\_agent-hub\v2\tests\test_strategy_gate.py D:\AIOS\_agent-hub\v2\tests\test_strategy_gate_submit_task.py
```

Output head:

```text
============================= test session starts =============================
platform win32 -- Python 3.11.15, pytest-9.1.1
collecting ... collected 24 items
```

Output tail:

```text
_agent-hub/v2/tests/test_strategy_gate_submit_task.py::test_real_policy_loader_works_via_submit_task_path PASSED [100%]
============================= 24 passed in 0.46s =============================
```

Full capture: `D:\AIOS\_agent-hub\reports\strategy_gate_audit_pytest.log`.
**Result:** 24/24 passed, exit code 0.

## 2. Rule-to-test coverage

The policy declares six gate event types. The requested tests exercise at least one positive/blocking path for each:

| Policy event | Direct test evidence | Verdict |
|---|---|---|
| `STRATEGY_DRIFT_DETECTED` | `test_industry_preset_blocked`; `test_industry_preset_submission_rejected` | Covered for one preset only |
| `RETIRED_REQUIREMENT_REACTIVATED` | `test_retired_id_R001_blocks`, `test_retired_id_R009_blocks`, and submit-task title/description/input tests | Covered, but not all 20 IDs |
| `DEPRECATED_ASSET_REFERENCED` | `test_deprecated_asset_reference_blocks`; `test_deprecated_asset_submission_rejected` | Covered for one historical key only |
| `INVALID_TASK_GENERATED` | `test_invalid_task_blocks` | Covered for missing title/text only |
| `ARCHIVE_LEAK_DETECTED` | `test_archive_leak_detected`; `test_archive_leak_submission_rejected` | Covered for hard-coded archive marker only |
| `POLICY_GATE_REJECTED` | missing-policy submit test and reject-event tests | Covered for policy-load failure |

The 24 tests are a useful regression suite, but they do **not** prove complete policy coverage. The gaps below are real implementation/coverage findings, not test failures.

## 3. Policy vs gate findings

### A-1 — HIGH: `prohibited_active_assets` is not evaluated by `evaluate_envelope`

The policy contains 12 `prohibited_active_assets` entries (PA-01..PA-12), but `StrategyGate.evaluate_envelope()` never reads that field. It only scans `historical_source_prohibited_keys` and retired aliases. Live probes reproduced allowed/no-event decisions for PA-08 (`deepseek-v4-flash`), PA-09 (`minimax-cn`), PA-10 (`install_aios_loop.cmd`), and PA-12 (`_backup_aios_exe`), among others. The existing tests therefore do not cover the policy's PA list.

**Disposition:** open finding; no code changed in this audit-only task.

### A-2 — HIGH: `quarantine_paths` is not consulted by `evaluate_envelope`

The policy has five WorkBuddy quarantine paths. `evaluate_envelope()` never reads `policy["quarantine_paths"]`; archive detection uses a hard-coded marker tuple. A clean text containing one of the actual quarantine paths was allowed. This is a policy/gate inconsistency.

### A-3 — MEDIUM: malformed non-empty task payloads can bypass the task-shape check

The malformed-task branch runs only when `isinstance(payload, dict)`. A non-empty list, string, or number used as a task payload was allowed in live probes. An empty list is normalized to `{}` and blocked, but non-empty wrong-type payloads are not consistently rejected. The task envelope should validate payload type independently of content scans.

### A-4 — MEDIUM: submit-task nested GoalContract criteria are not checked

`_enforce_strategy_gate()` serializes `input_payload` into the envelope's `text` field. `evaluate_envelope()` only checks `payload["goal"]`, so a submit-like task with `input_payload={"goal": {"description": "x"}}` and no `success_criteria` was allowed. The direct goal warning is therefore not reachable through the public submit-task path for nested input payloads.

### A-5 — MEDIUM: alias matching does not honor its documented ASCII case-insensitive contract

`strategy_policy.is_retired_alias()` uses case-sensitive substring matching. A live probe using lowercase `cloudtech v22` was allowed, while the helper documentation says ASCII components should be case-insensitive. No requested test covers case variants.

### A-6 — MEDIUM: gate event vocabulary is hard-coded instead of policy-driven

The policy has `gate_event_types`, but the gate emits a fixed set of six event names. A future policy event type can validate successfully without any implementation path emitting it. The loader validates the vocabulary; the gate does not consume it as the runtime source of truth.

### A-7 — MEDIUM: terminal short-circuit exists in the hook but not in the gate

The requested gate test only proves benign terminal payloads pass. A terminal `result` payload containing `R-001` is rejected by `StrategyGate.evaluate_envelope()` itself. `goal_guard_hook.py` currently short-circuits terminal types before invoking the gate, so production dispatch is defended, but the gate is not independently defense-in-depth and its own contract is inconsistent with the hook.

### A-8 — LOW: fixed `R-\d{3}` regex is narrower than the policy helper contract

The policy currently contains exactly R-001..R-020, so the regex catches all current IDs. A future requirement ID with another width/format would be in policy but not in the gate's token scanner. Tests cover only R-001 and R-009, not all 20 current IDs.

## 4. Race-condition review

No data race was found in `evaluate_envelope()` under the current implementation: it builds a request-local `events` list, only reads shared policy data, and does not mutate the registry/scanner. `time.time()` values can differ between concurrent calls but do not affect the allow/deny decision. This is a static/behavioral review; no thread stress harness was added.

The main correctness risk is input-shape and policy-drift behavior, not shared-memory concurrency.

## 5. Verdict

- **Machine test status:** PASS — 24/24.
- **Policy completeness status:** FAIL / open findings — not every policy rule is implemented or covered by these tests.
- **Race-condition status:** no shared-state race identified; gate should still be stress-tested if mutable scanner/registry state is introduced later.
- **Action:** findings are documented for follow-up rather than hidden or silently treated as covered.
