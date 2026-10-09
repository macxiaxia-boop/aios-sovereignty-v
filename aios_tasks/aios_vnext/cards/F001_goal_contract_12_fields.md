---
id: F001
title: GoalContract 完整化 — Goal 模型扩到 12 字段
owner: CC
priority: P0
track: 6 — VNext Phase F (Cognitive Governance)
preconditions: [F000, T0032]
estimated_minutes: 90
depends_on: [F000, T0032]
blocks: [F002, F005]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

把现有 `Goal` 模型（10 字段：`title, description, success_criteria, budget, deadline, owner, status, tags, plan_ids, metadata`）扩展到 12 字段完整 GoalContract。

### 1. 必改文件（白名单内）

**`D:\AIOS\kernel\src\aios_kernel\domain\goal.py`** — 改字段定义：

```python
# 保留现有（最小修改）
title: str
description: str | None
success_criteria: str
budget: float
deadline: datetime | None
owner: str
status: GoalStatus
tags: list[str]
plan_ids: list[str]

# 新增子模型（在 goal.py 内 or 新建 goal_contract.py — 优先 goal.py 同文件）

class Constraint(BaseModel):
    type: Literal["budget", "timeout", "forbidden_path", "rate_limit", "scope"]
    value: Any
    rationale: str

class EnvSnapshot(BaseModel):
    cwd: str
    os: str
    available_tools: list[str]
    recent_failures: list[str] = Field(default_factory=list)
    history_refs: list[str] = Field(default_factory=list)  # goal_ids referenced

class FailureMode(BaseModel):
    description: str
    detection: str  # how to detect this trap
    indicator: str | None = None

class PermissionScope(BaseModel):
    allowed_paths: list[str]
    allowed_ops: list[str]  # ['read', 'write', 'execute', 'network', 'delete']
    max_budget: float
    max_duration_sec: int | None
    requires_approval: list[str] = Field(default_factory=list)  # op types requiring explicit auth

class EvidenceRequest(BaseModel):
    description: str
    source: str  # path/URL/tool
    required: bool = True

class Tradeoff(BaseModel):
    decision: str
    cost: str
    benefit: str
    approved_by: str  # 'user' | agent_name

class OpType(BaseModel):
    domain: Literal["file", "network", "service", "data", "config"]
    action: Literal["read", "write", "execute", "delete", "modify"]
    target: str | None = None

# 扩展 Goal
class Goal(Envelope):
    # ... 保留 10 字段 ...
    inferred_intent: str | None = None
    preserve_capabilities: list[str] = Field(default_factory=list)
    known_constraints: list[Constraint] = Field(default_factory=list)
    environment_context: EnvSnapshot | None = None
    failure_modes: list[FailureMode] = Field(default_factory=list)
    permission_scope: PermissionScope | None = None
    missing_evidence: list[EvidenceRequest] = Field(default_factory=list)
    approved_tradeoffs: list[Tradeoff] = Field(default_factory=list)
    autonomous_scope: list[OpType] = Field(default_factory=list)
    requires_authorization: list[OpType] = Field(default_factory=list)
```

### 2. SQLAlchemy ORM 扩展

**`D:\AIOS\kernel\src\aios_kernel\persistence\models.py`** — 扩 `GoalORM`：

```python
class GoalORM(Base):
    # 现有列
    inferred_intent = Column(String, nullable=True)
    preserve_capabilities = Column(JSON, default=list)  # list[str]
    known_constraints = Column(JSON, default=list)      # list[dict]
    environment_context = Column(JSON, nullable=True)   # dict
    failure_modes = Column(JSON, default=list)          # list[dict]
    permission_scope = Column(JSON, nullable=True)      # dict
    missing_evidence = Column(JSON, default=list)       # list[dict]
    approved_tradeoffs = Column(JSON, default=list)     # list[dict]
    autonomous_scope = Column(JSON, default=list)       # list[dict]
    requires_authorization = Column(JSON, default=list) # list[dict]
```

**`D:\AIOS\kernel\src\aios_kernel\persistence\repository.py`** — 加 to_orm/from_orm 双向转换

### 3. Alembic migration

**`D:\AIOS\kernel\alembic\versions\`** — 新建 `002_goal_contract_12_fields.py`：
- upgrade: 加 10 列（全部 nullable 或 default 空）
- downgrade: 删 10 列（保 backward-compat）

### 4. 单元测试（25+ case）

**`D:\AIOS\kernel\tests\unit\test_goal_contract_12_fields.py`**：

```python
# 12 字段构造 + 验证（每字段 1-2 case）
def test_inferred_intent_optional()
def test_preserve_capabilities_default_empty()
def test_constraint_validation_budget()
def test_constraint_validation_timeout()
def test_constraint_validation_forbidden_path()
def test_env_snapshot_with_recent_failures()
def test_failure_modes_detection_required()
def test_permission_scope_allowed_ops_subset()
def test_permission_scope_requires_approval()
def test_evidence_request_required_vs_optional()
def test_tradeoff_approved_by_validation()
def test_op_type_domain_action_enum()
# 兼容性测试
def test_existing_goal_10_fields_still_valid()
def test_round_trip_pydantic_to_orm_to_pydantic()
# 业务规则
def test_permission_scope_max_budget_matches_goal_budget()
def test_autonomous_scope_disjoint_from_requires_authorization()
def test_failure_modes_minimum_one_required()
def test_env_snapshot_required_when_known_constraints_present()
# Migration
def test_alembic_upgrade_002_adds_10_columns()
def test_alembic_downgrade_002_removes_10_columns()
# JSON Schema
def test_goal_json_schema_includes_all_12_fields()
```

### 5. 文档

**`D:\AIOS\kernel\docs\goal_contract.md`** — 12 字段 schema 文档（已存在的 docs/ 目录内，可写）

## Out-of-scope (不要做)

- ❌ 不重写 Plan/Task/Trace/Evidence 现有模型（仅扩展 Goal）
- ❌ 不实现 Intent Parser（F002 才做）
- ❌ 不实现 Decision Audit Log（F003 才做）
- ❌ 不实现 GoalGuard Hook（F005 才做）
- ❌ 不改 verifier/deterministic.py
- ❌ 不改 v2 consumer / v2_consumer.py
- ❌ 不引入新依赖（pydantic + sqlalchemy + alembic 已够）
- ❌ 不删除现有字段（只新增）
- ❌ 不创建 `_v6_*.py` / `_r*.py` / `protocol_*.md` 等 forbidden pattern

## Inputs (必须先读)

1. `D:\AIOS\kernel\src\aios_kernel\domain\goal.py` — 现有 Goal 模型（4299B）
2. `D:\AIOS\kernel\src\aios_kernel\persistence\models.py` — 现有 5 ORM（25940B）
3. `D:\AIOS\kernel\tests\unit\test_goal_schema.py` — 现有 15 测试（4969B）
4. `D:\AIOS\aios_tasks\aios_vnext\cards\T0032_schema_migration.md` — 模式参考
5. `D:\AIOS\aios_tasks\aios_vnext\cards\F000_phase_f_acceptance_spec.md` — Phase F spec

## Outputs (必须产出)

1. `D:\AIOS\aios_tasks\aios_vnext\evidence\F001__<ts>.md` — 必含 preflight 附件
2. `D:\AIOS\kernel\src\aios_kernel\domain\goal.py` — 扩展后（≥5000B）
3. `D:\AIOS\kernel\src\aios_kernel\persistence\models.py` — 扩 GoalORM
4. `D:\AIOS\kernel\src\aios_kernel\persistence\repository.py` — 双向转换
5. `D:\AIOS\kernel\alembic\versions\002_goal_contract_12_fields.py`
6. `D:\AIOS\kernel\tests\unit\test_goal_contract_12_fields.py` — 25+ case
7. `D:\AIOS\kernel\docs\goal_contract.md`

## Evidence Requirements

- [ ] Goal 12 字段全部 Pydantic schema 化
- [ ] GoalORM 扩 10 列（JSON + nullable 默认）
- [ ] Alembic upgrade 002 exit 0
- [ ] Alembic downgrade 002 exit 0
- [ ] `pytest tests/unit/test_goal_contract_12_fields.py` 25+ case 全 PASS
- [ ] `pytest tests/unit/test_goal_schema.py` 既有 15 case 仍 PASS（向后兼容）
- [ ] JSON schema 含 12 字段
- [ ] `alembic upgrade head && alembic upgrade head` 双跑不报错
- [ ] preflight = 0 issues
- [ ] 现有 49 张 Verified 卡未受影响（pytest 跑全套仍 PASS）

## Exit Criteria

1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex
3. **不要自封 Verified**

## Rollback

1. `git reset --hard HEAD~1`（如有 commit）
2. `alembic downgrade -1` 回到 001
3. 恢复 `goal.py` 到 HEAD 版本

## Time Budget

90 分钟

## Codex Acceptance Gate

Codex 独立验证：
1. `cd D:\AIOS\kernel && alembic upgrade head && alembic downgrade -1 && alembic upgrade head` 完整周期
2. `pytest tests/unit/test_goal_contract_12_fields.py tests/unit/test_goal_schema.py -v` 全 PASS
3. `grep -n "inferred_intent\|preserve_capabilities\|known_constraints\|environment_context\|failure_modes\|permission_scope\|missing_evidence\|approved_tradeoffs\|autonomous_scope\|requires_authorization" src/aios_kernel/domain/goal.py` 至少 10 命中
4. `pytest tests/unit -v` 全套仍 PASS（向后兼容）
5. preflight v4 = 0 issues
6. 抽样 5 个新建 Pydantic 子模型（Constraint/EnvSnapshot/FailureMode/PermissionScope/EvidenceRequest/Tradeoff/OpType）各 1 case PASS

全部通过 → status=Verified