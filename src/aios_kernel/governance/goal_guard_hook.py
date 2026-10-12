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
    Returns HookResult(ALLOW) by default. If any registered hook matches the
    event's type and returns Block=1, returns HookResult(BLOCK).
    """
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
