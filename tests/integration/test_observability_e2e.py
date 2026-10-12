"""test_observability_e2e.py - Production healthz/readyz/metrics endpoints (R1505-1)."""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest

# Reuse the bootstrap that spawns AIOS kernel gateway via uvicorn subprocess.
# The bootstrap lives in tests/integration/_aios_kernel_gateway_bootstrap.py


def _hit(url: str, timeout: int = 5):
    return urllib.request.urlopen(url, timeout=timeout)


def test_observability_healthz_liveness():
    r = _hit("http://127.0.0.1:9001/healthz")
    assert r.status == 200
    body = json.loads(r.read().decode())
    assert body["status"] == "alive"
    assert "ts" in body


def test_observability_readyz_readiness():
    r = _hit("http://127.0.0.1:9001/readyz")
    assert r.status == 200
    body = json.loads(r.read().decode())
    assert body["status"] in ("ready", "degraded")
    assert "submitted" in body
    assert "dlq_size" in body


def test_observability_metrics_prometheus_format():
    r = _hit("http://127.0.0.1:9001/metrics")
    assert r.status == 200
    # Prometheus content type
    ct = r.headers.get("content-type", "")
    assert "text/plain" in ct or "openmetrics" in ct
    body = r.read().decode()
    # check key aios_kernel_* metrics present
    assert "aios_kernel_submitted_total" in body
    assert "aios_kernel_completed_total" in body
    assert "aios_kernel_dlq_size" in body
    assert "aios_kernel_queue_depth{" in body
    assert 'priority="P' in body


def test_observability_healthz_always_alive_even_after_failed_submit():
    """Even when /tasks fails, /healthz stays alive (separate concerns)."""
    # /healthz is process-level, not request-level
    r1 = _hit("http://127.0.0.1:9001/healthz")
    assert r1.status == 200
    # submit a bogus task (will get 422)
    req = urllib.request.Request(
        "http://127.0.0.1:9001/tasks",
        data=b'{"goal_id":"x","title":"y","priority":"Z"}',
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    import urllib.error
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(req, timeout=5)
    assert exc.value.code == 422
    # /healthz still alive
    r2 = _hit("http://127.0.0.1:9001/healthz")
    assert r2.status == 200