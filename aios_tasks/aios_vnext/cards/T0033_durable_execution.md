---
id: T0033
title: Durable Execution Adapter（Temporal vs PG checkpointer 选型）
owner: CC
priority: P0
track: 3 — VNext Phase A
preconditions: [T0031, T0032]
estimated_minutes: 180
depends_on: [T0031, T0032]
blocks: [T0034, T0035, T0036, T0037]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

实现 **durable execution**（规格 §2.1 + §28 Phase A 要求）：

1. **选型设计文档** `D:\AIOS\kernel\docs\durable_execution_choice.md`：
   - 选项 A：Temporal（最成熟，复杂）
   - 选项 B：PostgreSQL checkpointer（轻量，自实现）
   - 选项 C：DBOS / Restate（中等）
   - 每项含：开发成本、运维成本、可观察性、可扩展性、AIOS 适配度
   - **本次实施默认选 B**（理由：避免 Temporal 部署复杂度，PG 已用；与 T0032 ORM 共用基础设施）

2. **实现 `aios_kernel.workflows.engine`**：
   - `WorkflowEngine` Protocol 接口
   - `WorkflowStep`：原子步骤：StepMeta (id, name), StepStatus, retry_policy
   - `Workflow`：包含 List[WorkflowStep] + DAG 依赖
   - 持久化：每个 Step checkpoint 写到 `workflow_checkpoints` 表
   - 重启恢复：从最近 checkpoint 重放

3. **接口定义**：
   ```python
   class WorkflowEngine(Protocol):
       async def start(workflow: Workflow) -> WorkflowRun: ...
       async def signal(run_id: str, signal: Signal) -> None: ...
       async def query(run_id: str, query: Query) -> Any: ...
       async def cancel(run_id: str, reason: str) -> None: ...
       async def get_status(run_id: str) -> WorkflowStatus: ...

   class Activity(Protocol):
       async def execute(ctx: ActivityContext) -> ActivityResult: ...
       async def compensate(ctx: ActivityContext) -> None: ...  # 失败回滚
   ```

4. **PG checkpointer 实现**：
   - 表 `workflow_runs`（run_id, workflow_id, status, current_step, started_at, completed_at）
   - 表 `workflow_checkpoints`（run_id, step_id, state_json, created_at）
   - 表 `activity_history`（run_id, activity_id, attempt, status, error）
   - 重启恢复：`SELECT * FROM workflow_checkpoints WHERE run_id = X ORDER BY created_at DESC LIMIT 1` 后从该 Step 继续
   - 支持 retry（指数退避）+ timeout

5. **示例工作流**：
   - `examples/three_step_workflow.py`：3 个 Activity 串行
   - 测试：kill engine mid-way → 重启 → 自动续跑
   - 测试：Activity 失败 → retry → 最终成功
   - 测试：Activity 永久失败 → 标记 Workflow 为 Failed

6. **集成测试** `tests/integration/test_workflow_engine.py`：
   - 5+ test cases 覆盖 start/signal/query/cancel/restart
   - 用 sqlite 异步（开发）+ 标注生产需 PG

## Out-of-scope (不要做)
- ❌ 不要引入真实 Temporal cluster
- ❌ 不要做 Temporal UI 集成
- ❌ 不要做分布式 worker（T0034 负责）
- ❌ 不要做 JWT/auth
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs
- T0031 kernel
- T0032 Pydantic + ORM
- VNext Master Spec §2.1（Temporal 范式）

## Outputs
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0033_<ts>.md`
2. `D:\AIOS\kernel\docs\durable_execution_choice.md`
3. `src/aios_kernel/workflows/` 全部代码
4. `examples/three_step_workflow.py` + README
5. `tests/integration/test_workflow_engine.py`

## Evidence Requirements
- [ ] 设计文档 4 选项 + 选型理由
- [ ] WorkflowEngine Protocol 含 5 方法
- [ ] PG checkpointer 实现含 3 表
- [ ] 3 个 Activity 串行工作流能跑通
- [ ] kill-restart 测试通过（kill 后重启 → 自动续）
- [ ] retry 测试通过（指数退避）
- [ ] 永久失败测试通过（标记 Failed）
- [ ] 5+ integration test 全部 pass
- [ ] `pytest tests/integration/test_workflow_engine.py -v` 输出

## Exit Criteria
1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex

## Rollback
1. `git reset --hard HEAD~N`（回滚到 T0032 完成状态）
2. 写 rollback log

## Time Budget
180 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. 跑 3-step workflow e2e
2. kill -9 mid-execution → 重启 → 验证续跑
4. 跑 retry test（注入失败 2 次后成功）
5. 跑永久失败 test
全部通过 → status=Verified。