"""test_decision_audit.py — DecisionAudit + DecisionService (Phase F F003).

20+ unit tests across construction, validation, state transitions,
JSON roundtrip, service-layer operations, ORM migration roundtrip,
index creation, and cross-feature compatibility.
"""
from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from aios_kernel.domain.decision import (
    DecisionActor,
    DecisionAudit,
    DecisionOutcome,
)
from aios_kernel.domain.services import DecisionService
from aios_kernel.domain.services.repository import (
    InMemoryRepository,
    make_engine,
    make_session_factory,
    session_scope,
)
from aios_kernel.persistence import (
    DecisionAuditORM,
    SqlAlchemyRepository,
    create_all,
    decision_to_orm,
    drop_all,
)

KERNEL_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_INI = KERNEL_ROOT / "alembic.ini"


# ============================================================
# 1. Construction + validation (5 cases)
# ============================================================


def test_decision_audit_required_fields():
    """Every required field must be present at construction."""
    a = DecisionAudit(
        goal_id="g-001",
        actor=DecisionActor.CODEX,
        rationale="Because X is the best path.",
        chosen="option_x",
    )
    assert a.goal_id == "g-001"
    assert a.actor == DecisionActor.CODEX
    assert a.rationale.startswith("Because")
    assert a.chosen == "option_x"
    # Defaults
    assert a.outcome == DecisionOutcome.PENDING
    assert a.confidence == 1.0
    assert a.alternatives == []
    assert a.tags == []
    assert a.outcome_detail is None
    # Envelope fields
    assert a.id is not None
    assert len(a.id) == 36  # UUID4 string
    assert a.created_at.tzinfo is not None
    assert a.updated_at.tzinfo is not None
    assert a.schema_version == 1


def test_decision_actor_enum_5_values():
    """Six actors: codex, claudecode, hermes, openclaw, human, system."""
    assert {a.value for a in DecisionActor} == {
        "codex",
        "claudecode",
        "hermes",
        "openclaw",
        "human",
        "system",
    }


def test_decision_outcome_enum_4_values():
    """Four outcomes: pending, succeeded, failed, blocked."""
    assert {o.value for o in DecisionOutcome} == {
        "pending",
        "succeeded",
        "failed",
        "blocked",
    }


def test_confidence_must_be_0_to_1():
    """Confidence outside [0,1] is rejected by the field_validator."""
    with pytest.raises(Exception):
        DecisionAudit(
            goal_id="g",
            actor=DecisionActor.CODEX,
            rationale="r",
            chosen="c",
            confidence=1.5,
        )
    with pytest.raises(Exception):
        DecisionAudit(
            goal_id="g",
            actor=DecisionActor.CODEX,
            rationale="r",
            chosen="c",
            confidence=-0.1,
        )
    # Boundary values must be accepted.
    a0 = DecisionAudit(
        goal_id="g",
        actor=DecisionActor.CODEX,
        rationale="r",
        chosen="c",
        confidence=0.0,
    )
    assert a0.confidence == 0.0
    a1 = DecisionAudit(
        goal_id="g",
        actor=DecisionActor.CODEX,
        rationale="r",
        chosen="c",
        confidence=1.0,
    )
    assert a1.confidence == 1.0


def test_rationale_required_min_length():
    """Rationale must be non-empty."""
    with pytest.raises(Exception):
        DecisionAudit(
            goal_id="g",
            actor=DecisionActor.CODEX,
            rationale="",
            chosen="c",
        )


# ============================================================
# 2. State transitions (3 cases)
# ============================================================


def test_mark_outcome_succeeded():
    a = _make()
    a.mark_outcome(DecisionOutcome.SUCCEEDED, detail="ran cleanly")
    assert a.outcome == DecisionOutcome.SUCCEEDED
    assert a.outcome_detail == "ran cleanly"


def test_mark_outcome_failed():
    a = _make()
    a.mark_outcome(DecisionOutcome.FAILED, detail="transient error")
    assert a.outcome == DecisionOutcome.FAILED
    assert a.outcome_detail == "transient error"


def test_mark_outcome_blocked():
    a = _make()
    a.mark_outcome(DecisionOutcome.BLOCKED, detail="GoalGuard veto")
    assert a.outcome == DecisionOutcome.BLOCKED
    assert a.outcome_detail == "GoalGuard veto"


# ============================================================
# 3. JSON roundtrip (1 case)
# ============================================================


def test_decision_audit_json_roundtrip():
    a = _make(
        alternatives=["x", "y", "z"],
        tags=["routing", "p0"],
        outcome_detail="early detail",
    )
    payload = a.model_dump_json()
    restored = DecisionAudit.model_validate_json(payload)
    assert restored.id == a.id
    assert restored.goal_id == a.goal_id
    assert restored.actor == a.actor
    assert restored.rationale == a.rationale
    assert restored.alternatives == a.alternatives
    assert restored.chosen == a.chosen
    assert restored.outcome == a.outcome
    assert restored.confidence == a.confidence
    assert restored.tags == a.tags
    # JSON-Schema export also works (T0035 API uses this).
    schema = a.export_json_schema()
    assert isinstance(schema, dict)
    assert "properties" in schema


# ============================================================
# 4. Service layer (5 cases — one per public method)
# ============================================================


@pytest.mark.asyncio
async def test_decision_service_record():
    """record() persists + populates id/created_at/updated_at."""
    repo = InMemoryRepository()
    svc = DecisionService(repo)
    a = await svc.record(
        goal_id="g-1",
        actor=DecisionActor.CLAUDECODE,
        rationale="worker dispatch chosen",
        chosen="dispatch_w1",
        alternatives=["dispatch_w2", "dispatch_w3"],
        confidence=0.7,
        tags=["routing"],
    )
    assert a.id is not None
    assert a.actor == DecisionActor.CLAUDECODE
    assert a.confidence == 0.7
    # InMemoryRepository bucket check.
    assert repo.all(DecisionAudit).__len__() == 1


@pytest.mark.asyncio
async def test_decision_service_update_outcome():
    """update_outcome() updates the outcome and detail, persists."""
    repo = InMemoryRepository()
    svc = DecisionService(repo)
    a = await svc.record(
        goal_id="g-1",
        actor=DecisionActor.CLAUDECODE,
        rationale="r",
        chosen="c",
    )
    assert a.outcome == DecisionOutcome.PENDING
    returned = await svc.update_outcome(
        a, outcome=DecisionOutcome.SUCCEEDED, detail="done"
    )
    assert returned is a
    assert a.outcome == DecisionOutcome.SUCCEEDED
    assert a.outcome_detail == "done"
    # Second call with only detail should keep outcome.
    await svc.update_outcome(a, detail="more info")
    assert a.outcome == DecisionOutcome.SUCCEEDED
    assert a.outcome_detail == "more info"
    # Empty update rejected.
    with pytest.raises(ValueError):
        await svc.update_outcome(a)


@pytest.mark.asyncio
async def test_decision_service_get_by_goal():
    """get_by_goal returns all audits for a single goal, sorted by time."""
    repo = InMemoryRepository()
    svc = DecisionService(repo)
    g1 = "goal-A"
    g2 = "goal-B"
    await svc.record(goal_id=g1, actor=DecisionActor.CODEX, rationale="r", chosen="c")
    await svc.record(goal_id=g1, actor=DecisionActor.HERMES, rationale="r", chosen="c")
    await svc.record(goal_id=g2, actor=DecisionActor.HUMAN, rationale="r", chosen="c")
    rows_g1 = await svc.get_by_goal(g1)
    assert len(rows_g1) == 2
    for row in rows_g1:
        assert row.goal_id == g1
    rows_g2 = await svc.get_by_goal(g2)
    assert len(rows_g2) == 1
    assert rows_g2[0].actor == DecisionActor.HUMAN


@pytest.mark.asyncio
async def test_decision_service_get_by_actor():
    """get_by_actor returns only audits by that actor, newest first."""
    repo = InMemoryRepository()
    svc = DecisionService(repo)
    for _ in range(3):
        await svc.record(
            goal_id="g",
            actor=DecisionActor.CODEX,
            rationale="r",
            chosen="c",
        )
    await svc.record(goal_id="g", actor=DecisionActor.HUMAN, rationale="r", chosen="c")
    codex_rows = await svc.get_by_actor(DecisionActor.CODEX)
    assert len(codex_rows) == 3
    for row in codex_rows:
        assert row.actor == DecisionActor.CODEX
    # limit clamps result count.
    limited = await svc.get_by_actor(DecisionActor.CODEX, limit=2)
    assert len(limited) == 2
    human_rows = await svc.get_by_actor(DecisionActor.HUMAN)
    assert len(human_rows) == 1


@pytest.mark.asyncio
async def test_decision_service_get_pending_outcomes():
    """get_pending_outcomes returns only PENDING rows; SUCCEEDED not included."""
    repo = InMemoryRepository()
    svc = DecisionService(repo)
    a1 = await svc.record(goal_id="g", actor=DecisionActor.CODEX, rationale="r", chosen="c")
    a2 = await svc.record(goal_id="g", actor=DecisionActor.HERMES, rationale="r", chosen="c")
    await svc.record(goal_id="g", actor=DecisionActor.HUMAN, rationale="r", chosen="c")
    await svc.update_outcome(a2, outcome=DecisionOutcome.SUCCEEDED)
    pending = await svc.get_pending_outcomes()
    assert len(pending) == 2
    ids = {p.id for p in pending}
    assert a1.id in ids
    assert a2.id not in ids  # already SUCCEEDED


# ============================================================
# 5. ORM migration (2 cases)
# ============================================================


def _run_alembic(args, url):
    env = os.environ.copy()
    env["AIOS_KERNEL_DATABASE_URL"] = url
    cmd = [sys.executable, "-m", "alembic", "-c", str(ALEMBIC_INI), *args]
    result = subprocess.run(
        cmd,
        cwd=str(KERNEL_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    return result


def _tables_in(url):
    path = url.replace("sqlite+aiosqlite:///", "")
    con = sqlite3.connect(path)
    cur = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    names = [r[0] for r in cur.fetchall()]
    con.close()
    return names


def test_alembic_upgrade_002_creates_decision_audit_table(tmp_path):
    """alembic upgrade head creates the decision_audit table."""
    db_path = tmp_path / "f003.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    result = _run_alembic(["upgrade", "head"], url)
    assert result.returncode == 0, f"upgrade failed: {result.stderr}"
    tables = _tables_in(url)
    assert "decision_audit" in tables


def test_alembic_downgrade_002_drops_decision_audit_table(tmp_path):
    """alembic downgrade to 001 drops the decision_audit table added by 002.

    Phase F puts the head at 003 (after F001 goal_contract). -1 from head only
    goes to 002, which still has decision_audit. Chain two -1 to reach 001.
    """
    db_path = tmp_path / "f003.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    r1 = _run_alembic(["upgrade", "head"], url)
    assert r1.returncode == 0
    _run_alembic(["downgrade", "-1"], url)  # 003 -> 002
    r2 = _run_alembic(["downgrade", "-1"], url)  # 002 -> 001
    assert r2.returncode == 0, f"downgrade failed: {r2.stderr}"
    tables = _tables_in(url)
    assert "decision_audit" not in tables


# ============================================================
# 6. Indexes (3 cases)
# ============================================================


def test_decision_audit_goal_id_indexed(tmp_path):
    """ix_decision_audit_goal_id exists after upgrade head."""
    db_path = tmp_path / "f003.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    _run_alembic(["upgrade", "head"], url)
    con = sqlite3.connect(str(db_path))
    cur = con.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='decision_audit'"
    )
    names = {r[0] for r in cur.fetchall()}
    con.close()
    assert "ix_decision_audit_goal_id" in names


def test_decision_audit_actor_indexed(tmp_path):
    """ix_decision_audit_actor exists after upgrade head."""
    db_path = tmp_path / "f003.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    _run_alembic(["upgrade", "head"], url)
    con = sqlite3.connect(str(db_path))
    cur = con.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='decision_audit'"
    )
    names = {r[0] for r in cur.fetchall()}
    con.close()
    assert "ix_decision_audit_actor" in names


def test_decision_audit_outcome_indexed(tmp_path):
    """ix_decision_audit_outcome exists after upgrade head."""
    db_path = tmp_path / "f003.db"
    url = f"sqlite+aiosqlite:///{db_path}"
    _run_alembic(["upgrade", "head"], url)
    con = sqlite3.connect(str(db_path))
    cur = con.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='decision_audit'"
    )
    names = {r[0] for r in cur.fetchall()}
    con.close()
    assert "ix_decision_audit_outcome" in names


# ============================================================
# 7. Compatibility (2 cases)
# ============================================================


def test_existing_models_still_valid():
    """Adding DecisionAudit must not break existing model imports."""
    from aios_kernel.domain import (
        Artifact,
        Evidence,
        Goal,
        Plan,
        Task,
        Trace,
    )

    g = Goal(title="g", success_criteria="x", budget=1.0, owner="o")
    assert g.title == "g"
    assert Goal is not None
    assert Artifact is not None
    assert Evidence is not None
    assert Plan is not None
    assert Task is not None
    assert Trace is not None


@pytest.mark.asyncio
async def test_decision_audit_orm_roundtrip(db_repo, async_engine):
    """Round-trip a DecisionAudit through the SQL repo."""
    # Create a parent Goal so the FK can resolve.
    from aios_kernel.domain import Goal

    g = Goal(title="g", success_criteria="x", budget=1.0, owner="o")
    await db_repo.add(g)
    await db_repo.commit()

    svc = DecisionService(db_repo)
    audit = await svc.record(
        goal_id=g.id,
        actor=DecisionActor.CODEX,
        rationale="because",
        chosen="x",
        alternatives=["y", "z"],
        confidence=0.5,
        tags=["routing"],
    )

    # Read back via a fresh session to bypass the in-session identity map.
    factory = make_session_factory(async_engine)
    async with session_scope(factory) as session:
        orm = await session.get(DecisionAuditORM, audit.id)
        assert orm is not None
        assert orm.actor == "codex"
        assert orm.outcome == "pending"
        assert orm.alternatives == ["y", "z"]
        assert orm.confidence == 0.5
        assert orm.goal_id == g.id


# ============================================================
# 8. Cross-feature (2 cases)
# ============================================================


@pytest.mark.asyncio
async def test_link_to_goal_fk_constraint(db_repo, async_engine):
    """Inserting an audit with a non-existent goal_id must fail at the FK."""
    from sqlalchemy import text as sa_text
    from sqlalchemy.exc import IntegrityError

    # SQLite needs PRAGMA foreign_keys=ON per connection to enforce FK.
    # Issue it via the engine's connection before running the test action.
    async with async_engine.connect() as conn:
        await conn.execute(sa_text("PRAGMA foreign_keys = ON"))
        await conn.commit()

    svc = DecisionService(db_repo)
    try:
        with pytest.raises(IntegrityError):
            await svc.record(
                goal_id="does-not-exist",
                actor=DecisionActor.CODEX,
                rationale="r",
                chosen="c",
            )
    finally:
        # After IntegrityError, the session is in error state.
        # Rollback so fixture teardown doesn't PendingRollbackError.
        try:
            await db_repo.session.rollback()
        except Exception:
            pass


@pytest.mark.asyncio
async def test_decision_audit_chain_for_one_goal():
    """One goal can accumulate many audit rows (1 -> N)."""
    repo = InMemoryRepository()
    svc = DecisionService(repo)
    goal = "goal-chain"
    actors = [
        DecisionActor.CODEX,
        DecisionActor.CLAUDECODE,
        DecisionActor.HERMES,
        DecisionActor.HUMAN,
        DecisionActor.SYSTEM,
    ]
    for i, actor in enumerate(actors):
        await svc.record(
            goal_id=goal,
            actor=actor,
            rationale=f"step {i}",
            chosen=f"option_{i}",
        )
    chain = await svc.get_by_goal(goal)
    assert len(chain) == 5
    # Ordered by created_at; verify the order matches insertion.
    for i, row in enumerate(chain):
        assert row.actor == actors[i]


# ============================================================
# Helpers
# ============================================================


def _make(
    goal_id: str = "g-default",
    actor: DecisionActor = DecisionActor.CODEX,
    rationale: str = "default rationale",
    chosen: str = "default",
    alternatives: list[str] | None = None,
    tags: list[str] | None = None,
    outcome_detail: str | None = None,
    confidence: float = 1.0,
) -> DecisionAudit:
    return DecisionAudit(
        goal_id=goal_id,
        actor=actor,
        rationale=rationale,
        chosen=chosen,
        alternatives=alternatives or [],
        tags=tags or [],
        outcome_detail=outcome_detail,
        confidence=confidence,
    )