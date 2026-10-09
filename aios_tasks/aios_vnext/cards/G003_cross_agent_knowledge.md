---
id: G003
title: Cross-agent knowledge layer — 5 Agent 共享 failure cluster + capability index
owner: CC
priority: P0
track: 7 — VNext Phase G (Learning Closure)
preconditions: [G000, F003, F004]
estimated_minutes: 90
depends_on: [G000, F003, F004]
blocks: [G004]
status: Pending
created: 2026-10-09
codex_supervisor_signoff_required: true
---

## Scope (要做)

让 Codex / Claude Code / Hermes / OpenClaw / Human 5 个 Agent 共享 failure cluster + capability index，避免每个 Agent 重复犯同样错误。

### 1. 必建/改文件（白名单内）

**`kernel/src/aios_kernel/learning/cross_agent_knowledge.py`** — 新建：

```python
"""cross_agent_knowledge.py — 5 Agent 共享 knowledge (Phase G G003).

每个 Agent 维护自己的 CrossAgentKnowledge:
  - agent: str
  - failure_clusters: list[FailureCluster]
  - capability_index: dict[str, list[str]]  # skill_id -> use cases
  - last_updated: datetime

GoalGuard 在 dispatch 时 reference 所有 5 Agent 的 failure cluster.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, Field

from aios_kernel.domain.envelope import Envelope
from aios_kernel.learning.clustering import FailureCluster

CROSS_AGENT_KNOWLEDGE_DIR = Path("D:/AIOS/_agent-hub/knowledge")


class AgentName(str, Enum):
    CODEX = "codex"
    CLAUDECODE = "claudecode"
    HERMES = "hermes"
    OPENCLAW = "openclaw"
    HUMAN = "human"


class CapabilityIndex(BaseModel):
    """一个 Agent 的 capability 索引"""
    model_config = {"extra": "forbid"}
    
    skill_id: str = Field(..., description="Capability name (e.g. 'goal_guard_validate')")
    use_cases: list[str] = Field(default_factory=list, description="When this capability applies")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class CrossAgentKnowledge(Envelope):
    """一个 Agent 的 knowledge 快照"""
    
    SCHEMA_VERSION: ClassVar[int] = 1
    
    agent: AgentName = Field(..., description="Which agent this knowledge belongs to")
    failure_clusters: list[FailureCluster] = Field(default_factory=list)
    capability_index: list[CapabilityIndex] = Field(default_factory=list)
    failure_count_total: int = Field(default=0, ge=0)
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_failure_cluster(self, cluster: FailureCluster):
        existing_keys = {c.cluster_id for c in self.failure_clusters}
        if cluster.cluster_id not in existing_keys:
            self.failure_clusters.append(cluster)
            self.failure_count_total += cluster.occurrence_count
            self.touch()
    
    def add_capability(self, capability: CapabilityIndex):
        existing_keys = {c.skill_id for c in self.capability_index}
        if capability.skill_id not in existing_keys:
            self.capability_index.append(capability)
            self.touch()
    
    def has_failure_with_root_cause(self, root_cause: str) -> bool:
        return any(c.root_cause == root_cause for c in self.failure_clusters)
    
    def relevant_capabilities(self, use_case_keyword: str) -> list[CapabilityIndex]:
        return [
            c for c in self.capability_index
            if any(use_case_keyword.lower() in uc.lower() for uc in c.use_cases)
        ]


class CrossAgentKnowledgeService:
    """5 Agent knowledge 服务"""
    
    def __init__(self, root: Path | None = None):
        self.root = root or CROSS_AGENT_KNOWLEDGE_DIR
        self.root.mkdir(parents=True, exist_ok=True)
    
    def _path_for(self, agent: AgentName) -> Path:
        return self.root / f"{agent.value}_knowledge.json"
    
    def load(self, agent: AgentName) -> CrossAgentKnowledge:
        p = self._path_for(agent)
        if p.exists():
            import json
            return CrossAgentKnowledge.model_validate_json(p.read_text(encoding="utf-8"))
        # default empty
        return CrossAgentKnowledge(agent=agent)
    
    def save(self, knowledge: CrossAgentKnowledge) -> Path:
        knowledge.last_updated = datetime.now(timezone.utc)
        p = self._path_for(knowledge.agent)
        p.write_text(knowledge.model_dump_json(indent=2), encoding="utf-8")
        return p
    
    def load_all(self) -> dict[AgentName, CrossAgentKnowledge]:
        return {a: self.load(a) for a in AgentName}
    
    def merge_failure_clusters(self, agent: AgentName, clusters: list[FailureCluster]):
        knowledge = self.load(agent)
        for c in clusters:
            knowledge.add_failure_cluster(c)
        self.save(knowledge)
    
    def has_any_agent_seen_failure(self, root_cause: str) -> bool:
        """任何 Agent 见过这个 root_cause 的 failure? """
        return any(
            self.load(a).has_failure_with_root_cause(root_cause)
            for a in AgentName
        )


__all__ = [
    "AgentName",
    "CapabilityIndex",
    "CrossAgentKnowledge",
    "CrossAgentKnowledgeService",
    "CROSS_AGENT_KNOWLEDGE_DIR",
]
```

**`kernel/src/aios_kernel/learning/__init__.py`** — 导出

**`kernel/tests/unit/test_cross_agent_knowledge.py`** — 15+ case

**`kernel/src/aios_kernel/governance/goal_guard.py`** — 最小修改：validate 时 reference cross-agent knowledge：

```python
# Phase G G003: cross-agent knowledge reference
class GoalGuard:
    def __init__(self, knowledge_service=None):
        self.knowledge = knowledge_service  # optional
    
    def validate(self, goal: Goal) -> GuardReport:
        ...
        # G003: 检查 cross-agent knowledge (任何 Agent 见过这个 root_cause?)
        # 只 reference, 不修改
        ...
```

### 2. 单元测试 (15+ case)

```python
def test_agent_name_enum_5_values()
def test_capability_index_validation()
def test_cross_agent_knowledge_required_fields()
def test_cross_agent_knowledge_default_empty()
def test_add_failure_cluster_idempotent()
def test_add_capability_idempotent()
def test_has_failure_with_root_cause()
def test_relevant_capabilities_match_keyword()
def test_knowledge_service_load_default_when_no_file()
def test_knowledge_service_save_load_roundtrip()
def test_knowledge_service_load_all_returns_5_agents()
def test_knowledge_service_merge_failure_clusters()
def test_knowledge_service_has_any_agent_seen_failure()
def test_cross_agent_knowledge_persistence_to_disk()
def test_capability_confidence_must_be_0_to_1()
```

### 3. 关键设计
- 每个 Agent 独立 JSON 持久化到 `_agent-hub/knowledge/{agent}_knowledge.json`
- GoalGuard 在 validate 时 reference 但不修改
- 任何 Agent 见过同 root_cause → 复用经验（避免重复）

## Out-of-scope (不要做)

- ❌ 不重写 FailurePatternMerger (F004 已有)
- ❌ 不重写 DecisionAudit (F003 已有)
- ❌ 不改 GoalGuard 的 5 类检查 (F005 已有) — G003 只加 reference 层
- ❌ 不实现 failure feedback 反哺 (G001 才做)
- ❌ 不实现 inbound 循环 (G002 才做)
- ❌ 不创建 `_v6_*.py` / `_r*.py` / `protocol_*.md` 等 forbidden pattern

## Inputs (必须先读)

1. `D:\AIOS\kernel\src\aios_kernel\learning\clustering.py` — FailureCluster schema
2. `D:\AIOS\kernel\src\aios_kernel\governance\goal_guard.py` — GoalGuard validate 5 类检查
3. `D:\AIOS\kernel\src\aios_kernel\domain\envelope.py` — Envelope base class
4. `D:\AIOS\aios_tasks\aios_vnext\cards\G000_phase_g_acceptance_spec.md`
5. `D:\AIOS\aios_tasks\aios_vnext\cards\F004_failure_pattern_merger.md`

## Outputs (必须产出)

1. `D:\AIOS\aios_tasks\aios_vnext\evidence\G003__<ts>.md` — 必含 preflight
2. `D:\AIOS\kernel\src\aios_kernel\learning\cross_agent_knowledge.py`
3. `D:\AIOS\kernel\src\aios_kernel\learning\__init__.py` — 导出
4. `D:\AIOS\kernel\tests\unit\test_cross_agent_knowledge.py` — 15+ case
5. 至少 5 个 agent 知识文件占位：`{codex,claudecode,hermes,openclaw,human}_knowledge.json`

## Evidence Requirements

- [ ] CrossAgentKnowledge / AgentName / CapabilityIndex 可 import
- [ ] CrossAgentKnowledgeService.load/save/load_all/merge_failure_clusters 全 PASS
- [ ] 15+ case 全 PASS
- [ ] 5 个 agent JSON 文件存在
- [ ] GoalGuard reference cross-agent knowledge 时不报错
- [ ] preflight = 0 issues
- [ ] 现有 baseline 不退化

## Exit Criteria

1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex
3. **不自封 Verified**

## Rollback

1. 删除 `cross_agent_knowledge.py`
2. 删除 `test_cross_agent_knowledge.py`
3. 恢复 `goal_guard.py` 到 git HEAD
4. `git reset --hard HEAD~1`（如有 commit）

## Time Budget

90 分钟

## Codex Acceptance Gate

Codex 独立验证：
1. `pytest tests/unit/test_cross_agent_knowledge.py -v` 15+ PASS
2. 手动测试 service.load_all() 返回 5 agents
3. GoalGuard validate() 调用不报错
4. `pytest tests/unit -v` 全套仍 PASS
5. preflight v4 = 0 issues

通过 → status=Verified