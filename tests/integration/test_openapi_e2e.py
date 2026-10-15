"""test_openapi_e2e.py - Validate FastAPI auto-generated OpenAPI schema (R1505-2)."""
from __future__ import annotations

import json
import urllib.request


def _hit(url: str, timeout: int = 5):
    return urllib.request.urlopen(url, timeout=timeout)


def test_openapi_json_served():
    r = _hit("http://127.0.0.1:9001/openapi.json")
    assert r.status == 200
    body = json.loads(r.read().decode())
    assert "openapi" in body
    assert body["info"]["title"] == "AIOS Kernel Gateway"
    # check our routes are registered
    paths = body.get("paths", {})
    assert "/health" in paths
    assert "/tasks" in paths
    assert "/healthz" in paths or "/readyz" in paths  # observability routes
    # POST /tasks has request body schema
    assert "post" in paths["/tasks"]
    assert "SubmitTaskRequest" in paths["/tasks"]["post"]["requestBody"] or \
           "requestBody" in paths["/tasks"]["post"]


def test_swagger_ui_served():
    r = _hit("http://127.0.0.1:9001/docs")
    assert r.status == 200
    # Swagger UI is HTML
    ct = r.headers.get("content-type", "")
    assert "text/html" in ct
