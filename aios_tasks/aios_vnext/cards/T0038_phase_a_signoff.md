---
id: T0038
title: Phase A 综合验收（Codex 独立签字）
owner: Codex (CC 提交 → Codex 验)
priority: P0
track: 3 — VNext Phase A
preconditions: [T0030, T0031, T0032, T0033, T0034, T0035, T0036, T0037]
estimated_minutes: 90
depends_on: [T0030, T0031, T0032, T0033, T0034, T0035, T0036, T0037]
blocks: []
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: false
---

## Scope (要做)

**Codex 独立签字** Phase A 通过。CC 提交前期所有 evidence + 报告，Codex 独立重跑 10 项判据 + 5 个 integration test。

1. **收集所有前期 evidence**（Codex 自查）：
   - T0030 → Acceptance Spec v0.1
   - T0031 → kernel repo init
   - T0032 → schema + migration
   - T0033 → durable execution
   - T0034 → worker adapters
   - T0035 → verifier independent
   - T0036 → 100-task closed loop + False Completion
   - T0037 → crash recovery

2. **独立重跑 10 项 Phase A 判据**（Codex 在 fresh 环境跑）：
   | # | 判据 | 测试方法 |
   |---|------|---------|
   | 1 | Goal 持久化 | 写 100 Goal，重启 Kernel，全部读出 |
   | 2 | Task 状态机 | 8 种状态转换正确 |
   | 3 | Plan 版本化 | 5 次重规划 v1-v5 |
   | 4 | Durable Execution | 模拟 Workflow 崩溃恢复 |
   | 5 | Worker 可替换 | CodexAdapter → ClaudeCodeAdapter 业务连续 |
   | 6 | Crash 可恢复 | Kernel 崩溃 100% 状态恢复 |
   | 7 | 100-task 闭环 | 100 Task 全 PASS |
   | 8 | False Completion 阻止 | 5 个注入全拒 |
   | 9 | Evidence 完整 | 100% 含 artifacts + report + cost |
   | 10 | Verifier 独立 | PID 验证 |

3. **独立重跑 5 个 integration test**（T0036/T0037 出）：
   - test_100_task_closed_loop.py
   - test_false_completion_rejected.py
   - test_crash_recovery.py
   - test_worker_swap.py
   - test_plan_rollback.py

4. **Phase A 最终报告** `D:\AIOS\_agent-hub\reports\aios_vnext_phase_a_done_<ts>.md`：
   - 11 段：范围 / 完成判据 / 数据 Schema / Worker Adapter 接口 / Verifier 协议 / Durable Execution 选型 / 存储 Schema / 失败模式 / 测试基础设施 / Codex 验收签字 / 后续（Phase B 入口）

5. **签字条件**：
   - 10 项判据全通过
   - 5 个 integration test 全 pass
   - 任何 Verifier 单独通过
   - Phase A 报告落到正确位置

## Out-of-scope (不要做)
- ❌ 不要修改 kernel 代码（仅验收）
- ❌ 不要做 Phase B 工作
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence + 报告）
- ❌ 不要在 Production 跑测试

## Inputs
- T0030–T0037 全部 evidence + 报告

## Outputs (Codex 必须产出)
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0038_<ts>.md`
2. `D:\AIOS\_agent-hub\reports\aios_vnext_phase_a_done_<ts>.md`

## Evidence Requirements
- [ ] 10 项 Phase A 判据全部独立跑过，全通过
- [ ] 5 个 integration test 全部独立跑过，全 pass
- [ ] Phase A 报告 11 段全在
- [ ] Verifier 签字（Codex supervisor sign）
- [ ] Kernel repo 仍可干净 rebuild

## Exit Criteria
1. evidence 全部勾选
2. 报告落位置
3. Codex 自签 status=Verified → Phase A 完成

## Rollback
1. Phase A 没"完成"概念——一旦 Verified 即为 Baseline
2. 失败则回滚到 T0030 重做
3. 写 rollback log

## Time Budget
90 分钟（Codex 独立验收时间）

## Codex Acceptance Gate
本卡是 Codex 自签，无需 CC 验。
Verified 后：
- INDEX.md 更新 Phase A 状态 = DONE
- 用户可拍板启动 Phase B
- 不进入 Phase B 自动门（用户必须显式说"go Phase B"）