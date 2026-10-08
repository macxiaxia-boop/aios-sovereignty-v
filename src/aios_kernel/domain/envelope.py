"""envelope.py — Base model shared by all AIOS Kernel domain entities.

Provides:
- Envelope (Pydantic BaseModel) with id (UUID), created_at, updated_at, schema_version
- utcnow() helper (always tz-aware UTC, replaces naive datetime.now())
- JSON-Schema export helpers used by API/SDKs (T0035+)

All Pydantic models in the kernel inherit from Envelope so the 4 fields
(id/created_at/updated_at/schema_version) are consistent across Goal/Task/
Plan/Artifact/Evidence/Trace.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import ClassVar
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


def utcnow():
    """Return current UTC time, always tz-aware.

    Replaces datetime.now() (naive) — the kernel MUST use tz-aware UTC
    everywhere (spec §3: 不可接受 = naive datetimes).
    """
    return datetime.now(UTC)


class Envelope(BaseModel):
    """Base for every persisted domain entity.

    Provides:
    - id: stable UUID4 primary key (string form to keep JSON/JSONB portable)
    - created_at: tz-aware UTC, set once at construction
    - updated_at: tz-aware UTC, refreshed on every Pydantic re-validation
    - schema_version: int bumped on backward-incompatible model changes

    Subclasses get free JSON-Schema export via model_json_schema().
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,  # re-run validators on attribute set
        ser_json_timedelta="iso8601",
    )

    # Subclasses override this; bumped on breaking schema changes
    SCHEMA_VERSION: ClassVar[int] = 1

    id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Stable UUID4 identifier (string form, portable across JSON/JSONB).",
    )
    created_at: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp when the entity was first persisted (tz-aware).",
    )
    updated_at: datetime = Field(
        default_factory=utcnow,
        description="UTC timestamp when the entity was last mutated (tz-aware).",
    )
    schema_version: int = Field(
        default=1,
        ge=1,
        description="Envelope schema version; bump on breaking changes.",
    )

    # ---------- validators --------------------------------------------------

    @field_validator("id")
    @classmethod
    def _validate_id(cls, value):
        try:
            UUID(value)
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError(f"id must be a valid UUID, got {value!r}") from exc
        return value

    @field_validator("created_at", "updated_at")
    @classmethod
    def _ensure_tz_aware(cls, value):
        if value.tzinfo is None:
            raise ValueError(
                "datetime must be tz-aware (use datetime.now(UTC) or aios_kernel.domain.envelope.utcnow())"
            )
        return value.astimezone(UTC)

    # ---------- serializers -------------------------------------------------

    @field_serializer("created_at", "updated_at")
    def _serialize_dt(self, value):
        return value.astimezone(UTC).isoformat()

    # ---------- helpers -----------------------------------------------------

    def touch(self):
        """Refresh updated_at to now. Call this after mutation logic."""
        self.updated_at = utcnow()

    def export_json_schema(self):
        """Return the Pydantic-generated JSON Schema (T0035 API uses this)."""
        return self.model_json_schema()

    def __eq__(self, other):
        if not isinstance(other, Envelope):
            return NotImplemented
        return self.id == other.id


__all__ = ["Envelope", "utcnow"]
