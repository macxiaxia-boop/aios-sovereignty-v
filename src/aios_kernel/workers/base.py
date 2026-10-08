from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Protocol, runtime_checkable


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthReport:
    worker_id: str
    status: HealthStatus
    last_check_at: datetime
    message: str = ""
    metadata: dict = None


@runtime_checkable
class WorkerAdapter(Protocol):
    worker_id: str
    async def execute(self, task): ...
    async def cancel(self, task_id): ...
    async def health(self): ...
    async def warmup(self): ...
    async def shutdown(self): ...


class NotRegistered(LookupError):
    pass


class _StubAdapterBase:
    def __init__(self, worker_id: str):
        self.worker_id = worker_id

    async def execute(self, task):
        from aios_kernel.domain.artifact import Artifact, ArtifactType
        return Artifact(
            task_id=task.id,
            artifact_type=ArtifactType.CUSTOM,
            label="stub",
            inline_json={"worker": self.worker_id, "task_id": str(task.id)},
        )

    async def cancel(self, task_id):
        return None

    async def health(self):
        return HealthReport(
            worker_id=self.worker_id,
            status=HealthStatus.HEALTHY,
            last_check_at=datetime.utcnow(),
            metadata={"stub": True},
        )

    async def warmup(self):
        return None

    async def shutdown(self):
        return None
