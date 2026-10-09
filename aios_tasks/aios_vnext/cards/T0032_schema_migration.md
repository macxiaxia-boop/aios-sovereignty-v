---
id: T0032
title: Goal/State/Task/Plan Schema + Alembic migration
owner: CC
priority: P0
track: 3 — VNext Phase A
preconditions: [T0031]
estimated_minutes: 120
depends_on: [T0031]
blocks: [T0033, T0034, T0035, T0036, T0037]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

依据 T0030 §4 数据 Schema，**一次性**产出完整持久化层：

1. **Pydantic models**（`src/aios_kernel/domain/`）：
   - `goal.py`: Goal, GoalStatus (Pending/Active/Completed/Failed/Aborted)
   - `task.py`: Task, TaskStatus (Pending/Running/Verifying/Done/Failed/Blocked), TaskType
   - `plan.py`: Plan, PlanVersion (auto-increment int), PlanStep, Dependency
   - `artifact.py`: Artifact, ArtifactType
   - `evidence.py`: Evidence, Verdict (PASS/FAIL/BLOCKED)
   - `trace.py`: Trace, TraceSpan, EventType
   - `envelope.py`: 通用基类，含 id (UUID), updated_at, created_at, schema_version
   - 每个字段含 Pydantic 验证 + JSON Schema 导出

2. **SQLAlchemy ORM**（`src/aios_kernel/persistence/`）：
   - 6 张表对应 Pydantic（goals, tasks, plans, artifacts, evidences, traces）
   - 辅助表：worker_runs（worker 调用审计）、verifier_runs（verifier 调用审计）
   - 所有表含 `id` (UUID PK), `created_at`, `updated_at`
   - 关键索引：tasks(goal_id, status), plans(goal_id, version), traces(task_id, span_id)
   - 外键 + 级联规则
   - Alembic config + 初始 migration `001_initial.py`

3. **迁移工具**：
   - `alembic upgrade head` 在空 PG 上成功
   - `alembic downgrade -1` 回滚成功
   - 测试用 sqlite 兼容模式（开发期 fast iteration）

4. **单元测试**（`tests/unit/`）：
   - `test_goal_schema.py`：10+ case 覆盖 Goal 创建/验证/序列化
   - `test_task_state_machine.py`：8 种状态转换合法/非法
   - `test_plan_versioning.py`：v1→v2→v3 链正确
   - `test_migration.py`：up/down 完整周期
   - 全部使用 `pytest.mark.asyncio` + `aiosqlite` 做异步测试

6. **领域服务**（`src/aios_kernel/domain/services/`）：
   - `GoalService.create_goal()`：创建 Goal 并分配 id
   - `TaskService.transition()`：状态机驱动
   - `PlanService.create_version()`：Plan 版本化
   - 仅做"写库 + 触发事件"两层，不做 workflow 调度（那是 T0033）

## Out-of-scope (不要做)
- ❌ 不要引入 workflow 调度（T0033 才做）
- ❌ 不要接入真实 PG（先用 sqlite 异步）
- ❌ 不要做 REST API（T0031 留 api/ 但本卡不实现）
- ❌ 不要做 JWT / auth
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs
- T0031 kernel 仓库
- T0030 §4 Schema

## Outputs
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0032_<ts>.md`
2. 完整 Pydantic models（6+ 文件）
3. 完整 SQLAlchemy ORM（6+ 模型 + 1 migration）
4. `tests/unit/test_*.py` ≥ 5 文件
5. `pytest` 全部 pass 的输出

## Evidence Requirements
- [ ] Pydantic models 全部含 JSON Schema 导出
- [ ] ORM 8 张表（6 主 + 2 辅）全在 migration 中
- [ ] `alembic upgrade head` exit 0
- [ ] `alembic downgrade -1` exit 0
- [ ] `pytest tests/unit` 全部 pass
- [ ] 测试覆盖：Goal schema、Task 8 状态、Plan 版本化、迁移 up/down
- [ ] `aios_kernel.domain.Goal` 可 import
- [ ] 所有时间字段用 `datetime.now(UTC)`，禁 naive datetime

## Exit Criteria
1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex

## Rollback
1. `git reset --hard HEAD~1`（如有 commit）
2. 写 rollback log

## Time Budget
120 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. 跑 `alembic upgrade head && alembic upgrade head`（双跑）
3. 跑 `pytest tests/unit -v`
4. 抽样 5 个 Pydantic model + 5 个表
5. `grep -r "datetime.now()" --include="*.py" | grep -v "datetime.now(UTC)"` 必须为空
全部通过 → status=Verified。