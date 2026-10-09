---
id: T0035
title: Verifier 独立进程 + 协议
owner: CC
priority: P0
track: 3 — VNext Phase A
preconditions: [T0031, T0032, T0033, T0034]
estimated_minutes: 120
depends_on: [T0031, T0032, T0033, T0034]
blocks: [T0036, T0037]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

实现**独立进程的 Verifier**——规格 §97.7 "Worker 执行不得自我验收" + §104.10 "Verifier 独立"。

1. **协议定义** `src/aios_kernel/verifier/protocol.py`：
   ```python
   class Verifier(Protocol):
       verifier_id: str
       async def verify(self, task: Task, evidence_ids: List[str]) -> Verdict: ...
       async def health(self) -> HealthReport: ...

   class Verdict(BaseModel):
       task_id: str
       verifier_id: str
       verdict: Literal["PASS", "FAIL", "BLOCKED"]
       reason: str
       details: Dict[str, Any]
       signed_at: datetime
   ```

2. **Verifier 独立进程强制**（规格 §97.7）：
   - 提供 `scripts/run_verifier.sh` + `scripts/run_verifier.py` 启动独立子进程
   - 子进程通过 Unix socket / Named pipe / HTTP 与 Kernel 通信（**禁止在同一进程内运行**）
   - 测试断言：Verifier 的 `os.getpid()` ≠ Kernel 的 `os.getpid()`

3. **Deterministic Verifier（核心实现）** `src/aios_kernel/verifier/deterministic.py`：
   - 不调用 LLM（避免循环）
   - 校验清单：
       1. evidence 列表非空
       2. 每个 evidence 在 evidence_store 中存在
       3. 每个 evidence 的 hash 与 record 中一致
       4. 每个 artifact 在文件系统存在
       5. task.success_criteria 全部得到验证（基于 evidence 中字段）
       6. 没有 budget 溢出（cost < budget）
   - 任何一项失败 → verdict=FAIL 或 BLOCKED
   - 全通过 → verdict=PASS

4. **Evidence Store** `src/aios_kernel/verifier/evidence_store.py`：
   - 抽象接口：`store(evidence)`, `get(evidence_id)`, `verify(evidence_id) -> bool`
   - 实现：基于 `evidences` 表（T0032）+ 文件系统 hash 校验
   - 不依赖 Worker 进程

5. **Verifier 进程实现** `src/aios_kernel/verifier/server.py`：
   - 启动：监听端口 9001（开发期）
   - API: POST /verify {task_id, evidence_ids} → 返回 Verdict
   - API: GET /health → HealthReport
   - 进程隔离：每个 verify 起独立 subprocess worker pool

6. **集成测试** `tests/integration/test_verifier_independent.py`：
   - 测试 1：Verifier 进程启动，Kernel 调用，验证 PID 不同
   - 测试 2：缺 evidence → FAIL
   - 测试 3：evidence hash 不匹配 → FAIL
   - 测试 4：artifact 缺失 → FAIL
   - 测试 5：budget 溢出 → FAIL
   - 测试 6：全通过 → PASS
   - 测试 7：BLOCKED 案例（partial evidence）

7. **接入 T0033 Workflow**：
   - Workflow Engine 增加 `verify_step`：Task activity 完成后自动 trigger verifier
   - Verifier PASS → 任务 Done；FAIL → 重试或 Failed

## Out-of-scope (不要做)
- ❌ 不要做 LLM-based verifier（只用规则）
- ❌ 不要做 JWT/auth
- ❌ 不要做 verifier 高可用（单实例够 Phase A）
- ❌ 不要做 verifier 结果缓存（T0042 是 Session Cache 的事）
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs
- T0031 kernel
- T0032 Task + Evidence + Artifact schemas
- T0033 Workflow Engine
- T0034 Worker Adapter

## Outputs
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0035_<ts>.md`
2. `src/aios_kernel/verifier/` 全部代码
3. `scripts/run_verifier.py` + `.sh`
4. `tests/integration/test_verifier_independent.py`

## Evidence Requirements
- [ ] Verifier Protocol 2 签名 + Verdict schema
- [ ] Verifier 独立进程脚本可执行
- [ ] 测试断言 PID 不同
- [ ] 6 类校验全部实现（evidence/hash/artifact/criteria/budget/...）
- [ ] Evidence Store 三方法实现
- [ ] Server 启动 + 2 API
- [ ] 7 个 integration test 全部 pass
- [ ] 接入 Workflow：verify_step 工作

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
1. 启动 verifier 子进程
2. Kernel 调用 verifier，验证 PID 不同
3. 跑 7 个 integration test
4. 注入缺 evidence → 验证 FAIL
5. 注入全证据 → 验证 PASS
全部通过 → status=Verified。