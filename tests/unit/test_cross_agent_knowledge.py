"""test_cross_agent_knowledge.py — G003 cross-agent knowledge layer unit tests.

15+ cases covering:
  - AgentName enum (5 values)
  - CapabilityIndex validation
  - CrossAgentKnowledge defaults
  - add_failure_cluster / add_capability idempotent
  - has_failure_with_root_cause
  - relevant_capabilities keyword filter
  - CrossAgentKnowledgeService: load/save/load_all/merge_failure_clusters
  - has_any_agent_seen_failure
  - Disk persistence roundtrip
  - confidence field range enforcement
  - GoalGuard integration (G003 reference layer)

Run:
    cd D:\\AIOS\\kernel
    python -m pytest tests/unit/test_cross_agent_knowledge.py -v
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Make sure src/ is on path for direct pytest runs
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))

from aios_kernel.learning.clustering import (  # noqa: E402
    FailureCluster,
    FailurePatternMerger,
    FailureTrace,
)
from aios_kernel.learning.cross_agent_knowledge import (  # noqa: E402
    AgentName,
    CapabilityIndex,
    CrossAgentKnowledge,
    CrossAgentKnowledgeService,
    CROSS_AGENT_KNOWLEDGE_DIR,
)


# ---------------------------------------------------------------- Helpers
def _cluster(
    cluster_id: str = "cl-1",
    root_cause: str = "timeout",
    occurrence_count: int = 1,
) -> FailureCluster:
    """Build a minimal FailureCluster for tests."""
    return FailureCluster(
        cluster_id=cluster_id,
        root_cause=root_cause,
        error_type="TimeoutError",
        affected_trace_ids=["t1"],
        occurrence_count=occurrence_count,
        severity_score=1.0,
        first_seen="2026-10-09T00:00:00Z",
        last_seen="2026-10-09T00:00:01Z",
        recommended_fix="check timeout",
        sample_error_messages=["connect timeout"],
    )


# =====================================================================
# 1. AgentName enum
# =====================================================================

def test_agent_name_enum_5_values() -> None:
    """AgentName has exactly 5 values: codex / claudecode / hermes / openclaw / human."""
    values = {a.value for a in AgentName}
    assert values == {"codex", "claudecode", "hermes", "openclaw", "human"}
    assert len(AgentName) == 5


def test_agent_name_is_str_enum() -> None:
    """AgentName is a str-based Enum (serializes cleanly to JSON)."""
    assert AgentName.CODEX == "codex"
    assert isinstance(AgentName.CODEX, str)
    assert AgentName.CODEX.value == "codex"


# =====================================================================
# 2. CapabilityIndex validation
# =====================================================================

def test_capability_index_validation() -> None:
    """CapabilityIndex accepts skill_id + use_cases + confidence."""
    cap = CapabilityIndex(
        skill_id="goal_guard_validate",
        use_cases=["validate goal", "v2 dispatch"],
        confidence=0.8,
    )
    assert cap.skill_id == "goal_guard_validate"
    assert cap.use_cases == ["validate goal", "v2 dispatch"]
    assert cap.confidence == 0.8


def test_capability_index_default_confidence_is_1() -> None:
    """Default confidence is 1.0 (fully confident)."""
    cap = CapabilityIndex(skill_id="x")
    assert cap.confidence == 1.0
    assert cap.use_cases == []


def test_capability_confidence_must_be_0_to_1() -> None:
    """confidence must be in [0.0, 1.0] (Pydantic ge/le)."""
    with pytest.raises(ValueError):
        CapabilityIndex(skill_id="x", confidence=1.5)
    with pytest.raises(ValueError):
        CapabilityIndex(skill_id="x", confidence=-0.1)


def test_capability_index_empty_skill_id_rejected() -> None:
    """skill_id must be non-empty (min_length=1)."""
    with pytest.raises(ValueError):
        CapabilityIndex(skill_id="")


# =====================================================================
# 3. CrossAgentKnowledge defaults
# =====================================================================

def test_cross_agent_knowledge_default_empty() -> None:
    """Default-constructed CrossAgentKnowledge has empty clusters/caps."""
    k = CrossAgentKnowledge(agent=AgentName.CODEX)
    assert k.agent == AgentName.CODEX
    assert k.failure_clusters == []
    assert k.capability_index == []
    assert k.failure_count_total == 0
    # Envelope fields
    assert k.id  # non-empty UUID
    assert k.schema_version == 1


def test_cross_agent_knowledge_agent_required() -> None:
    """CrossAgentKnowledge must specify an agent."""
    with pytest.raises(ValueError):
        CrossAgentKnowledge()  # type: ignore[call-arg]


def test_cross_agent_knowledge_extra_forbid() -> None:
    """Unknown fields are rejected (extra='forbid' on Envelope)."""
    with pytest.raises(ValueError):
        CrossAgentKnowledge(agent=AgentName.CODEX, this_does_not_exist="x")  # type: ignore[call-arg]


# =====================================================================
# 4. add_failure_cluster / add_capability idempotency
# =====================================================================

def test_add_failure_cluster_idempotent() -> None:
    """Adding the same cluster_id twice does not duplicate or throw."""
    k = CrossAgentKnowledge(agent=AgentName.CODEX)
    c = _cluster(cluster_id="cl-1", root_cause="timeout", occurrence_count=3)
    assert k.add_failure_cluster(c) is True
    assert k.add_failure_cluster(c) is False  # duplicate
    assert len(k.failure_clusters) == 1
    assert k.failure_count_total == 3  # not 6 — only first add increments


def test_add_failure_cluster_distinct_ids() -> None:
    """Adding different cluster_ids appends both."""
    k = CrossAgentKnowledge(agent=AgentName.CODEX)
    assert k.add_failure_cluster(_cluster(cluster_id="cl-1", occurrence_count=2)) is True
    assert k.add_failure_cluster(_cluster(cluster_id="cl-2", root_cause="file_missing", occurrence_count=1)) is True
    assert len(k.failure_clusters) == 2
    assert k.failure_count_total == 3


def test_add_capability_idempotent() -> None:
    """Adding the same skill_id twice does not duplicate."""
    k = CrossAgentKnowledge(agent=AgentName.CODEX)
    cap = CapabilityIndex(skill_id="goal_guard_validate", use_cases=["dispatch"])
    assert k.add_capability(cap) is True
    assert k.add_capability(cap) is False
    assert len(k.capability_index) == 1


# =====================================================================
# 5. Queries
# =====================================================================

def test_has_failure_with_root_cause() -> None:
    """has_failure_with_root_cause matches by root_cause string."""
    k = CrossAgentKnowledge(agent=AgentName.CODEX)
    k.add_failure_cluster(_cluster(root_cause="timeout"))
    k.add_failure_cluster(_cluster(cluster_id="cl-2", root_cause="file_missing"))
    assert k.has_failure_with_root_cause("timeout") is True
    assert k.has_failure_with_root_cause("file_missing") is True
    assert k.has_failure_with_root_cause("permission_denied") is False


def test_has_failure_with_root_cause_empty_string() -> None:
    """Empty root_cause returns False (no false-positive)."""
    k = CrossAgentKnowledge(agent=AgentName.CODEX)
    k.add_failure_cluster(_cluster(root_cause="timeout"))
    assert k.has_failure_with_root_cause("") is False


def test_relevant_capabilities_match_keyword() -> None:
    """relevant_capabilities filters by case-insensitive substring in use_cases."""
    k = CrossAgentKnowledge(agent=AgentName.CODEX)
    k.add_capability(CapabilityIndex(skill_id="goal_guard", use_cases=["validate goal", "v2 dispatch"]))
    k.add_capability(CapabilityIndex(skill_id="failure_merger", use_cases=["cluster failures"]))
    k.add_capability(CapabilityIndex(skill_id="unrelated", use_cases=["other stuff"]))
    found = k.relevant_capabilities("goal")
    assert len(found) == 1
    assert found[0].skill_id == "goal_guard"


def test_relevant_capabilities_empty_keyword() -> None:
    """Empty keyword returns empty list (no false-positive)."""
    k = CrossAgentKnowledge(agent=AgentName.CODEX)
    k.add_capability(CapabilityIndex(skill_id="x", use_cases=["anything"]))
    assert k.relevant_capabilities("") == []


# =====================================================================
# 6. Service: load / save / roundtrip
# =====================================================================

def test_knowledge_service_load_default_when_no_file(tmp_path: Path) -> None:
    """load() returns default empty when file does not exist."""
    svc = CrossAgentKnowledgeService(root=tmp_path)
    k = svc.load(AgentName.CODEX)
    assert k.agent == AgentName.CODEX
    assert k.failure_clusters == []
    assert k.failure_count_total == 0


def test_knowledge_service_save_load_roundtrip(tmp_path: Path) -> None:
    """save() then load() preserves data."""
    svc = CrossAgentKnowledgeService(root=tmp_path)
    k = CrossAgentKnowledge(agent=AgentName.CODEX)
    k.add_failure_cluster(_cluster(root_cause="timeout", occurrence_count=5))
    k.add_capability(CapabilityIndex(skill_id="goal_guard", use_cases=["validate"]))
    svc.save(k)
    # Confirm file exists
    p = tmp_path / "codex_knowledge.json"
    assert p.exists()
    # Reload
    loaded = svc.load(AgentName.CODEX)
    assert loaded.agent == AgentName.CODEX
    assert len(loaded.failure_clusters) == 1
    assert loaded.failure_clusters[0].root_cause == "timeout"
    assert loaded.failure_count_total == 5
    assert len(loaded.capability_index) == 1
    assert loaded.capability_index[0].skill_id == "goal_guard"


def test_knowledge_service_load_all_returns_5_agents(tmp_path: Path) -> None:
    """load_all() returns exactly 5 agents."""
    svc = CrossAgentKnowledgeService(root=tmp_path)
    all_k = svc.load_all()
    assert set(all_k.keys()) == set(AgentName)
    assert len(all_k) == 5
    for agent, knowledge in all_k.items():
        assert knowledge.agent == agent


def test_knowledge_service_merge_failure_clusters(tmp_path: Path) -> None:
    """merge_failure_clusters adds clusters idempotently and persists."""
    svc = CrossAgentKnowledgeService(root=tmp_path)
    clusters = [
        _cluster(cluster_id="cl-1", root_cause="timeout"),
        _cluster(cluster_id="cl-2", root_cause="file_missing"),
    ]
    k1 = svc.merge_failure_clusters(AgentName.CODEX, clusters)
    assert len(k1.failure_clusters) == 2
    # Re-merge same clusters → no duplicates
    k2 = svc.merge_failure_clusters(AgentName.CODEX, clusters)
    assert len(k2.failure_clusters) == 2  # still 2, not 4


def test_knowledge_service_has_any_agent_seen_failure(tmp_path: Path) -> None:
    """has_any_agent_seen_failure returns True iff ANY of 5 agents has it."""
    svc = CrossAgentKnowledgeService(root=tmp_path)
    # No data yet
    assert svc.has_any_agent_seen_failure("timeout") is False
    # Add to one agent only
    svc.merge_failure_clusters(
        AgentName.CLAUDECODE,
        [_cluster(root_cause="timeout")],
    )
    assert svc.has_any_agent_seen_failure("timeout") is True
    # Other root_causes still False
    assert svc.has_any_agent_seen_failure("file_missing") is False


# =====================================================================
# 7. Persistence (cross-load via real service)
# =====================================================================

def test_cross_agent_knowledge_persistence_to_disk(tmp_path: Path) -> None:
    """Files written to disk are valid JSON and parseable by load()."""
    svc = CrossAgentKnowledgeService(root=tmp_path)
    k = CrossAgentKnowledge(agent=AgentName.HERMES)
    k.add_failure_cluster(_cluster(root_cause="network_unavailable", occurrence_count=7))
    p = svc.save(k)
    assert p.exists()
    # Verify it's valid JSON
    raw = json.loads(p.read_text(encoding="utf-8"))
    assert raw["agent"] == "hermes"
    assert raw["failure_count_total"] == 7
    # Re-load via a brand-new service instance on same dir
    svc2 = CrossAgentKnowledgeService(root=tmp_path)
    loaded = svc2.load(AgentName.HERMES)
    assert loaded.failure_count_total == 7


def test_cross_agent_knowledge_default_dir_constant() -> None:
    """CROSS_AGENT_KNOWLEDGE_DIR points to the canonical hub location."""
    assert str(CROSS_AGENT_KNOWLEDGE_DIR).replace("\\", "/") == "D:/AIOS/_agent-hub/knowledge"


def test_service_corrupt_file_recovers_to_default(tmp_path: Path) -> None:
    """A corrupted JSON file should not crash load() — return default empty."""
    p = tmp_path / "codex_knowledge.json"
    p.write_text("{ this is not valid json }", encoding="utf-8")
    svc = CrossAgentKnowledgeService(root=tmp_path)
    k = svc.load(AgentName.CODEX)
    assert k.agent == AgentName.CODEX
    assert k.failure_clusters == []  # recovered to empty


# =====================================================================
# 8. Real failure flow: FailurePatternMerger → cross_agent_knowledge
# =====================================================================

def test_merger_output_feeds_cross_agent_knowledge(tmp_path: Path) -> None:
    """Real F004 FailurePatternMerger output flows into cross-agent knowledge."""
    merger = FailurePatternMerger()
    traces = [
        FailureTrace(id="t1", error_message="connect timeout at api", error_type="TimeoutError", timestamp="2026-10-09T00:00:00Z"),
        FailureTrace(id="t2", error_message="connect timeout at db", error_type="TimeoutError", timestamp="2026-10-09T00:00:01Z"),
    ]
    clusters = merger.merge(traces)
    assert len(clusters) >= 1
    # Persist via service
    svc = CrossAgentKnowledgeService(root=tmp_path)
    k = svc.merge_failure_clusters(AgentName.OPENCLAW, clusters)
    # At least one cluster has root_cause 'timeout'
    assert any(c.root_cause == "timeout" for c in k.failure_clusters)
    # Cross-agent query works
    assert svc.has_any_agent_seen_failure("timeout") is True


# =====================================================================
# 9. GoalGuard integration (G003 reference layer)
# =====================================================================

def test_goalkeeper_guard_constructs_with_knowledge_service(tmp_path: Path) -> None:
    """GoalGuard accepts an optional knowledge_service (backward-compatible)."""
    # No service (F005 default)
    from aios_kernel.governance.goal_guard import GoalGuard
    g0 = GoalGuard()
    assert g0.knowledge is None
    # With service
    svc = CrossAgentKnowledgeService(root=tmp_path)
    g1 = GoalGuard(knowledge_service=svc)
    assert g1.knowledge is svc


def test_goalkeeper_guard_references_knowledge_without_crashing(tmp_path: Path) -> None:
    """GoalGuard.validate() with knowledge_service must not crash on PASS."""
    from aios_kernel.governance.goal_guard import (
        EvidenceRequest, FailureMode, GoalContract, GoalGuard, OpType, PermissionScope,
    )
    svc = CrossAgentKnowledgeService(root=tmp_path)
    # Add a cluster that matches the failure_modes name
    svc.merge_failure_clusters(
        AgentName.CODEX,
        [_cluster(root_cause="api_quota_exceeded", cluster_id="cl-quota")],
    )
    contract = GoalContract(
        id="g1", title="Build X", success_criteria="Live", budget=10.0, owner="codex",
        status="Active",
        permission_scope=PermissionScope(allowed_paths=["D:/safe/"], allowed_ops=["dispatch"]),
        failure_modes=[FailureMode("api_quota_exceeded", "high")],
        missing_evidence=[EvidenceRequest("e", required=True)],
        autonomous_scope=[OpType("v2", "dispatch")],
        requires_authorization=[OpType("kernel", "modify")],
    )
    g = GoalGuard(knowledge_service=svc)
    report = g.validate(contract)
    # 5 baseline checks pass
    assert report.verdict.value == "pass"
    # G003 reference is recorded
    refs = [p for p in report.passed_checks if "cross_agent_knowledge_referenced" in p]
    assert refs, "expected cross_agent_knowledge_referenced in passed_checks"
    assert "1/1" in refs[0]
