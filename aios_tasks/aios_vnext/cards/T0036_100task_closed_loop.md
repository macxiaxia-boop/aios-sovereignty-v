---
id: T0036
title: 100-task 闭环 + False Completion 注入
owner: CC
priority: P0
track: 3 — VNext Phase A
preconditions: [T0030, T0031, T0032, T0033, T0034, T0035]
estimated_minutes: 240
depends_on: [T0030, T0031, T0032, T0033, T0034, T0035]
blocks: [T0038]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

**这是 Phase A 的核心验收测试**——3 张卡一起跑（T0036 主体 + T0037 Crash Recovery + T0038 综合验收）。本卡只包含 T0036 + False Completion 注入。

### Part A — 100-task 闭环
1. **创建 100 个真实业务 Task**:
   - 任务集合：覆盖至少 5 种类型
     - Type A: 文件摘要（30 个）
     - Type B: 字符串拼接 / 格式化（20 个）
     - Type C: 数学运算（20 个）
     - Type D: 路径探测 / 环境检查（15 个）
     - Type E: 跨 worker 协作（15 个）
   - 每个 Task 有明确 success_criteria

3. **跑 Task 通过 Worker Adapter**:
   - 70% 走 CodexAdapter
   - 20% 走 ClaudeCodeAdapter
   - 10% 走 OpenClawAdapter
   - 每个 Task 都被分配到对应 worker

4. **每个 Task 完成后 Verifier 必须独立签字**:
   - Verifier 与 Worker 独立进程
   - Verifier 校验 evidence 完整性
   - Verifier 签 PASS / FAIL / BLOCKED

5. **统计**:
   - 100/100 PASS = 通过
   - 95–99 PASS = 部分通过，需修复
   - < 95 PASS = 失败

### Part B — False Completion 注入测试
1. **注入 5 个故意假完成的 Worker Task**:
   - Worker 在 Task 未真正完成时报告 Done
   - Verifier 必须**全部拒绝**这 5 个 Task
   - Verdict = FAIL 或 BLOCKED，**不是** PASS

2. **测试方法**:
   - 编写 `tests/integration/test_false_completion.py`
   - 注入逻辑：`MockWorker` 在调用 `complete()` 前 sleep 5 秒 + 抛 WorkerDoneException 但 evidence 为空
   - 期望：Verifier 检测 evidence 缺失 → 签 FAIL

3. **统计**:
   - 5/5 被拒 = 通过
   - 1–4 被拒 = 部分通过
   - 0 被拒 = 失败

### Part C — 综合报告
输出：`D:\AIOS\_agent-hub\reports\t0036_phase_a_100task_closed_loop_<ts>.md`

报告 6 段：
1. 测试环境
2. 100-task 详细结果（表格）
3. False Completion 详细结果
4. Worker Adapter 分布统计
5. Verifier 独立签字统计
6. 失败任务清单（如有）

## Out-of-scope (不要做)
- ❌ 不要修改 T0030–T0035 已经产出的 schema / adapter（仅测试）
- ❌ 不要修改 VNext Master Spec
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence + 报告）
- ❌ 不要触碰 `_agent-hub/memory/*`
- ❌ 不要跑真实业务（如 OpenClaw 真实调度）—— 仅 Kernel 测试
- ❌ 不要修改 Production（仅 Kernel 仓库内的测试）

## Inputs (CC 必须先读)
- T0030 Acceptance Spec v0.1（前置阻塞）
- T0031 Kernel 仓库
- T0032 Goal/Task/Plan Schema + Migration
- T0033 Durable Execution Adapter
- T0034 Worker Adapter 接口
- T0035 Verifier 协议

## Outputs (CC 必须产出)
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0036_<ts>.md`
2. `D:\AIOS\_agent-hub\reports\t0036_phase_a_100task_closed_loop_<ts>.md`
3. `tests/integration/test_100_task_closed_loop.py`
4. `tests/integration/test_false_completion.py`
5. 测试运行 log（stdout/stderr 全文）
6. 失败任务清单（如有）
7. CI 报告（如果跑 CI）

## Evidence Requirements (Codex 验收看的)

### Part A — 100-task 闭环
- [ ] 100 个 Task 全部跑完
- [ ] 100/100 Verifier 签 PASS（或 ≥ 95）
- [ ] Worker Adapter 分布符合 70/20/10 ± 5%
- [ ] 每个 Task 含 artifacts 列表
- [ ] 每个 Task 含 evidence 报告
- [ ] 每个 Task 含 cost 记录
- [ ] 跨 worker 协作的 15 个 Task 全部跑通
- [ ] Verifier 与 Worker 进程 ID 不同（grep 验证）

### Part B — False Completion 注入
- [ ] 5 个注入 Task 全部被 Verifier 拒绝
- [ ] Verdict 全是 FAIL 或 BLOCKED
- [ ] 拒绝原因含"evidence 缺失"或类似
- [ ] 没有 false PASS
- [ ] test_false_completion.py 5 个 case 全通过

### Part C — 报告
- [ ] 报告 6 段全在
- [ ] 详细结果含每个 Task 的 ID + type + worker + verdict + duration
- [ ] Worker Adapter 分布含 5 种类型的统计
- [ ] 失败任务清单非空（如有失败）

## Exit Criteria (CC 算做完)
1. evidence 全部勾选
2. report 落到正确位置
3. CC 把 status=Submitted 后等 Codex

## Rollback (失败怎么回)
1. 删除 test 注入文件
2. 清理 mock worker 状态
3. 写 rollback log

## Time Budget
240 分钟（4 小时）
- Part A 100-task 跑测试 ≈ 90 分钟
- Part B False Completion 测试 ≈ 30 分钟
- Part C 报告 ≈ 60 分钟
- 调测 / 重跑 ≈ 60 分钟

## Codex Acceptance Gate
Codex 独立跑:
1. 重跑 100-task 测试（独立 CI 环境或本地）
2. 重跑 False Completion 注入（独立 Python 进程）
3. 验证 Verifier 独立（grep Worker 进程 ID ≠ Verifier 进程 ID）
4. 验证 Worker Adapter 分布
6. 读报告 + 抽样 5 个 Task 详细 evidence
全部通过 → status=Verified。
任何一项失败 → status=Failed + 阻塞 T0038。