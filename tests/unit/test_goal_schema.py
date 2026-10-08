"""test_goal_schema.py - Pydantic Goal schema (10+ cases).

Covers:
- Construction with required fields
- Optional fields (description, deadline, tags)
- JSON schema export
- Status enum completeness
- Goal transitions (legal/illegal)
- Naive datetime rejection
- UUID id validation
- tz-aware serialization
- Cost/budget validation
- plan_ids idempotent add
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from aios_kernel.domain import GOAL_TRANSITIONS, Goal, GoalStatus


def _make_goal(**overrides):
    base = dict(
        title="Build AIOS Marketing Tool",
        success_criteria="Live in 2 weeks",
        budget=100.0,
        owner="codex",
    )
    base.update(overrides)
    return Goal(**base)


# 1. Construction with required fields
def test_goal_required_fields():
    g = _make_goal()
    assert g.title == "Build AIOS Marketing Tool"
    assert g.budget == 100.0
    assert g.owner == "codex"
    assert g.status == GoalStatus.PENDING
    assert g.id is not None
    assert g.created_at.tzinfo is not None
    assert g.updated_at.tzinfo is not None


# 2. Optional fields
def test_goal_optional_fields():
    deadline = datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
    g = _make_goal(description="Long rationale", deadline=deadline, tags=["v1", "p0"])
    assert g.description == "Long rationale"
    assert g.deadline == deadline
    assert g.tags == ["v1", "p0"]


# 3. JSON schema export
def test_goal_json_schema_export():
    g = _make_goal()
    schema = g.model_json_schema()
    assert "properties" in schema
    assert "title" in schema["properties"]
    assert "budget" in schema["properties"]
    assert "status" in schema["properties"]
    # Envelope fields
    assert "id" in schema["properties"]
    assert "created_at" in schema["properties"]


# 4. JSON roundtrip
def test_goal_json_roundtrip():
    g = _make_goal()
    blob = g.model_dump_json()
    g2 = Goal.model_validate_json(blob)
    assert g2.id == g.id
    assert g2.title == g.title
    assert g2.budget == g.budget
    # datetime should round-trip in ISO 8601
    assert g2.created_at.tzinfo is not None


# 5. Status enum completeness
def test_status_enum_has_5_states():
    assert len(list(GoalStatus)) == 5
    names = {s.name for s in GoalStatus}
    assert names == {"PENDING", "ACTIVE", "COMPLETED", "FAILED", "ABORTED"}


# 6. Legal forward transitions
def test_goal_legal_transitions():
    g = _make_goal()
    assert g.can_transition_to(GoalStatus.ACTIVE)
    g.transition_to(GoalStatus.ACTIVE)
    assert g.status == GoalStatus.ACTIVE
    assert g.can_transition_to(GoalStatus.COMPLETED)
    g.transition_to(GoalStatus.COMPLETED)
    assert g.is_terminal
    # terminal: no further moves
    assert not g.can_transition_to(GoalStatus.ABORTED)
    assert not g.can_transition_to(GoalStatus.FAILED)


# 7. Illegal transition raises
def test_goal_illegal_transition_raises():
    g = _make_goal()
    with pytest.raises(ValueError, match="illegal Goal status transition"):
        g.transition_to(GoalStatus.COMPLETED)  # Pending -> Completed is illegal


# 8. Abort from Pending or Active
def test_goal_abort_paths():
    for start in (GoalStatus.PENDING, GoalStatus.ACTIVE):
        g = _make_goal()
        if start != GoalStatus.PENDING:
            g.transition_to(start)
        g.transition_to(GoalStatus.ABORTED)
        assert g.is_terminal


# 9. Naive datetime rejection
def test_goal_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        _make_goal(deadline=datetime(2026, 1, 1))  # naive


# 10. UUID id format
def test_goal_uuid_id_format():
    g = _make_goal()
    # Validates as UUID (would raise if not)
    UUID(g.id)
    # Hex-only lowercase
    assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", g.id)


# 11. Budget must be >= 0
def test_goal_budget_non_negative():
    with pytest.raises(ValidationError):
        _make_goal(budget=-1.0)


# 12. Title length constraints
def test_goal_title_required():
    with pytest.raises(ValidationError):
        _make_goal(title="")


# 13. plan_ids add idempotent
def test_goal_plan_ids_idempotent():
    g = _make_goal()
    pid = "plan-1"
    g.add_plan(pid)
    g.add_plan(pid)
    assert g.plan_ids == [pid]


# 14. remaining_budget
def test_goal_remaining_budget():
    g = _make_goal(budget=100.0)
    assert g.remaining_budget(0) == 100.0
    assert g.remaining_budget(40) == 60.0
    assert g.remaining_budget(150) == 0.0  # clamped


# 15. GOAL_TRANSITIONS table completeness
def test_goal_transitions_table_completeness():
    # Every status has an entry, even if empty
    for s in GoalStatus:
        assert s in GOAL_TRANSITIONS
    # All sets contain only GoalStatus values
    for src, dsts in GOAL_TRANSITIONS.items():
        for d in dsts:
            assert isinstance(d, GoalStatus)
