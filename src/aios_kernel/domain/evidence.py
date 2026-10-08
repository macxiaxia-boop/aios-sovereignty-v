"""evidence.py — Evidence + Verdict (Phase A T0030 §4 + §6).

Evidence is the **signed record** a Verifier emits after independently
inspecting the worker's output. A Task may only transition to Done
when at least one Evidence row with verdict == PASS is attached
(enforced by T0035 Verifier service).
"""
from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, ClassVar

from pydantic import Field, field_validator

from aios_kernel.domain.envelope import Envelope, utcnow


class Verdict(str, Enum):
    """Verifier outcome codes (T0030 §6).

    - PASS: worker output independently reproducible
    - FAIL: worker output did not match criteria
    - BLOCKED: verifier could not reach a conclusion (e.g. timeout)
    """

    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


class Evidence(Envelope):
    """A signed evidence record produced by the Verifier.

    Carries:
    - the worker artifact ids the verifier inspected
    - the verifier's identity (verifier_id) — must be a separate process
      (T0030 §3 不可接受: Verifier 与 Worker 同进程)
    - the verdict and structured details
    - an optional tamper-evident hash (T0036 False Completion defence)
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    task_id: str = Field(..., description="Task the evidence is for.")
    artifact_ids: list[str] = Field(
        default_factory=list, description="Artifact ids the Verifier inspected."
    )
    verifier_id: str = Field(..., min_length=1, description="Verifier process/agent id.")
    verdict: Verdict = Field(default=Verdict.BLOCKED)
    details: dict[str, Any] = Field(
        default_factory=dict, description="Structured findings (test output, hashes, etc.)."
    )
    signed_at: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp the Verifier signed the record (tz-aware).",
    )
    recheck_required: bool = Field(
        default=False, description="Set if Verifier needs worker to redo with corrections."
    )
    cost_yuan: float = Field(default=0.0, ge=0.0, description="Verifier compute cost in CNY (¥).")
    error: str | None = Field(default=None, description="Verifier-side error if BLOCKED.")
    evidence_hash: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        description="SHA-256 of (task_id || artifact_ids || verdict || details) — tamper detection.",
    )
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("signed_at")
    @classmethod
    def _tz(cls, v):
        if v.tzinfo is None:
            raise ValueError("signed_at must be tz-aware")
        return v.astimezone(UTC)

    @field_validator("evidence_hash")
    @classmethod
    def _hash_hex(cls, v):
        if v is None:
            return None
        if len(v) != 64:
            raise ValueError("evidence_hash must be 64 hex characters")
        try:
            int(v, 16)
        except ValueError as exc:
            raise ValueError("evidence_hash must be lowercase hex") from exc
        return v

    @property
    def is_pass(self):
        return self.verdict == Verdict.PASS

    @property
    def is_fail(self):
        return self.verdict == Verdict.FAIL


__all__ = ["Evidence", "Verdict"]
