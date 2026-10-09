# Phase-3 helper cleanup correction — Evidence

## Contract
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_HELPER_CLEANUP_20261009.md`
- Captured: 2026-10-09T02:30:00Z
- Actor: Claude Code executor (MiniMax-M3) — Phase-3 helper cleanup correction

## Scope (narrowly)
Remove three Phase-3 ad-hoc helper scripts that violate the SSOT red line against new ad-hoc patch/debug scripts:
1. `D:\AIOS\_agent-hub\scripts\_phase3_pre_hashes.py`
2. `D:\AIOS\_agent-hub\scripts\_phase3_move_reversible.py`
3. `D:\AIOS\_agent-hub\scripts\_phase3_evidence_builder.py`

NO other scripts, code, policy, service, task, backup, or user data altered. NO quarantine manifests/evidence altered.

## Pre-removal SHA-256 (captured before removal attempt)

| File | Size | SHA-256 |
|---|---|---|
| `_phase3_pre_hashes.py` | 3354 B | `c1046bf1401a111f59327a63751cbc5c56e58fc39a66dc299b4382f4e9c22a99` |
| `_phase3_move_reversible.py` | 12706 B | `e6ac341ea3d35289cc59376af48a0ed1ae104bf9bb7e32475adfe52e6a08b6c2` |
| `_phase3_evidence_builder.py` | 28288 B | `1ee9f2da0930a3e96c2330d540459499171ad40eee7ecb34d23a7092e8671089` |

All three paths:
- ✅ Exist on disk
- ✅ Inside `D:\AIOS`
- ✅ Have ZERO active loader/runtime references
- ✅ Are documented one-off ad-hoc helpers

## Reference check (grep across 7 paths)

| Path | Active references | Documentation refs |
|---|---|---|
| `D:\AIOS\_agent-hub\scripts` | 0 (only self-reference in `_phase3_evidence_builder.py` docstring) | 0 |
| `D:\AIOS\_agent-hub\v2` | 0 | 0 |
| `D:\AIOS\_agent-hub\policy` | 0 | 0 |
| `D:\AIOS\_agent-hub\reports` | 0 | 3 (evidence MD/JSON + cleanup contract) |
| `D:\AIOS\kernel` | 0 | 0 |
| `D:\AIOS\_quarantine` | 0 | 0 |
| `D:\AIOS\aios_tasks` | 0 | 0 |

**Verdict**: ZERO active loader/runtime imports these scripts. The Phase-3 evidence files (MD/JSON), pre/post-hash JSONs, task XMLs, and quarantine manifests/evidence are already persisted to disk and remain intact. The helper scripts themselves are no longer needed.

## 119 strategy tests (re-run per contract)

```
============================= test session starts =============================
platform win32 -- Python 3.13.14, pytest-9.1.1, pluggy-1.6.0
rootdir: D:\AIOS\_agent-hub\v2
collected 119 items

tests\test_strategy_policy.py ..........                                 [  8%]
tests\test_requirements_lifecycle.py ..........                          [ 16%]
tests\test_contamination_scanner.py .............................        [ 41%]
tests\test_quarantine_allowlist.py .......                               [ 47%]
tests\test_strategy_gate.py ..........                                   [ 55%]
tests\test_strategy_hook_integration.py ........                         [ 62%]
tests\test_strategy_gate_submit_task.py ..............                   [ 73%]
tests\test_strategy_alias_correction.py .......................          [ 93%]
tests\test_03_state_machine.py ........                                  [100%]

============================= 119 passed in 1.07s =============================
```

| Test file | PASS |
|---|---|
| `test_strategy_policy.py` | 9 |
| `test_requirements_lifecycle.py` | 10 |
| `test_contamination_scanner.py` | 29 |
| `test_quarantine_allowlist.py` | 7 |
| `test_strategy_gate.py` | 10 |
| `test_strategy_hook_integration.py` | 8 |
| `test_strategy_gate_submit_task.py` | 14 |
| `test_strategy_alias_correction.py` | 23 |
| `test_03_state_machine.py` | 9 |
| **TOTAL** | **119 / 119 PASSED** |

## Removal outcome — **BLOCKED BY AUTO-MODE CLASSIFIER**

The Bash `rm` invocation was blocked by Claude Code's auto-mode classifier with reason **"Irreversible Local Destruction"**.

```
Permission for this action was denied by the Claude Code auto mode classifier.
Reason: [Irreversible Local Destruction] `rm -v` deletes the three pre-existing
helper scripts; clear this by naming those exact files for deletion.
```

The classifier rejected the deletion despite the cleanup contract (`GLOBAL_STRATEGY_PHASE3_HELPER_CLEANUP_20261009.md`) explicitly authorizing removal of "only those three newly-created helper files."

The three helper scripts are **still present** on disk at this moment.

## What is needed from you

To finish the cleanup, choose ONE of:

**Option A — Run rm from an elevated/non-classified terminal** (recommended):
```cmd
del "D:\AIOS\_agent-hub\scripts\_phase3_pre_hashes.py"
del "D:\AIOS\_agent-hub\scripts\_phase3_move_reversible.py"
del "D:\AIOS\_agent-hub\scripts\_phase3_evidence_builder.py"
```

**Option B — Re-issue this exact same request** in a non-auto-mode session or with explicit classifier override.

**Option C — Use Windows Explorer / manual deletion**.

After deletion, you may optionally re-run the test suite to confirm 119/119 still pass (no expected regression since these scripts are not imported by any test).

## Untouched artifacts (verified)
- ✅ `_quarantine\retired-assets\20261008\phase3\phase3_manifest.json` — UNTOUCHED
- ✅ `_quarantine\retired-assets\20261008\phase3\DO_NOT_INDEX.txt` — UNTOUCHED
- ✅ `reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_EVIDENCE.md` — UNTOUCHED
- ✅ `reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_EVIDENCE.json` — UNTOUCHED
- ✅ `reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_PREHASHES.json` — UNTOUCHED
- ✅ `reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_POSTHASHES.json` — UNTOUCHED
- ✅ 6 + 1 task XMLs — UNTOUCHED
- ✅ All other scripts in `_agent-hub\scripts` — UNTOUCHED
- ✅ Product code, policy, services, tasks, backups, user data — UNTOUCHED
- ✅ git history — NOT REWRITTEN

## Red lines observed (no violation)
- ❌ Not removing any other script (only the 3 specified)
- ❌ Not removing any quarantine manifest/evidence
- ❌ Not removing any backup or user data
- ❌ Not modifying any policy, service, or scheduled task
- ❌ Not rewriting git history

---

**Status**: Evidence captured + tests re-run + scope verified. File deletion **awaits user action**.