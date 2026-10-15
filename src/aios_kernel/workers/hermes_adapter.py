"""hermes_adapter.py - Hermes in-process CIO Worker Adapter (R1503-FINAL).

Hermes runs in-process; we record the dispatch intent in the runtime
memory ledger (when memory is provided) so that downstream cron can act.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from aios_kernel.domain.artifact import Artifact, ArtifactType
from aios_kernel.workers.base import HealthReport, HealthStatus, WorkerAdapter

log = logging.getLogger("aios_kernel.workers.hermes_adapter")


class HermesAdapter(WorkerAdapter):
    worker_id = "hermes-adapter"

    def __init__(self) -> None:
        self._ledger = None  # set by attach_ledger()

    def attach_ledger(self, ledger):
        """Attach a runtime/memory.MemoryPersistence for audit."""
        self._ledger = ledger

    async def execute(self, task):
        if self._ledger is not None:
            try:
                self._ledger.append_ledger({
                    "type": "hermes_dispatch",
                    "task_id": str(task.id),
                    "title": task.title,
                    "intent": "in_process_cio",
                })
            except Exception as exc:  # noqa: BLE001
                log.warning("hermes ledger append failed: %s", exc)
        return Artifact(
            task_id=task.id,
            artifact_type=ArtifactType.CUSTOM,
            label="hermes_dispatch",
            inline_json={"worker": self.worker_id, "intent": "in_process_cio"},
        )

    async def cancel(self, task_id):
        log.info("hermes cancel %s", task_id)

    async def health(self):
        return HealthReport(
            worker_id=self.worker_id,
            status=HealthStatus.HEALTHY,
            last_check_at=datetime.now(UTC),
            metadata={"mode": "in_process"},
        )

    async def warmup(self):
        pass

    async def shutdown(self):
        pass
