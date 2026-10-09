"""test_goal_guard.py — F005 GoalGuard Hook unit tests (15+ cases).

Covers the 5 type checks GoalGuard.validate() runs on every envelope:

  1. Required-fields completeness (10 fields)
  2. failure_modes non-empty (surface success trap)
  3. permission_scope permission overrun (FATAL)
  4. autonomous_scope ∩ requires_authorization == ∅
  5. missing_evidence collection plan (required=True)

Plus construction tests, verdict logic, risk-envelope generation,
duck-typing against dict / object / None, and the F005-required
PASS / RISK_BLOCK / FATAL coverage.

Run:
    cd D:\\AIOS\\kernel
    python -m pytest tests/unit/test_goal_guard.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make sure src/ is on path for direct pytest runs
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
# v2 hook layer lives in a sibling repo; add it to sys.path so the integration tests work.
V2_SRC = Path("D:/AIOS/_agent-hub/v2/src").resolve()
if V2_SRC.exists() and str(V2_SRC) not in sys.path:
    sys.path.insert(0, str(V2_SRC))

from aios_kernel.governance import (  # noqa: E402
    GoalContract,
    GoalGuard,
    GuardReport,
    GuardVerdict,
    make_risk_envelope,
)
from aios_kernel.governance.goal_guard import (  # noqa: E402
    EvidenceRequest,
    FailureMode,
    OpType,
    PermissionScope,
)


# ---------------------------------------------------------------- Helpers
def _complete_goal_contract(**overrides) -> GoalContract:
    """Build a fully-populated GoalContract (all 5 checks PASS)."""
    base = dict(
        id="goal-test-1",
        title="Build AIOS Marketing Tool",
        success_criteria="Live in 2 weeks",
        budget=100.0,
        owner="codex",
        status="Active",
        permission_scope=PermissionScope(
            allowed_paths=["D:/AIOS/_agent-hub/v2/"],
            allowed_ops=["dispatch"],
        ),
        failure_modes=[FailureMode("api_quota_exceeded", "high")],
        missing_evidence=[EvidenceRequest("competitor_pricing", required=True)],
        autonomous_scope=[OpType("v2", "dispatch")],
        requires_authorization=[OpType("kernel", "modify")],
    )
    base.update(overrides)
    return GoalContract(**base)


# =====================================================================
# 1. Construction
# =====================================================================

def test_goal_guard_init_no_args():
    """GoalGuard() with no args is the canonical constructor."""
    g = GoalGuard()
    assert isinstance(g, GoalGuard)
    assert g.REQUIRED_FIELDS is not None
    assert len(g.REQUIRED_FIELDS) == 10


def test_goal_guard_required_fields_list_10():
    """REQUIRED_FIELDS must list exactly the 10 mandatory fields per F000 §2."""
    expected = {
        "title", "success_criteria", "budget", "owner", "status",
        "permission_scope", "failure_modes", "missing_evidence",
        "autonomous_scope", "requires_authorization",
    }
    assert set(GoalGuard.REQUIRED_FIELDS) == expected


def test_goal_contract_minimal_defaults_to_invalid():
    """A default-constructed GoalContract has empty lists for most
    fields, which means the required-fields check should flag it."""
    g = GoalContract()
    assert g.title == ""
    assert g.failure_modes == []
    assert g.autonomous_scope == []
    assert g.missing_evidence == []
    # A default-constructed contract must NOT pass the guard.
    report = GoalGuard().validate(g)
    assert report.verdict != GuardVerdict.PASS


# =====================================================================
# 2. PASS cases
# =====================================================================

def test_validate_complete_goal_returns_pass():
    g = GoalGuard()
    report = g.validate(_complete_goal_contract())
    assert report.verdict == GuardVerdict.PASS
    assert report.failed_checks == []
    assert len(report.passed_checks) == 5
    assert "required_fields_complete" in report.passed_checks
    assert "failure_modes_present" in report.passed_checks
    assert "permission_scope_in_bounds" in report.passed_checks
    assert "autonomous_vs_authorization_disjoint" in report.passed_checks
    assert "missing_evidence_has_collection_plan" in report.passed_checks


def test_validate_dict_complete_goal_returns_pass():
    """The guard must also accept plain dicts (duck typing)."""
    g = GoalGuard()
    contract = {
        "title": "Build AIOS",
        "success_criteria": "Live in 2 weeks",
        "budget": 100.0,
        "owner": "codex",
        "status": "Pending",
        "permission_scope": {"allowed_paths": ["D:/AIOS/_agent-hub/v2/"]},
        "failure_modes": [{"name": "quota", "severity": "high"}],
        "missing_evidence": [{"name": "pricing", "required": True}],
        "autonomous_scope": [{"domain": "v2", "action": "dispatch"}],
        "requires_authorization": [{"domain": "kernel", "action": "modify"}],
    }
    report = g.validate(contract)
    assert report.verdict == GuardVerdict.PASS


def test_validate_object_duck_type_passes():
    """Duck-typed object: any class with the 10 attrs works."""
    from types import SimpleNamespace

    class FakeGoal:
        title = "x"
        success_criteria = "y"
        budget = 1.0
        owner = "z"
        status = "Active"
        permission_scope = PermissionScope(allowed_paths=["D:/safe/"])
        failure_modes = [FailureMode("x")]
        missing_evidence = [EvidenceRequest("x", required=True)]
        autonomous_scope = [OpType("a", "b")]
        requires_authorization = [OpType("c", "d")]

    g = GoalGuard()
    report = g.validate(FakeGoal())
    assert report.verdict == GuardVerdict.PASS


def test_validate_none_returns_fatal():
    """None is treated as the most-incomplete possible contract → FATAL."""
    g = GoalGuard()
    report = g.validate(None)
    assert report.verdict == GuardVerdict.FATAL
    assert any("overrun" in f for f in report.failed_checks)


# =====================================================================
# 3. Missing fields → RISK_BLOCK
# =====================================================================

def test_validate_missing_title_returns_risk_block():
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(title=""))
    assert report.verdict == GuardVerdict.RISK_BLOCK
    assert any("title" in f for f in report.failed_checks)


def test_validate_missing_permission_scope_returns_risk_block():
    """An empty allowed_paths list is treated as 'missing'."""
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(
        permission_scope=PermissionScope(allowed_paths=[]),
    ))
    # Empty list → "required_fields_missing" but ALSO counts as overrun
    # because no allowed_paths = nothing safe.  Either RISK_BLOCK or FATAL
    # is acceptable; the spec just says it must not PASS.
    assert report.verdict != GuardVerdict.PASS


def test_validate_missing_failure_modes_returns_risk_block():
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(failure_modes=[]))
    assert report.verdict == GuardVerdict.RISK_BLOCK
    assert any("failure_modes" in f for f in report.failed_checks)


def test_validate_missing_autonomous_scope_returns_risk_block():
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(autonomous_scope=[]))
    assert report.verdict == GuardVerdict.RISK_BLOCK


def test_validate_missing_requires_authorization_returns_risk_block():
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(requires_authorization=[]))
    assert report.verdict == GuardVerdict.RISK_BLOCK


def test_validate_missing_owner_returns_risk_block():
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(owner=""))
    assert report.verdict == GuardVerdict.RISK_BLOCK


# =====================================================================
# 4. failure_modes check (surface success trap)
# =====================================================================

def test_failure_modes_empty_returns_risk_block():
    """A goal with no failure_modes declared is the 'surface success trap'."""
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(failure_modes=[]))
    assert report.verdict == GuardVerdict.RISK_BLOCK
    assert any("surface success trap" in f for f in report.failed_checks)


def test_failure_modes_present_passes():
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(
        failure_modes=[FailureMode("quota", "high"), FailureMode("timeout", "medium")],
    ))
    assert "failure_modes_present" in report.passed_checks


# =====================================================================
# 5. permission_scope overrun → FATAL
# =====================================================================

def test_permission_scope_overrun_verifier_returns_fatal():
    """A goal that tries to claim access to verifier/ is FATAL — never retry."""
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(
        permission_scope=PermissionScope(
            allowed_paths=["D:/AIOS/kernel/src/aios_kernel/verifier/deterministic.py"],
        ),
    ))
    assert report.verdict == GuardVerdict.FATAL
    assert any("forbidden_path" in f or "overrun" in f for f in report.failed_checks)


def test_permission_scope_overrun_agents_md_returns_fatal():
    """AGENTS.md is also forbidden — guards the central SSOT from being clobbered."""
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(
        permission_scope=PermissionScope(
            allowed_paths=["D:/AIOS/_agent-hub/AGENTS.md"],
        ),
    ))
    assert report.verdict == GuardVerdict.FATAL


def test_permission_scope_safe_passes():
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(
        permission_scope=PermissionScope(
            allowed_paths=["D:/AIOS/_agent-hub/v2/src/", "D:/AIOS/kernel/src/aios_kernel/domain/"],
        ),
    ))
    assert "permission_scope_in_bounds" in report.passed_checks


# =====================================================================
# 6. autonomous vs authorization scope overlap
# =====================================================================

def test_autonomous_and_authorization_overlap_returns_risk_block():
    """Same (domain, action) in BOTH lists is a contradiction."""
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(
        autonomous_scope=[OpType("v2", "dispatch"), OpType("kernel", "modify")],
        requires_authorization=[OpType("v2", "dispatch")],
    ))
    assert report.verdict == GuardVerdict.RISK_BLOCK
    assert any("scope_overlap" in f for f in report.failed_checks)


def test_autonomous_and_authorization_disjoint_passes():
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(
        autonomous_scope=[OpType("v2", "dispatch")],
        requires_authorization=[OpType("kernel", "modify"), OpType("finance", "transfer")],
    ))
    assert "autonomous_vs_authorization_disjoint" in report.passed_checks


# =====================================================================
# 7. missing_evidence plan
# =====================================================================

def test_missing_evidence_no_required_true_returns_risk_block():
    """All missing_evidence entries marked required=False means no plan."""
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(
        missing_evidence=[EvidenceRequest("pricing", required=False)],
    ))
    assert report.verdict == GuardVerdict.RISK_BLOCK
    assert any("no_collection_plan" in f for f in report.failed_checks)


def test_missing_evidence_empty_passes():
    """missing_evidence=[] is the 'I have everything I need' case → OK."""
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(missing_evidence=[]))
    assert "missing_evidence_empty_ok" in report.passed_checks


def test_missing_evidence_at_least_one_required_passes():
    g = GoalGuard()
    report = g.validate(_complete_goal_contract(
        missing_evidence=[
            EvidenceRequest("pricing", required=False),
            EvidenceRequest("competitor_data", required=True),
        ],
    ))
    assert "missing_evidence_has_collection_plan" in report.passed_checks


# =====================================================================
# 8. Risk envelope factory
# =====================================================================

def test_make_risk_envelope_format():
    contract = _complete_goal_contract()
    report = GuardReport(
        verdict=GuardVerdict.RISK_BLOCK,
        passed_checks=["failure_modes_present"],
        failed_checks=["failure_modes_empty (surface success trap risk)"],
    )
    original = {"id": "env-abc", "message_type": "task", "payload": {}}
    risk_env = make_risk_envelope(contract, report, original)
    assert risk_env["type"] == "goal_guard_risk"
    assert risk_env["goal_id"] == "goal-test-1"
    assert risk_env["verdict"] == "risk_block"
    assert risk_env["original_envelope_id"] == "env-abc"
    assert risk_env["original_envelope_type"] == "task"
    assert isinstance(risk_env["failed_checks"], list)
    assert isinstance(risk_env["passed_checks"], list)
    assert "ts" in risk_env
    assert "created_at" in risk_env


def test_make_risk_envelope_with_dict_contract():
    """The hook layer hands dict-shaped contracts → must still produce a valid envelope."""
    contract = {"id": "goal-42", "title": "x"}
    report = GuardReport(
        verdict=GuardVerdict.FATAL,
        passed_checks=[],
        failed_checks=["forbidden_path_access: foo"],
    )
    original = {"id": "env-xyz", "message_type": "message"}
    risk_env = make_risk_envelope(contract, report, original)
    assert risk_env["goal_id"] == "goal-42"
    assert risk_env["verdict"] == "fatal"


def test_guard_report_to_dict_roundtrip():
    report = GuardReport(
        verdict=GuardVerdict.RISK_BLOCK,
        passed_checks=["a", "b"],
        failed_checks=["c"],
        risk_envelope={"x": 1},
    )
    d = report.to_dict()
    assert d["verdict"] == "risk_block"
    assert d["passed"] == ["a", "b"]
    assert d["failed"] == ["c"]
    assert d["risk_envelope"] == {"x": 1}


# =====================================================================
# 9. Integration with v2 hook layer (sanity)
# =====================================================================

def test_hook_layer_pass_terminal_envelope():
    """v2 hook: ack / result / status / heartbeat / error must auto-PASS."""
    from goal_guard_hook import guard_dispatch
    for t in ("ack", "result", "status", "heartbeat", "error"):
        allowed, risk = guard_dispatch({"message_type": t, "id": "1"}, ".")
        assert allowed is True, f"{t} must pass"
        assert risk is None


def test_hook_layer_pass_message_without_goal():
    """v2 hook: an envelope without payload.goal is not a GoalContract → PASS."""
    from goal_guard_hook import guard_dispatch
    allowed, risk = guard_dispatch(
        {"message_type": "message", "id": "2", "payload": {"text": "hello"}},
        ".",
    )
    assert allowed is True
    assert risk is None


def test_hook_layer_block_incomplete_goal():
    """v2 hook: a task envelope with an incomplete goal must be blocked."""
    from goal_guard_hook import guard_dispatch
    env = {
        "message_type": "task",
        "id": "env-blocked",
        "payload": {
            "title": "Build a thing",  # Phase-2: Strategy Gate requires payload.title
            "text": "Build a thing",
            "goal": {
                "title": "Build a thing",
                # missing 9 of 10 required fields
            }
        },
    }
    allowed, risk = guard_dispatch(env, ".")
    assert allowed is False
    assert risk is not None
    assert risk["type"] == "goal_guard_risk"
    assert risk["verdict"] in ("risk_block", "fatal")
    assert risk["original_envelope_id"] == "env-blocked"


def test_hook_layer_block_goal_with_verifier_path():
    """v2 hook: a goal that wants verifier/ access is FATAL."""
    from goal_guard_hook import guard_dispatch
    env = {
        "message_type": "task",
        "id": "env-fatal",
        "payload": {
            "title": "Modify verifier",  # Phase-2: Strategy Gate requires payload.title
            "text": "Modify verifier",
            "goal": {
                "title": "Modify verifier",
                "success_criteria": "y",
                "budget": 1.0,
                "owner": "codex",
                "status": "Active",
                "permission_scope": {
                    "allowed_paths": ["D:/AIOS/kernel/src/aios_kernel/verifier/deterministic.py"],
                },
                "failure_modes": [{"name": "x"}],
                "missing_evidence": [{"name": "y", "required": True}],
                "autonomous_scope": [{"domain": "a", "action": "b"}],
                "requires_authorization": [{"domain": "c", "action": "d"}],
            }
        },
    }
    allowed, risk = guard_dispatch(env, ".")
    assert allowed is False
    assert risk["type"] == "goal_guard_risk"
    assert risk["verdict"] == "fatal"


def test_hook_layer_pass_complete_goal():
    """v2 hook: a complete goal envelope passes."""
    from goal_guard_hook import guard_dispatch
    env = {
        "message_type": "task",
        "id": "env-pass",
        "payload": {
            "title": "OK",  # Phase-2: Strategy Gate requires payload.title
            "text": "OK complete task",
            "goal": {
                "title": "OK",
                "success_criteria": "Live",
                "budget": 1.0,
                "owner": "codex",
                "status": "Active",
                "permission_scope": {"allowed_paths": ["D:/safe/"]},
                "failure_modes": [{"name": "x"}],
                "missing_evidence": [{"name": "y", "required": True}],
                "autonomous_scope": [{"domain": "a", "action": "b"}],
                "requires_authorization": [{"domain": "c", "action": "d"}],
            }
        },
    }
    allowed, risk = guard_dispatch(env, ".")
    assert allowed is True
    assert risk is None


def test_write_risk_envelope_creates_file(tmp_path):
    """The hook layer writes the risk envelope to v2/messages/risk/."""
    from goal_guard_hook import write_risk_envelope
    risk_env = {
        "type": "goal_guard_risk",
        "verdict": "risk_block",
        "original_envelope_id": "abc-123",
        "failed_checks": ["x"],
    }
    p = write_risk_envelope(tmp_path, risk_env)
    assert p is not None
    assert p.exists()
    assert "abc-123" in p.name
    assert p.parent.name == "risk"
    # File content must be valid JSON
    import json
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["verdict"] == "risk_block"
