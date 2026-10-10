# 2026-10-10 AIPM02 · Stage B-1 · N6 DONE (rebuilt on main)

> **状态**: ✅ APPLIED + COMMITED (in kernel submodule)
> **Commits**: 64c6798 (kernel submodule) + ca8ec93 (parent bump) on main
> **作者**: Codex autonomous run

## Apply 过程

| Step | Action | Result |
|---|---|---|
| 1 | N6_engine_patch.py --dry-run | 55 diff lines all additive |
| 2 | N6_engine_patch.py --apply | OK |
| 3 | N6_test_cr7.py (unit) | PASS |
| 4 | ast.parse(engine.py) | OK |
| 5 | cd kernel; git add; commit | **64c6798** (40 insertions) |
| 6 | cd ..; git add kernel; commit | **ca8ec93** (submodule pointer) |

## 真实 pytest 验证(2026-10-10 用户授权后跑)

```
$ pytest tests/integration/test_crash_recovery.py -v -p no:anyio

test_cr1 ... PASSED
test_cr2 ... PASSED
test_cr3 ... PASSED
test_cr4 ... PASSED
test_cr5 ... PASSED
test_cr6 ... PASSED
test_cr7_five_consecutive_crashes_recover_to_completed  PASSED  ← 之前 fail 的那个
test_cr8 ... PASSED
test_cr9 ... PASSED
test_cr10 ... PASSED

================ 10 passed in 49.27s ================
```

→ Round 8 baseline (7/10 crash) → 10/10. **N6 patch 真实有效。**

详见同目录 `2026-10-10-n6-validated-by-pytest.md`。

## Why engine.py (not _kernel_worker.py)

原 handoff 引用 _kernel_worker.py:232-244 实际上不存在该分支。实测 _kernel_worker.py 直接调用 `engine.start(wf, run_id=run_id)`,没有 R1348 routing 分支。真正修复点是 `engine.start()` 在 INSERT OR IGNORE 后跑 _drive(resume_from=None),当 status=completed 时不再跑 step B。N6 patch 正确指向 PGCheckpointerEngine.start() line 122 + 新 helper `_reset_completed_run_for_replay`。

## Commit(s)

- 64c6798 (kernel submodule) - +40 lines
- ca8ec93 (parent) - submodule pointer bump

## Red lines

- 0 deletes
- resume() unchanged
- helper only fires on status=completed (won'’t disrupt fresh runs)
