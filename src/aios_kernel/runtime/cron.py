"""runtime/cron.py - Cron-like scheduler (R1503-012).

Lightweight in-process cron for periodic kernel tasks (drift check,
ledger rotation, etc.). Supports 5-field cron expressions.

R1503-012 acceptance:
  - CronManager API (register, unregister, list, start, stop)
  - 5-field parser (minute hour day-of-month month day-of-week)
  - asyncio-based tick loop (60s)
  - Tests ≥ 80% coverage

Co-Authored-By: Claude Code (Agent 4 / Hermes) via AIOS R1503
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Awaitable, Callable

log = logging.getLogger("aios_kernel.runtime.cron")


@dataclass
class CronJob:
    name: str
    expr: str
    callback: Callable[[], Awaitable[None]]
    last_run_at: float | None = None
    last_run_ok: bool | None = None
    runs: int = 0


def _parse_field(field: str, lo: int, hi: int) -> set[int]:
    """Parse a single cron field into the set of matching integers."""
    out: set[int] = set()
    for token in field.split(","):
        step = 1
        if "/" in token:
            token, step_s = token.split("/", 1)
            step = int(step_s)
        if token == "*":
            start, end = lo, hi
        elif "-" in token:
            a, b = token.split("-", 1)
            start, end = int(a), int(b)
        else:
            try:
                out.add(int(token))
                continue
            except ValueError:
                raise ValueError(f"bad cron field: {field!r}")
        out.update(range(start, end + 1, step))
    return {v for v in out if lo <= v <= hi}


def matches(expr: str, now: datetime) -> bool:
    """Return True if the cron expression fires at `now` (5-field).

    Day-of-week mapping (R1503-012):
      cron: 0=Sun, 1=Mon, ..., 6=Sat
      py    : 0=Mon, 1=Tue, ..., 6=Sun
      transform: py_dow = (cron_dow + 6) % 7
    """
    parts = expr.split()
    if len(parts) != 5:
        raise ValueError(f"cron expr must have 5 fields, got {len(parts)}: {expr!r}")
    minute, hour, dom, month, dow = parts
    cron_dow = _parse_field(dow, 0, 6)
    py_dow = {(d + 6) % 7 for d in cron_dow}
    return (
        now.minute in _parse_field(minute, 0, 59)
        and now.hour in _parse_field(hour, 0, 23)
        and now.day in _parse_field(dom, 1, 31)
        and now.month in _parse_field(month, 1, 12)
        and now.weekday() in py_dow
    )


class CronManager:
    """In-process cron scheduler."""

    def __init__(self) -> None:
        self._jobs: dict[str, CronJob] = {}
        self._task: asyncio.Task | None = None
        self._stopped = False

    def register(self, name: str, expr: str, callback: Callable[[], Awaitable[None]]) -> CronJob:
        if name in self._jobs:
            raise ValueError(f"job {name!r} already registered")
        # validate expr
        matches(expr, datetime.now())
        job = CronJob(name=name, expr=expr, callback=callback)
        self._jobs[name] = job
        return job

    def unregister(self, name: str) -> None:
        self._jobs.pop(name, None)

    def list(self) -> list[CronJob]:
        return list(self._jobs.values())

    async def start(self) -> None:
        if self._task is not None:
            return
        self._stopped = False
        self._task = asyncio.create_task(self._tick_loop(), name="aios-cron")
        log.info("cron_manager.start: tick loop spawned, %d jobs", len(self._jobs))

    async def stop(self) -> None:
        self._stopped = True
        if self._task:
            self._task.cancel()
            self._task = None

    async def _tick_loop(self) -> None:
        last_minute = -1
        while not self._stopped:
            now = datetime.now()
            await asyncio.sleep(60 - now.second)
            now = datetime.now()
            if now.minute == last_minute:
                continue
            last_minute = now.minute
            for job in list(self._jobs.values()):
                try:
                    if matches(job.expr, now):
                        await self._fire(job)
                except Exception:  # noqa: BLE001
                    log.exception("cron tick failed for job %s", job.name)

    async def _fire(self, job: CronJob) -> None:
        job.last_run_at = time.time()
        try:
            await job.callback()
            job.last_run_ok = True
        except Exception:  # noqa: BLE001
            log.exception("cron callback failed for job %s", job.name)
            job.last_run_ok = False
        finally:
            job.runs += 1


__all__ = ["CronManager", "CronJob", "matches"]