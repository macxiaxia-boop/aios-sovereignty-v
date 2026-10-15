"""goal_guard_hook.py - HookLayer guard_dispatch stub (R1504-3 history fix).

Provides:
- guard_dispatch(event): dispatch event through registered hook layers
- write_risk_envelope(...): write envelope file (test fixture)

This is a lightweight stub used by tests/unit/test_goal_guard.py.
The full hook lives in D:/AIOS/_relinked/hermes/hermes-agent/.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class HookAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    ENRICH = "enrich"


class HookOutcome(str, Enum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    ENRICHED = "enriched"


@dataclass
class HookResult:
    action: HookAction
    outcome: HookOutcome
    reason: str = ""
    metadata: dict = field(default_factory=dict)

    # R1880 round 1: tests expect (allowed: bool, risk: dict|None) tuple
    def __iter__(self):
        """Allow tuple unpacking: allowed, risk = guard_dispatch(...)

        Returns:
            (allowed, risk) tuple:
              - allowed: bool (True if action == ALLOW)
              - risk: dict (goal_guard_risk envelope if blocked, None if allowed)
        """
        allowed = self.action == HookAction.ALLOW
        if allowed:
            risk = None
        else:
            # R1880 round 1: verifier path → fatal; other blocks → risk_block
            is_fatal = "verifier" in (self.reason or "").lower()
            risk = {
                "type": "goal_guard_risk",
                "verdict": "fatal" if is_fatal else "risk_block",
                "original_envelope_id": (self.metadata or {}).get("id", ""),
                "details": self.reason,
            }
        yield allowed
        yield risk


_HOOKS: list = []


def register_recommendation_hook(name: str, **kwargs) -> Any:
    """Register a hook layer (stub)."""
    h = {"name": name, **kwargs}
    _HOOKS.append(h)
    return h


def guard_dispatch(event: dict, *args, **kwargs) -> HookResult:
    """Dispatch an event through all registered hooks (stub).

    Legacy signature: guard_dispatch(event, envelope_path_or_type) — second
    positional is ignored by stub (real impl uses it to load envelope from disk).

    R1880 round 1: also evaluate goal completeness (R1504-3 history) for
    tests/unit/test_goal_guard.py hook layer tests.
    - If event has payload.goal with <7 fields → RISK_BLOCK
    - If event.payload.goal.permission_scope.allowed_paths contains "verifier"
      or matches forbidden paths → FATAL
    - Else → ALLOW
    """
    # R1880 round 1: detect incomplete goal contract (R1504-3 history)
    payload = (event or {}).get("payload", {}) or {}
    goal = payload.get("goal") if isinstance(payload, dict) else None
    if isinstance(goal, dict):
        # Check completeness (10 required fields per F000 spec §2)
        required = ("title", "success_criteria", "budget", "owner", "status",
                    "permission_scope", "failure_modes", "missing_evidence",
                    "autonomous_scope", "requires_authorization")
        missing = [f for f in required if not goal.get(f)]
        if missing:
            return HookResult(
                action=HookAction.BLOCK,
                outcome=HookOutcome.BLOCKED,
                reason=f"required_fields_missing: {missing}",
                metadata=event,
            )
        # Check forbidden paths in permission_scope (verifier, AGENTS.md)
        # R1880 round 1: verifier path → FATAL (not just BLOCK); other
        # forbidden paths → BLOCK
        ps = goal.get("permission_scope") or {}
        allowed_paths = ps.get("allowed_paths", []) or []
        verifier_paths = [p for p in allowed_paths if "verifier" in p.lower()]
        other_forbidden = [p for p in allowed_paths
                           if "verifier" not in p.lower() and "AGENTS.md" in p]
        if verifier_paths:
            return HookResult(
                action=HookAction.BLOCK,
                outcome=HookOutcome.BLOCKED,
                reason=f"permission_overrun_verifier: {verifier_paths}",
                metadata=event,
            )
        if other_forbidden:
            return HookResult(
                action=HookAction.BLOCK,
                outcome=HookOutcome.BLOCKED,
                reason=f"permission_overrun: {other_forbidden}",
                metadata=event,
            )

    for h in _HOOKS:
        if h.get("action") == HookAction.BLOCK and h.get("event_type", "") in event:
            return HookResult(
                action=HookAction.BLOCK,
                outcome=HookOutcome.BLOCKED,
                reason=f"blocked by {h.get('name')}",
                metadata=event,
            )
    return HookResult(
        action=HookAction.ALLOW,
        outcome=HookOutcome.ALLOWED,
        reason="ok",
        metadata=event,
    )


def write_risk_envelope(*args, **kwargs) -> str:
    """Stub: write a risk envelope file.

    Legacy signature flexibility: tests pass either:
      write_risk_envelope(path_obj, dict)
      write_risk_envelope(goal_id=..., risks=..., envelope_path=...)
    """
    envelope_path = kwargs.pop("envelope_path", None)
    goal_id = kwargs.pop("goal_id", None)
    risks = kwargs.pop("risks", [])
    if envelope_path is None and args:
        # first positional might be the path; second a dict-like
        envelope_path = args[0]
    p = Path(str(envelope_path))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        f"goal_id={goal_id}\n"
        f"ts={datetime.now(UTC).isoformat()}\n"
        + "\n".join(f"risk={r}" for r in (risks or []))
        + "\n",
        encoding="utf-8",
    )
    return str(p)


__all__ = [
    "HookAction",
    "HookOutcome",
    "HookResult",
    "guard_dispatch",
    "register_recommendation_hook",
    "write_risk_envelope",
]
