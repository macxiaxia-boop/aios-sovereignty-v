"""test_requirements_lifecycle.py — Tests for RequirementsRegistry.

Verifies that:
  - Lifecycle states are correctly modeled.
  - Valid transitions are allowed.
  - Invalid transitions raise InvalidTransition.
  - RETIRED is terminal (except → ARCHIVED).
  - bulk_register_deprecated + bulk_archive_all work.
  - persistence round-trips.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT.parent / "policy"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from policy.requirements_lifecycle import (  # noqa: E402
    InvalidTransition,
    LifecycleState,
    RequirementsRegistry,
    UnknownRequirement,
    load_registry,
    save_registry,
)


def test_valid_transition_path():
    reg = RequirementsRegistry()
    reg.register("R-001", title="x", initial_state=LifecycleState.PROPOSED)
    reg.transition("R-001", LifecycleState.APPROVED)
    reg.transition("R-001", LifecycleState.ACTIVE)
    reg.transition("R-001", LifecycleState.COMPLETED)
    reg.transition("R-001", LifecycleState.SUPERSEDED)
    reg.transition("R-001", LifecycleState.ARCHIVED)
    assert reg.get("R-001").state == LifecycleState.ARCHIVED


def test_invalid_transition_raises():
    reg = RequirementsRegistry()
    reg.register("R-001", initial_state=LifecycleState.PROPOSED)
    # PROPOSED -> ACTIVE is not valid (must go through APPROVED)
    with pytest.raises(InvalidTransition):
        reg.transition("R-001", LifecycleState.ACTIVE)


def test_unknown_requirement_raises():
    reg = RequirementsRegistry()
    with pytest.raises(UnknownRequirement):
        reg.get("R-999")


def test_retired_is_terminal_except_to_archived():
    reg = RequirementsRegistry()
    reg.register("R-001", initial_state=LifecycleState.RETIRED)
    # Anything except ARCHIVED is forbidden
    with pytest.raises(InvalidTransition):
        reg.transition("R-001", LifecycleState.ACTIVE)
    with pytest.raises(InvalidTransition):
        reg.transition("R-001", LifecycleState.COMPLETED)
    # ARCHIVED is allowed
    reg.transition("R-001", LifecycleState.ARCHIVED)
    assert reg.get("R-001").state == LifecycleState.ARCHIVED


def test_archived_is_terminal():
    reg = RequirementsRegistry()
    reg.register("R-001", initial_state=LifecycleState.ARCHIVED)
    with pytest.raises(InvalidTransition):
        reg.transition("R-001", LifecycleState.RETIRED)
    with pytest.raises(InvalidTransition):
        reg.transition("R-001", LifecycleState.ACTIVE)


def test_bulk_register_deprecated():
    reg = RequirementsRegistry()
    reg.bulk_register_deprecated(["R-001", "R-002", "R-009"])
    for rid in ("R-001", "R-002", "R-009"):
        r = reg.get(rid)
        assert r.state == LifecycleState.RETIRED
        assert r.deprecated is True
    assert reg.retired_ids() == ["R-001", "R-002", "R-009"]


def test_bulk_archive_all_moves_retired_to_archived():
    reg = RequirementsRegistry()
    reg.bulk_register_deprecated(["R-001", "R-002"])
    n = reg.bulk_archive_all()
    assert n == 2
    assert reg.state_counts().get("RETIRED", 0) == 0
    assert reg.state_counts().get("ARCHIVED", 0) == 2


def test_history_recorded_on_transition():
    reg = RequirementsRegistry()
    reg.register("R-001", initial_state=LifecycleState.PROPOSED, owner="alice")
    reg.transition("R-001", LifecycleState.APPROVED, actor="bob", note="looks good")
    h = reg.get("R-001").history
    assert len(h) == 2
    assert h[0]["from"] is None
    assert h[0]["to"] == "PROPOSED"
    assert h[1]["from"] == "PROPOSED"
    assert h[1]["to"] == "APPROVED"
    assert h[1]["actor"] == "bob"
    assert h[1]["note"] == "looks good"


def test_persistence_round_trip(tmp_path):
    reg = RequirementsRegistry()
    reg.register("R-001", title="t1", initial_state=LifecycleState.ACTIVE)
    reg.register("R-002", title="t2", initial_state=LifecycleState.RETIRED)
    p = tmp_path / "registry.json"
    save_registry(reg, p)
    loaded = load_registry(p)
    assert len(loaded) == 2
    assert loaded.get("R-001").state == LifecycleState.ACTIVE
    assert loaded.get("R-002").state == LifecycleState.RETIRED
    assert loaded.get("R-001").title == "t1"


def test_load_registry_missing_returns_empty(tmp_path):
    reg = load_registry(tmp_path / "does-not-exist.json")
    assert len(reg) == 0