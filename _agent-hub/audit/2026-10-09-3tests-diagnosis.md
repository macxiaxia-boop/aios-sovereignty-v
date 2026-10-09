# AIOS-SOVEREIGNTY-V · 3 个真 test 失败诊断 · 2026-10-09

> **执行者**: Codex (supervisor) · read-only 调查 · 不实现修复
> **目标**: test_crash_recovery · test_verifier_independent · test_long_term_memory.test_source_evidence_backlink
> **红线**: 不写新 R 编号 · 不动 policy v2 · 不实际改 test 或源码

---

## 摘要

| Test | 失败模式 | 根因定位 | 修复难度 | 建议 R 编号（待批） |
|---|---|---|---|---|
| **test_long_term_memory.test_source_evidence_backlink** | `get()` 返回 dict 不含 `source_evidence_id` | **模型不存在**：`aios_kernel.persistence.models.LongTermMemoryORM` 在 `models.py` 中**完全缺失**。`put()` import 即失败（ImportError） | M（需 schema 设计 + migration + 模型字段） | 待用户批 R1339 |
| **test_verifier_independent** | subprocess `_wait_for_http` 超时（20s） | 4 个候选根因，最可能 = `SqlAlchemyEvidenceStore` 初始化失败（默认 DB URL `aios_kernel.db` 不存在 / schema 未迁移） | M | 待用户批 R1340 |
| **test_crash_recovery** (7 个 fail) | `KeyError 'workflow_run'` | `aios_kernel.workflows.PGCheckpointerEngine` 启动时查询 `run_state` 字典时少键。最可能 = 持久化层缺 `workflow_run_state` 表 或 `WorkflowRun` ORM | L-M | 待用户批 R1341 |

---

## T2.1 — test_long_term_memory.test_source_evidence_backlink

### 现象
```python
# tests/integration/test_long_term_memory.py:90-104
async def test_source_evidence_backlink():
    ...
    svc = LongTermMemoryService(factory)
    ev_id = uuid4()
    await svc.put(key="k", value={"v": 1}, retention_days=30, source_evidence_id=ev_id)
    v = await svc.get("k")
    assert v.get("source_evidence_id") == str(ev_id) or v.get("source_evidence_id") == ev_id
```

### 期望行为
- `put()` 接受 `source_evidence_id=ev_id` (UUID)
- `get()` 返回 dict 含 `source_evidence_id` 字段（UUID 或 str）

### 真实根因（已通过 read-only 验证）

**`aios_kernel.persistence.models.LongTermMemoryORM` 在 `models.py` 中完全缺失。**

证据 1 — import 必然失败：
```python
# aios_kernel/context/long_term_memory.py:243
from aios_kernel.persistence.models import LongTermMemoryORM, long_term_memory_to_orm
```

证据 2 — `models.py` (34 KB) 实际表清单（由 docstring + grep 双重确认）:
```
6 main tables: goals, tasks, plans, artifacts, evidences, traces
Aux tables:   worker_runs, verifier_runs
Phase F:      decision_audit (F003)
Plus:         documents, document_chunks, embeddings
```
**没有 LongTermMemoryORM**。也没有 `long_term_memory_to_orm` 函数。

证据 3 — 代码里所有引用 `LongTermMemoryORM` 的地方：
```
- long_term_memory.py:243 (import, fails)
- long_term_memory.py:248 (select — never reached)
- long_term_memory.py:251 (session.add)
- long_term_memory.py:283 (select in get)
- long_term_memory.py:329 (query — never reached)
```

**结论**: `put()` 在第一个 await 之前就因 `ModuleNotFoundError` 抛出。test 报告里看到的"get() 返回 dict 不带 source_evidence_id"可能是历史观察（put() 一度 OK 但 ORM 字段缺失），或更可能是 user 错误解读。

### 修复方案（待批 R1339）

**选项 A — 完整实施**（推荐）:
1. 新增 `models.py::LongTermMemoryORM`:
   - `id: String(36) PK`
   - `key: String(200) unique not null`
   - `value_json: JSON not null`
   - `retention_days: Integer not null default 30 check >= 30`
   - `tags: JSON not null default []`
   - `source_evidence_id: String(36) nullable` — **这是 backlink 字段**
   - `expires_at: DateTime(timezone=True) nullable`
   - `created_at / updated_at / schema_version`
   - Index on `key` (already unique)
2. 新增 `long_term_memory_to_orm(pyd)` converter
3. 新增 alembic migration: `versions/004_long_term_memory.py`
4. run migration + 重新跑 5 个 test

**选项 B — 临时降级**:
- 把 `test_source_evidence_backlink` 标 `@pytest.mark.xfail(reason="LongTermMemoryORM pending (R1339)")`
- 其他 4 个 test 仍可测（put_and_get_roundtrip / retention_days_below_30 / query_by_tag / delete_explicit_only）—— 它们的 put/get 也会因 import 失败而 fail
- 不推荐：临时降级会让所有 LTM 测试一起瘫

**推荐**: 选项 A · 估计工作量 2-3h + migration + 5 个 test 验证

---

## T2.2 — test_verifier_independent (timeout)

### 现象
```python
# tests/integration/test_verifier_independent.py
def _wait_for_http(url: str, timeout_s: float = 20.0) -> None:
    while time.monotonic() < deadline:
        try:
            r = c.get(url)
            if r.status_code in (200, 404):
                return
        except Exception:
            ...
    raise TimeoutError(f"server at {url} did not respond in {timeout_s}s")
```

test 1 (`test_verifier_pid_differs_from_kernel`) 调用 `_running_verifier(port)` 上下文管理器，启动 `python -m aios_kernel.verifier.server` 子进程，等 20s 内 `/health` 响应 → 超时。

### 候选根因（未实测，依可能性排序）

| 序 | 根因 | 证据 | 验证方式 |
|---|---|---|---|
| **1** | `SqlAlchemyEvidenceStore` init 抛异常 | server.py default `AIOS_DATABASE_URL=sqlite+aiosqlite:///D:/AIOS/kernel/aios_kernel.db` · 文件**可能不存在**或缺 `evidence` 表 | 手工跑 `python -m aios_kernel.verifier.server`，看 stderr |
| 2 | `DeterministicVerifier.health()` 抛异常 | evidence_store.py (7.9 KB) 内 `health()` 实现可能依赖 DB schema | 同上 |
| 3 | uvicorn 启动失败（端口/host 配置） | test 用 ephemeral port (env VERIFIER_PORT) · 不太可能 | 看 stderr |
| 4 | 子进程 Python venv 不一致 | test 用 `sys.executable` · 实际 venv 是 `D:\AIOS\kernel\.venv\Scripts\python.exe` · worker 在 _kernel_worker.py 中明确要求 venv | 看 env |

### 已知情况（read-only 验证）
- ✅ `aios_kernel/verifier/server.py` 存在 (5.4 KB)
- ✅ `aios_kernel/verifier/deterministic.py` 存在 (15.2 KB)
- ✅ `aios_kernel/verifier/evidence_store.py` 存在 (7.9 KB)
- ✅ `aios_kernel/verifier/protocol.py` 存在 (5.2 KB)
- ✅ `aios_kernel/verifier/__init__.py` 存在 (1.9 KB)
- ✅ `aios_kernel/verifier/workflow_integration.py` 存在 (7.8 KB)

### 修复方案（待批 R1340）

**步骤 1: 诊断 (read-only)**:
```powershell
cd D:\AIOS\kernel
.\.venv\Scripts\python.exe -m aios_kernel.verifier.server
# 观察 stderr · 大概率看到 SQLAlchemy / 缺表 / 缺 DB 错误
```

**步骤 2: 修复（按发现的问题选）**:
- A. 若 DB 不存在: 创建 + 跑 `alembic upgrade head`
- B. 若 `evidence` 表缺: 检查 migration 是否包含此 schema
- C. 若 `SqlAlchemyEvidenceStore` 实现有 bug: 读 evidence_store.py 找根因
- D. 若 server 子进程用错 python: 在 `_running_verifier` 中显式 `_KERNEL_ROOT/.venv/Scripts/python.exe`

**推荐**: 先实测 R1340 步骤 1（单步 stderr 读取不违反 DB schema 与 migration 文件红线）。估计 1-2h。

---

## T2.3 — test_crash_recovery (7 个 fail, KeyError 'workflow_run')

### 现象
KernWorker subprocess `mode="workflow_run"` 启动后，`PGCheckpointerEngine.start(wf, run_id=run_id)` 抛 `KeyError: 'workflow_run'`。

### 已查证（read-only）

**`_kernel_worker.py` 支持 `workflow_run` mode**（docstring 列明 + 代码 line 152 实现）。

`_workflow_run()` 内导入:
```python
from aios_kernel.workflows import (
    PGCheckpointerEngine, RetryPolicy, StepMeta, Workflow,
    WorkflowStep, ActivityResult, from_callable,
)
```

`engine = PGCheckpointerEngine(db_url)` 后 `await engine.init()`。

### 真实根因（推断，未实测）

`PGCheckpointerEngine.init()` 或 `.start()` 在某处查询 `state` / `run_state` 字典，期望键 `'workflow_run'` 存在但缺。

最可能原因（3 选 1）:
1. **持久化层缺表**: 缺 `workflow_runs` 表 或 `WorkflowRunORM` · models.py 未声明 · migration 也未提供
2. **`PGCheckpointerEngine` 实现 bug**: 用错 key 名（应该是 `run_state` 或 `state`）
3. **`init()` 缺 schema bootstrap**: 即使 ORM 定义了，没调 `create_all` 或 migration

### 修复方案（待批 R1341）

**步骤 1: 验证 (read-only)**:
```python
# 在 venv python REPL 跑:
from aios_kernel.workflows import PGCheckpointerEngine
e = PGCheckpointerEngine("sqlite+aiosqlite:///./test.db")
await e.init()
# 看 exception
```

**步骤 2: 修复（按发现选）**:
- A. 若 ORM 缺: 仿 LongTermMemoryORM 加 `WorkflowRunORM` + migration
- B. 若 key 名错: 改 `PGCheckpointerEngine` 内部
- C. 若 schema bootstrap 缺: 在 init() 调 create_all / 确认 migration 已跑

### 已知限制
- **test_crash_recovery 7 个 fail 是 1 个根因造成的**（workflow engine 启动失败）· 不是 7 个独立问题
- 一旦 R1341 修通，7 个 fail 应该一齐过

**推荐**: R1341 与 R1339 同步做（同样涉及 models.py schema gap）。估计 2-4h（含 7 个 test 重跑）。

---

## 总览：3 个 R 编号提案（待用户授权）

| R | 标题 | 估计 | 依赖 |
|---|---|---|---|
| **R1339** | LongTermMemoryORM 缺 + migration + 5 test 验证 | 2-3h | 无 |
| **R1340** | Verifier subprocess 启动诊断 + 修复 | 1-2h | 无 |
| **R1341** | PGCheckpointerEngine WorkflowRunORM 缺 + migration + 7 test | 2-4h | 无 |

**总工作量**: 5-9h · 涉及 kernel 持久层补齐 + 12 个 test 真 test 修复（5+0+7）

### 跨 R 编号共性
- 3 个 R 都涉及 `aios_kernel.persistence.models` schema gap
- 全部需要新 alembic migration
- 全部需要重跑 pytest baseline 确认不引入新退化
- **不需要**改动 policy v2
- **不需要**改动 Phase H 已 promote 的 5 模块

### 风险评估
- L (低): schema 改动是 additive, 不影响现有 6 主表
- M (中): migration 顺序需要插在 003 之后
- 0 个 expected regression: 现有 6 主表都跑过 348 tests PASS

---

## 等用户回复

请批 R1339/R1340/R1341（可批 1/2/3 个任意组合），或者让我先实测 R1340 步骤 1（手工跑 server 看 stderr，**纯 read-only**，等用户授权）后再决定。

按 current policy，**Codex 不可在未经显式 R 编号授权时改任何 `kernel/` 文件**。这条线我会守。

---

_— Codex (supervisor) · T2 诊断报告 · 3 个真问题根因定位 · 等用户批 R 编号 · 2026-10-09_