"""test_goal_contract_12_fields.py - Phase F F001 GoalContract (12-field schema).

Covers the F001 evidence requirements:
  - 10 new fields on Goal (inferred_intent, preserve_capabilities,
    known_constraints, environment_context, failure_modes, permission_scope,
    missing_evidence, approved_tradeoffs, autonomous_scope, requires_authorization)
  - 7 Pydantic sub-models (Constraint / EnvSnapshot / FailureMode /
    PermissionScope / EvidenceRequest / Tradeoff / OpType)
  - Cross-field business rules:
    * permission_scope.max_budget == goal.budget
    * autonomous_scope disjoint from requires_authorization
    * failure_modes min 1 when environment_context is set
    * environment_context required when known_constraints has entries
  - Backward compat (existing 10-field construction still valid)
  - ORM round-trip Pydantic -> ORM dict -> Pydantic
  - JSON Schema export contains all 12 fields
  - Alembic upgrade 003 adds 10 columns; downgrade -1 removes them
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from aios_kernel.domain.goal import (
    ALLOWED_OPS,
    Constraint,
    EnvSnapshot,
    EvidenceRequest,
    FailureMode,
    Goal,
    GoalStatus,
    OpType,
    PermissionScope,
    Tradeoff,
)


# ----- helpers --------------------------------------------------------------


def _make_goal(**overrides):
    base = dict(
        title="Build AIOS Marketing Tool",
        success_criteria="Live in 2 weeks",
        budget=100.0,
        owner="codex",
    )
    base.update(overrides)
    return Goal(**base)


# ===== Section 1: 12-field construction ======================================


# 1. inferred_intent optional
def test_inferred_intent_optional():
    g = _make_goal()
    assert g.inferred_intent is None
    g2 = _make_goal(inferred_intent="ship faster")
    assert g2.inferred_intent == "ship faster"


# 2. preserve_capabilities default empty
def test_preserve_capabilities_default_empty():
    g = _make_goal()
    assert g.preserve_capabilities == []
    assert isinstance(g.preserve_capabilities, list)


# 3. Constraint validation - budget
def test_constraint_validation_budget():
    c = Constraint(type="budget", value=99.5, rationale="hard cap from user")
    assert c.type == "budget"
    assert c.value == 99.5


# 4. Constraint validation - timeout
def test_constraint_validation_timeout():
    c = Constraint(type="timeout", value=3600, rationale="one hour max")
    assert c.type == "timeout"


# 5. Constraint validation - forbidden_path
def test_constraint_validation_forbidden_path():
    c = Constraint(
        type="forbidden_path",
        value="D:/AIOS/_agent-hub",
        rationale="do not modify the SSOT",
    )
    assert c.type == "forbidden_path"


# 6. EnvSnapshot with recent_failures + history_refs
def test_env_snapshot_with_recent_failures():
    env = EnvSnapshot(
        cwd="D:/AIOS",
        os="Windows 11",
        available_tools=["Read", "Write", "Bash"],
        recent_failures=["auth timeout", "OOM on plan A"],
        history_refs=["goal-001", "goal-007"],
    )
    assert env.cwd == "D:/AIOS"
    assert env.available_tools == ["Read", "Write", "Bash"]
    assert len(env.recent_failures) == 2
    assert "goal-001" in env.history_refs


# 7. FailureMode: description + detection required
def test_failure_modes_detection_required():
    fm = FailureMode(description="looks done but DB not flushed", detection="check WAL")
    assert fm.description.startswith("looks")
    assert fm.detection == "check WAL"
    # indicator is optional
    assert fm.indicator is None
    # Empty detection must fail
    with pytest.raises(ValidationError):
        FailureMode(description="x", detection="")


# 8. PermissionScope allowed_ops subset
def test_permission_scope_allowed_ops_subset():
    ps = PermissionScope(
        allowed_paths=["D:/AIOS/kernel"],
        allowed_ops=["read", "write"],
        max_budget=100.0,
        max_duration_sec=3600,
    )
    assert ps.allowed_ops == ["read", "write"]
    # Bad op rejected
    with pytest.raises(ValidationError):
        PermissionScope(
            allowed_paths=["x"],
            allowed_ops=["read", "rm-rf"],
            max_budget=1.0,
        )


# 9. PermissionScope requires_approval subset
def test_permission_scope_requires_approval():
    ps = PermissionScope(
        allowed_paths=["D:/tmp"],
        allowed_ops=["read", "execute"],
        max_budget=10.0,
        requires_approval=["execute"],
    )
    assert ps.requires_approval == ["execute"]
    # Bad op rejected
    with pytest.raises(ValidationError):
        PermissionScope(
            allowed_paths=["x"],
            allowed_ops=["read"],
            max_budget=1.0,
            requires_approval=["drop"],
        )


# 10. EvidenceRequest required vs optional
def test_evidence_request_required_vs_optional():
    e1 = EvidenceRequest(description="log of upgrade", source="D:/AIOS/logs/u.log")
    assert e1.required is True  # default
    e2 = EvidenceRequest(description="chat screenshot", source="https://...", required=False)
    assert e2.required is False


# 11. Tradeoff approved_by validation
def test_tradeoff_approved_by_validation():
    t1 = Tradeoff(
        decision="use SQLite for dev",
        cost="some advanced pgvector features missing",
        benefit="zero-setup local dev",
        approved_by="user",
    )
    assert t1.approved_by == "user"
    t2 = Tradeoff(
        decision="test",
        cost="c",
        benefit="b",
        approved_by="custom-agent",
    )
    assert t2.approved_by == "custom-agent"
    # Empty rejected
    with pytest.raises(ValidationError):
        Tradeoff(decision="c", cost="c", benefit="b", approved_by="")


# 12. OpType domain/action enums (Literal validation)
def test_op_type_domain_action_enum():
    op1 = OpType(domain="file", action="write", target="D:/x.py")
    assert op1.domain == "file"
    # Bad domain rejected
    with pytest.raises(ValidationError):
        OpType(domain="bogus", action="write")
    # Bad action rejected
    with pytest.raises(ValidationError):
        OpType(domain="file", action="explode")


# ===== Section 2: backward compat ===========================================


# 13. Existing 10-field construction still valid
def test_existing_goal_10_fields_still_valid():
    g = _make_goal()
    # All 10 original fields preserved
    assert g.title == "Build AIOS Marketing Tool"
    assert g.success_criteria == "Live in 2 weeks"
    assert g.budget == 100.0
    assert g.owner == "codex"
    assert g.status == GoalStatus.PENDING
    # All 10 NEW fields have safe defaults
    assert g.inferred_intent is None
    assert g.preserve_capabilities == []
    assert g.known_constraints == []
    assert g.environment_context is None
    assert g.failure_modes == []
    assert g.permission_scope is None
    assert g.missing_evidence == []
    assert g.approved_tradeoffs == []
    assert g.autonomous_scope == []
    assert g.requires_authorization == []
    # SCHEMA_VERSION (class-level marker) bumped to 2
    # NOTE: instance g.schema_version stays at Envelope default (1) until
    # to_orm() / save() refreshes it. The class var is what tests/consumers
    # gate on for forward compatibility.
    assert Goal.SCHEMA_VERSION == 2
    assert g.schema_version == 1  # default before save


# 14. Round-trip Pydantic -> ORM dict -> Pydantic (via goal_to_orm / goal_from_orm)
def test_round_trip_pydantic_to_orm_to_pydantic():
    from aios_kernel.persistence.models import goal_from_orm, goal_to_orm

    g_orig = _make_goal(
        description="full goal",
        inferred_intent="ship MVP",
        preserve_capabilities=["db:aios_kernel.db"],
        known_constraints=[
            Constraint(type="budget", value=100.0, rationale="user cap"),
            Constraint(type="timeout", value=3600, rationale="max 1h"),
        ],
        environment_context=EnvSnapshot(
            cwd="D:/AIOS", os="Windows 11", available_tools=["Read"]
        ),
        failure_modes=[
            FailureMode(description="silent fail", detection="check WAL"),
        ],
        permission_scope=PermissionScope(
            allowed_paths=["D:/AIOS/kernel"],
            allowed_ops=["read", "write"],
            max_budget=100.0,
        ),
        missing_evidence=[
            EvidenceRequest(description="log", source="D:/log.txt"),
        ],
        approved_tradeoffs=[
            Tradeoff(
                decision="SQLite", cost="no pgvector", benefit="zero-setup",
                approved_by="user",
            ),
        ],
        autonomous_scope=[OpType(domain="file", action="read")],
        requires_authorization=[OpType(domain="file", action="delete", target="D:/x")],
    )

    orm_obj = goal_to_orm(g_orig)
    # All 12 fields persisted (10 in columns + title/desc/success_criteria/budget/...)
    assert orm_obj.inferred_intent == "ship MVP"
    assert orm_obj.preserve_capabilities == ["db:aios_kernel.db"]
    assert isinstance(orm_obj.known_constraints, list) and len(orm_obj.known_constraints) == 2
    assert orm_obj.environment_context["cwd"] == "D:/AIOS"
    assert len(orm_obj.failure_modes) == 1
    assert orm_obj.permission_scope["max_budget"] == 100.0
    assert len(orm_obj.missing_evidence) == 1
    assert len(orm_obj.approved_tradeoffs) == 1
    assert len(orm_obj.autonomous_scope) == 1
    assert len(orm_obj.requires_authorization) == 1

    # Round-trip back to Pydantic.
    g_back = goal_from_orm(orm_obj)
    assert g_back.id == g_orig.id
    assert g_back.title == g_orig.title
    assert g_back.inferred_intent == g_orig.inferred_intent
    assert g_back.preserve_capabilities == g_orig.preserve_capabilities
    assert len(g_back.known_constraints) == 2
    assert g_back.environment_context.cwd == "D:/AIOS"
    assert len(g_back.failure_modes) == 1
    assert g_back.permission_scope.max_budget == 100.0
    assert len(g_back.missing_evidence) == 1
    assert len(g_back.approved_tradeoffs) == 1
    assert len(g_back.autonomous_scope) == 1
    assert len(g_back.requires_authorization) == 1
    # Sub-model types preserved
    assert isinstance(g_back.known_constraints[0], Constraint)
    assert isinstance(g_back.environment_context, EnvSnapshot)
    assert isinstance(g_back.failure_modes[0], FailureMode)
    assert isinstance(g_back.permission_scope, PermissionScope)
    assert isinstance(g_back.missing_evidence[0], EvidenceRequest)
    assert isinstance(g_back.approved_tradeoffs[0], Tradeoff)
    assert isinstance(g_back.autonomous_scope[0], OpType)
    assert isinstance(g_back.requires_authorization[0], OpType)


# ===== Section 3: business rules ============================================


# 15. permission_scope.max_budget matches goal.budget
def test_permission_scope_max_budget_matches_goal_budget():
    ps = PermissionScope(allowed_paths=["D:/x"], allowed_ops=["read"], max_budget=100.0)
    _make_goal(permission_scope=ps, budget=100.0)  # OK
    with pytest.raises(ValidationError, match="max_budget"):
        _make_goal(permission_scope=ps, budget=99.0)  # mismatch rejected


# 16. autonomous_scope disjoint from requires_authorization
def test_autonomous_scope_disjoint_from_requires_authorization():
    auto_op = OpType(domain="file", action="read")
    auth_op = OpType(domain="file", action="delete", target="D:/x")
    # OK when disjoint
    _make_goal(autonomous_scope=[auto_op], requires_authorization=[auth_op])
    # Overlap rejected
    with pytest.raises(ValidationError, match="disjoint"):
        _make_goal(
            autonomous_scope=[auto_op],
            requires_authorization=[auto_op],
        )


# 17. failure_modes minimum one required when environment_context is set
def test_failure_modes_minimum_one_required():
    env = EnvSnapshot(cwd="D:/x", os="Linux", available_tools=["Read"])
    # Without failure_modes -> rejected
    with pytest.raises(ValidationError, match="failure_modes"):
        _make_goal(environment_context=env)
    # With one -> OK
    _make_goal(
        environment_context=env,
        failure_modes=[FailureMode(description="x", detection="y")],
    )


# 18. environment_context required when known_constraints has entries
def test_env_snapshot_required_when_known_constraints_present():
    c = Constraint(type="budget", value=50.0, rationale="cap")
    # No env -> rejected
    with pytest.raises(ValidationError, match="environment_context"):
        _make_goal(known_constraints=[c])
    # With env -> OK
    _make_goal(
        known_constraints=[c],
        environment_context=EnvSnapshot(cwd="D:/x", os="Linux"),
        failure_modes=[FailureMode(description="x", detection="y")],
    )


# ===== Section 4: migration ==================================================


def _run_alembic(args, url):
    env = os.environ.copy()
    env["AIOS_KERNEL_DATABASE_URL"] = url
    cmd = [sys.executable, "-m", "alembic", "-c", str(KERNEL_ROOT / "alembic.ini"), *args]
    return subprocess.run(cmd, cwd=str(KERNEL_ROOT), env=env, capture_output=True, text=True)


KERNEL_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def sqlite_url(tmp_path):
    db_path = tmp_path / "test.db"
    yield f"sqlite+aiosqlite:///{db_path}"
    if db_path.exists():
        db_path.unlink()


def _goal_columns(url):
    import sqlite3
    path = url.replace("sqlite+aiosqlite:///", "")
    con = sqlite3.connect(path)
    cur = con.execute("PRAGMA table_info(goals)")
    cols = [r[1] for r in cur.fetchall()]
    con.close()
    return cols


# 19. Alembic upgrade head reaches 003 with 10 new columns
def test_alembic_upgrade_003_adds_10_columns(sqlite_url):
    r = _run_alembic(["upgrade", "head"], sqlite_url)
    assert r.returncode == 0, f"upgrade failed: {r.stderr}"
    cols = _goal_columns(sqlite_url)
    new_cols = {
        "inferred_intent",
        "preserve_capabilities",
        "known_constraints",
        "environment_context",
        "failure_modes",
        "permission_scope",
        "missing_evidence",
        "approved_tradeoffs",
        "autonomous_scope",
        "requires_authorization",
    }
    assert new_cols.issubset(set(cols)), f"missing F001 columns: {new_cols - set(cols)}"


# 20. Alembic downgrade -1 removes the 10 new columns
def test_alembic_downgrade_003_removes_10_columns(sqlite_url):
    _run_alembic(["upgrade", "head"], sqlite_url)
    r = _run_alembic(["downgrade", "-1"], sqlite_url)
    assert r.returncode == 0, f"downgrade failed: {r.stderr}"
    cols = _goal_columns(sqlite_url)
    new_cols = {
        "inferred_intent",
        "preserve_capabilities",
        "known_constraints",
        "environment_context",
        "failure_modes",
        "permission_scope",
        "missing_evidence",
        "approved_tradeoffs",
        "autonomous_scope",
        "requires_authorization",
    }
    assert not (new_cols & set(cols)), f"F001 columns survived downgrade: {new_cols & set(cols)}"


# 21. Alembic upgrade head reaches revision 003
def test_alembic_head_is_003(sqlite_url):
    _run_alembic(["upgrade", "head"], sqlite_url)
    cur = _run_alembic(["current"], sqlite_url)
    assert cur.returncode == 0
    assert "003" in cur.stdout


# 22. upgrade / downgrade / upgrade idempotent
def test_alembic_upgrade_downgrade_upgrade_roundtrip(sqlite_url):
    r1 = _run_alembic(["upgrade", "head"], sqlite_url)
    r2 = _run_alembic(["downgrade", "-1"], sqlite_url)
    r3 = _run_alembic(["upgrade", "head"], sqlite_url)
    assert r1.returncode == 0
    assert r2.returncode == 0
    assert r3.returncode == 0


# ===== Section 5: JSON schema & exports =====================================


# 23. JSON schema contains all 12 fields
def test_goal_json_schema_includes_all_12_fields():
    g = _make_goal()
    schema = g.model_json_schema()
    props = schema["properties"]
    expected = {
        # 10 new
        "inferred_intent",
        "preserve_capabilities",
        "known_constraints",
        "environment_context",
        "failure_modes",
        "permission_scope",
        "missing_evidence",
        "approved_tradeoffs",
        "autonomous_scope",
        "requires_authorization",
        # 5 of the original fields still present
        "title",
        "description",
        "success_criteria",
        "budget",
        "status",
    }
    missing = expected - set(props.keys())
    assert not missing, f"JSON schema missing fields: {missing}"


# 24. JSON dump roundtrip preserves sub-model list fields
def test_json_dump_roundtrip_submodels():
    env = EnvSnapshot(cwd="D:/x", os="Linux")
    g = _make_goal(
        known_constraints=[Constraint(type="budget", value=50.0, rationale="x")],
        environment_context=env,  # required when known_constraints non-empty
        failure_modes=[FailureMode(description="d", detection="c")],
        autonomous_scope=[OpType(domain="file", action="read")],
    )
    blob = g.model_dump_json()
    g2 = Goal.model_validate_json(blob)
    assert len(g2.known_constraints) == 1
    assert isinstance(g2.known_constraints[0], Constraint)
    assert len(g2.failure_modes) == 1
    assert isinstance(g2.failure_modes[0], FailureMode)
    assert len(g2.autonomous_scope) == 1
    assert isinstance(g2.autonomous_scope[0], OpType)


# 25. ALLOWED_OPS exports the canonical set
def test_allowed_ops_constant_exports():
    assert set(ALLOWED_OPS) == {"read", "write", "execute", "network", "delete"}


# 26. has_full_contract helper (Phase F F005 gate)
def test_has_full_contract_helper():
    # Empty Goal -> not full
    g = _make_goal()
    assert g.has_full_contract() is False
    # Fully populated -> full
    env = EnvSnapshot(cwd="D:/x", os="Linux")
    g2 = _make_goal(
        preserve_capabilities=["db"],
        known_constraints=[Constraint(type="budget", value=1.0, rationale="x")],
        environment_context=env,
        failure_modes=[FailureMode(description="d", detection="c")],
        permission_scope=PermissionScope(allowed_paths=["D:/x"], allowed_ops=["read"], max_budget=100.0),
        missing_evidence=[EvidenceRequest(description="log", source="x.txt")],
        autonomous_scope=[OpType(domain="file", action="read")],
        requires_authorization=[OpType(domain="file", action="delete")],
    )
    assert g2.has_full_contract() is True


# 27. Sub-model JSON serialization (datetime-free, portable)
def test_submodel_json_serialization():
    ps = PermissionScope(allowed_paths=["D:/x"], allowed_ops=["read"], max_budget=10.0)
    blob = ps.model_dump_json()
    ps2 = PermissionScope.model_validate_json(blob)
    assert ps2 == ps

    env = EnvSnapshot(cwd="D:/x", os="Linux")
    env2 = EnvSnapshot.model_validate_json(env.model_dump_json())
    assert env2.cwd == env.cwd
    assert env2.recent_failures == env.recent_failures


# 28. Domain __init__ exports the new sub-models
def test_domain_package_exports_submodels():
    from aios_kernel.domain import (
        Constraint,
        EnvSnapshot,
        EvidenceRequest,
        FailureMode,
        OpType,
        PermissionScope,
        Tradeoff,
    )
    assert Constraint is not None
    assert EnvSnapshot is not None
    assert FailureMode is not None
    assert PermissionScope is not None
    assert EvidenceRequest is not None
    assert Tradeoff is not None
    assert OpType is not None


# 29. Repository exposes goal_from_orm + get_domain
def test_repository_goal_from_orm_roundtrip():
    from aios_kernel.persistence.models import goal_from_orm, goal_to_orm
    from aios_kernel.persistence.repository import _FROM_ORM

    # _FROM_ORM must register Goal -> goal_from_orm
    assert Goal in _FROM_ORM
    assert _FROM_ORM[Goal] is goal_from_orm

    # Round-trip
    g = _make_goal(
        preserve_capabilities=["asset-x"],
        autonomous_scope=[OpType(domain="file", action="read")],
    )
    orm_obj = goal_to_orm(g)
    g_back = goal_from_orm(orm_obj)
    assert g_back.id == g.id
    assert g_back.preserve_capabilities == ["asset-x"]
    assert len(g_back.autonomous_scope) == 1


# 30. Default Goal construction with all-new fields returns expected types
def test_default_field_types():
    g = _make_goal()
    assert isinstance(g.preserve_capabilities, list)
    assert isinstance(g.known_constraints, list)
    assert isinstance(g.failure_modes, list)
    assert isinstance(g.missing_evidence, list)
    assert isinstance(g.approved_tradeoffs, list)
    assert isinstance(g.autonomous_scope, list)
    assert isinstance(g.requires_authorization, list)
    assert g.environment_context is None
    assert g.permission_scope is None
    assert g.inferred_intent is None
