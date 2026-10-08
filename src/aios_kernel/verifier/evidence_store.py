"""evidence_store.py - EvidenceStore (T0035 §Scope 4).

Two implementations of the same Protocol:
- InMemoryEvidenceStore: dict-backed; used in tests
- SqlAlchemyEvidenceStore: reads from the kernel's `evidences` + `artifacts`
  tables; this is what the production Verifier uses

The Verifier process never writes to this store (it only reads). Writes
go through the Kernel's normal SqlAlchemyRepository path (T0032). This
is the "Verifier independent" boundary: even if the Verifier is
compromised, it cannot forge evidence.
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

log = logging.getLogger("aios_kernel.verifier.evidence_store")

# ---------- Value objects ---------------------------------------------------


@dataclass(frozen=True)
class EvidenceRecord:
    """A read-only projection of the `evidences` table.

    Kept as a plain dataclass (not the Pydantic Evidence from domain/) so
    the Verifier process doesn't have to import the kernel's Pydantic
    models — the whole point of process isolation.
    """

    evidence_id: str
    task_id: str
    verifier_id: str
    verdict: str
    artifact_ids: list[str]
    evidence_hash: str | None
    details: dict[str, Any]
    signed_at: datetime


@dataclass(frozen=True)
class ArtifactRecord:
    """A read-only projection of the `artifacts` table."""

    artifact_id: str
    task_id: str
    artifact_type: str
    path: str | None
    inline_content: str | None
    inline_json: dict[str, Any] | None
    hash_sha256: str | None
    size_bytes: int | None


# ---------- Protocol --------------------------------------------------------


@runtime_checkable
class EvidenceStore(Protocol):
    """Abstract interface the Verifier uses to look up evidence + artifacts.

    Three operations:
      - get_evidence(id) -> EvidenceRecord | None
      - list_evidence_for_task(task_id) -> list[EvidenceRecord]
      - get_artifact(id) -> ArtifactRecord | None
    """

    def get_evidence(self, evidence_id: str) -> EvidenceRecord | None: ...

    def list_evidence_for_task(self, task_id: str) -> list[EvidenceRecord]: ...

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None: ...


# ---------- In-memory implementation (tests) --------------------------------


class InMemoryEvidenceStore:
    """Dict-backed store. Pure-Python, no I/O, used in unit/integration tests."""

    def __init__(self) -> None:
        self._evidence: dict[str, EvidenceRecord] = {}
        self._artifacts: dict[str, ArtifactRecord] = {}

    # write API (used by tests to seed)
    def put_evidence(self, record: EvidenceRecord) -> None:
        self._evidence[record.evidence_id] = record

    def put_artifact(self, record: ArtifactRecord) -> None:
        self._artifacts[record.artifact_id] = record

    # read API (Protocol)
    def get_evidence(self, evidence_id: str) -> EvidenceRecord | None:
        return self._evidence.get(evidence_id)

    def list_evidence_for_task(self, task_id: str) -> list[EvidenceRecord]:
        return [r for r in self._evidence.values() if r.task_id == task_id]

    def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        return self._artifacts.get(artifact_id)


# ---------- SQLAlchemy implementation (production) --------------------------


class SqlAlchemyEvidenceStore:
    """Reads the kernel's `evidences` + `artifacts` tables over a DB URL.

    The Verifier process opens its own connection (no shared session with
    the Kernel). Reads only — the Verifier has no write path to the DB.

    The Verifier does NOT need to know the table names in detail; we keep
    the column names as constants so a future schema change is one place.
    """

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._engine = None  # lazy-init on first call

    def _ensure_engine(self):
        if self._engine is None:
            # Lazy import so the Verifier process doesn't pull SQLAlchemy
            # at module load if it never queries the DB (e.g. health-only).
            from sqlalchemy.ext.asyncio import create_async_engine

            self._engine = create_async_engine(self._database_url, future=True)
        return self._engine

    async def get_evidence(self, evidence_id: str) -> EvidenceRecord | None:
        from sqlalchemy import select

        from aios_kernel.persistence.models import EvidenceORM

        eng = self._ensure_engine()
        async with eng.connect() as conn:
            stmt = select(EvidenceORM).where(EvidenceORM.id == evidence_id)
            row = (await conn.execute(stmt)).first()
        if row is None:
            return None
        orm = row[0]
        return _orm_to_evidence_record(orm)

    async def list_evidence_for_task(self, task_id: str) -> list[EvidenceRecord]:
        from sqlalchemy import select

        from aios_kernel.persistence.models import EvidenceORM

        eng = self._ensure_engine()
        async with eng.connect() as conn:
            stmt = select(EvidenceORM).where(EvidenceORM.task_id == task_id)
            rows = (await conn.execute(stmt)).all()
        return [_orm_to_evidence_record(r[0]) for r in rows]

    async def get_artifact(self, artifact_id: str) -> ArtifactRecord | None:
        from sqlalchemy import select

        from aios_kernel.persistence.models import ArtifactORM

        eng = self._ensure_engine()
        async with eng.connect() as conn:
            stmt = select(ArtifactORM).where(ArtifactORM.id == artifact_id)
            row = (await conn.execute(stmt)).first()
        if row is None:
            return None
        orm = row[0]
        return _orm_to_artifact_record(orm)


# ---------- ORM -> Record projection helpers --------------------------------


def _orm_to_evidence_record(orm) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=orm.id,
        task_id=orm.task_id,
        verifier_id=orm.verifier_id,
        verdict=orm.verdict,
        artifact_ids=list(orm.artifact_ids or []),
        evidence_hash=orm.evidence_hash,
        details=dict(orm.details or {}),
        signed_at=orm.signed_at,
    )


def _orm_to_artifact_record(orm) -> ArtifactRecord:
    return ArtifactRecord(
        artifact_id=orm.id,
        task_id=orm.task_id,
        artifact_type=orm.artifact_type,
        path=orm.path,
        inline_content=orm.inline_content,
        inline_json=dict(orm.inline_json) if orm.inline_json is not None else None,
        hash_sha256=orm.hash_sha256,
        size_bytes=orm.size_bytes,
    )


# ---------- File-system hash helper -----------------------------------------


def compute_file_sha256(path: str) -> str:
    """SHA-256 of a file's content, lowercase hex, 64 chars.

    Used by the deterministic verifier to check that the artifact the
    worker claims to have produced actually exists on disk and matches
    the recorded hash. Raises FileNotFoundError if the path is missing.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def artifact_record_payload_exists(artifact: ArtifactRecord) -> bool:
    """True if the artifact's payload can be located.

    - path: file must exist on disk and be non-empty
    - inline_content: must be a non-empty string
    - inline_json: must be a non-None dict
    - none of the above: False
    """
    if artifact.path:
        return os.path.isfile(artifact.path) and os.path.getsize(artifact.path) > 0
    if artifact.inline_content:
        return len(artifact.inline_content) > 0
    if artifact.inline_json is not None:
        return True
    return False


__all__ = [
    "EvidenceRecord",
    "ArtifactRecord",
    "EvidenceStore",
    "InMemoryEvidenceStore",
    "SqlAlchemyEvidenceStore",
    "compute_file_sha256",
    "artifact_record_payload_exists",
]
