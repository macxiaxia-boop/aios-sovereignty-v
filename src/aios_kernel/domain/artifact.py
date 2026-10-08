"""artifact.py — Artifact (Phase A T0030 §4).

An Artifact is a concrete output produced by a worker (a file, a JSON
blob, a screenshot, etc.). Workers emit Artifacts during execution; the
Task references them by id; the Verifier hashes them to produce Evidence.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, ClassVar

from pydantic import Field, field_validator

from aios_kernel.domain.envelope import Envelope


class ArtifactType(str, Enum):
    """The 6 canonical artifact kinds (T0030 §4 schema)."""

    FILE = "file"          # file on disk, path + size + hash
    TEXT = "text"          # inline text blob
    JSON = "json"          # inline JSON document
    IMAGE = "image"        # PNG/JPG; path required
    LOG = "log"            # worker log output
    CUSTOM = "custom"      # anything else (workers may extend)


class Artifact(Envelope):
    """A piece of work output a Task produced.

    Either path (for on-disk artifacts) or inline_content (for
    in-memory payloads) should be set. hash_sha256 is the cryptographic
    fingerprint the Verifier uses to confirm the worker did not mutate
    the artifact after the fact (False Completion defence, T0030 3).
    """

    SCHEMA_VERSION: ClassVar[int] = 1

    task_id: str = Field(..., description="Owning Task id.")
    artifact_type: ArtifactType = Field(default=ArtifactType.FILE)
    path: str | None = Field(default=None, description="Filesystem path (FILE/IMAGE/LOG).")
    inline_content: str | None = Field(default=None, description="In-memory text payload.")
    inline_json: dict[str, Any] | None = Field(default=None, description="In-memory JSON payload.")
    hash_sha256: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
        description="SHA-256 of the file or inline payload (lowercase hex).",
    )
    size_bytes: int | None = Field(default=None, ge=0)
    mime_type: str | None = Field(default=None, max_length=100)
    label: str | None = Field(default=None, max_length=200)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("hash_sha256")
    @classmethod
    def _validate_hash_hex(cls, v):
        if v is None:
            return None
        if len(v) != 64:
            raise ValueError("hash_sha256 must be 64 hex characters")
        try:
            int(v, 16)
        except ValueError as exc:
            raise ValueError("hash_sha256 must be lowercase hex") from exc
        return v

    @field_validator("path")
    @classmethod
    def _no_empty_path(cls, v):
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("path cannot be empty when set")
        return v

    @property
    def has_payload(self):
        return bool(self.path or self.inline_content or self.inline_json is not None)


__all__ = ["Artifact", "ArtifactType"]
