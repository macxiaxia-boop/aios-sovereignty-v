"""server.py - Verifier FastAPI server (T0035 Section 5).

Two endpoints:
    POST /verify  -> Verdict
    GET  /health  -> HealthReport

The server runs in its own OS process (started by scripts/run_verifier.py
or directly via `python -m aios_kernel.verifier.server`). The Kernel
process calls the server over HTTP, proving process isolation by
inspecting the Verifier's pid in the /health response.

The server is intentionally minimal: no auth, no caching, no LLM
(per T0035 Out-of-scope). A single instance is sufficient for Phase A.
"""
from __future__ import annotations

import logging
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from aios_kernel.verifier.deterministic import DeterministicVerifier
from aios_kernel.verifier.evidence_store import (
    SqlAlchemyEvidenceStore,
)
from aios_kernel.verifier.protocol import (
    HealthReport,
    Verdict,
    VerifyRequest,
)

log = logging.getLogger("aios_kernel.verifier.server")

# Default port (per T0035 Section 5: "listening on port 9001").
DEFAULT_HOST = os.environ.get("VERIFIER_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("VERIFIER_PORT", "9001"))
DEFAULT_VERIFIER_ID = os.environ.get("VERIFIER_ID", "deterministic-verifier")
DEFAULT_DATABASE_URL = os.environ.get(
    "AIOS_DATABASE_URL",
    "sqlite+aiosqlite:///D:/AIOS/kernel/aios_kernel.db",
)


# ---------- response models for /health and /verify ------------------------


class VerifyResponse(BaseModel):
    """HTTP wrapper around Verdict (keeps the wire schema explicit)."""

    model_config = ConfigDict(extra="forbid")

    verdict: Verdict
    verifier_pid: int = Field(..., description="PID of the Verifier process (for isolation tests).")


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report: HealthReport
    verifier_pid: int = Field(..., description="PID of the Verifier process.")


# ---------- factory --------------------------------------------------------


def create_app(
    *,
    verifier_id: str | None = None,
    database_url: str | None = None,
    store=None,
) -> FastAPI:
    """Build a FastAPI app bound to a fresh DeterministicVerifier.

    Args:
        verifier_id: identity reported in HealthReport and Verdict.
        database_url: SQLAlchemy URL for SqlAlchemyEvidenceStore.
        store: pre-built EvidenceStore (overrides database_url). Useful
               in tests where the Verifier server is wired to an
               InMemoryEvidenceStore.

    Returns a FastAPI app. The Verifier is created here (so its PID is
    the PID of whichever process imports+creates the app).
    """
    _verifier_id = verifier_id or DEFAULT_VERIFIER_ID
    if store is None:
        store = SqlAlchemyEvidenceStore(database_url or DEFAULT_DATABASE_URL)
    verifier = DeterministicVerifier(_verifier_id, store)

    app = FastAPI(
        title="AIOS Verifier (T0035)",
        version="0.1.0",
        description="Independent-process deterministic verifier.",
    )

    # --- endpoints -------------------------------------------------------

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        report = await verifier.health()
        return HealthResponse(report=report, verifier_pid=os.getpid())

    @app.post("/verify", response_model=VerifyResponse)
    async def verify(req: VerifyRequest) -> VerifyResponse:
        # Validate task projection (must at least have an id)
        task = req.task
        if not task.get("id"):
            raise HTTPException(
                status_code=400,
                detail="task.id is required",
            )
        evidence_ids = list(task.get("evidence_ids") or [])

        # Re-stamp the verifier id if the caller did not specify one
        effective_id = req.verifier_id or verifier.verifier_id
        # Note: we use the verifier instance as-is (its id is fixed at
        # construction). If a different id was requested, we wrap the
        # verdict's verifier_id to match the request - this lets one
        # Verifier process serve multiple logical identities.
        verdict = await verifier.verify(task, evidence_ids)
        if effective_id != verdict.verifier_id:
            verdict = verdict.model_copy(update={"verifier_id": effective_id})

        return VerifyResponse(verdict=verdict, verifier_pid=os.getpid())

    @app.get("/")
    async def root() -> dict:
        return {
            "name": "aios-verifier",
            "version": "0.1.0",
            "pid": os.getpid(),
            "verifier_id": verifier.verifier_id,
            "endpoints": ["POST /verify", "GET /health"],
        }

    return app


# ---------- CLI entry point -------------------------------------------------


def main() -> None:
    """Console entry point: `python -m aios_kernel.verifier.server`."""
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    host = os.environ.get("VERIFIER_HOST", DEFAULT_HOST)
    port = int(os.environ.get("VERIFIER_PORT", str(DEFAULT_PORT)))
    log.info("starting AIOS Verifier on %s:%d (pid=%d)", host, port, os.getpid())
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
