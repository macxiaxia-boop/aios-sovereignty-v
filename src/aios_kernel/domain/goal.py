"""goal.py - Goal aggregate root (Phase A T0030 + Phase F F001).

A Goal is the top-level unit of intent. Each Goal has success criteria,
budget, optional deadline, and an owner (agent identifier). Multiple Tasks
inside a Goal all contribute to the same success_criteria.

Status machine: Pending -> Active -> Completed | Failed | Aborted.

Phase F F001 expansion — 12-field GoalContract:
    1. stated_goal       -> existing title + description
    2. inferred_intent   -> NEW (str | None) — F002 Intent Parser fills it
    3. preserve_capabilities -> NEW (list[str])
    4. known_constraints -> NEW (list[Constraint])
    5. environment_context -> NEW (EnvSnapshot | None)
    6. success_criteria  -> existing
    7. failure_modes     -> NEW (list[FailureMode])
    8. permission_scope  -> NEW (PermissionScope | None)
    9. missing_evidence  -> NEW (list[EvidenceRequest])
   10. approved_tradeoffs -> NEW (list[Tradeoff])
   11. autonomous_scope  -> NEW (list[OpType])
   12. requires_authorization -> NEW (list[OpType])

Backward compatibility:
- SCHEMA_VERSION bumped from 1 -> 2
- All 10 new fields default to None / empty list / empty dict
- Existing 10-field construction still passes (F001 §3: 兼容性测试)
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, ClassVar, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from aios_kernel.domain.envelope import Envelope


class GoalStatus(str, Enum):
    """Lifecycle states for a Goal.

    Order reflects forward progression; reverse transitions are not allowed
    (use Aborted from any state if you need to cancel).
    """

    PENDING = "Pending"
    ACTIVE = "Active"
    COMPLETED = "Completed"
    FAILED = "Failed"
    ABORTED = "Aborted"

    @classmethod
    def terminal(cls):
        return {cls.COMPLETED, cls.FAILED, cls.ABORTED}


# Allowed forward transitions (FROM -> set of valid TO).
GOAL_TRANSITIONS: dict = {
    GoalStatus.PENDING: {GoalStatus.ACTIVE, GoalStatus.ABORTED, GoalStatus.FAILED},
    GoalStatus.ACTIVE: {GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.ABORTED},
    GoalStatus.COMPLETED: set(),
    GoalStatus.FAILED: set(),
    GoalStatus.ABORTED: set(),
}


# -----------------------------------------------------------------------
# Phase F F001 — 7 sub-models for the 12-field GoalContract.
# -----------------------------------------------------------------------

# A single, canonical list of allowed ops. Used by PermissionScope.allowed_ops.
ALLOWED_OPS: tuple[str, ...] = ("read", "write", "execute", "network", "delete")

# Canonical set of OpType.domain values.
_OP_DOMAINS: tuple[str, ...] = ("file", "network", "service", "data", "config")

# Canonical set of OpType.action values (mirrors ALLOWED_OPS but per-op type).
_OP_ACTIONS: tuple[str, ...] = ("read", "write", "execute", "delete", "modify")

# Canonical set of approved_by values for Tradeoff.
_TRADEOFF_APPROVERS: tuple[str, ...] = (
    "user",
    "codex",
    "claudecode",
    "hermes",
    "openclaw",
    "human",
)


class Constraint(BaseModel):
    """A single constraint on goal execution (budget cap, timeout, forbidden path, ...)."""

    model_config = {"extra": "forbid"}

    type: Literal["budget", "timeout", "forbidden_path", "rate_limit", "scope"]
    value: Any
    rationale: str = Field(..., min_length=1)


class EnvSnapshot(BaseModel):
    """A snapshot of the execution environment at goal creation time."""

    model_config = {"extra": "forbid"}

    cwd: str = Field(..., min_length=1)
    os: str = Field(..., min_length=1)
    available_tools: list[str] = Field(default_factory=list)
    recent_failures: list[str] = Field(default_factory=list)
    history_refs: list[str] = Field(default_factory=list)  # referenced goal_ids


class FailureMode(BaseModel):
    """A 'looks like success but isn't''' failure mode the agent must watch for.

    Phase F F000 §2 (7) — surface-success traps.
    """

    model_config = {"extra": "forbid"}

    description: str = Field(..., min_length=1)
    detection: str = Field(..., min_length=1)  # how to detect this trap
    indicator: str | None = None


class PermissionScope(BaseModel):
    """A bounded permission scope for autonomous execution."""

    model_config = {"extra": "forbid"}

    allowed_paths: list[str] = Field(default_factory=list)
    allowed_ops: list[str] = Field(default_factory=list)
    max_budget: float = Field(..., ge=0.0)
    max_duration_sec: int | None = Field(default=None, ge=0)
    requires_approval: list[str] = Field(
        default_factory=list,
        description="op types requiring explicit user authorization before execution",
    )

    @field_validator("allowed_ops", "requires_approval")
    @classmethod
    def _ops_subset(cls, value: list[str]) -> list[str]:
        for op in value:
            if op not in ALLOWED_OPS:
                raise ValueError(
                    f"op {op!r} not in allowed set {ALLOWED_OPS!r}"
                )
        return list(value)


class EvidenceRequest(BaseModel):
    """An item of missing evidence the agent must collect before claiming success."""

    model_config = {"extra": "forbid"}

    description: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)  # path/URL/tool
    required: bool = True


class Tradeoff(BaseModel):
    """A user-approved cost/benefit tradeoff.

    approved_by must be a known agent identifier or 'user'/'human'.
    """

    model_config = {"extra": "forbid"}

    decision: str = Field(..., min_length=1)
    cost: str = Field(..., min_length=1)
    benefit: str = Field(..., min_length=1)
    approved_by: str = Field(..., min_length=1)

    @field_validator("approved_by")
    @classmethod
    def _approved_by_known(cls, value: str) -> str:
        # Allow any string, but reject empty. We do not hard-restrict to a closed
        # set so custom agent names can be plugged in; the constant just
        # documents the canonical names.
        if not value.strip():
            raise ValueError("approved_by must be non-empty")
        return value


class OpType(BaseModel):
    """An operation type: (domain, action, target?) within an autonomous scope."""

    model_config = {"extra": "forbid"}

    domain: Literal["file", "network", "service", "data", "config"]
    action: Literal["read", "write", "execute", "delete", "modify"]
    target: str | None = None


# -----------------------------------------------------------------------
# Goal — the 12-field GoalContract.
# -----------------------------------------------------------------------


class Goal(Envelope):
    """A Goal represents the high-level intent of a session.

    Fields beyond the Envelope base:
    - title / description -> stated_goal (Phase F #1)
    - success_criteria: machine-checkable success statement (Phase F #6)
    - budget: spending cap in CNY (\u00a5), enforced by T0034/T0036
    - deadline: optional hard deadline (tz-aware UTC)
    - owner: agent identifier (e.g. "codex", "claudecode", "human:user")
    - status: lifecycle state (see GoalStatus)
    - tags: free-form labels for grouping
    - plan_ids: list of Plan ids attached to this goal (forward ref; T0032 ORM
      enforces FK; we keep the list denormalized for fast read).

    Phase F F001 — 7 new GoalContract sub-fields:
    - inferred_intent (str | None)        # Phase F #2
    - preserve_capabilities (list[str])   # Phase F #3
    - known_constraints (list[Constraint])  # Phase F #4
    - environment_context (EnvSnapshot | None)  # Phase F #5
    - failure_modes (list[FailureMode])   # Phase F #7
    - permission_scope (PermissionScope | None)  # Phase F #8
    - missing_evidence (list[EvidenceRequest])   # Phase F #9
    - approved_tradeoffs (list[Tradeoff])        # Phase F #10
    - autonomous_scope (list[OpType])            # Phase F #11
    - requires_authorization (list[OpType])      # Phase F #12
    """

    SCHEMA_VERSION: ClassVar[int] = 2

    # ----- existing 10 fields (preserved verbatim) -------------------------
    title: str = Field(..., min_length=1, max_length=200, description="Short goal title.")
    description: str | None = Field(
        default=None, max_length=2000, description="Longer rationale (Markdown ok)."
    )
    success_criteria: str = Field(
        ..., min_length=1, description="Machine-checkable success statement."
    )
    budget: float = Field(..., ge=0.0, description="Spending cap in CNY (\u00a5); must be >= 0.")
    deadline: datetime | None = Field(
        default=None, description="Optional hard deadline (tz-aware UTC)."
    )
    owner: str = Field(..., min_length=1, description="Agent/user identifier owning this goal.")
    status: GoalStatus = Field(default=GoalStatus.PENDING, description="Lifecycle state.")
    tags: list = Field(default_factory=list, description="Free-form labels.")
    plan_ids: list = Field(
        default_factory=list, description="Plan ids attached to this Goal (denormalized)."
    )
    metadata: dict = Field(
        default_factory=dict, description="Free-form structured metadata."
    )

    # ----- Phase F F001: 10 new fields (all default to empty / None) -------
    inferred_intent: str | None = Field(
        default=None,
        description="Inferred real intent (filled by F002 Intent Parser; optional).",
    )
    preserve_capabilities: list[str] = Field(
        default_factory=list,
        description="Asset capabilities that must NOT be destroyed (e.g. 'db:aios_kernel.db').",
    )
    known_constraints: list[Constraint] = Field(
        default_factory=list,
        description="Concrete constraints (budget caps, timeouts, forbidden paths, ...).",
    )
    environment_context: EnvSnapshot | None = Field(
        default=None,
        description="Snapshot of execution environment at goal creation.",
    )
    failure_modes: list[FailureMode] = Field(
        default_factory=list,
        description="Looks-like-success-but-isn't failure modes the agent must watch for.",
    )
    permission_scope: PermissionScope | None = Field(
        default=None,
        description="Bounded permission scope for autonomous execution.",
    )
    missing_evidence: list[EvidenceRequest] = Field(
        default_factory=list,
        description="Evidence items required to claim success.",
    )
    approved_tradeoffs: list[Tradeoff] = Field(
        default_factory=list,
        description="User-approved cost/benefit tradeoffs (metadata upgrade).",
    )
    autonomous_scope: list[OpType] = Field(
        default_factory=list,
        description="OpTypes the agent may execute without seeking authorization.",
    )
    requires_authorization: list[OpType] = Field(
        default_factory=list,
        description="OpTypes that always need explicit authorization.",
    )

    @field_validator("deadline")
    @classmethod
    def _deadline_tz(cls, value):
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("deadline must be tz-aware (use envelope.utcnow()-style)")
        return value.astimezone(UTC)

    # ----- Phase F F001: cross-field business rules -----------------------
    # These only fire when the relevant optional fields are non-empty / set,
    # so old 10-field construction (test_goal_schema.py) keeps passing.

    @model_validator(mode="after")
    def _goal_contract_rules(self):
        # (1) permission_scope.max_budget must match Goal.budget when set.
        if self.permission_scope is not None:
            if abs(self.permission_scope.max_budget - self.budget) > 1e-9:
                raise ValueError(
                    f"permission_scope.max_budget ({self.permission_scope.max_budget}) "
                    f"must match goal.budget ({self.budget})"
                )

        # (2) autonomous_scope and requires_authorization must be disjoint.
        auto_keys = {(o.domain, o.action, o.target) for o in self.autonomous_scope}
        auth_keys = {(o.domain, o.action, o.target) for o in self.requires_authorization}
        overlap = auto_keys & auth_keys
        if overlap:
            raise ValueError(
                f"autonomous_scope and requires_authorization must be disjoint; "
                f"overlap={sorted(overlap)}"
            )

        # (3) When environment_context is set, failure_modes must have >= 1 entry.
        if self.environment_context is not None and not self.failure_modes:
            raise ValueError(
                "environment_context is set, so failure_modes must list at least one mode"
            )

        # (4) When known_constraints is non-empty, environment_context must be set.
        if self.known_constraints and self.environment_context is None:
            raise ValueError(
                "known_constraints is non-empty, so environment_context must be set"
            )

        return self

    # ---------- business methods -------------------------------------------

    def can_transition_to(self, new_status):
        return new_status in GOAL_TRANSITIONS.get(self.status, set())

    def transition_to(self, new_status):
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"illegal Goal status transition: {self.status.value} -> {new_status.value}"
            )
        self.status = new_status
        self.touch()
        return self

    @property
    def is_terminal(self):
        return self.status in GoalStatus.terminal()

    def add_plan(self, plan_id):
        if plan_id not in self.plan_ids:
            self.plan_ids.append(plan_id)
            self.touch()

    def remaining_budget(self, spent):
        return max(0.0, float(self.budget) - float(spent))

    def has_full_contract(self) -> bool:
        """Phase F F005 helper. Returns True if all 12 fields are present.

        Required by F000 §2: inferred_intent | None is optional but the other
        9 non-stated_goal fields must be non-empty.
        """
        return all([
            bool(self.title),
            bool(self.success_criteria),
            bool(self.preserve_capabilities),
            bool(self.known_constraints),
            self.environment_context is not None,
            bool(self.failure_modes),
            self.permission_scope is not None,
            bool(self.missing_evidence),
            bool(self.autonomous_scope),
            bool(self.requires_authorization),
        ])


__all__ = [
    "Goal",
    "GoalStatus",
    "GOAL_TRANSITIONS",
    "Constraint",
    "EnvSnapshot",
    "FailureMode",
    "PermissionScope",
    "EvidenceRequest",
    "Tradeoff",
    "OpType",
    "ALLOWED_OPS",
]
