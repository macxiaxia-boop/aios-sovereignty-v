"""requirements_lifecycle.py — Requirement lifecycle registry.

This module provides a STANDALONE registry for requirement IDs that flow
through the AIOS planning loop. It is NOT a rewrite of the existing
Task aggregate / state_machine; it is a thin attribute ledger that the
Strategy Gate reads when deciding whether a task references a retired
or completed requirement.

Lifecycle states
----------------
    PROPOSED     — submitted, not yet reviewed
    APPROVED     — reviewed and approved for activation
    ACTIVE       — currently in active use
    COMPLETED    — work finished; remains valid as a reference
    SUPERSEDED   — replaced by a newer requirement
    RETIRED      — cancelled, must not be re-activated
    REJECTED     — submitted but refused; remains visible for audit
    ARCHIVED     — moved to long-term storage; read-only reference

Valid transitions
-----------------
    PROPOSED     → APPROVED, REJECTED, RETIRED
    APPROVED     → ACTIVE, REJECTED, RETIRED
    ACTIVE       → COMPLETED, SUPERSEDED, RETIRED
    COMPLETED    → SUPERSEDED, RETIRED, ARCHIVED
    SUPERSEDED   → ARCHIVED, RETIRED
    REJECTED     → ARCHIVED
    RETIRED      → ARCHIVED          (terminal; cannot re-activate)
    ARCHIVED     → (terminal — no transitions out)
    ACTIVE_FOR_VALIDATION -> ACTIVE_LIVE, ACTIVE, COMPLETED, SUPERSEDED, RETIRED
    ACTIVE_LIVE -> COMPLETED, SUPERSEDED, RETIRED, ARCHIVED

Any other transition is rejected with `InvalidTransition`.

Storage
-------
    The registry is held in-memory by default. A small JSON persistence
    helper (`load_registry` / `save_registry`) is provided so the gate
    can be tested with a known state and audit runs can produce a
    deterministic registry snapshot.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------- Enums
class LifecycleState(str, Enum):
    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    SUPERSEDED = "SUPERSEDED"
    RETIRED = "RETIRED"
    REJECTED = "REJECTED"
    ARCHIVED = "ARCHIVED"
    ACTIVE_FOR_VALIDATION = "ACTIVE_FOR_VALIDATION"  # AIPM02 D4: maps task VALIDATED
    ACTIVE_LIVE = "ACTIVE_LIVE"  # AIPM02 D4: maps task PRODUCTION_READY


VALID_TRANSITIONS: dict[LifecycleState, frozenset[LifecycleState]] = {
    LifecycleState.PROPOSED: frozenset({
        LifecycleState.APPROVED,
        LifecycleState.REJECTED,
        LifecycleState.RETIRED,
    }),
    LifecycleState.APPROVED: frozenset({
        LifecycleState.ACTIVE,
        LifecycleState.REJECTED,
        LifecycleState.RETIRED,
    }),
    LifecycleState.ACTIVE: frozenset({
        LifecycleState.COMPLETED,
        LifecycleState.SUPERSEDED,
        LifecycleState.RETIRED,
    }),
    LifecycleState.COMPLETED: frozenset({
        LifecycleState.SUPERSEDED,
        LifecycleState.RETIRED,
        LifecycleState.ARCHIVED,
    }),
    LifecycleState.SUPERSEDED: frozenset({
        LifecycleState.ARCHIVED,
        LifecycleState.RETIRED,
    }),
    LifecycleState.REJECTED: frozenset({
        LifecycleState.ARCHIVED,
    }),
    LifecycleState.RETIRED: frozenset({
        LifecycleState.ARCHIVED,
    }),
    LifecycleState.ARCHIVED: frozenset(),  # terminal
    LifecycleState.ACTIVE_FOR_VALIDATION: frozenset({
        LifecycleState.ACTIVE_LIVE,
        LifecycleState.ACTIVE,
        LifecycleState.COMPLETED,
        LifecycleState.SUPERSEDED,
        LifecycleState.RETIRED,
    }),
    LifecycleState.ACTIVE_LIVE: frozenset({
        LifecycleState.COMPLETED,
        LifecycleState.SUPERSEDED,
        LifecycleState.RETIRED,
        LifecycleState.ARCHIVED,
    }),
}


# ---------------------------------------------------------------- Errors
class InvalidTransition(Exception):
    """Raised when a transition is not allowed from the current state."""

    def __init__(self, requirement_id: str, from_state: LifecycleState, to_state: LifecycleState):
        self.requirement_id = requirement_id
        self.from_state = from_state
        self.to_state = to_state
        super().__init__(
            f"Invalid transition for {requirement_id}: {from_state.value} -> {to_state.value}"
        )


class UnknownRequirement(Exception):
    """Raised when a requirement id is not registered."""

    def __init__(self, requirement_id: str):
        self.requirement_id = requirement_id
        super().__init__(f"Unknown requirement id: {requirement_id}")


# ---------------------------------------------------------------- Model
@dataclass
class Requirement:
    """A requirement entry in the registry."""

    requirement_id: str
    state: LifecycleState = LifecycleState.PROPOSED
    title: str = ""
    owner: str = ""
    deprecated: bool = False
    history: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["state"] = self.state.value
        d["history"] = list(self.history)
        return d


# ---------------------------------------------------------------- Registry
class RequirementsRegistry:
    """In-memory registry of requirement lifecycle states."""

    def __init__(self) -> None:
        self._items: dict[str, Requirement] = {}

    # ----- CRUD
    def register(
        self,
        requirement_id: str,
        *,
        title: str = "",
        owner: str = "",
        deprecated: bool = False,
        initial_state: LifecycleState = LifecycleState.PROPOSED,
    ) -> Requirement:
        """Add a new requirement. Idempotent on id (overwrite)."""
        now = time.time()
        req = Requirement(
            requirement_id=requirement_id,
            title=title,
            owner=owner,
            deprecated=deprecated,
            state=initial_state,
            created_at=now,
            updated_at=now,
        )
        req.history.append({
            "from": None,
            "to": initial_state.value,
            "ts": now,
            "event": "register",
        })
        self._items[requirement_id] = req
        return req

    def get(self, requirement_id: str) -> Requirement:
        if requirement_id not in self._items:
            raise UnknownRequirement(requirement_id)
        return self._items[requirement_id]

    def has(self, requirement_id: str) -> bool:
        return requirement_id in self._items

    def all_ids(self) -> list[str]:
        return sorted(self._items.keys())

    def __len__(self) -> int:
        return len(self._items)

    # ----- Transitions
    def transition(
        self,
        requirement_id: str,
        to_state: LifecycleState,
        *,
        actor: str = "",
        note: str = "",
    ) -> Requirement:
        req = self.get(requirement_id)
        allowed = VALID_TRANSITIONS[req.state]
        if to_state not in allowed:
            raise InvalidTransition(requirement_id, req.state, to_state)

        now = time.time()
        req.history.append({
            "from": req.state.value,
            "to": to_state.value,
            "ts": now,
            "actor": actor,
            "note": note,
        })
        req.state = to_state
        req.updated_at = now
        return req

    # ----- Bulk helpers
    def bulk_register_deprecated(self, ids: list[str]) -> None:
        """Register many deprecated requirements in RETIRED state."""
        for rid in ids:
            self.register(
                rid,
                title=f"Deprecated by Global Strategy Retirement Audit",
                owner="audit-2026-10-08",
                deprecated=True,
                initial_state=LifecycleState.RETIRED,
            )

    def bulk_archive_all(self) -> int:
        """Move every terminal RETIRED entry to ARCHIVED. Returns count."""
        n = 0
        for rid, req in list(self._items.items()):
            if req.state == LifecycleState.RETIRED:
                req.history.append({
                    "from": req.state.value,
                    "to": LifecycleState.ARCHIVED.value,
                    "ts": time.time(),
                    "actor": "bulk_archive_all",
                })
                req.state = LifecycleState.ARCHIVED
                n += 1
        return n

    def active_ids(self) -> list[str]:
        return sorted(r.requirement_id for r in self._items.values() if r.state == LifecycleState.ACTIVE)

    def retired_ids(self) -> list[str]:
        return sorted(r.requirement_id for r in self._items.values() if r.state == LifecycleState.RETIRED)

    def state_counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self._items.values():
            out[r.state.value] = out.get(r.state.value, 0) + 1
        return out


# ---------------------------------------------------------------- Persistence
def save_registry(registry: RequirementsRegistry, path: Path | str) -> None:
    """Write registry to JSON."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    items = {rid: req.to_dict() for rid, req in registry._items.items()}
    p.write_text(
        json.dumps({"items": items, "saved_at": time.time()}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_registry(path: Path | str) -> RequirementsRegistry:
    """Load registry from JSON. Returns empty registry if file missing."""
    p = Path(path)
    reg = RequirementsRegistry()
    if not p.exists():
        return reg
    data = json.loads(p.read_text(encoding="utf-8"))
    for rid, raw in (data.get("items") or {}).items():
        req = Requirement(
            requirement_id=rid,
            title=raw.get("title", ""),
            owner=raw.get("owner", ""),
            deprecated=bool(raw.get("deprecated", False)),
            state=LifecycleState(raw.get("state", "PROPOSED")),
        )
        req.history = list(raw.get("history") or [])
        req.created_at = float(raw.get("created_at") or time.time())
        req.updated_at = float(raw.get("updated_at") or time.time())
        reg._items[rid] = req
    return reg


__all__ = [
    "LifecycleState",
    "VALID_TRANSITIONS",
    "InvalidTransition",
    "UnknownRequirement",
    "Requirement",
    "RequirementsRegistry",
    "save_registry",
    "load_registry",
]