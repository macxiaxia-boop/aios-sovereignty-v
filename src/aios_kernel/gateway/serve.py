"""Host the EXISTING AIOS Gateway with its Scheduler in one ASGI process.

Do not run a separate "aios-kernel scheduler" concurrently; each host owns its
own in-process queue. Production durable dispatch is NOT yet implemented.
Local explicit start:
  uvicorn aios_kernel.gateway.serve:app --host 127.0.0.1 --port 5090
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from aios_kernel.cli import build_default_registry
from aios_kernel.gateway.http import create_app
from aios_kernel.scheduler import AIOSScheduler


def create_hosted_app() -> FastAPI:
    """Reuse the existing app factory, worker registry and scheduler."""
    scheduler = AIOSScheduler(registry=build_default_registry())

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        await scheduler.start()
        try:
            yield
        finally:
            await scheduler.stop()

    hosted = create_app(scheduler)
    hosted.router.lifespan_context = lifespan
    return hosted


app = create_hosted_app()
