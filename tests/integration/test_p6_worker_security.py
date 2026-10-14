"""P6 regression: fail closed on explicit worker routing and unsafe gateway config.

Tests only existing AIOS modules; no external network, credentials or real workers.
"""
from types import SimpleNamespace

import pytest

from aios_kernel.gateway.auth_middleware import (
    JWTAuthMiddleware, RateLimitMiddleware, _env_enabled,
)
from aios_kernel.workers.base import NotRegistered, _StubAdapterBase
from aios_kernel.workers.registry import WorkerRegistry


@pytest.mark.parametrize(
    ("value", "expected"),
    [("0", False), ("false", False), ("off", False), ("", False),
     ("1", True), ("true", True), ("yes", True), ("on", True)],
)
def test_explicit_auth_flag_parsing(monkeypatch, value, expected):
    monkeypatch.setenv("AIOS_KERNEL_AUTH_REQUIRED", value)
    assert _env_enabled("AIOS_KERNEL_AUTH_REQUIRED") is expected


def test_unknown_auth_flag_is_a_configuration_error(monkeypatch):
    monkeypatch.setenv("AIOS_KERNEL_AUTH_REQUIRED", "sometimes")
    with pytest.raises(ValueError, match="invalid boolean"):
        JWTAuthMiddleware(object())


def test_auth_disabled_by_literal_zero(monkeypatch):
    monkeypatch.setenv("AIOS_KERNEL_AUTH_REQUIRED", "0")
    monkeypatch.delenv("AIOS_KERNEL_JWT_SECRET", raising=False)
    mw = JWTAuthMiddleware(object())
    assert mw._required is False


def test_jwt_auth_cannot_start_with_default_or_short_secret(monkeypatch):
    monkeypatch.setenv("AIOS_KERNEL_AUTH_REQUIRED", "1")
    monkeypatch.delenv("AIOS_KERNEL_JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="32\\+ bytes"):
        JWTAuthMiddleware(object())
    monkeypatch.setenv("AIOS_KERNEL_JWT_SECRET", "aios-default-secret")
    with pytest.raises(RuntimeError, match="32\\+ bytes"):
        JWTAuthMiddleware(object())


def test_jwt_auth_initializes_with_secure_config(monkeypatch):
    monkeypatch.setenv("AIOS_KERNEL_AUTH_REQUIRED", "1")
    monkeypatch.setenv("AIOS_KERNEL_JWT_SECRET", "p6-test-secret-value-32-characters-long")
    mw = JWTAuthMiddleware(object())
    assert mw._required is True
    assert len(mw._jwt_secret) >= 32


@pytest.mark.parametrize("raw", ["0", "false", "off", "no"])
def test_rate_limit_disabled_flags_are_not_truthy(monkeypatch, raw):
    monkeypatch.setenv("AIOS_KERNEL_RATELIMIT_ENABLED", raw)
    mw = RateLimitMiddleware(object())
    assert mw._enabled is False


def test_explicit_worker_missing_refuses_implicit_reroute():
    registry = WorkerRegistry()
    registry.register(_StubAdapterBase("codex-adapter"))
    task = SimpleNamespace(worker="private-worker", type=SimpleNamespace(value="custom"))
    with pytest.raises(NotRegistered, match="refusing fallback"):
        registry.route(task)


def test_explicit_registered_worker_is_respected():
    registry = WorkerRegistry()
    registry.register(_StubAdapterBase("codex-adapter"))
    registry.register(_StubAdapterBase("hermes-adapter"))
    task = SimpleNamespace(worker="hermes-adapter", type=SimpleNamespace(value="custom"))
    assert registry.route(task).worker_id == "hermes-adapter"


def test_unbound_worker_uses_existing_type_mapping():
    registry = WorkerRegistry()
    registry.register(_StubAdapterBase("codex-adapter"))
    task = SimpleNamespace(worker=None, type=SimpleNamespace(value="custom"))
    assert registry.route(task).worker_id == "codex-adapter"
