---
id: T0040
title: Simulation Harness + Mock Layer（一次性验证基础设施）
owner: CC
priority: P0
track: 4 — VNext One-Shot Validation
preconditions: [T0031]
estimated_minutes: 120
depends_on: [T0031]
blocks: [T0036, T0037, T0038]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## 核心理念

> **"时间只是需要次数验证，那就模拟测试就好了"**
> — 用户原话

规格 §104 的 17 项终态里，多项含时间维度（Phase C Evolution / Phase D Business 反馈）。**真实时间压缩进模拟**：1 天业务反馈 → 1 秒模拟推进；100-task 闭环 → 100 mock task 即时跑完；多次崩溃恢复 → 自动化 100 次。

T0040 不属于 Phase A 业务范围，**是 Phase A 测试基础设施**——一次建好，所有 integration test 通过它跑。

## Scope (要做)

1. **Mock Layer** `tests/sim/mocks/`：

   a. **Mock Tasks** `mock_tasks.py`：
   - 100 个 mock 任务，5 类型 × 20 个
   - Type A: file_summary（文件摘要）
   - Type B: string_format（字符串格式化）
   - Type C: math_calc（数学运算）
   - Type D: env_probe（环境探测）
   - Type E: cross_worker（跨 worker 协作）
   - 每个 task 含：id, type, success_criteria, budget, deadline, preferred_worker
   - 任务生成是确定性的（seed=42），可重复

   b. **Mock Worker Adapters** `mock_workers.py`：
   - `SuccessWorker`：正常返回 mock artifact
   - `FakeDoneWorker`：**故意**在 evidence 为空时返"done"（T0036 False Completion 用）
   - `CrashWorker`：**故意**在 execute 中途抛 WorkerCrashException（T0037 用）
   - `TimeoutWorker`：故意 sleep 超过 timeout
   - `RetryableFailWorker`：前 2 次失败，第 3 次成功（T0033 retry 用）
   - `PermanentFailWorker`：永远失败

   c. **Mock Evidence Store** `mock_evidence.py`：
   - 内存实现（不需要 PG）
   - 支持 `put(evidence)`, `get(evidence_id)`, `verify(hash) -> bool`
   - 支持故意污染（hash mismatch for FAIL test）

   d. **Mock Time** `mock_clock.py`：
   - 提供 `Clock` 接口：`now()`, `advance(seconds)`, `freeze_at(datetime)`
   - 替代 `datetime.now()` 用于 simulation
   - 支持 1 秒模拟 1 天（time_compression = 86400）
   - Kernel 时间敏感代码必须使用 `Clock.now()` 而非 `datetime.now()`

2. **Crash Injector**（已在 T0037 定义，T0040 提供 Python 友好的 wrapper）：
   - `CrashInjector.kill_and_restart(kernel, count=N)` → 自动 N 次 kill+restart
   - 用于 T0037 CR7 "连续 5 次 crash + restart"

3. **Test Runner** `tests/sim/runner.py`：
   - `runner.run_all_acceptance_tests()`：一次跑完 10 项 Phase A 判据
   - 输出：JSON 报告，含每项通过/失败 + 恢复时间 + evidence id
   - 可被 CI 调用

5. **示例集成** `tests/sim/test_simulation_e2e.py`：
   - e2e test 跑完所有 mock task + crash + recovery + false completion
   - 1 分钟内跑完（模拟 1 天业务 + 5 次崩溃 + 100 个任务）
   - 报告总耗时 vs 实际耗时对比（演示模拟压缩效果）

## Out-of-scope (不要做)
- ❌ 不要做真实时间测试
- ❌ 不要做真实业务（OpenClaw / Codex / Claude 真实调用）
- ❌ 不要做 distribution（mock worker 同进程）
- ❌ 不要做 production mock（仅测试）
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs
- T0031 kernel 仓库
- T0030 Acceptance Spec（10 项判据定义）

## Outputs
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0040_<ts>.md`
2. `tests/sim/mocks/` 5+ 文件
4. `tests/sim/runner.py`
5. `tests/sim/test_simulation_e2e.py`

## Evidence Requirements
- [ ] 100 个 mock task 覆盖 5 类型
- [ ] 6 种 mock worker（Success/FakeDone/Crash/Timeout/RetryableFail/PermanentFail）
- [ ] Mock Clock 支持 advance / freeze / compression
- [ ] Crash Injector wrapper 提供 kill_and_restart
- [ ] Test Runner 跑完 10 项判据 + 输出报告
- [ ] e2e test 1 分钟内跑完（演示模拟压缩）
- [ ] 所有 mock 都是确定性的（seed=42，重复 → 同结果）
- [ ] T0036/T0037/T0038 测试通过 T0040 跑出

## Exit Criteria
1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex

## Rollback
1. `git reset --hard HEAD~N`
2. 写 rollback log

## Time Budget
120 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. 跑 `tests/sim/test_simulation_e2e.py`
2. 验证总耗时 < 60 秒
4. 抽样 5 个 mock task + 3 个 mock worker
全部通过 → status=Verified。

## 为什么必须做这张卡

规格 §104 终态要求：
- §104.7 "100-task 闭环" → 需要 100 task，T0040 mock 提供
- §104.8 "False Completion 被阻止" → 需要故意假完成 worker，T0040 FakeDoneWorker 提供
- §104.6 "Crash 可恢复" → 需要 N 次崩溃，T0040 CrashInjector 提供
- Phase C 后续需要"模拟时间反馈" → T0040 MockClock 提供

**没有 T0040，T0036/T0037/T0038 都跑不起来；T0031 启动，意味着 T0040 必须同步或紧随启动。**