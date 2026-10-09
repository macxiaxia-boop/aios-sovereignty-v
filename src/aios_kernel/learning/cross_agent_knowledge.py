"""cross_agent_knowledge.py — 5 Agent 共享 knowledge (Phase G G003).

每个 Agent 维护自己的 CrossAgentKnowledge:
  - agent: AgentName
  - failure_clusters: list[FailureCluster]
  - capability_index: list[CapabilityIndex]
  - last_updated: datetime

GoalGuard 在 dispatch 时 reference 所有 5 Agent 的 failure cluster
(只读, 不修改).

Phase G 范围:
- G003 ONLY: 建立 cross-agent knowledge 数据层 + service
- G001 后续: FailureFeedbackService 反哺 (NOT in this file)
- G002 后续: Inbound 循环自动生成 GoalContract (NOT in this file)

设计要点
--------
1. **Pydantic v2 + dataclass 兼容** — FailureCluster (F004) 是 dataclass,
   Envelope 是 Pydantic BaseModel; 通过 ``arbitrary_types_allowed=True``
   桥接, 不重写 F004.
2. **idempotent** — add_* 方法用 cluster_id / skill_id 去重, 重复添加
   不抛错, 不修改已有数据.
3. **持久化** — 每个 Agent 独立 JSON 落盘到
   ``_agent-hub/knowledge/{agent}_knowledge.json``; load() 缺文件时
   返回默认空 knowledge, 显式 self-healing.
4. **不引入 IO 到 Pydantic 字段** — 持久化由 service 层负责, model 层
   纯 in-memory, 便于单测.
"""
from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import ClassVar

from pydantic import BaseModel, ConfigDict, Field

from aios_kernel.domain.envelope import Envelope, utcnow
from aios_kernel.learning.clustering import FailureCluster

# 默认持久化目录 — 5 个 agent 各一个 JSON
CROSS_AGENT_KNOWLEDGE_DIR = Path("D:/AIOS/_agent-hub/knowledge")


class AgentName(str, Enum):
    """5 个共享 knowledge 的 Agent (Phase G G003)."""

    CODEX = "codex"
    CLAUDECODE = "claudecode"
    HERMES = "hermes"
    OPENCLAW = "openclaw"
    HUMAN = "human"


class CapabilityIndex(BaseModel):
    """一个 Agent 的 capability 索引 (skill + use cases + confidence)."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(..., min_length=1, description="Capability name (e.g. 'goal_guard_validate')")
    use_cases: list[str] = Field(
        default_factory=list,
        description="When this capability applies (free text keywords)",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Self-reported confidence in [0, 1]; < 1 = 仍在学习",
    )


class CrossAgentKnowledge(Envelope):
    """一个 Agent 的 knowledge 快照.

    注意: 继承 Envelope 提供 id/created_at/updated_at/schema_version 4 字段.
    FailureCluster 是 F004 的 dataclass — 通过 arbitrary_types_allowed 兼容.
    """

    # FailureCluster 是 dataclass, Pydantic v2 需显式允许任意类型
    model_config = ConfigDict(
        extra="forbid",
        arbitrary_types_allowed=True,
    )

    SCHEMA_VERSION: ClassVar[int] = 1

    agent: AgentName = Field(..., description="Which agent this knowledge belongs to")
    failure_clusters: list[FailureCluster] = Field(
        default_factory=list,
        description="Aggregated failure clusters (from F004 FailurePatternMerger)",
    )
    capability_index: list[CapabilityIndex] = Field(
        default_factory=list,
        description="Capabilities this agent has + their use cases + confidence",
    )
    failure_count_total: int = Field(
        default=0,
        ge=0,
        description="Sum of occurrence_count across all clusters (lifetime counter)",
    )
    last_updated: datetime = Field(
        default_factory=utcnow,
        description="Last time knowledge was mutated (tz-aware UTC)",
    )

    # ----------------------------- mutators --------------------------------
    def add_failure_cluster(self, cluster: FailureCluster) -> bool:
        """添加 failure cluster; idempotent (重复 cluster_id 跳过).

        Returns True if added, False if already present.
        """
        existing_keys = {c.cluster_id for c in self.failure_clusters}
        if cluster.cluster_id in existing_keys:
            return False
        self.failure_clusters.append(cluster)
        self.failure_count_total += int(cluster.occurrence_count)
        self.last_updated = utcnow()
        self.touch()
        return True

    def add_capability(self, capability: CapabilityIndex) -> bool:
        """添加 capability; idempotent (重复 skill_id 跳过).

        Returns True if added, False if already present.
        """
        existing_keys = {c.skill_id for c in self.capability_index}
        if capability.skill_id in existing_keys:
            return False
        self.capability_index.append(capability)
        self.last_updated = utcnow()
        self.touch()
        return True

    # ----------------------------- queries ---------------------------------
    def has_failure_with_root_cause(self, root_cause: str) -> bool:
        """是否有任何 cluster 匹配该 root_cause?"""
        if not root_cause:
            return False
        return any(c.root_cause == root_cause for c in self.failure_clusters)

    def relevant_capabilities(self, use_case_keyword: str) -> list[CapabilityIndex]:
        """按 use_case 关键字过滤 capabilities (case-insensitive substring)."""
        if not use_case_keyword:
            return []
        needle = use_case_keyword.lower()
        return [
            cap
            for cap in self.capability_index
            if any(needle in uc.lower() for uc in cap.use_cases)
        ]


class CrossAgentKnowledgeService:
    """5 Agent knowledge 的持久化 service (load / save / merge / cross-agent query).

    持久化策略:
    - 每个 agent 一个 JSON: ``{root}/{agent}_knowledge.json``
    - load() 缺文件时返回 default empty CrossAgentKnowledge
      (不会抛 FileNotFoundError — service 必须 self-heal)
    - save() 写盘前自动更新 ``last_updated`` 字段
    - merge_failure_clusters() 走 model.add_failure_cluster 的 idempotent 路径
    """

    def __init__(self, root: Path | None = None):
        self.root = Path(root) if root else CROSS_AGENT_KNOWLEDGE_DIR
        self.root.mkdir(parents=True, exist_ok=True)

    def _path_for(self, agent: AgentName) -> Path:
        return self.root / f"{agent.value}_knowledge.json"

    # ----------------------------- IO --------------------------------------
    def load(self, agent: AgentName) -> CrossAgentKnowledge:
        """从磁盘加载指定 agent 的 knowledge; 缺文件返回 default empty."""
        p = self._path_for(agent)
        if p.exists():
            raw = p.read_text(encoding="utf-8")
            try:
                return CrossAgentKnowledge.model_validate_json(raw)
            except (ValueError, json.JSONDecodeError):
                # 文件损坏 → fallback 到 default empty
                return CrossAgentKnowledge(agent=agent)
        return CrossAgentKnowledge(agent=agent)

    def save(self, knowledge: CrossAgentKnowledge) -> Path:
        """持久化到磁盘; 自动更新 last_updated. 返回写入路径."""
        knowledge.last_updated = utcnow()
        p = self._path_for(knowledge.agent)
        # 兼容 pydantic 2.13.x (无 mode kwarg): 用 model_dump(mode="json") + json.dumps
        p.write_text(
            json.dumps(knowledge.model_dump(mode="json"), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return p

    # ----------------------------- batch -----------------------------------
    def load_all(self) -> dict[AgentName, CrossAgentKnowledge]:
        """加载全部 5 个 agent 的 knowledge."""
        return {a: self.load(a) for a in AgentName}

    def merge_failure_clusters(
        self,
        agent: AgentName,
        clusters: list[FailureCluster],
    ) -> CrossAgentKnowledge:
        """把 clusters merge 到指定 agent 的 knowledge (idempotent), 落盘后返回."""
        knowledge = self.load(agent)
        for c in clusters:
            knowledge.add_failure_cluster(c)
        self.save(knowledge)
        return knowledge

    # ----------------------------- cross-agent ----------------------------
    def has_any_agent_seen_failure(self, root_cause: str) -> bool:
        """任何 Agent 见过这个 root_cause 的 failure?"""
        if not root_cause:
            return False
        for agent in AgentName:
            if self.load(agent).has_failure_with_root_cause(root_cause):
                return True
        return False

    def agents_seen_failure(self, root_cause: str) -> list[AgentName]:
        """列出所有见过这个 root_cause 的 agent (用于 audit)."""
        if not root_cause:
            return []
        return [
            agent
            for agent in AgentName
            if self.load(agent).has_failure_with_root_cause(root_cause)
        ]


__all__ = [
    "AgentName",
    "CapabilityIndex",
    "CrossAgentKnowledge",
    "CrossAgentKnowledgeService",
    "CROSS_AGENT_KNOWLEDGE_DIR",
]
