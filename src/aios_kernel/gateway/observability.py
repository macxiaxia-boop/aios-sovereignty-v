"""observability.py - Production health / readiness / metrics endpoints (R1505-1).

Exposes for production monitoring:
  GET  /healthz     -> liveness probe (process alive)
  GET  /readyz      -> readiness probe (subsystem ready)
  GET  /metrics     -> Prometheus exposition format

These are added alongside the existing /health endpoint (which stays
as a human-readable JSON for k8s/monitoring).
"""
from __future__ import annotations

import asyncio
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
        """K8s readiness probe — returns 200 if all subsystems are healthy.

        R1505-2: also probes each registered WorkerAdapter's health (asyncio.gather
        with a 1.0s timeout) plus checks for an attached database (best-effort).
        """
        snap = scheduler.metrics()
        dlq = snap.get("dlq_size", 0)
        ok_dlq = dlq < 1000

        # Probe adapter health (best effort, 1s timeout each).
        adapter_results: dict[str, str] = {}
        adapter_overall_ok = True
        try:
            # Discover via scheduler's adapter handles if accessible; we fallback
            # to listing from a registry attached as an attribute (best-effort).
            registry = getattr(scheduler, "_registry", None)
            if registry is not None and hasattr(registry, "list_ids"):
                ids = registry.list_ids()
                async def _probe_one(adapter):
                    try:
                        rep = await asyncio.wait_for(adapter.health(), timeout=1.0)
                        return rep.status.value
                    except Exception as exc:  # noqa: BLE001
                        return f"err:{type(exc).__name__}"
                probes = await asyncio.gather(
                    *(_probe_one(registry.get(i)) for i in ids),
                    return_exceptions=True,
                )
                for i, st in zip(ids, probes, strict=True):
                    s = "ok" if st == "healthy" else ("degraded" if st == "degraded" else "unhealthy")
                    adapter_results[i] = s
                    if s != "ok":
                        adapter_overall_ok = False
        except Exception:  # noqa: BLE001
            pass  # adapter probe is best-effort

        # Probe database (best-effort, async via asyncio.to_thread).
        db_ok = True
        db_msg = "ok"
        try:
            mem = getattr(scheduler, "_memory", None)
            if mem is not None:
                # touch ledger read as a liveness probe
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(None, mem.read_ledger)
        except Exception as exc:  # noqa: BLE001
            db_ok = False
            db_msg = f"err:{type(exc).__name__}"

        ok = ok_dlq and adapter_overall_ok and db_ok
        return {
            "status": "ready" if ok else "degraded",
            "dlq_size": dlq,
            "adapters": adapter_results,
            "db": db_msg,
            **snap,
        }

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
