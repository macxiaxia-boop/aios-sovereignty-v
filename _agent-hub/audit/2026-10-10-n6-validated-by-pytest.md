# 2026-10-10 · N6 真实 pytest VALIDATION · PASSED (rebuilt on main)

> **状态**: ✅ N6 commit 64c6798 VERIFIED BY REAL PYTEST
> **测试员**: Codex

## 测试范围

```
pytest -v -p no:anyio tests/integration/test_crash_recovery.py
```

**结果**: **10/10 PASSED** in 49.27s

| Test | Status |
|---|---|
| test_cr1 | PASS |
| test_cr2 | PASS |
| test_cr3 | PASS |
| test_cr4 | PASS |
| test_cr5 | PASS |
| test_cr6 | PASS |
| test_cr7_five_consecutive_crashes_recover_to_completed | **PASS** (was R1348B blocker) |
| test_cr8 | PASS |
| test_cr9 | PASS |
| test_cr10 | PASS |

## 比较

| Round | Crash-recovery score |
|---|---|
| Round 6 baseline | 16/22 |
| Round 7 | 19/22 |
| Round 8 (latest reported) | 22/23 (CR7 race 残留) |
| **Round 9 / AIPM02 N6** | **10/10 crash suite** |

## Engine import smoke

```
from aios_kernel.workflows.engine import PGCheckpointerEngine
methods = [m for m in dir(PGCheckpointerEngine) if 'reset' in m.lower() or 'start' in m.lower() or 'resume' in m.lower()]
=> ['_reset_completed_run_for_replay', 'resume', 'start']
```

Helper on the **correct** class (`PGCheckpointerEngine`, not `WorkflowEngine` Protocol).

## 含义

N6 fix works. Round 9 baseline now potentially clean (kernel crash recovery + run_id handling).

## EVIDENCE_TRAIL

完整 pytest run log: `C:\Users\xinzh\Documents\Codex\2026-10-09\files-pasted-by-the-user-codex\outputs\test_crash_recovery_full.log`
Commits: 64c6798 + ca8ec93 (both on main)
