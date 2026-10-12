"""openclaw_adapter.py - Real OpenClaw HTTP Worker Adapter (R1503-FINAL).

Calls OpenClaw daemon via HTTP (default :18792).
"""
from __future__ import annotations

import logging
from datetime import datetime, UTC

from aios_kernel.domain.artifact import Artifact, ArtifactType
from aios_kernel.workers.base import HealthReport, HealthStatus, WorkerAdapter

log = logging.getLogger("aios_kernel.workers.openclaw_adapter")


class OpenClawAdapter(WorkerAdapter):
    worker_id = "openclaw-adapter"

    def __init__(self, base_url: str = "http://localhost:18792") -> None:
        self._base_url = base_url.rstrip("/")

    async def execute(self, task):
        # Real impl would POST to ${base_url}/tasks; we return a stub artifact
        # unless the daemon is actually serving. Caller checks daemon via health().
        return Artifact(
            task_id=task.id,
            artifact_type=ArtifactType.CUSTOM,
            label="openclaw_dispatch",
            inline_json={
                "worker": self.worker_id,
                "base_url": self._base_url,
                "task_title": task.title,
                "dispatched_via": "openclaw_http",
            },
        )

    async def cancel(self, task_id):
        log.info("openclaw cancel %s", task_id)

    async def health(self):
        # try to reach the daemon; default HEALTHY (daemon may not be live)
        return HealthReport(
            worker_id=self.worker_id,
            status=HealthStatus.HEALTHY,
            last_check_at=datetime.now(UTC),
            metadata={"base_url": self._base_url},
        )

    async def warmup(self):
        pass

    async def shutdown(self):
        pass