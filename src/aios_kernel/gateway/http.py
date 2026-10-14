"""gateway/http.py - HTTP REST surface for AIOSScheduler (R1503-007).

FastAPI app exposing:
  GET  /health          liveness
  GET  /metrics         scheduler metrics snapshot
  POST /tasks           submit a Task (returns run_id)
  GET  /tasks/{run_id}  task status

R1503-007 acceptance:
  - FastAPI app factory create_app()
  - POST /tasks returns 202 Accepted + run_id
  - GET /tasks/{id} returns current state
  - Tests >= 80% coverage

Co-Authored-By: Claude Code (Agent 3 / OpenClaw) via AIOS R1503
"""
from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from aios_kernel.scheduler import AIOSScheduler

log = logging.getLogger("aios_kernel.gateway.http")


# ---------- request / response models ---------------------------------------


class SubmitTaskRequest(BaseModel):
    goal_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    priority: str = Field(default="P2", pattern=r"^P[012]$")
    worker: str | None = Field(default=None, description="Only allowlisted specialized workers")
    input_payload: dict[str, Any] = Field(default_factory=dict)


class SubmitTaskResponse(BaseModel):
    run_id: str
    task_id: str


class TaskStatusResponse(BaseModel):
    run_id: str
    state: str
    submitted: bool | None = None
    completed: bool | None = None
    failed: bool | None = None


# ---------- app factory ---------------------------------------------------


def create_app(scheduler: AIOSScheduler) -> FastAPI:
    """Build the FastAPI app bound to the given scheduler instance."""
    app = FastAPI(title="AIOS Kernel Gateway", version="R1503-007")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"ok": True, "service": "aios-gateway", "version": "R1503"}

    @app.get("/metrics")
    async def metrics() -> dict[str, Any]:
        return scheduler.metrics()

    @app.post("/tasks", response_model=SubmitTaskResponse, status_code=202)
    async def submit_task(req: SubmitTaskRequest) -> SubmitTaskResponse:
        from aios_kernel.domain.task import Task, TaskType
        from aios_kernel.scheduler import Priority
        try:
            priority = Priority(req.priority)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"unknown priority {req.priority!r}"
            ) from exc
        if req.worker is not None:
            if req.worker != "cloudtech-v4-adapter":
                raise HTTPException(400, "Gateway cannot route arbitrary worker identities")
            if os.environ.get("CLOUDTECH_V4_GATEWAY_ENABLED", "0").lower() not in {
                "1", "true", "yes",
            }:
                raise HTTPException(403, "CloudTech Gateway worker is not enabled")
            if req.input_payload.get("action") not in {
                "preflight", "create_and_execute_local",
            }:
                raise HTTPException(400, "CloudTech Gateway does not allow this action")
            if not req.input_payload.get("path_id") or not req.input_payload.get("tenant_id"):
                raise HTTPException(422, "CloudTech path_id and tenant_id are required")
            if not os.environ.get("CLOUDTECH_V4_BASE_URL"):
                raise HTTPException(503, "CloudTech V4 service URL not configured")
        elif req.input_payload:
            raise HTTPException(400, "Unbound worker cannot accept arbitrary input_payload")
        task = Task(
            goal_id=req.goal_id,
            title=req.title,
            description=req.description,
            task_type=TaskType.CUSTOM,
            worker=req.worker,
            input_payload=req.input_payload,
        )
        run_id = await scheduler.submit(task, priority=priority)
        return SubmitTaskResponse(run_id=run_id, task_id=task.id)

    @app.get("/tasks/{run_id}", response_model=TaskStatusResponse)
    async def task_status(run_id: str) -> TaskStatusResponse:
        st = await scheduler.status(run_id)
        return TaskStatusResponse(
            run_id=st["run_id"],
            state=st["state"],
        )

    # R1505-1: production observability (healthz/readyz/metrics)
    from aios_kernel.gateway.observability import add_observability_routes

    add_observability_routes(app, scheduler=scheduler)

    # R1505-2: auth + rate limit middlewares (gated by env vars)
    from aios_kernel.gateway.auth_middleware import install_auth_middlewares

    install_auth_middlewares(app)

    return app


__all__ = ["create_app", "SubmitTaskRequest", "SubmitTaskResponse", "TaskStatusResponse"]
