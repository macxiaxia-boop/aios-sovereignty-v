"""Regression tests for secure-by-default task gateway behavior.

No live backend, secrets, or external network calls.
"""
import time
import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aios_kernel.gateway.auth_middleware import JWTAuthMiddleware, RateLimitMiddleware


def app_with_auth():
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"ok": True}

    @app.post("/tasks", status_code=202)
    def task():
        return {"accepted": True}

    app.add_middleware(JWTAuthMiddleware)
    return app


def test_task_auth_enabled_by_default(monkeypatch):
    monkeypatch.delenv("AIOS_KERNEL_AUTH_REQUIRED", raising=False)
    monkeypatch.delenv("AIOS_KERNEL_JWT_SECRET", raising=False)
    with TestClient(app_with_auth()) as client:
        assert client.get("/health").status_code == 200
        assert client.post("/tasks").status_code == 401


def test_missing_secret_fails_closed(monkeypatch):
    monkeypatch.delenv("AIOS_KERNEL_AUTH_REQUIRED", raising=False)
    monkeypatch.delenv("AIOS_KERNEL_JWT_SECRET", raising=False)
    with TestClient(app_with_auth()) as client:
        response = client.post("/tasks", headers={"Authorization": "Bearer example"})
        assert response.status_code == 503


def test_insecure_literal_secret_is_never_accepted(monkeypatch):
    monkeypatch.delenv("AIOS_KERNEL_AUTH_REQUIRED", raising=False)
    monkeypatch.setenv("AIOS_KERNEL_JWT_SECRET", "aios-default-secret")
    with TestClient(app_with_auth()) as client:
        assert client.post("/tasks", headers={"Authorization": "Bearer example"}).status_code == 503


def test_explicit_local_opt_out(monkeypatch):
    monkeypatch.setenv("AIOS_KERNEL_AUTH_REQUIRED", "false")
    with TestClient(app_with_auth()) as client:
        assert client.post("/tasks").status_code == 202


def test_rate_limit_enabled_by_default(monkeypatch):
    monkeypatch.delenv("AIOS_KERNEL_RATELIMIT_ENABLED", raising=False)
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"ok": True}

    app.add_middleware(RateLimitMiddleware, capacity=1.0, refill_rate=0.00001)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 429



def test_jwt_expires_at_boundary_and_rejects_modified_signature():
    from aios_kernel.gateway.auth import InvalidToken, sign_jwt, verify_jwt
    secret = b"test-only-strong-key"
    token = sign_jwt({"sub": "sample", "exp": int(time.time())}, secret)
    with pytest.raises(InvalidToken):
        verify_jwt(token, secret)
    valid = sign_jwt({"sub": "sample"}, secret, ttl_s=60)
    pieces = valid.split(".")
    altered_signature = ("A" if pieces[2][0] != "A" else "B") + pieces[2][1:]
    with pytest.raises(InvalidToken):
        verify_jwt(".".join(pieces[:2] + [altered_signature]), secret)
