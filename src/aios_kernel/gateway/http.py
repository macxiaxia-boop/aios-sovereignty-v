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

from fastapi import FastAPI, HTTPException, Request
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
    async def submit_task(req: SubmitTaskRequest, request: Request) -> SubmitTaskResponse:
        from aios_kernel.domain.task import Task, TaskType
        from aios_kernel.scheduler import Priority
        try:
            priority = Priority(req.priority)
        except ValueError as exc:
            raise HTTPException(
                status_code=400, detail=f"unknown priority {req.priority!r}"
            ) from exc
        if req.worker is not None:
            from aios_kernel.gateway.auth_middleware import _env_enabled

            # Never accept a tenant claimed by an unauthenticated caller.
            if not _env_enabled("AIOS_KERNEL_AUTH_REQUIRED"):
                raise HTTPException(403, "CloudTech work requires signed tenant auth")
            claims = getattr(request.state, "user", None)
            caller_tenant = claims.get("tenant_id") if isinstance(claims, dict) else None
            requested_tenant = req.input_payload.get("tenant_id")
            if (
                not isinstance(caller_tenant, str)
                or not caller_tenant
                or not isinstance(requested_tenant, str)
                or requested_tenant != caller_tenant
            ):
                raise HTTPException(403, "signed tenant claim does not match work tenant")
            if req.worker != "cloudtech-v4-adapter":
                raise HTTPException(400, "Gateway cannot route arbitrary worker identities")
            if os.environ.get("CLOUDTECH_V4_GATEWAY_ENABLED", "0").lower() not in {
                "1", "true", "yes",
            }:
                raise HTTPException(403, "CloudTech Gateway worker is not enabled")
            if req.input_payload.get("action") not in {
                "preflight", "create_and_execute_local",
                "create_enqueue_and_collect_subtitles",
                "create_enqueue_and_collect_article_analysis",
            }:
                raise HTTPException(400, "CloudTech Gateway does not allow this action")
            if (
                req.input_payload.get("action") == "create_enqueue_and_collect_subtitles"
                and req.input_payload.get("path_id") != "WP-LOCAL-SUBTITLE-EXPORT"
            ):
                raise HTTPException(400, "subtitle Worker action only supports supplied segments")
            if (
                req.input_payload.get("action") == "create_enqueue_and_collect_article_analysis"
                and req.input_payload.get("path_id") != "WP-LOCAL-ARTICLE-ANALYZE"
            ):
                raise HTTPException(400, "article analysis Worker action requires supplied HTML")
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

    @app.get("/tasks/{run_id}/result")
    async def task_result(run_id: str, request: Request) -> dict[str, Any]:
        """Authenticated, tenant-scoped access to actual worker artifact."""
        from aios_kernel.gateway.auth_middleware import _env_enabled

        if not _env_enabled("AIOS_KERNEL_AUTH_REQUIRED"):
            raise HTTPException(403, "artifact read requires JWT authentication")
        user = getattr(request.state, "user", None)
        tenant_id = user.get("tenant_id") if isinstance(user, dict) else None
        if not isinstance(tenant_id, str) or not tenant_id:
            raise HTTPException(403, "JWT must bind tenant_id")
        result = await scheduler.result(run_id, tenant_id=tenant_id)
        if result["state"] == "unknown":
            raise HTTPException(404, "run not found")
        return result

    @app.get("/tasks/{run_id}", response_model=TaskStatusResponse)
    async def task_status(run_id: str, request: Request) -> TaskStatusResponse:
        from aios_kernel.gateway.auth_middleware import _env_enabled

        if _env_enabled("AIOS_KERNEL_AUTH_REQUIRED"):
            user = getattr(request.state, "user", None)
            tenant_id = user.get("tenant_id") if isinstance(user, dict) else None
            if not isinstance(tenant_id, str) or not tenant_id:
                raise HTTPException(403, "signed tenant claim required")
            # Same tenant gate as artifact route, including queued/running work.
            st = await scheduler.result(run_id, tenant_id=tenant_id)
            if st["state"] == "unknown":
                raise HTTPException(404, "run not found")
        else:
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
