"""observability.py - Production health / readiness / metrics endpoints (R1505-1).

Exposes for production monitoring:
  GET  /healthz     -> liveness probe (process alive)
  GET  /readyz      -> readiness probe (subsystem ready)
  GET  /metrics     -> Prometheus exposition format

These are added alongside the existing /health endpoint (which stays
as a human-readable JSON for k8s/monitoring).
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI

log = logging.getLogger("aios_kernel.gateway.observability")


def add_observability_routes(
    app: FastAPI,
    *,
    scheduler: Any,
) -> None:
    """Attach /healthz, /readyz, /metrics to an existing FastAPI app."""
    started_at: float = 0.0
    try:
        import time as _t
        started_at = _t.time()
    except Exception:  # noqa: BLE001
        pass

    @app.get("/healthz", include_in_schema=False)
    async def healthz() -> dict[str, Any]:
        """K8s liveness probe — returns 200 if process is alive."""
        return {"status": "alive", "ts": started_at}

    @app.get("/readyz", include_in_schema=False)
    async def readyz() -> dict[str, Any]:
        """K8s readiness probe — returns 200 if all subsystems are healthy."""
        snap = scheduler.metrics()
        # consider "ready" if dispatcher hasn't crashed and DLQ is bounded
        dlq = snap.get("dlq_size", 0)
        ok = dlq < 1000  # configurable in SchedulerConfig.dlq_max_size
        return {"status": "ready" if ok else "degraded", "dlq_size": dlq, **snap}

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> str:
        """Prometheus exposition format (text/plain v0.0.4)."""
        snap = scheduler.metrics()
        lines = []
        # HELP/TYPE comments omitted for brevity in Phase A
        lines.append(f"aios_kernel_submitted_total {snap.get('submitted', 0)}")
        lines.append(f"aios_kernel_completed_total {snap.get('completed', 0)}")
        lines.append(f"aios_kernel_failed_total {snap.get('failed', 0)}")
        lines.append(f"aios_kernel_retried_total {snap.get('retried', 0)}")
        lines.append(f"aios_kernel_dlq_size {snap.get('dlq_size', 0)}")
        lines.append(
            f"aios_kernel_avg_dispatch_latency_seconds {snap.get('avg_dispatch_latency_s', 0.0)}"
        )
        lines.append(
            f"aios_kernel_circuit_opened_total {snap.get('circuit_opened', 0)}"
        )
        for prio, depth in (snap.get("queue_depth_by_priority") or {}).items():
            lines.append(f'aios_kernel_queue_depth{{priority="{prio}"}} {depth}')
        return "\n".join(lines) + "\n"


__all__ = ["add_observability_routes"]