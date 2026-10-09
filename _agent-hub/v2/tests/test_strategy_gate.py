"""test_strategy_gate.py — Tests for StrategyGate (Phase-2).

Verifies that:
  - Valid horizontal-marketing envelope is allowed (PASS).
  - Envelope referencing R-001 / R-009 → RETIRED_REQUIREMENT_REACTIVATED + BLOCK.
  - Envelope referencing industry preset → STRATEGY_DRIFT_DETECTED + BLOCK.
  - Envelope referencing deprecated asset → DEPRECATED_ASSET_REFERENCED + BLOCK.
  - Envelope referencing archive / quarantine → ARCHIVE_LEAK_DETECTED + BLOCK.
  - Malformed task (no title) → INVALID_TASK_GENERATED + BLOCK.
  - Terminal envelopes (result / heartbeat) are NOT blocked.
  - Risk envelope shape mirrors goal_guard_hook contract.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT.parent / "policy"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from policy.strategy_gate import StrategyGate, gate_from_policy_dir  # noqa: E402
from policy.strategy_policy import load_strategy_policy  # noqa: E402


@pytest.fixture
def gate() -> StrategyGate:
    res = load_strategy_policy(POLICY_DIR)
    assert res.ok, res.errors
    return StrategyGate(res.policy, quarantine_root=r"D:\AIOS\_quarantine")


def _build_envelope(payload: dict, *, msg_type: str = "task", sender: str = "codex") -> dict:
    return {
        "id": "env-" + str(abs(hash(str(payload))) % 100000),
        "sender": sender,
        "recipient": "claudecode",
        "message_type": msg_type,
        "payload": payload,
        "schema_version": "1.0",
    }


def test_valid_horizontal_marketing_task_passes(gate: StrategyGate):
    env = _build_envelope({
        "title": "Plan a Q4 SaaS retention campaign",
        "text": "Use general marketing automation for upsell.",
    })
    decision = gate.evaluate_envelope(env)
    assert decision.allowed, decision.events
    assert decision.risk_envelope is None


def test_retired_id_R001_blocks(gate: StrategyGate):
    env = _build_envelope({
        "title": "Implement CloudTech V22 unified gateway",
        "text": "Per R-001, deploy the 23-tool AI 数字营销中台.",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    assert any(e.event_type == "RETIRED_REQUIREMENT_REACTIVATED" for e in decision.events)
    assert decision.risk_envelope is not None
    assert decision.risk_envelope["policy_id"] == "GLOBAL_PRODUCT_STRATEGY"


def test_retired_id_R009_blocks(gate: StrategyGate):
    env = _build_envelope({
        "title": "Revive 装修矩阵 V2 roadmap",
        "text": "Resume work on R-009 (装修矩阵 V2 + 小红书仿写管线).",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    assert any(e.event_type == "RETIRED_REQUIREMENT_REACTIVATED" for e in decision.events)


def test_industry_preset_blocked(gate: StrategyGate):
    env = _build_envelope({
        "title": "Load vertical preset",
        "text": "Initialize the industry-zhuangxiu preset.",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    assert any(e.event_type == "STRATEGY_DRIFT_DETECTED" for e in decision.events)


def test_deprecated_asset_reference_blocks(gate: StrategyGate):
    env = _build_envelope({
        "title": "Re-point",
        "text": "Use the path D:\\CloudTech-Portable\\gateway_v22.py as the source.",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    assert any(e.event_type == "DEPRECATED_ASSET_REFERENCED" for e in decision.events)


def test_archive_leak_detected(gate: StrategyGate):
    env = _build_envelope({
        "title": "Pull source",
        "text": "Read D:\\AIOS\\AIOS_SOURCE_OF_TRUTH_FINAL\\roadmap\\P3-01.md and re-activate it.",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    # Must emit at least one of the leak-related events
    event_types = [e.event_type for e in decision.events]
    assert "ARCHIVE_LEAK_DETECTED" in event_types or "DEPRECATED_ASSET_REFERENCED" in event_types


def test_invalid_task_blocks(gate: StrategyGate):
    """A task with no title/text → INVALID_TASK_GENERATED."""
    env = _build_envelope({"summary": "no title"}, msg_type="task")
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    assert any(e.event_type == "INVALID_TASK_GENERATED" for e in decision.events)


def test_terminal_envelope_is_not_blocked(gate: StrategyGate):
    """Terminal envelopes (result/ack/heartbeat) must never be blocked."""
    for t in ("result", "ack", "status", "heartbeat", "error"):
        env = _build_envelope({"note": f"terminal {t}"}, msg_type=t)
        decision = gate.evaluate_envelope(env)
        assert decision.allowed, f"terminal {t} should auto-pass: {decision.events}"


def test_risk_envelope_shape_matches_goal_guard_hook_contract(gate: StrategyGate):
    env = _build_envelope({
        "title": "Re-activate R-001",
        "text": "do R-001 again",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    risk = decision.risk_envelope
    assert risk is not None
    for field in ("envelope_type", "original_envelope_id", "reason",
                  "events", "ts", "policy_id", "policy_version",
                  "schema_version"):
        assert field in risk, f"missing {field} in risk envelope"
    assert risk["policy_id"] == "GLOBAL_PRODUCT_STRATEGY"
    assert risk["policy_version"] == "2026-10-08"
    assert risk["schema_version"] == "1.0"
    assert risk["envelope_type"] == "strategy_gate_risk"
    assert isinstance(risk["events"], list)


def test_gate_from_policy_dir_returns_gate():
    res, gate = gate_from_policy_dir(POLICY_DIR)
    assert res.ok
    assert gate is not None