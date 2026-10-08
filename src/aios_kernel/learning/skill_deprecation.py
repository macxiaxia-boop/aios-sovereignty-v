"""skill_deprecation.py - C007 Skill Deprecation."""
from __future__ import annotations
import uuid
from datetime import UTC, datetime, timedelta
from typing import Optional

from pydantic import Field

from aios_kernel.domain.envelope import Envelope, utcnow
from aios_kernel.learning.skill_usage import SkillUsage


class Deprecation(Envelope):
    """Record of a skill being marked for deprecation."""
    skill_id: str
    unused_days: int = 0
    last_used_at: Optional[datetime] = None
    reason: str = ""
    deprecated_at: Optional[datetime] = None
    audit_log: list[str] = Field(default_factory=list)


class SkillDeprecationDetector:
    """Detect skills that should be deprecated based on usage."""

    def __init__(self):
        self._deprecations: list[Deprecation] = []

    def detect_deprecated(
        self,
        skill_usage_map: dict[str, SkillUsage],
        unused_days: int = 30,
        now: datetime = None,
    ) -> list[Deprecation]:
        """Detect skills with no recent usage."""
        now = now or utcnow()
        threshold = now - timedelta(days=unused_days)
        new_deprecations = []
        for skill_id, usage in skill_usage_map.items():
            if usage.last_used_at is None or usage.last_used_at < threshold:
                dep = Deprecation(
                    id=str(uuid.uuid4()),
                    skill_id=skill_id,
                    unused_days=unused_days,
                    last_used_at=usage.last_used_at,
                    reason=f"No usage in last {unused_days} days",
                    deprecated_at=now,
                    audit_log=[
                        f"detected at {now.isoformat()}",
                        f"last_used_at={usage.last_used_at.isoformat() if usage.last_used_at else 'never'}",
                        f"threshold={threshold.isoformat()}",
                    ],
                )
                new_deprecations.append(dep)
                self._deprecations.append(dep)
        return new_deprecations


__all__ = ["Deprecation", "SkillDeprecationDetector"]
