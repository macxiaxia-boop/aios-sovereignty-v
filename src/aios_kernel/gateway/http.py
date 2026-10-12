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
        task = Task(
            goal_id=req.goal_id,
            title=req.title,
            description=req.description,
            task_type=TaskType.CUSTOM,
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

    return app


__all__ = ["create_app", "SubmitTaskRequest", "SubmitTaskResponse", "TaskStatusResponse"]
