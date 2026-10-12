"""runtime/process.py - Process Lifecycle Manager (R1503-010).

Manages background processes spawned by the AIOS kernel (verifier daemon,
schedulers, adapters). Supports start/stop/restart + health probe + metrics.

R1503-010 acceptance:
  - ProcessManager API (start, stop, restart, list)
  - ProcessRecord (pid, name, status, started_at, exit_code, last_health)
  - Health probe (async, configurable interval)
  - Tests >= 80% coverage

Co-Authored-By: Claude Code (Agent 4 / Hermes) via AIOS R1503
"""
from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from enum import Enum

log = logging.getLogger("aios_kernel.runtime.process")


class ProcessStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    CRASHED = "crashed"


@dataclass
class ProcessRecord:
    pid: int
    name: str
    status: ProcessStatus
    cmd: list[str]
    started_at: float
    exit_code: int | None = None
    last_health_at: float | None = None
    last_health_ok: bool | None = None


class ProcessManager:
    """Manages kernel-spawned background processes."""

    def __init__(self) -> None:
        self._records: dict[str, ProcessRecord] = {}
        self._proc_handles: dict[str, asyncio.subprocess.Process] = {}
        self._health_tasks: dict[str, asyncio.Task] = {}

    async def start(
        self,
        name: str,
        cmd: list[str],
        *,
        env: dict[str, str] | None = None,
        health_interval_s: float = 30.0,
    ) -> ProcessRecord:
        if name in self._records and self._records[name].status == ProcessStatus.RUNNING:
            raise RuntimeError(f"process {name!r} already running (pid={self._records[name].pid})")
        log.info("process_manager.start: name=%s cmd=%s", name, cmd)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ.copy(), **(env or {})},
        )
        record = ProcessRecord(
            pid=proc.pid,
            name=name,
            status=ProcessStatus.RUNNING,
            cmd=cmd,
            started_at=time.time(),
        )
        self._records[name] = record
        self._proc_handles[name] = proc
        self._health_tasks[name] = asyncio.create_task(
            self._health_probe(name, health_interval_s),
            name=f"process-health-{name}",
        )
        return record

    async def stop(self, name: str, *, timeout_s: float = 5.0) -> ProcessRecord:
        record = self._records.get(name)
        if record is None:
            raise KeyError(f"no process {name!r}")
        proc = self._proc_handles.get(name)
        if proc is None or proc.returncode is not None:
            record.status = ProcessStatus.STOPPED
            return record
        log.info("process_manager.stop: name=%s pid=%s", name, record.pid)
        try:
            proc.terminate()
            await asyncio.wait_for(proc.wait(), timeout=timeout_s)
            record.status = ProcessStatus.STOPPED
            record.exit_code = proc.returncode
        except TimeoutError:
            log.warning("process_manager.stop: SIGTERM timed out, SIGKILL")
            proc.kill()
            await proc.wait()
            record.status = ProcessStatus.FAILED
            record.exit_code = proc.returncode
        ht = self._health_tasks.pop(name, None)
        if ht is not None:
            ht.cancel()
        return record

    async def restart(
        self, name: str, *, env: dict[str, str] | None = None
    ) -> ProcessRecord:
        old = self._records.get(name)
        if old is not None:
            await self.stop(name)
        cmd = old.cmd if old else []
        return await self.start(name, cmd, env=env)

    def list(self) -> list[ProcessRecord]:
        return list(self._records.values())

    def get(self, name: str) -> ProcessRecord:
        if name not in self._records:
            raise KeyError(f"no process {name!r}")
        return self._records[name]

    async def wait(self, name: str) -> int:
        proc = self._proc_handles.get(name)
        if proc is None:
            raise KeyError(f"no process {name!r}")
        return await proc.wait()

    async def _health_probe(self, name: str, interval_s: float) -> None:
        record = self._records[name]
        proc = self._proc_handles[name]
        while True:
            await asyncio.sleep(interval_s)
            if proc.returncode is not None:
                record.exit_code = proc.returncode
                if proc.returncode == 0:
                    record.status = ProcessStatus.STOPPED
                else:
                    record.status = ProcessStatus.CRASHED
                log.warning(
                    "process exited: name=%s pid=%s exit_code=%s status=%s",
                    name, record.pid, record.exit_code, record.status.value,
                )
                return
            record.last_health_at = time.time()
            record.last_health_ok = True


__all__ = ["ProcessManager", "ProcessRecord", "ProcessStatus"]
