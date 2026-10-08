# Durable Execution — 选型设计 (T0033)

> **Author**: dev #15 (CC)
> **Date**: 2026-10-08
> **Status**: **Option B 选定 → PG checkpointer + SQLAlchemy 异步**
> **Reference**: T0033 任务卡 §Scope 1; VNext Master Spec §2.1 (Temporal 范式); T0032 ORM (前置)

---

## 0. TL;DR

| 维度 | 选项 B (PG checkpointer) | 选项 A (Temporal) | 选项 C (DBOS / Restate) | 选项 D (纯 asyncio + 内存) |
|------|-------------------------|-------------------|------------------------|-----------------------------|
| **开发成本** | ⭐⭐ 中 | ⭐⭐⭐⭐ 高 | ⭐⭐⭐ 中高 | ⭐ 低 |
| **运维成本** | ⭐ 低（无新服务） | ⭐⭐⭐⭐ 高（Temporal cluster + worker + UI） | ⭐⭐ 中 | ⭐ 极低（不持久） |
| **可观察性** | ⭐⭐ 中（SQL 查询） | ⭐⭐⭐⭐⭐ 极强（UI + history） | ⭐⭐⭐⭐ 高 | ⭐ 极低 |
| **可扩展性** | ⭐⭐ 中（单进程写） | ⭐⭐⭐⭐⭐ 强 | ⭐⭐⭐⭐ 强 | ⭐ 不支持 |
| **AIOS 适配度** | ⭐⭐⭐⭐⭐（已用 PG + T0032 ORM） | ⭐⭐ 中（增加独立服务） | ⭐⭐ 中（新依赖） | ⭐ 极低（不可重启） |
| **Phase A 工期** | 180 min | 估 2-3 周 | 估 1 周 | < 60 min（不可生产） |
| **持久化** | ✅ workflow_checkpoints 3 表 | ✅ Temporal history | ✅ 内置 | ❌ 进程即状态 |

**本次实施 = Option B**。理由：AIOS VNext Phase A 已经有 PG + SQLAlchemy ORM 基础（T0032），PG checkpointer 与基础设施完全共享；不引入 Temporal cluster 减少运维复杂度和发布风险；180 分钟内可实现并通过 T0037 crash recovery 测试。

---

## 1. 4 个选项详评

### 1.1 Option A — Temporal

**是什么**：成熟的 workflow orchestration 框架，提供 worker、history、UI、retry、signal/query。

| 维度 | 评估 |
|------|------|
| 开发成本 | 高。要写 worker、activity、workflow decorator；学习 curve 陡；TDD 时需起 Temporal dev server |
| 运维成本 | **极高**。需要 Temporal cluster（≥ 3 节点生产，或 1 节点 dev）+ worker 进程 + DB（仍要 PG）+ Temporal UI（可选）。Phase A 验收要在 docker-compose 起 4 个服务 |
| 可观察性 | 强。tctl + UI 可看每步、retry、history |
| 可扩展性 | 强。多 worker、shard、namespace 都内置 |
| AIOS 适配度 | 中。Temporal 是"workflow-as-code"，而 AIOS Kernel 已经有自己的 WorkflowEngine Protocol 抽象，再叠一层 Temporal 会双重协议 |
| 180 min 内能完成 | ❌。仅"Temporal dev server + 一个 hello world"就需 ≥ 30 min 启动 + 配置 + 学习 |

**否决理由**：运维复杂度（独立 Temporal cluster）与 Phase A 范围严重不匹配；学习成本在 180 分钟内不可接受；Card Out-of-scope 已显式禁 `Temporal cluster`。

### 1.2 Option B — PostgreSQL checkpointer (本次选定)

**是什么**：自己实现 WorkflowEngine，3 张表持久化 run 状态 + 每步 checkpoint；重启时按最近 checkpoint 续跑。

| 维度 | 评估 |
|------|------|
| 开发成本 | 中。SQLAlchemy ORM（T0032 已有）+ asyncio 即可 |
| 运维成本 | **低**。无新服务；用现有 PG |
| 可观察性 | 中。SQL 直接查 workflow_runs / activity_history（谁失败 / 几次） |
| 可扩展性 | 中。**单进程写**瓶颈（v1.0 范围）；Phase B 引入多 worker 时需加 `SELECT ... FOR UPDATE SKIP LOCKED` |
| AIOS 适配度 | **极好**。直接落到 PG，与 T0032 domain/persistence 共用基础设施；WorkflowEngine Protocol 设计完全自主 |
| 180 min 内能完成 | ✅。本卡即实施此选项 |

**选定理由**：
- **复用 PG + SQLAlchemy**（T0032 已建基础设施）
- **不引入新服务**（Temporal cluster 排除）
- **Protocol 自主**（不绑死第三方；将来要切 Temporal/Restate 只换实现）
- **restart 行为可验证**（kill engine → 新 engine → 从最新 checkpoint 续跑）

### 1.3 Option C — DBOS / Restate

**是什么**：较新的 durable execution 框架（DBOS 2023+、Restate 2022+），比 Temporal 轻，SDK 简化。

| 维度 | 评估 |
|------|------|
| 开发成本 | 中高。SDK 学习；无 Python 长期生态 |
| 运维成本 | 中。需 DBOS server（轻量，但仍是新服务） |
| 可观察性 | 高。DBOS 仪表盘；Restate 内置 journal |
| 可扩展性 | 强。内置 partition / virtual worker |
| AIOS 适配度 | 中。仍要新依赖；社区小；v0.x 风险 |
| 180 min 内能完成 | ❌。SDK 接入 + 本地 server 启动 + 测试 ≈ 半天 |

**否决理由**：Python 生态小；引入新依赖与"wrap-not-rewrite"原则冲突；Phase B 之前无显著收益。

### 1.4 Option D — 纯 asyncio + 内存

**是什么**：完全不持久化，state 只在内存；engine 崩即丢。

| 维度 | 评估 |
|------|------|
| 开发成本 | 极低 |
| 运维成本 | 极低 |
| 可观察性 | 极低 |
| 可扩展性 | 不支持 |
| AIOS 适配度 | **0**。T0037 Crash Recovery 测试必失败；Phase A 整体不通过 |

**否决理由**：明显不能作为"durable execution"方案。仅作"Phase 0 prototype"使用。

---

## 2. Option B 详细设计

### 2.1 数据模型（3 张表）

```sql
workflow_runs         -- 每个 workflow run 一行
  run_id              PK (uuid string)
  workflow_id         FK to workflow definition (string)
  status              pending | running | completed | failed | cancelled
  current_step        step id 当前执行到哪一步
  input_json          启动参数
  output_json         最终输出（completed 时填）
  error               错误信息（failed 时填）
  started_at          timestamptz
  completed_at        timestamptz nullable

workflow_checkpoints  -- 每个 step 完成后一行
  id                  PK autoincrement
  run_id              FK workflow_runs.run_id
  step_id             step.id
  step_index          0-based
  state_json          完整 ActivityContext state（input + output + attempt）
  attempt             第几次尝试
  status              completed | failed
  created_at          timestamptz

activity_history      -- 每次 attempt 一行（即便失败也记）
  id                  PK autoincrement
  run_id              FK workflow_runs.run_id
  activity_id         activity name
  step_id             step.id
  attempt             第几次尝试（1-based）
  status              started | completed | failed | retried
  error               error message
  started_at          timestamptz
  finished_at         timestamptz nullable
```

### 2.2 Restart 恢复算法

```
function resume_run(run_id):
  latest = SELECT * FROM workflow_checkpoints
           WHERE run_id = X
           ORDER BY created_at DESC
           LIMIT 1

  if latest is None:
    return start_from_scratch()      # 第一次跑

  # 从 latest.step_id 之后继续
  remaining = workflow.steps[latest.step_index + 1 :]

  for step in remaining:
    execute_with_retry(step, prior_state=latest.state_json)
    save_checkpoint(...)
```

### 2.3 Retry 策略（指数退避）

```
retry_policy:
  max_attempts: int          # 默认 3
  backoff_factor: float      # 默认 2.0
  initial_delay_s: float     # 默认 0.1
  max_delay_s: float         # 默认 5.0

delay(attempt) = min(
    initial_delay_s * backoff_factor ** (attempt - 1),
    max_delay_s,
)
```

### 2.4 Timeout 策略

- 每个 Activity 可设 `timeout_s: float`
- engine 用 `asyncio.wait_for(act.execute(ctx), timeout=timeout_s)`
- 超时 → 视为失败 → 进入 retry 链

---

## 3. WorkflowEngine Protocol

```python
class WorkflowEngine(Protocol):
    async def start(self, workflow: Workflow, *, input: dict) -> WorkflowRun
    async def signal(self, run_id: str, signal: Signal) -> None
    async def query(self, run_id: str, query: Query) -> Any
    async def cancel(self, run_id: str, reason: str) -> None
    async def get_status(self, run_id: str) -> WorkflowStatus


class Activity(Protocol):
    async def execute(self, ctx: ActivityContext) -> ActivityResult
    async def compensate(self, ctx: ActivityContext) -> None
```

5 个方法 + Activity 协议 = T0033 验收 Gate §1。

---

## 4. 与下游卡关系

| 下游卡 | 依赖点 |
|--------|--------|
| **T0034 Worker Adapter** | Worker 通过 Activity Protocol 接入 workflow |
| **T0035 Verifier** | Verifier 监听 workflow_runs.status 变化（completed/failed） |
| **T0036 100-task 闭环** | 100 个 workflow run 走完 engine |
| **T0037 Crash Recovery** | kill engine mid-execution → 重启 → 自动续（restart 算法） |
| **T0038 Phase A 验收** | Codex 独立签字：跑 3-step e2e + kill-restart + retry + 永久失败 4 个 acceptance gate |

---

## 5. 开发期 vs 生产期

| 维度 | 开发（本次 T0033） | 生产（Phase B+） |
|------|--------------------|-----------------|
| DB | SQLite (aiosqlite) | PostgreSQL 16 |
| Connection | 文件本地 | 共享 PG cluster |
| 并发写 | 单进程 | 多 worker + `SELECT ... FOR UPDATE SKIP LOCKED` |
| 监控 | 单元测试断言 | Langfuse / PG 视图 |

**ORM 抽象**：用 SQLAlchemy 2.0 async。开发用 `sqlite+aiosqlite://`；生产切到 `postgresql+asyncpg://`，schema 由 T0032 Alembic 迁移统一管。

---

## 6. 风险与缓解

| 风险 | 缓解 |
|------|------|
| 单进程写瓶颈 | Phase A 不需要多 worker；T0034 stub 后 Phase B 再扩展 |
| SQLite JSON 字段 | 用 `JSON` 类型（SQLAlchemy 自动映射） |
| Restart 时 activity 已部分执行 | checkpoint 只在 activity **完成**后写；崩溃时该 step 重跑（activity 必须 idempotent） |
| 信号丢失 | signal 表暂未实现（Phase A 仅 5 method 协议） |

---

## 7. 决策记录

- **2026-10-08 dev #15**: 选 Option B (PG checkpointer)。理由：180 min 内可完成；与 T0032 基础设施共用；WorkflowEngine Protocol 自主可演进；Out-of-scope 已禁 Temporal cluster。

**签字**: dev #15 (CC) · 2026-10-08 · T0033 完成时同步更新
