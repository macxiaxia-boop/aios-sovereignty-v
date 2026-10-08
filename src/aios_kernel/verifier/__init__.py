"""aios_kernel.verifier - T0035 Verifier independent process.

Public surface:

- Verifier (Protocol)            - structural verifier interface
- Verdict (Pydantic)             - response model (PASS / FAIL / BLOCKED)
- HealthReport (Pydantic)        - /health response
- VerifyRequest (Pydantic)       - /verify request body
- DeterministicVerifier           - rule-based implementation (no LLM)
- EvidenceStore (Protocol)       - abstract read interface
- InMemoryEvidenceStore          - dict-backed store (tests)
- SqlAlchemyEvidenceStore        - DB-backed store (production)

Server (T0035 Section 5):
- create_app(...)                - FastAPI factory
- main()                         - uvicorn entry point

Workflow integration (T0035 Section 7):
- make_verify_activity           - wrap a Verifier as a WorkflowStep Activity
- make_remote_verify_activity    - wrap a remote HTTP Verifier as a WorkflowStep Activity
- remote_health                  - GET /health helper for tests

Run as a standalone process:
    python -m aios_kernel.verifier.server
    # or
    python scripts/run_verifier.py
"""
from aios_kernel.verifier.deterministic import DeterministicVerifier
from aios_kernel.verifier.evidence_store import (
    ArtifactRecord,
    EvidenceRecord,
    EvidenceStore,
    InMemoryEvidenceStore,
    SqlAlchemyEvidenceStore,
    artifact_record_payload_exists,
    compute_file_sha256,
)
from aios_kernel.verifier.protocol import (
    HealthReport,
    Verdict,
    VerdictCode,
    Verifier,
    VerifyRequest,
)

__all__ = [
    # protocol
    "Verifier",
    "Verdict",
    "VerdictCode",
    "HealthReport",
    "VerifyRequest",
    # deterministic implementation
    "DeterministicVerifier",
    # evidence store
    "EvidenceStore",
    "EvidenceRecord",
    "ArtifactRecord",
    "InMemoryEvidenceStore",
    "SqlAlchemyEvidenceStore",
    "compute_file_sha256",
    "artifact_record_payload_exists",
]
