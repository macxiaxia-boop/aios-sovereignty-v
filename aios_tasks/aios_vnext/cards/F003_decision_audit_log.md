---
id: F003
title: Decision Audit Log — 新 ORM + 持久化 + retrieve API
owner: CC
priority: P0
track: 6 — VNext Phase F (Cognitive Governance)
preconditions: [F000]
estimated_minutes: 60
depends_on: [F000]
blocks: [F004, F005]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

新增 `DecisionAudit` 域模型 + `DecisionAuditORM` 持久化 + retrieve API，让 AIOS 的每个决策都有可追溯的审计链。

### 1. 必建/改文件（白名单内）

**`D:\AIOS\kernel\src\aios_kernel\domain\decision.py`** — 新建 DecisionAudit 模型：

```python
"""decision.py — Decision Audit domain model (Phase F F003).

每个 AIOS 决策（路由派单/GoalContract 解析/失败归并等）都写一条审计记录。
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import ClassVar

from pydantic import Field, field_validator

from aios_kernel.domain.envelope import Envelope


class DecisionActor(str, Enum):
    """决策主体"""
    CODEX = "codex"
    CLAUDECODE = "claudecode"
    HERMES = "hermes"
    OPENCLAW = "openclaw"
    HUMAN = "human"
    SYSTEM = "system"  # 自动规则


class DecisionOutcome(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"


class DecisionAudit(Envelope):
    """决策审计记录"""
    
    SCHEMA_VERSION: ClassVar[int] = 1
    
    goal_id: str = Field(..., description="关联的 Goal ID")
    actor: DecisionActor = Field(..., description="决策主体")
    rationale: str = Field(..., min_length=1, description="为什么这样决策")
    alternatives: list[str] = Field(default_factory=list, description="备选方案列表")
    chosen: str = Field(..., min_length=1, description="最终选择")
    outcome: DecisionOutcome = Field(default=DecisionOutcome.PENDING, description="执行结果")
    outcome_detail: str | None = Field(default=None, description="结果详情")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="决策置信度 0-1")
    tags: list[str] = Field(default_factory=list, description="分类标签")
    
    @field_validator("confidence")
    @classmethod
    def _conf_range(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"confidence must be in [0.0, 1.0], got {v}")
        return v
    
    def mark_outcome(self, outcome: DecisionOutcome, detail: str | None = None):
        """CC/executor 调用：标记执行结果"""
        self.outcome = outcome
        if detail:
            self.outcome_detail = detail
        self.touch()
```

**`D:\AIOS\kernel\src\aios_kernel\persistence\models.py`** — 加 DecisionAuditORM：

```python
class DecisionAuditORM(Base):
    __tablename__ = "decision_audit"
    
    id = Column(String, primary_key=True)  # UUID
    goal_id = Column(String, ForeignKey("goals.id", ondelete="CASCADE"), nullable=False, index=True)
    actor = Column(String, nullable=False, index=True)
    rationale = Column(Text, nullable=False)
    alternatives = Column(JSON, default=list)
    chosen = Column(String, nullable=False)
    outcome = Column(String, default="pending")
    outcome_detail = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0)
    tags = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), nullable=False)
    updated_at = Column(DateTime(timezone=True), nullable=False)
```

**`D:\AIOS\kernel\src\aios_kernel\domain\services\decision_service.py`** — 新建：

```python
class DecisionService:
    """决策审计服务"""
    
    def __init__(self, repo):
        self.repo = repo
    
    async def record(self, goal_id, actor, rationale, chosen, alternatives=None, confidence=1.0, tags=None) -> DecisionAudit:
        audit = DecisionAudit(goal_id=goal_id, actor=actor, rationale=rationale, chosen=chosen,
                              alternatives=alternatives or [], confidence=confidence, tags=tags or [])
        await self.repo.add(audit)
        await self.repo.commit()
        return audit
    
    async def update_outcome(self, audit, detail: str | None = None):
        # outcome 来自 executor 调用
        if detail:
            audit.outcome_detail = detail
        await self.repo.add(audit)
        await self.repo.commit()
        return audit
    
    async def get_by_goal(self, goal_id: str) -> list[DecisionAudit]:
        return await self.repo.find(DecisionAuditORM, goal_id=goal_id)
    
    async def get_by_actor(self, actor: DecisionActor, limit: int = 100) -> list[DecisionAudit]:
        return await self.repo.find(DecisionAuditORM, actor=actor.value, limit=limit)
    
    async def get_pending_outcomes(self) -> list[DecisionAudit]:
        return await self.repo.find(DecisionAuditORM, outcome="pending")
```

### 2. Alembic migration 003

**`D:\AIOS\kernel\alembic\versions\003_decision_audit.py`**：

```python
def upgrade():
    op.create_table(
        "decision_audit",
        sa.Column("id", sa.String, primary_key=True),
        sa.Column("goal_id", sa.String, sa.ForeignKey("goals.id", ondelete="CASCADE"), nullable=False),
        sa.Column("actor", sa.String, nullable=False),
        sa.Column("rationale", sa.Text, nullable=False),
        sa.Column("alternatives", sa.JSON, default=list),
        sa.Column("chosen", sa.String, nullable=False),
        sa.Column("outcome", sa.String, default="pending"),
        sa.Column("outcome_detail", sa.Text, nullable=True),
        sa.Column("confidence", sa.Float, default=1.0),
        sa.Column("tags", sa.JSON, default=list),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("decision_audit_goal_id_idx", "decision_audit", ["goal_id"])
    op.create_index("decision_audit_actor_idx", "decision_audit", ["actor"])
    op.create_index("decision_audit_outcome_idx", "decision_audit", ["outcome"])

def downgrade():
    op.drop_index("decision_audit_outcome_idx")
    op.drop_index("decision_audit_actor_idx")
    op.drop_index("decision_audit_goal_id_idx")
    op.drop_table("decision_audit")
```

### 3. 单元测试（20+ case）

**`D:\AIOS\kernel\tests\unit\test_decision_audit.py`**：

```python
# Construction + validation
def test_decision_audit_required_fields()
def test_decision_actor_enum_5_values()
def test_decision_outcome_enum_4_values()
def test_confidence_must_be_0_to_1()
def test_rationale_required_min_length()
# State transitions
def test_mark_outcome_succeeded()
def test_mark_outcome_failed()
def test_mark_outcome_blocked()
# JSON roundtrip
def test_decision_audit_json_roundtrip()
# Service layer
async def test_decision_service_record()
async def test_decision_service_update_outcome()
async def test_decision_service_get_by_goal()
async def test_decision_service_get_by_actor()
async def test_decision_service_get_pending_outcomes()
# ORM migration
def test_alembic_upgrade_003_creates_table()
def test_alembic_downgrade_003_drops_table()
# Indexes
def test_decision_audit_goal_id_indexed()
def test_decision_audit_actor_indexed()
def test_decision_audit_outcome_indexed()
# Compatibility
def test_existing_models_still_valid()
# Cross-feature
async def test_link_to_goal_5_fk_constraint()
async def test_decision_audit_chain_for_one_goal()  # 1 goal → N audits
```

## Out-of-scope (不要做)

- ❌ 不实现 Failure Pattern Merger（F004 才做）
- ❌ 不实现 Intent Parser 接入（F002 才做）
- ❌ 不实现 GoalGuard Hook（F005 才做）
- ❌ 不改现有 Goal/Plan/Task/Trace/Evidence 模型
- ❌ 不动 verifier/deterministic.py
- ❌ 不动 v2 consumer
- ❌ 不创建 `_v6_*.py` / `_r*.py` / `protocol_*.md` 等 forbidden

## Inputs (必须先读)

1. `D:\AIOS\kernel\src\aios_kernel\domain\envelope.py` — Envelope 基类（3755B）
2. `D:\AIOS\kernel\src\aios_kernel\persistence\models.py` — 5 ORM（25940B）
3. `D:\AIOS\kernel\src\aios_kernel\domain\services\repository.py` — repo pattern
4. `D:\AIOS\aios_tasks\aios_vnext\cards\T0032_schema_migration.md` — migration 模式
5. `D:\AIOS\aios_tasks\aios_vnext\cards\F000_phase_f_acceptance_spec.md`

## Outputs (必须产出)

1. `D:\AIOS\aios_tasks\aios_vnext\evidence\F003__<ts>.md` — 必含 preflight 附件
2. `D:\AIOS\kernel\src\aios_kernel\domain\decision.py`
3. `D:\AIOS\kernel\src\aios_kernel\persistence\models.py` — 加 DecisionAuditORM
4. `D:\AIOS\kernel\src\aios_kernel\domain\services\decision_service.py`
5. `D:\AIOS\kernel\alembic\versions\003_decision_audit.py`
6. `D:\AIOS\kernel\tests\unit\test_decision_audit.py` — 20+ case

## Evidence Requirements

- [ ] DecisionAudit Pydantic model 可 import
- [ ] DecisionAuditORM 在 persistence/models.py 中
- [ ] Alembic upgrade 003 exit 0
- [ ] Alembic downgrade 003 exit 0
- [ ] DecisionService 5 方法（record/update_outcome/get_by_goal/get_by_actor/get_pending_outcomes）全 PASS
- [ ] `pytest tests/unit/test_decision_audit.py -v` 20+ case PASS
- [ ] 3 索引（goal_id/actor/outcome）创建成功
- [ ] `alembic upgrade head` 双跑不报错
- [ ] preflight = 0 issues
- [ ] 现有 49 张 Verified 卡未受影响（pytest 全套仍 PASS）

## Exit Criteria

1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex
3. **不要自封 Verified**

## Rollback

1. `alembic downgrade -1` 回到 002
2. 删除 decision.py / decision_service.py
3. 从 persistence/models.py 移除 DecisionAuditORM
4. 删除 test_decision_audit.py
5. `git reset --hard HEAD~1`（如有 commit）

## Time Budget

60 分钟

## Codex Acceptance Gate

Codex 独立验证：
1. `cd D:\AIOS\kernel && alembic upgrade head && alembic downgrade -1 && alembic upgrade head` 完整周期
2. `pytest tests/unit/test_decision_audit.py -v` 20+ case PASS
3. `pytest tests/unit -v` 全套仍 PASS
4. 手动测试 record/update_outcome/get_by_goal 闭环
5. preflight v4 = 0 issues

全部通过 → status=Verified