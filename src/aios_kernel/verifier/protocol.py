"""protocol.py - Verifier Protocol + Verdict Pydantic model (T0035).

Per spec §97.7 "Worker execution must not self-verify" + §104.10
"Verifier independent": the Verifier is a separate process with its own
PID, listening on its own port. The Kernel dispatches verify requests
over HTTP, never in-process.

Public surface:
- Verifier: structural Protocol any verifier implementation must satisfy
- Verdict: Pydantic response model (task_id, verifier_id, PASS/FAIL/BLOCKED, details, signed_at)
- HealthReport: verifier-side health snapshot (mirrors workers/base.py HealthReport)
- VerifyRequest: inbound payload schema
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, ClassVar, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

# ---------- Verdict codes ----------------------------------------------------


class VerdictCode(str, Enum):
    """Verifier outcome codes (T0035 §3).

    - PASS: all 6 deterministic rules satisfied
    - FAIL: at least one rule failed (worker output is rejected)
    - BLOCKED: verifier could not reach a conclusion (partial evidence, exception)
    """

    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


# ---------- Inbound / outbound schemas --------------------------------------


class VerifyRequest(BaseModel):
    """Inbound payload to POST /verify.

    task: minimal task projection (id, evidence_ids, artifact_ids, success_criteria,
          cost_yuan, budget_yuan).  We accept a plain dict so the Verifier never
          has to import the kernel's Pydantic models (process isolation).
    """

    model_config = ConfigDict(extra="forbid")

    task: dict[str, Any] = Field(
        ..., description="Task projection: id, evidence_ids, artifact_ids, success_criteria, cost_yuan, budget_yuan."
    )
    verifier_id: str | None = Field(
        default=None, description="Optional explicit verifier id; defaults to VERIFIER_ID env or 'deterministic-verifier'."
    )


class HealthReport(BaseModel):
    """Verifier-side health snapshot for GET /health.

    Independent from workers/base.py HealthReport so the two process classes
    don't share a Pydantic model (process isolation is the whole point).
    """

    model_config = ConfigDict(extra="forbid")

    verifier_id: str
    status: str = Field(default="healthy", description="healthy | degraded | unhealthy")
    pid: int = Field(..., description="OS process id of the Verifier (used to prove process isolation).")
    started_at: datetime = Field(..., description="UTC tz-aware timestamp when this Verifier process started.")
    uptime_seconds: float = Field(default=0.0, ge=0.0)
    rules_loaded: list[str] = Field(
        default_factory=list, description="Names of the deterministic rules the Verifier currently runs."
    )
    message: str = ""


class Verdict(BaseModel):
    """Outbound payload from /verify.

    T0035 §Scope 1 contract:
        task_id: str
        verifier_id: str
        verdict: Literal["PASS", "FAIL", "BLOCKED"]
        reason: str
        details: Dict[str, Any]
        signed_at: datetime
    """

    model_config = ConfigDict(extra="forbid")

    SCHEMA_VERSION: ClassVar[int] = 1

    task_id: str = Field(..., min_length=1)
    verifier_id: str = Field(..., min_length=1)
    verdict: VerdictCode = Field(default=VerdictCode.BLOCKED)
    reason: str = Field(default="", description="Short human-readable verdict rationale.")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Per-rule findings: {rule_name: {ok: bool, message: str, ...}}.",
    )
    signed_at: datetime = Field(..., description="UTC tz-aware timestamp the Verifier signed the verdict.")
    cost_yuan: float = Field(default=0.0, ge=0.0, description="Verifier compute cost in CNY (¥).")
    error: str | None = Field(default=None, description="Verifier-side error if verdict=BLOCKED.")


# ---------- Protocol --------------------------------------------------------


@runtime_checkable
class Verifier(Protocol):
    """Structural protocol for a Verifier implementation.

    Any concrete verifier (DeterministicVerifier today; future LLM-backed,
    human-in-the-loop, etc.) MUST satisfy this surface. The Kernel talks
    to the Verifier via these two methods plus a /health endpoint.
    """

    verifier_id: str

    async def verify(self, task: dict[str, Any], evidence_ids: list[str]) -> Verdict:
        """Inspect task + evidence and return a verdict.

        Args:
            task: minimal task projection (id, evidence_ids, artifact_ids, success_criteria,
                  cost_yuan, budget_yuan).  Plain dict (no Pydantic coupling).
            evidence_ids: the evidence ids the worker claims to have produced.

        Returns:
            Verdict with one of PASS / FAIL / BLOCKED. The Verifier MUST NOT
            silently swallow errors; any internal exception must surface as
            verdict=BLOCKED with error set.
        """
        ...

    async def health(self) -> HealthReport:
        """Return a HealthReport describing this Verifier's process state."""
        ...


__all__ = [
    "VerdictCode",
    "VerifyRequest",
    "HealthReport",
    "Verdict",
    "Verifier",
]
