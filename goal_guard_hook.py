"""goal_guard_hook.py — v2 hook dispatcher for goal_guard

R1880 round 1: tests/unit/test_goal_guard.py imports `guard_dispatch`
and `write_risk_envelope` from this module.

Real interface from tests:
  guard_dispatch(envelope, path) → (allowed: bool, risk: dict | None)
  write_risk_envelope(contract, report, envelope, out_dir) → str (file path)

Verdict mapping:
  - envelope has no payload.goal → not a GoalContract → auto-PASS (risk=None)
  - message_type in (ack, result, status, heartbeat, error) → auto-PASS (risk=None)
  - message_type = "message" with no payload.goal → auto-PASS (risk=None)
  - message_type = "task" with payload.goal:
    - GoalContract valid (PASS) → allowed=True, risk=None
    - GoalContract incomplete (RISK_BLOCK) → allowed=False, risk=dict
    - GoalContract with verifier path (FATAL) → allowed=False, risk=dict
"""
from __future__ import annotations
import sys
from pathlib import Path
import json

# Make src/ importable
sys.path.insert(0, str(Path(__file__).parent / "src"))

from typing import Any, Tuple, Optional, Dict

from aios_kernel.governance.goal_guard import (
    GoalGuard, GuardVerdict, GuardReport, make_risk_envelope,
)


_AUTO_PASS_TYPES = frozenset({"ack", "result", "status", "heartbeat", "error"})


def _is_goal_contract(envelope: dict) -> bool:
    """A GoalContract is a task envelope with payload.goal."""
    if not isinstance(envelope, dict):
        return False
    payload = envelope.get("payload", {})
    if not isinstance(payload, dict):
        return False
    return "goal" in payload


def _verdict_to_str(verdict: GuardVerdict) -> str:
    """GuardVerdict enum → lowercase string for risk dict."""
    name = getattr(verdict, "name", str(verdict))
    return name.lower()


def _build_risk_dict(report: GuardReport, envelope: dict) -> dict:
    """Build risk dict per v2 hook spec: {type, verdict, original_envelope_id, details}."""
    return {
        "type": "goal_guard_risk",
        "verdict": _verdict_to_str(report.verdict),
        "original_envelope_id": envelope.get("id", ""),
        "details": getattr(report, "details", "") or "",
    }


def guard_dispatch(envelope: dict, _path: str = ".") -> Tuple[bool, Optional[dict]]:
    """v2 hook entry point for goal_guard.

    Args:
        envelope: dict with at least 'message_type' key
        _path: project root path (unused; reserved for v3 file scope checks)

    Returns:
        (allowed, risk) tuple
        - allowed: True if dispatch should proceed
        - risk: None for PASS, dict for block (type=goal_guard_risk, verdict, ...)
    """
    if not isinstance(envelope, dict):
        # Malformed envelope — fail-closed
        return (False, {
            "type": "goal_guard_risk",
            "verdict": "fatal",
            "original_envelope_id": "",
            "details": "envelope not a dict",
        })

    message_type = envelope.get("message_type", "")

    # Auto-PASS: control-plane message types
    if message_type in _AUTO_PASS_TYPES:
        return (True, None)

    # Auto-PASS: non-GoalContract envelopes (no payload.goal)
    if not _is_goal_contract(envelope):
        return (True, None)

    # GoalContract evaluation
    # R1880 round 1: GoalGuard.validate expects a GoalContract (or dict
    # with goal fields at top level). The v2 envelope nests the goal at
    # payload.goal, so extract it before passing to validate.
    payload = envelope.get("payload", {}) or {}
    goal = payload.get("goal", envelope) if isinstance(payload, dict) else envelope
    guard = GoalGuard()
    report = guard.validate(goal)
    if report.verdict == GuardVerdict.PASS:
        return (True, None)
    return (False, _build_risk_dict(report, envelope))


def write_risk_envelope(out_dir: str, risk_envelope: dict) -> "Path":
    """v2 hook: write risk envelope to disk. R1880 round 1.

    Test signature: write_risk_envelope(tmp_path, risk_env) → Path
    Writes to {out_dir}/v2/messages/risk/{original_envelope_id}.json

    Args:
        out_dir: parent directory (typically pytest tmp_path)
        risk_envelope: dict with at least 'original_envelope_id' key

    Returns:
        Path to written file
    """
    env_id = risk_envelope.get("original_envelope_id", "unknown")
    out_path = Path(out_dir) / "v2" / "messages" / "risk" / f"{env_id}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(risk_envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path
