"""mock_evidence.py - In-memory evidence store with hash-verification support.

Goals:
- Replace a Postgres-backed evidence table during simulation
- Provide deterministic verify(hash) for verifier to sign PASS/FAIL
- Support intentional pollution: a record can be marked tainted; verify() then
  reports mismatch (used by T0036 False Completion + T0037 crash-recovery tests)

API:
- put(evidence) -> evidence_id
- get(evidence_id) -> evidence dict or None
- verify(evidence_id) -> bool       # hash matches, not tainted
- tamper(evidence_id) -> None       # mark as tainted (test fault injection)
- all() -> iterable for inspection
"""
from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional


@dataclass
class EvidenceRecord:
    id: str
    task_id: str
    artifact_id: Optional[str]
    payload: str
    verifier_id: str = "verifier-mock-001"
    signed_at: str = "1970-01-01T00:00:00Z"
    verdict: str = "PENDING"  # PENDING | PASS | FAIL | BLOCKED

    def compute_hash(self) -> str:
        h = hashlib.sha256()
        h.update(self.id.encode("utf-8"))
        h.update(b"\x00")
        h.update((self.task_id or "").encode("utf-8"))
        h.update(b"\x00")
        h.update((self.artifact_id or "").encode("utf-8"))
        h.update(b"\x00")
        h.update(self.payload.encode("utf-8"))
        return h.hexdigest()


@dataclass
class _TaintedReason:
    code: str
    detail: str


class MockEvidenceStore:
    """Thread-safe in-memory evidence store."""

    def __init__(self) -> None:
        self._records: Dict[str, EvidenceRecord] = {}
        self._hashes: Dict[str, str] = {}     # id -> recorded hash (snapshot at put time)
        self._tainted: Dict[str, _TaintedReason] = {}
        self._lock = threading.Lock()

    # ---- write side -------------------------------------------------------

    def put(self, evidence: EvidenceRecord) -> str:
        with self._lock:
            if not evidence.id:
                raise ValueError("EvidenceRecord.id required")
            self._records[evidence.id] = evidence
            self._hashes[evidence.id] = evidence.compute_hash()
        return evidence.id

    def tamper(self, evidence_id: str, code: str = "HASH_MISMATCH", detail: str = "") -> None:
        """Mark a stored evidence as tainted — verify() will then return False."""
        with self._lock:
            if evidence_id not in self._records:
                raise KeyError(evidence_id)
            self._tainted[evidence_id] = _TaintedReason(code=code, detail=detail)

    # ---- read side --------------------------------------------------------

    def get(self, evidence_id: str) -> Optional[EvidenceRecord]:
        with self._lock:
            rec = self._records.get(evidence_id)
            if rec is None:
                return None
            return EvidenceRecord(
                id=rec.id,
                task_id=rec.task_id,
                artifact_id=rec.artifact_id,
                payload=rec.payload,
                verifier_id=rec.verifier_id,
                signed_at=rec.signed_at,
                verdict=rec.verdict,
            )

    def verify(self, evidence_id: str) -> bool:
        """True iff the record's current hash matches the snapshot AND it has not been
        intentionally tainted via tamper()."""
        with self._lock:
            rec = self._records.get(evidence_id)
            if rec is None:
                return False
            if evidence_id in self._tainted:
                return False
            return rec.compute_hash() == self._hashes.get(evidence_id, "")

    def all(self) -> List[EvidenceRecord]:
        with self._lock:
            return [self.get(k) for k in sorted(self._records)]  # type: ignore[misc]

    def __len__(self) -> int:
        return len(self._records)

    def __iter__(self) -> Iterator[EvidenceRecord]:
        return iter(self.all())


# ---------- Verifier helper ---------------------------------------------------


def verify_worker_evidence(
    store: MockEvidenceStore,
    evidence_ids: List[str],
    require_non_empty: bool = True,
) -> Dict[str, Any]:
    """Simulated verifier verdict. PASS iff:
      - all IDs exist
      - require_non_empty → evidence_ids list not empty
      - verify(eid) returns True for every id (no tampering, hash matches)
    """
    if require_non_empty and not evidence_ids:
        return {"verdict": "FAIL", "reason": "evidence_ids_empty"}
    for eid in evidence_ids:
        rec = store.get(eid)
        if rec is None:
            return {"verdict": "FAIL", "reason": f"missing:{eid}"}
        if not store.verify(eid):
            return {"verdict": "FAIL", "reason": f"tampered_or_mismatch:{eid}"}
    return {"verdict": "PASS", "reason": "all_verified"}


if __name__ == "__main__":
    s = MockEvidenceStore()
    r = EvidenceRecord(
        id="ev-1",
        task_id="task-x",
        artifact_id="art-x",
        payload="hello",
        signed_at="2026-05-01T00:00:00Z",
    )
    s.put(r)
    assert s.verify("ev-1")
    s.tamper("ev-1")
    assert not s.verify("ev-1")
    out = verify_worker_evidence(s, ["ev-1"])
    assert out["verdict"] == "FAIL"
    empty = verify_worker_evidence(s, [], require_non_empty=True)
    assert empty["verdict"] == "FAIL" and empty["reason"] == "evidence_ids_empty"
    print("OK: mock_evidence store + tamper + verifier all work")