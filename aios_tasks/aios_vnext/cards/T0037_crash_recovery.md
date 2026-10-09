---
id: T0037
title: Crash Recovery 测试（含 kill -9 中途）
owner: CC
priority: P0
track: 3 — VNext Phase A
preconditions: [T0031, T0032, T0033, T0034, T0035]
estimated_minutes: 120
depends_on: [T0031, T0032, T0033, T0034, T0035]
blocks: [T0038]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

实现 **Crash Recovery 测试**（规格 §104.6 "Crash 可恢复" + §101 Kernel 必须独立）。

1. **Crash 注入工具** `tests/integration/crash_injector.py`：
   ```python
   class CrashInjector:
       async def start_kernel(self) -> KernelProcess: ...
       async def kill_n9(self, kernel: KernelProcess) -> None: ...  # SIGKILL
       async def kill_terminate(self, kernel: KernelProcess) -> None: ...  # SIGTERM
       async def restart(self, kernel: KernelProcess) -> KernelProcess: ...
       async def verify_state(self, expected: WorkflowState) -> bool: ...
   ```
   - Windows: 用 `subprocess.Popen` + `taskkill /F /PID` 模拟 SIGKILL
   - Linux: 用 `os.kill(pid, signal.SIGKILL)`

2. **测试用例**（`tests/integration/test_crash_recovery.py`）：

   | # | 场景 | 验证 |
   |---|------|------|
   | CR1 | Kernel 在 Goal 创建中途 crash | 重启后 Goal 存在且 status 正确 |
   | CR2 | Kernel 在 Task 执行中 crash（Activity 1/3 完成）| 重启后从 Activity 2 重跑，**不重复 Activity 1** |
   | CR3 | Kernel 在 Plan reversion 中 crash | 重启后 Plan vN-1 状态正确 |
   | CR4 | Kernel 在 Verifier 调用中 crash | 重启后 Verifier 重新跑，结果一致 |
   | CR5 | Kernel 在 Budget check 中 crash | 重启后 Budget 状态正确（不重复扣费） |
   | CR6 | Kernel 在 evidence 写入中 crash | 重启后 evidence 完整（无半写状态） |
   | CR7 | 连续 5 次 crash + restart | 系统最终达到稳定状态 |
   | CR8 | Crash 时 verifier 也在跑 | Verifier 独立进程不被影响 |
   | CR9 | DB 连接断开时 crash | 重启后能重建连接 |
   | CR10 | Workflow Run 跨 restart 续跑 | run_id 不变，状态连续 |

3. **断言规则**：
   - **幂等性**：同一个 Activity 不能跑 2 次（如已 done，跳过）
   - **原子性**：DB 写入要么全成要么全败（PG 事务）
   - **持久性**：kill -9 后数据不丢
   - **可恢复性**：100% workflow run 可恢复到最后 checkpoint

4. **测试基础设施**：
   - 用 T0031 的 dev 模式（sqlite + 本地启动）
   - 每个测试用例独立 DB（用临时目录）
   - 用 pytest fixture 提供 KernelProcess 实例

5. **测试报告** `D:\AIOS\_agent-hub\reports\t0037_crash_recovery_report_<ts>.md`：
   - 10 个测试用例详细结果
   - 恢复时间统计（每个 case 的 restart → recovery 时间）
   - 失败 case 分析

## Out-of-scope (不要做)
- ❌ 不要做 OS-level crash（如断电）模拟
- ❌ 不要做 network partition（不是 Phase A 范围）
- ❌ 不要做磁盘损坏
- ❌ 不要碰 Production 真实 kernel
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs
- T0031 kernel
- T0032 ORM (transaction 用)
- T0033 Workflow Engine + checkpointer
- T0034 Worker Adapter
- T0035 Verifier 独立进程

## Outputs
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0037_<ts>.md`
2. `tests/integration/crash_injector.py`
3. `tests/integration/test_crash_recovery.py`
4. `D:\AIOS\_agent-hub\reports\t0037_crash_recovery_report_<ts>.md`

## Evidence Requirements
- [ ] CrashInjector 5 方法实现
- [ ] 10 个测试用例 CR1-CR10 全部实现
- [ ] 每个 case 断言：幂等 + 原子 + 持久 + 可恢复
- [ ] 测试报告含详细结果 + 恢复时间
- [ ] `pytest tests/integration/test_crash_recovery.py -v` 全 pass
- [ ] 没有任何 Failed case: 不接受
- [ ] Verifier 独立（CR8）— pid 验证

## Exit Criteria
1. evidence 全部勾选
2. 测试报告落到正确位置
3. CC 把 status=Submitted 后等 Codex

## Rollback
1. `git reset --hard HEAD~N`
2. 写 rollback log

## Time Budget
120 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. 跑 CR1-CR10 全 10 个 case
2. 任意一个失败 → 阻塞 T0038
3. 验证恢复时间 < 30s 每个
4. 验证 Verifier PID 不同
全部通过 → status=Verified。