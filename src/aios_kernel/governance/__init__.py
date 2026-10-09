"""aios_kernel.governance — Cognitive governance plane (Phase F).

F005: GoalGuard Hook.  v2 consumer invokes GoalGuard.validate()
before dispatching any envelope.  GoalGuard enforces the 12-field
GoalContract defined in F000 spec §2.

Submodules:
- goal_guard: GoalGuard + GuardVerdict + GuardReport + 5 type checks
                + make_risk_envelope factory.

Backwards compatibility: importing this package does NOT touch the
existing Goal / Plan / Task / Trace / Evidence domain models.  GoalGuard
accepts either a real Goal, a GoalContract-shaped object (duck typing
via getattr), or a dict — so F001's eventual GoalContract extension can
plug in without breaking this hook.
"""
from __future__ import annotations

from .goal_guard import (
    GoalContract,
    GoalGuard,
    GuardReport,
    GuardVerdict,
    make_risk_envelope,
)

__all__ = [
    "GoalContract",
    "GoalGuard",
    "GuardReport",
    "GuardVerdict",
    "make_risk_envelope",
]