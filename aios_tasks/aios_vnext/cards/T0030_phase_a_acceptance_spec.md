---
id: T0030
title: Phase A Acceptance Spec v0.1 定稿
owner: Codex
priority: P0
track: 3 — VNext Phase A
preconditions: [T0020]
estimated_minutes: 90
depends_on: [T0020]
blocks: [T0031, T0032, T0033, T0034, T0035, T0036, T0037, T0038]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: false
---

## Scope (要做)

由 **Codex（supervisor）** 主导产出 Phase A Acceptance Spec v0.1。CC 不直接产出，但可被要求"读 5 分钟字段定义 / 现有 schema 探针"。

文件路径：`D:\AIOS\_agent-hub\reports\aios_vnext_phase_a_acceptance_spec_v0.1_<ts>.md`

文档 11 段：

### §1. Phase A 范围
- 引用 VNext Master Spec §28 + §104 中属于 Kernel 的 10 项
- Phase A 只做 Kernel: Goal / Plan / State / Temporal / Worker / Artifact / Verifier / Trace
- Phase B–E 不在本文档

### §2. Phase A 完成判据（10 项硬性指标）
| # | 判据 | 测试方法 | 通过线 |
|---|------|---------|---------|
| 1 | Goal 持久化 | 写 100 Goal，重启 Kernel，全部读出 | 100/100 |
| 2 | Task 状态机 | 注入 8 种状态转换（Pending→Running→Verifying→Done/Failed...），全部正确 | 8/8 |
| 3 | Plan 版本化 | 触发 5 次重规划，v1..v5 | 5/5 |
| 4 | Durable Execution | 模拟 Workflow 进程崩溃，重启后从 checkpoint 恢复 | 100% 恢复 |
| 5 | Worker 可替换 | 替换 CodexAdapter → ClaudeCodeAdapter，业务 Task 不中断 | 100% 业务连续 |
| 6 | Crash 可恢复 | 模拟 Kernel 进程崩溃，重启 Goal/Task/Plan 全部可恢复 | 100% 状态恢复 |
| 7 | 100-task 闭环 | 跑 100 个真实业务 Task，100 个 Verifier 签字 | 100/100 |
| 8 | False Completion 阻止 | 注入 5 个故意提前宣告 Done，全部被 Verifier 拒 | 5/5 拒绝 |
| 9 | Evidence 完整 | 每个 Done Task 含 artifacts 列表 + verifier report + cost | 100% |
| 10 | Verifier 独立 | Verifier 与 LLM Worker 不同进程，可复现证据 | 100% |

### §3. 不可接受（反面清单）
- ❌ Worker 自报 Done 即认定 Done
- ❌ Verifier 与 Worker 同进程
- ❌ Plan 没有版本号
- ❌ Crash 后 Task 状态丢失
- ❌ Goal/Task 数据仅在内存
- ❌ 无 evidence 的 Done
- ❌ Production Code 被 Worker 自由修改
- ❌ 没有 Budget 上限的 Task

### §4. 数据 Schema（必须）
- `goal`: id, title, success_criteria, budget, deadline, owner, status, created_at, updated_at
- `task`: id, goal_id, title, worker, status, plan_version, evidence_ids, retry_count, ...
- `plan`: id, goal_id, version, steps[], dependencies[], created_at, rollback_to
- `artifact`: id, task_id, type, path, hash, size, created_at
- `evidence`: id, task_id, verifier_id, verdict, details, signed_at
- `trace`: id, task_id, span_id, event_type, timestamp, payload

### §5. Worker Adapter 接口（必须）
```python
class WorkerAdapter(Protocol):
    def execute(task: Task) -> Artifact: ...
    def cancel(task_id: str) -> None: ...
    def health() -> HealthReport: ...
```
实现：CodexAdapter, ClaudeCodeAdapter, OpenClawAdapter, HermesAdapter。

### §6. Verifier 协议（必须）
- Verifier 与 Worker 独立进程（spec §97.7）
- Verifier 接收 task_id + evidence_ids → 校验 → 签 verdict（PASS/FAIL/BLOCKED）
- Verifier 不依赖 LLM 自证——必须能复现 Worker 证据

### §7. Temporal / Durable Execution 选型
- 选项 A：包装 Temporal（1 周）— 推荐
- 选项 B：PostgreSQL + checkpointer 自实现（2 周）
- 选项 C：Restate / DBOS（1 周）
- **建议选 A**（最成熟），但需评估部署成本

### §8. 存储 Schema（PostgreSQL 起步）
- 库名 `aios_vnext`
- 表：goals, tasks, plans, artifacts, evidences, traces, worker_runs, verifier_runs
- migrations 用 Alembic

### §9. 失败模式（核心域）
- Worker 崩溃 → Kernel 重启 Workflow，状态恢复
- Worker 假完成 → Verifier 检证据拒
- Plan 不收敛 → 回滚 Plan vN-1，重规划
- Budget 超 → 强制中断 + 报告
- Crash 中 Goal/Task 状态不一致 → 用 PostgreSQL 事务保证原子

### §10. 测试基础设施
- `tests/integration/test_100_task_closed_loop.py`
- `tests/integration/test_false_completion_rejected.py`
- `tests/integration/test_crash_recovery.py`
- `tests/integration/test_worker_swap.py`
- `tests/integration/test_plan_rollback.py`

### §11. Phase A 通过的签字条件
- §2 的 10 项判据全通过
- §10 的 5 个 integration test 全通过
- Verifier 独立签字
- Phase A 报告落到 `D:\AIOS\_agent-hub\reports\aios_vnext_phase_a_done_<ts>.md`

## Out-of-scope (不要做)
- ❌ 不要实施任何代码（这是 spec 文档）
- ❌ 不要覆盖 VNext Master Spec §28/§104 内容（仅扩展）
- ❌ 不要修改 Phase B–E 内容
- ❌ 不要在 T0030 阶段动 PostgreSQL schema（实施在 T0031+）
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs (Codex 必须先读)
- T0020 Phase 0 Spec-vs-Reality 报告（前置阻塞）
- VNext Master Spec §28 + §104（10 项 Kernel 判据）
- 10-03 memory log 中提到的现有组件（router, dispatcher, state builder, priority engine, feedback engine）—— 这些将被 Wrap 成 Adapter

## Outputs (Codex 必须产出)
1. `D:\AIOS\_agent-hub\reports\aios_vnext_phase_a_acceptance_spec_v0.1_<ts>.md`
2. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0030_<ts>.md`（evidence 文件）

## Evidence Requirements
- [ ] 11 段全在
- [ ] §2 10 项判据每项必有 测试方法 + 通过线
- [ ] §4 schema 至少 6 张表
- [ ] §7 选型有 A/B/C 评估
- [ ] §10 至少有 5 个 integration test 名字
- [ ] §11 签字条件引用 §2 和 §10
- [ ] 文档不修改 VNext Master Spec 本身

## Exit Criteria
1. evidence 全部勾选
2. 文档路径正确
3. Codex 自签（无需 CC 验）

## Rollback (失败怎么回)
1. 删除文档
2. 写 rollback log

## Time Budget
90 分钟（写文档时点）

## Codex Acceptance Gate
Codex 自签（这是 Codex 自己产出的文档，不需 CC 验）。
T0030 → Verified 后，T0031–T0038 才允许 CC 启动。