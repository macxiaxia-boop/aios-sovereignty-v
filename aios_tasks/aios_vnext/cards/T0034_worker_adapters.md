---
id: T0034
title: Worker Adapter 4 个接口（Codex/Claude/OpenClaw/Hermes stub）
owner: CC
priority: P0
track: 3 — VNext Phase A
preconditions: [T0031, T0032, T0033]
estimated_minutes: 90
depends_on: [T0031, T0032, T0033]
blocks: [T0035, T0036, T0037]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

实现 4 个 Worker Adapter 接口 + 注册中心。**本卡只做 stub 实现 + 接口契约测试**——真实集成在 Phase B（与外部 Agent 真正握手）。

1. **`aios_kernel.workers.base`**：
   ```python
   class WorkerAdapter(Protocol):
       worker_id: str
       async def execute(self, task: Task) -> Artifact: ...
       async def cancel(self, task_id: str) -> None: ...
       async def health(self) -> HealthReport: ...
       async def warmup(self) -> None: ...
       async def shutdown(self) -> None: ...
   ```
   `HealthReport`: 含 status (Healthy/Degraded/Unhealthy), last_check_at, message

2. **4 个 stub 实现**（`src/aios_kernel/workers/`）：
   - `codex_adapter.py`：stub 返回 mock artifact
   - `claude_code_adapter.py`：stub 返回 mock artifact
   - `openclaw_adapter.py`：stub 返回 mock artifact
   - `hermes_adapter.py`：stub 返回 mock artifact
   - 每个 stub：
     - `worker_id` = 唯一字符串
     - `execute(task)`: 写一行 log，返回 `Artifact(task_id=task.id, type="stub", payload={"worker": self.worker_id, "task_id": task.id})`
     - `cancel(task_id)`: 写一行 log
     - `health()`: 返回 `HealthReport(status=Healthy)`
     - `warmup/shutdown`: noop + log

3. **Worker Registry**：
   ```python
   class WorkerRegistry:
       def register(self, adapter: WorkerAdapter) -> None: ...
       def get(self, worker_id: str) -> WorkerAdapter: ...
       def list(self) -> List[str]: ...
       def route(self, task: Task) -> WorkerAdapter:
           """根据 task.type / task.preferred_worker 路由"""
   ```
   路由规则：
   - `task.preferred_worker` 优先
   - 否则按 `task.type` 映射（tofu → codex, code → claude, shell → openclaw, review → hermes）
   - 否则 round-robin

4. **单元测试** `tests/unit/test_workers.py`：
   - 4 个 stub 各自 execute/cancel/health 测试
   - Registry 注册/查询/路由测试
   - 边界：未注册的 worker_id 抛 NotRegistered
   - 路由：preferred / by-type / round-robin

## Out-of-scope (不要做)
- ❌ 不要集成真实 Codex / Claude / OpenClaw / Hermes API（本卡是 stub）
- ❌ 不要做 retry（那是 T0033 workflow engine 的事）
- ❌ 不要做 worker pool（单实例 stub）
- ❌ 不要做 JWT/auth
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs
- T0031 kernel
- T0032 Task Pydantic
- T0033 Workflow Engine（用于将来挂载）

## Outputs
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0034_<ts>.md`
2. `src/aios_kernel/workers/` 全部代码（base + 4 adapters + registry）
3. `tests/unit/test_workers.py`

## Evidence Requirements
- [ ] WorkerAdapter Protocol 6 方法签名完整
- [ ] 4 个 stub 各自实现 execute/cancel/health/warmup/shutdown
- [ ] WorkerRegistry 5 方法实现
- [ ] 路由规则 3 条：preferred / by-type / round-robin
- [ ] 单元测试覆盖：4 adapter × 3 method + Registry × 5 method + 路由 × 3 case
- [ ] `pytest tests/unit/test_workers.py -v` 全 pass

## Exit Criteria
1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex

## Rollback
1. `git reset --hard HEAD~N`
2. 写 rollback log

## Time Budget
90 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. 跑 4 个 stub 的 execute（手动 import）
2. 跑 Registry 路由 3 种 case
3. 验证 NotRegistered 异常
4. 抽样 5 个测试
全部通过 → status=Verified。