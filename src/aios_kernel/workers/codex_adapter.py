"""codex_adapter.py - Real Codex CLI Worker Adapter (R1503-FINAL).

Calls `codex exec` via subprocess.
"""
from __future__ import annotations

import logging
import shutil
from datetime import UTC, datetime

from aios_kernel.domain.artifact import Artifact, ArtifactType
from aios_kernel.workers.adapters import SubprocessRunner
from aios_kernel.workers.base import HealthReport, HealthStatus, WorkerAdapter

log = logging.getLogger("aios_kernel.workers.codex_adapter")


class CodexAdapter(WorkerAdapter):
    worker_id = "codex-adapter"

    def __init__(self, binary: str | None = None) -> None:
        self._binary = binary or shutil.which("codex") or "codex"
        self._runner = SubprocessRunner()

    async def execute(self, task):
        # defensive getattr: tests use MockTask without description
        prompt = f"{task.title or task.id}: {getattr(task, 'description', '') or ''}"
        cmd = [self._binary, "exec", prompt, "--quiet"]
        try:
            stdout, stderr, code = await self._runner.run(cmd, env={})
        except FileNotFoundError:
            return await self._stub_execute(task)
        return Artifact(
            task_id=task.id,
            artifact_type=ArtifactType.CUSTOM,
            label="codex_result",
            inline_json={
                "worker": self.worker_id,
                "binary": self._binary,
                "exit_code": code,
                "stdout": stdout[:4096],
                "stderr": stderr[:1024],
            },
        )

    async def _stub_execute(self, task):
        return Artifact(
            task_id=task.id,
            artifact_type=ArtifactType.CUSTOM,
            label="stub_fallback",
            inline_json={"worker": self.worker_id, "stub": True},
        )

    async def cancel(self, task_id):
        log.info("codex cancel %s", task_id)

    async def health(self):
        return HealthReport(
            worker_id=self.worker_id,
            status=HealthStatus.HEALTHY,
            last_check_at=datetime.now(UTC),
            metadata={"binary": self._binary},
        )

    async def warmup(self):
        pass

    async def shutdown(self):
        pass
