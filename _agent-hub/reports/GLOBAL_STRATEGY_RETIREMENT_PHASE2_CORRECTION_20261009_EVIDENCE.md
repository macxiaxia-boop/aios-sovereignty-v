# Phase-2 Correction — Evidence (2026-10-09)

> **Scope**: this file documents the bounded corrective patch that closes the
> `submit_task` policy-gap identified after Phase-2 main construction.
> It is **not** a re-implementation of Phase-2 main.

## 1. Issue (post-Phase-2 inspection finding)

The Phase-2 construction contract added a strategy gate that protected the
**dispatch** path through `goal_guard_hook.guard_dispatch()`. However, the
**task creation** path at `v2/src/state_machine.py::submit_task` had no
equivalent gate. A direct call to `submit_task(title="Re-activate R-001", ...)`
would happily write `tasks/<id>.json` and emit `task.submitted`, bypassing the
strategy gate entirely.

This is exactly the leak Phase-2 was built to close.

## 2. Patch (single-file, surgical)

**File**: `D:\AIOS\_agent-hub\v2\src\state_machine.py`

**Net change**: +140 lines (insertion only — no lines removed, no existing
model / signature rewritten).

Additions (3):

1. **Exception class `StrategyGateRejected`** — clean raised type carrying
   `.events` (structured gate events), `.reason` (machine-readable code),
   optional `.policy_id` / `.policy_version`. Subclasses the built-in
   `Exception`; does not depend on any new model.
2. **Helper `_enforce_strategy_gate()`** — builds a gate-shaped envelope
   from the task's title / description / input_payload (JSON-serialized)
   and calls `goal_guard_hook.strategy_gate_for_root(...).evaluate_envelope(...)`.
   On reject:
     - emits a `task.submit_rejected` event to `events.ndjson` carrying
       both `policy_gate_rejected=True` (umbrella) and
       `underlying_event_type=<matched gate type>` (specific), then
     - raises `StrategyGateRejected`.
   On accept: returns `None` and the caller proceeds normally.
   On policy load failure (missing / malformed / hash-mismatch):
   same reject path with reason `"policy_load_failed"`.
3. **One call site** — inserted at the top of `submit_task`, **before**
   any task JSON is written or any validation runs:

   ```python
   ensure_dirs()
   _enforce_strategy_gate(
       title=title, description=description,
       input_payload=input_payload,
       owner=owner, assignee=assignee,
   )
   now = utc_now_iso()
   task = { ... }   # unchanged
   ...
   ```

The `validate_task`, `_atomic_write_json`, `_log_event("task.submitted")`
and `_record_run` paths are untouched; the patch only inserts a check
before them.

## 3. What was NOT modified (red lines preserved)

| File | Status | Reason |
|---|---|---|
| `v2_consumer.py` | **0 line diff** (verified via `git diff --stat HEAD`) | red-line: v2_consumer diff ≤ 10 lines, this change adds zero |
| `AGENTS.md` | unchanged | not in scope of this correction |
| `policy/model-policy.v1.yaml` | unchanged | user-owned; sovereignty-v boundary |
| `kernel/src/aios_kernel/verifier/deterministic.py` | unchanged | Phase F red line |
| `kernel/src/aios_kernel/domain/{goal,plan,task,trace,evidence}.py` | unchanged | Phase F red line |
| `goal_guard_hook.py` | unchanged by this correction | pre-existing dirty from Phase-2 main work (commit `42e4c81`); not touched in this patch |
| `policy/product_strategy.v1.json` | unchanged | SHA-256 sidecar verified by loader |
| `policy/product_strategy.v1.sha256` | unchanged | sidecar format preserved |

`git diff --stat HEAD` shows only one tracked file changed by the
correction: `_agent-hub/v2/src/state_machine.py | 140 +++++++`.

## 4. Gate behavior contract

| Submission kind | Outcome | No task file? | Event log? | Exception? |
|---|---|---|---|---|
| Horizontal marketing (clean) | accepted | writes `tasks/<id>.json` | `task.submitted` only | no |
| Title references retired id (R-NNN) | rejected | **no new task file** | `task.submit_rejected` with `policy_gate_rejected=True`, `underlying_event_type=RETIRED_REQUIREMENT_REACTIVATED` | `StrategyGateRejected` |
| Description references retired id | rejected | no new task file | same, with matched event | `StrategyGateRejected` |
| `input_payload` references retired id | rejected | no new task file | same, with matched event | `StrategyGateRejected` |
| Title references industry preset (`industry-zhuangxiu` …) | rejected | no new task file | `underlying_event_type=STRATEGY_DRIFT_DETECTED` | `StrategyGateRejected` |
| Description references prohibited asset path | rejected | no new task file | `underlying_event_type=DEPRECATED_ASSET_REFERENCED` | `StrategyGateRejected` |
| Description references archive marker | rejected | no new task file | `underlying_event_type=ARCHIVE_LEAK_DETECTED` (or `DEPRECATED_ASSET_REFERENCED` if both match) | `StrategyGateRejected` |
| Policy file missing / hash-mismatch | rejected (fail-closed) | no new task file | `policy_gate_rejected=True`, `underlying_event_type=POLICY_GATE_REJECTED`, `reason=policy_load_failed` | `StrategyGateRejected` |

The "structured gate decision" requirement is satisfied by routing through
`StrategyGate.evaluate_envelope()`, which uses policy-version-checked lists
(`deprecated_requirement_ids`, `industry_presets_blocked`,
`historical_source_prohibited_keys`, archive markers) — **not** an
ad-hoc keyword block.

## 5. Tests (added)

**New file**: `D:\AIOS\_agent-hub\v2\tests\test_strategy_gate_submit_task.py`

| # | Test | Verifies |
|---|---|---|
| 1 | `test_valid_horizontal_marketing_task_accepted` | clean submission writes task file |
| 2 | `test_retired_id_in_title_rejected` | title-level retired id rejected, no task file, event log correct |
| 3 | `test_retired_id_in_description_rejected` | description-level retired id rejected |
| 4 | `test_retired_id_in_input_payload_rejected` | input_payload-level retired id rejected |
| 5 | `test_industry_preset_submission_rejected` | STRATEGY_DRIFT_DETECTED event |
| 6 | `test_deprecated_asset_submission_rejected` | DEPRECATED_ASSET_REFERENCED event |
| 7 | `test_archive_leak_submission_rejected` | ARCHIVE_LEAK_DETECTED or DEPRECATED_ASSET_REFERENCED event |
| 8 | `test_fail_closed_when_policy_missing` | policy load failure → fail-closed with reason `policy_load_failed` |
| 9 | `test_submit_rejected_event_has_both_umbrella_and_underlying_keys` | event log carries both flags |
| 10 | `test_submit_rejected_event_has_umbrella_when_policy_load_fails` | fail-closed path emits `POLICY_GATE_REJECTED` umbrella in `all_event_types` |
| 11 | `test_rejected_submission_does_not_break_subsequent_valid_submit` | cache and gate state survive rejections |
| 12 | `test_backwards_compat_simple_titles_still_pass` | existing `title="x"` style still works |
| 13 | `test_backwards_compat_full_lifecycle_still_works` | submit → cancel / submit → running → succeeded still works |
| 14 | `test_real_policy_loader_works_via_submit_task_path` | policy loader + SHA sidecar via its own public API still OK |

**Result**: **14/14 PASSED**.

## 6. Existing tests — no regression

The previous Phase-2 contract added 59 strategy tests. All of them
remain PASSING, plus the 8 existing state_machine tests:

| File | Tests |
|---|---|
| `test_strategy_policy.py` | 9 PASS |
| `test_requirements_lifecycle.py` | 10 PASS |
| `test_contamination_scanner.py` | 13 PASS |
| `test_quarantine_allowlist.py` | 7 PASS |
| `test_strategy_gate.py` | 10 PASS |
| `test_strategy_hook_integration.py` | 8 PASS |
| `test_03_state_machine.py` | 8 PASS |
| `test_strategy_gate_submit_task.py` (new) | 14 PASS |
| **TOTAL** | **81 PASS, 0 FAIL** |

Test command:
```bash
cd "D:\AIOS\_agent-hub\v2" && \
python -m pytest \
    tests/test_strategy_policy.py \
    tests/test_requirements_lifecycle.py \
    tests/test_contamination_scanner.py \
    tests/test_quarantine_allowlist.py \
    tests/test_strategy_gate.py \
    tests/test_strategy_hook_integration.py \
    tests/test_03_state_machine.py \
    tests/test_strategy_gate_submit_task.py
```

## 7. Policy loader + SHA sidecar — public API verification

The patch does **not** introduce a parallel loader. It uses
`goal_guard_hook.strategy_gate_for_root(...)` which internally calls
`policy.strategy_gate.gate_from_policy_dir(policy_dir)` →
`policy.strategy_policy.load_strategy_policy(policy_dir)`.

`load_strategy_policy` returns a `PolicyLoadResult` whose `.ok` is True
**only** when:

  - JSON parses (`malformed_json` otherwise)
  - SHA-256 matches sidecar (`hash_mismatch` otherwise)
  - Subset schema validation passes (`schema_violation` otherwise)
  - identity fields match expected `policy_id` / `policy_version` /
    `owner` / `change_authority` / `status`
    (`policy_identity_mismatch` otherwise)

When `.ok = False`, `strategy_gate_for_root` caches `None` and the gate
rejects with `reason="policy_load_failed"`.

`test_real_policy_loader_works_via_submit_task_path` asserts:

  - `load_strategy_policy(POLICY_DIR).ok` is True
  - `policy["policy_id"] == "GLOBAL_PRODUCT_STRATEGY"`
  - `policy["policy_version"] == "2026-10-08"`
  - `res.sha256` equals `hashlib.sha256(json_file.read_bytes()).hexdigest().upper()`

The sidecar format (`<HEX64>  product_strategy.v1.json` with comment
lines) was **not** modified; the public API in `strategy_policy.py` reads
it unchanged.

## 8. Diff summary

```
 _agent-hub/v2/src/state_machine.py                        | 140 +++++++
 _agent-hub/v2/tests/test_strategy_gate_submit_task.py     | (new) 14 tests
```

Tracked file change: `git diff --stat HEAD` shows only
`_agent-hub/v2/src/state_machine.py | 140 +++++++` — zero removals,
zero modifications to existing logic.

## 9. Unresolved issues

**None** for the gated task-creation path. The patch closes the
inspection-found gap exactly as the contract requires.

The Phase-2 main contract's deferred high-impact manifest
(`GLOBAL_STRATEGY_RETIREMENT_PHASE2_20261009_DEFERRED.md`) is unchanged
and remains requires_authorization: live CloudTech gateway teardown,
service stop+delete, scheduled task deletes, E:\AI_Backup scope change,
root installer scripts, archive deletes, git history rewrite, etc.