"""task_service.py — TaskService (T0032 scope: write + event).

Responsibilities:
- create_task: build a Task bound to a Goal, persist.
- transition: state-machine-driven mutation, persist, emit event.
- add_evidence / add_artifact: link produced rows back to the task.
"""
from __future__ import annotations

import logging
from typing import Any

from aios_kernel.domain.services.repository import Repository
from aios_kernel.domain.task import TASK_TRANSITIONS, Task, TaskStatus, TaskType

log = logging.getLogger(__name__)


class IllegalTaskTransition(ValueError):
    """Raised when the requested Task status transition is not allowed."""


class TaskService:
    def __init__(self, repo: Repository) -> None:
        self.repo = repo

    async def create_task(
        self,
        goal_id: str,
        title: str,
        task_type: TaskType = TaskType.CUSTOM,
        description: str | None = None,
        plan_id: str | None = None,
        plan_version: int = 1,
        worker: str | None = None,
        max_retries: int = 3,
        input_payload: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Task:
        task = Task(
            goal_id=goal_id,
            title=title,
            description=description,
            task_type=task_type,
            plan_id=plan_id,
            plan_version=plan_version,
            worker=worker,
            max_retries=max_retries,
            input_payload=input_payload or {},
            metadata=metadata or {},
        )
        await self.repo.add(task)
        await self.repo.commit()
        log.info(
            "task.created id=%s goal_id=%s type=%s plan_id=%s",
            task.id, task.goal_id, task.task_type.value, task.plan_id,
        )
        return task

    async def transition(self, task: Task, new_status: TaskStatus) -> Task:
        if new_status not in TASK_TRANSITIONS.get(task.status, set()):
            raise IllegalTaskTransition(
                f"illegal Task transition: {task.status.value} -> {new_status.value}"
            )
        old = task.status
        task.transition_to(new_status)
        await self.repo.add(task)
        await self.repo.commit()
        log.info(
            "task.transition id=%s %s -> %s", task.id, old.value, new_status.value
        )
        return task

    async def start(self, task: Task) -> Task:
        return await self.transition(task, TaskStatus.RUNNING)

    async def mark_verifying(self, task: Task) -> Task:
        return await self.transition(task, TaskStatus.VERIFYING)

    async def mark_done(self, task: Task) -> Task:
        return await self.transition(task, TaskStatus.DONE)

    async def mark_failed(self, task: Task, error: str = "") -> Task:
        if error:
            task.error = error
        return await self.transition(task, TaskStatus.FAILED)

    async def mark_blocked(self, task: Task, reason: str = "") -> Task:
        if reason:
            task.metadata["block_reason"] = reason
        return await self.transition(task, TaskStatus.BLOCKED)

    async def add_evidence(self, task: Task, evidence_id: str) -> Task:
        task.add_evidence(evidence_id)
        await self.repo.add(task)
        await self.repo.commit()
        return task

    async def add_artifact(self, task: Task, artifact_id: str) -> Task:
        task.add_artifact(artifact_id)
        await self.repo.add(task)
        await self.repo.commit()
        return task


__all__ = ["TaskService", "IllegalTaskTransition"]
