"""canary.py - C008 Skill Canary Mechanism.

5-step canary for skill deployment:
    shadow -> 5% -> 25% -> 50% -> 100%

Auto-rollback fires on EITHER:
    - error_rate > 1% (default; configurable)
    - latency_ratio > 2.0 (avg latency / baseline; configurable)

Design contract (C008 spec):

  - `CanaryDeployment` is the per-deployment state object (Pydantic
    Envelope). Fields: id, skill_id, version, started_at, canary_pct,
    current_step, metric, status, history.

  - `CanaryMetric` is the per-step metric snapshot. baseline_latency_ms
    is the latency observed on the previous (stable) skill version.
    Each step transition RESETS the metric; baseline is preserved.

  - 5-step progression (CANARY_STEPS_ORDER):
        SHADOW (0%, observation only) ->
        PCT_5  (5%) ->
        PCT_25 (25%) ->
        PCT_50 (50%) ->
        PCT_100 (100%, promotion complete)
    "Full deploy" without going through canary is FORBIDDEN
    (C008 spec Forbidden).

  - `CanaryDeployer.deploy_start(skill_id, version, baseline_latency_ms)`
    starts a canary at SHADOW.

  - `record_call(deployment_id, success, latency_ms)` records a single
    call and immediately checks rollback thresholds. Returns the
    (possibly rolled-back) deployment.

  - `advance_step(deployment_id)` moves the deployment to the next
    step. Resets the per-step metric. Marks the deployment
    'completed' once the next step is PCT_100.

  - `get_audit_log(deployment_id=None)` returns the audit trail of
    state transitions (deploy_start, advance_step, rollback, complete)
    optionally filtered to a single deployment. Per-call records are
    NOT in the audit log; the audit log is for state transitions only.

No LLM is involved - this is a pure state machine over the 5-step
progression. In-process, in-memory storage. Persistence is out of
scope for C008 (the canary is short-lived and the audit log can be
rebuilt from the trace stream in C002 if needed).
"""
from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import ClassVar, Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope, utcnow

# Module-level logger so every state transition leaves a non-silent
# audit trail in the kernel log. Mirrors the C006 pattern.
logger = logging.getLogger("aios_kernel.learning.canary")


class CanaryStep(str, Enum):
    """The 5 steps of the canary progression (ordered, fixed)."""

    SHADOW = "shadow"
    PCT_5 = "5%"
    PCT_25 = "25%"
    PCT_50 = "50%"
    PCT_100 = "100%"


# 5-step canary progression in deployment order.
CANARY_STEPS_ORDER: list[CanaryStep] = [
    CanaryStep.SHADOW,
    CanaryStep.PCT_5,
    CanaryStep.PCT_25,
    CanaryStep.PCT_50,
    CanaryStep.PCT_100,
]

# Mapping from step to its traffic percentage.
CANARY_STEP_PCT: dict[CanaryStep, int] = {
    CanaryStep.SHADOW: 0,
    CanaryStep.PCT_5: 5,
    CanaryStep.PCT_25: 25,
    CanaryStep.PCT_50: 50,
    CanaryStep.PCT_100: 100,
}

# Default rollback thresholds (per C008 spec).
DEFAULT_ERROR_RATE_THRESHOLD: float = 0.01  # 1%
DEFAULT_LATENCY_RATIO_THRESHOLD: float = 2.0  # 2x baseline


class CanaryMetric(Envelope):
    """Per-step metric snapshot for the active canary deployment.

    The metric is reset on every step transition; baseline_latency_ms
    is preserved across transitions.

    error_rate       = error_count / total_calls  (0.0 if no calls)
    avg_latency_ms   = total_latency_ms / total_calls
    latency_ratio    = avg_latency_ms / baseline_latency_ms
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    total_calls: int = Field(
        default=0, ge=0, description="Calls observed in the current step."
    )
    error_count: int = Field(
        default=0, ge=0, description="Failed calls observed in the current step."
    )
    total_latency_ms: int = Field(
        default=0, ge=0, description="Sum of call latencies in the current step."
    )
    baseline_latency_ms: float = Field(
        default=100.0,
        gt=0.0,
        description="Avg latency (ms) on the previous stable version.",
    )

    # ---------- helpers -----------------------------------------------------

    def error_rate(self) -> float:
        """Failure rate for the current step (0.0 if no calls)."""
        if self.total_calls == 0:
            return 0.0
        return self.error_count / self.total_calls

    def avg_latency_ms(self) -> float:
        """Average latency for the current step (0.0 if no calls)."""
        if self.total_calls == 0:
            return 0.0
        return self.total_latency_ms / self.total_calls

    def latency_ratio(self) -> float:
        """avg_latency_ms / baseline_latency_ms (0.0 if baseline invalid)."""
        if self.baseline_latency_ms <= 0:
            return 0.0
        return self.avg_latency_ms() / self.baseline_latency_ms


class CanaryDeployment(Envelope):
    """A single canary deployment of a skill.

    Each deployment starts at SHADOW and advances through 5 steps until
    either PCT_100 (status=completed) or auto-rollback
    (status=rolled_back).

    Invariants:
        - canary_pct == CANARY_STEP_PCT[CanaryStep(current_step)]
        - metric is reset on every step transition (baseline preserved)
        - history is append-only and contains at least the deploy_start
          entry plus one entry per state transition
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    skill_id: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Skill identifier (matches capability_registry).",
    )
    version: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Skill version string (e.g. '1.0.0' or 'v2').",
    )
    started_at: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp when the canary was started.",
    )
    canary_pct: int = Field(
        default=0,
        ge=0,
        le=100,
        description="Current traffic percentage (matches current_step).",
    )
    current_step: str = Field(
        default=CanaryStep.SHADOW.value,
        description="Current canary step (one of CanaryStep values).",
    )
    metric: CanaryMetric = Field(
        default_factory=CanaryMetric,
        description="Per-step metric snapshot (resets on advance_step).",
    )
    status: str = Field(
        default="active",
        description="Deployment status: 'active' | 'rolled_back' | 'completed'.",
    )
    history: list[dict] = Field(
        default_factory=list,
        description="Append-only audit log of state transitions.",
    )

    # ---------- helpers -----------------------------------------------------

    def step_index(self) -> int:
        """Return the 0-based index of current_step in CANARY_STEPS_ORDER.

        Returns -1 if current_step is not a valid CanaryStep value.
        """
        try:
            return CANARY_STEPS_ORDER.index(CanaryStep(self.current_step))
        except ValueError:
            return -1

    def is_active(self) -> bool:
        return self.status == "active"

    def is_complete(self) -> bool:
        return self.status == "completed"

    def is_rolled_back(self) -> bool:
        return self.status == "rolled_back"


class CanaryDeployer:
    """Orchestrates 5-step canary deployments of skills.

    Pure state machine. No LLM, no I/O. The audit log records every
    state transition (deploy_start, advance_step, rollback, complete)
    with the deployment_id, step, reason, and timestamp.

    Auto-rollback (checked inside record_call):
        - error_rate > error_threshold (default 1%)
        - latency_ratio > latency_ratio_threshold (default 2.0)

    Once a deployment is 'rolled_back' or 'completed', record_call
    becomes a no-op and advance_step raises ValueError.
    """

    def __init__(
        self,
        *,
        error_threshold: float = DEFAULT_ERROR_RATE_THRESHOLD,
        latency_ratio_threshold: float = DEFAULT_LATENCY_RATIO_THRESHOLD,
    ) -> None:
        if not 0.0 <= error_threshold <= 1.0:
            raise ValueError("error_threshold must be in [0, 1]")
        if latency_ratio_threshold < 1.0:
            raise ValueError("latency_ratio_threshold must be >= 1.0")
        self.error_threshold = error_threshold
        self.latency_ratio_threshold = latency_ratio_threshold
        self._deployments: dict[str, CanaryDeployment] = {}
        self._audit: list[dict] = []

    # ---------- public API --------------------------------------------------

    def deploy_start(
        self,
        skill_id: str,
        version: str,
        *,
        baseline_latency_ms: float = 100.0,
    ) -> CanaryDeployment:
        """Start a canary at the SHADOW step.

        SHADOW = 0% traffic, observation only. The caller must invoke
        advance_step() to move to 5%, etc. A full deploy without going
        through the canary is FORBIDDEN (C008 spec).

        Raises ValueError on bad input.
        """
        if not skill_id or not skill_id.strip():
            raise ValueError("skill_id must be non-empty")
        if not version or not version.strip():
            raise ValueError("version must be non-empty")
        if baseline_latency_ms <= 0:
            raise ValueError("baseline_latency_ms must be > 0")

        dep = CanaryDeployment(
            skill_id=skill_id,
            version=version,
            started_at=utcnow(),
            canary_pct=CANARY_STEP_PCT[CanaryStep.SHADOW],
            current_step=CanaryStep.SHADOW.value,
            metric=CanaryMetric(baseline_latency_ms=baseline_latency_ms),
            status="active",
        )
        self._deployments[dep.id] = dep
        self._append_history(dep, "deploy_start", CanaryStep.SHADOW.value)
        logger.info(
            "canary.deploy_start id=%s skill_id=%s version=%s baseline_ms=%s",
            dep.id,
            skill_id,
            version,
            baseline_latency_ms,
        )
        return dep

    def get_deployment(self, deployment_id: str) -> Optional[CanaryDeployment]:
        """Return the deployment by id, or None if not found."""
        return self._deployments.get(deployment_id)

    def list_deployments(self) -> list[CanaryDeployment]:
        """Return all deployments (insertion order)."""
        return list(self._deployments.values())

    def record_call(
        self,
        deployment_id: str,
        success: bool,
        latency_ms: float,
    ) -> CanaryDeployment:
        """Record a single canary call and check rollback thresholds.

        Returns the (possibly rolled-back) deployment. No-op on
        already-terminal deployments (rolled_back or completed).
        Raises KeyError on unknown deployment_id.
        """
        dep = self._deployments.get(deployment_id)
        if dep is None:
            raise KeyError(f"unknown deployment_id: {deployment_id!r}")
        if dep.status != "active":
            return dep  # no-op on terminal deployment
        if latency_ms < 0:
            raise ValueError("latency_ms must be >= 0")

        dep.metric.total_calls += 1
        if not success:
            dep.metric.error_count += 1
        dep.metric.total_latency_ms += int(latency_ms)
        dep.touch()

        # Threshold check (error_rate first, then latency_ratio).
        if dep.metric.error_rate() > self.error_threshold:
            self._rollback(dep, "error_rate_exceeded")
        elif dep.metric.latency_ratio() > self.latency_ratio_threshold:
            self._rollback(dep, "latency_ratio_exceeded")
        return dep

    def advance_step(self, deployment_id: str) -> CanaryDeployment:
        """Advance the deployment to the next canary step.

        Resets the per-step metric (baseline_latency_ms preserved).
        Marks the deployment 'completed' when the next step is PCT_100.

        Raises KeyError on unknown deployment_id. Raises ValueError if
        the deployment is not 'active' (already rolled back or
        completed).
        """
        dep = self._deployments.get(deployment_id)
        if dep is None:
            raise KeyError(f"unknown deployment_id: {deployment_id!r}")
        if dep.status != "active":
            raise ValueError(
                f"cannot advance_step: deployment is {dep.status!r} "
                f"(deployment_id={deployment_id})"
            )

        idx = dep.step_index()
        if idx < 0:
            raise ValueError(f"invalid current_step: {dep.current_step!r}")

        # Already at PCT_100: mark completed (idempotent guard).
        if idx >= len(CANARY_STEPS_ORDER) - 1:
            dep.status = "completed"
            self._append_history(dep, "complete", dep.current_step)
            logger.info("canary.complete id=%s (already at 100%%)", dep.id)
            return dep

        next_step = CANARY_STEPS_ORDER[idx + 1]
        # Reset per-step metric; keep baseline.
        dep.metric = CanaryMetric(baseline_latency_ms=dep.metric.baseline_latency_ms)
        dep.current_step = next_step.value
        dep.canary_pct = CANARY_STEP_PCT[next_step]
        dep.touch()
        self._append_history(dep, "advance_step", next_step.value)
        logger.info(
            "canary.advance_step id=%s step=%s pct=%s",
            dep.id,
            next_step.value,
            dep.canary_pct,
        )

        if next_step == CanaryStep.PCT_100:
            dep.status = "completed"
            self._append_history(dep, "complete", next_step.value)
            logger.info("canary.complete id=%s", dep.id)
        return dep

    def get_audit_log(
        self,
        deployment_id: Optional[str] = None,
    ) -> list[dict]:
        """Return the global audit log, optionally filtered to one deployment.

        The audit log contains only STATE TRANSITIONS, not per-call
        records. Each entry has: deployment_id, action, step, reason,
        timestamp, skill_id, version.
        """
        if deployment_id is None:
            return list(self._audit)
        return [e for e in self._audit if e.get("deployment_id") == deployment_id]

    # ---------- internals ---------------------------------------------------

    def _rollback(self, dep: CanaryDeployment, reason: str) -> None:
        dep.status = "rolled_back"
        dep.touch()
        self._append_history(dep, "rollback", dep.current_step, reason=reason)
        logger.warning(
            "canary.rollback id=%s step=%s reason=%s",
            dep.id,
            dep.current_step,
            reason,
        )

    def _append_history(
        self,
        dep: CanaryDeployment,
        action: str,
        step: str,
        *,
        reason: Optional[str] = None,
    ) -> None:
        entry = {
            "deployment_id": dep.id,
            "action": action,
            "step": step,
            "reason": reason,
            "timestamp": utcnow().isoformat(),
            "skill_id": dep.skill_id,
            "version": dep.version,
        }
        dep.history.append(entry)
        self._audit.append(entry)


__all__ = [
    "CanaryStep",
    "CANARY_STEPS_ORDER",
    "CANARY_STEP_PCT",
    "DEFAULT_ERROR_RATE_THRESHOLD",
    "DEFAULT_LATENCY_RATIO_THRESHOLD",
    "CanaryMetric",
    "CanaryDeployment",
    "CanaryDeployer",
]


