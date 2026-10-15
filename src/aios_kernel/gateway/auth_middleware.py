"""auth_middleware.py - JWT auth + rate limit middleware (R1505-2).

Starlette/FastAPI middlewares that wrap requests:
  - JWTAuthMiddleware: validates `Authorization: Bearer <jwt>` on /tasks routes
    and sets `request.state.user = claims` for downstream handlers. If
    `AIOS_KERNEL_AUTH_REQUIRED` env is unset, middleware is a no-op.
  - RateLimitMiddleware: per-worker-id token bucket; 429 on exhaustion.
    If `AIOS_KERNEL_RATELIMIT_ENABLED` env is unset, middleware is a no-op.

Both middlewares are wired by `install_auth_middlewares(app, scheduler, ...)`.
"""
from __future__ import annotations

import logging
import os
from collections.abc import Callable, Iterable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from aios_kernel.gateway.auth import RateLimiter, verify_jwt

log = logging.getLogger("aios_kernel.gateway.auth_middleware")


def _env_enabled(name: str) -> bool:
    """Strict boolean parsing: the string '0' must mean false."""
    raw = os.environ.get(name, "0").strip().lower()
    if raw in ("1", "true", "yes", "on"):
        return True
    if raw in ("0", "false", "no", "off", ""):
        return False
    raise ValueError(f"invalid boolean environment value for {name}: {raw!r}")


class JWTAuthMiddleware(BaseHTTPMiddleware):
    """Validate Bearer JWT on protected routes."""

    def __init__(self, app, *, protected_paths: Iterable[str] = ("/tasks",)):
        super().__init__(app)
        self._protected_paths = tuple(protected_paths)
        self._required = _env_enabled("AIOS_KERNEL_AUTH_REQUIRED")
        self._jwt_secret = b""
        if self._required:
            value = os.environ.get("AIOS_KERNEL_JWT_SECRET", "")
            if len(value.encode("utf-8")) < 32:
                raise RuntimeError("AIOS_KERNEL_JWT_SECRET must be set (32+ bytes) when JWT auth is required")
            self._jwt_secret = value.encode("utf-8")

    async def dispatch(self, request: Request, call_next: Callable):
        if not self._required:
            return await call_next(request)
        path = request.url.path
        if not any(path == p or path.startswith(p + "/") for p in self._protected_paths):
            return await call_next(request)
        auth = request.headers.get("authorization", "")
        if not auth.lower().startswith("bearer "):
            return Response(
                '{"detail":"missing bearer token"}',
                status_code=401,
                media_type="application/json",
            )
        token = auth.split(None, 1)[1]
        try:
            claims = verify_jwt(token, self._jwt_secret)
        except Exception as exc:  # noqa: BLE001
            return Response(
                f'{{"detail":"invalid token: {type(exc).__name__}"}}',
                status_code=401,
                media_type="application/json",
            )
        request.state.user = claims
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-worker-id token bucket."""

    def __init__(self, app, *, capacity: float = 100.0, refill_rate: float = 10.0):
        super().__init__(app)
        self._enabled = _env_enabled("AIOS_KERNEL_RATELIMIT_ENABLED")
        self._limiter = RateLimiter(capacity=capacity, refill_rate=refill_rate)

    async def dispatch(self, request: Request, call_next: Callable):
        if not self._enabled:
            return await call_next(request)
        # resolve worker-id from request.state.user (set by JWTAuthMiddleware)
        # or from path param / "anon" as fallback
        user = getattr(request.state, "user", None)
        if isinstance(user, dict) and "sub" in user:
            wid = str(user["sub"])
        else:
            wid = "anon"
        if not self._limiter.try_acquire(wid):
            return Response(
                '{"detail":"rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )
        return await call_next(request)


def install_auth_middlewares(
    app: FastAPI,
    *,
    protected_paths: list[str] | None = None,
    rl_capacity: float = 100.0,
    rl_refill_rate: float = 10.0,
) -> None:
    """Install both middlewares (gated by env vars)."""
    app.add_middleware(RateLimitMiddleware, capacity=rl_capacity, refill_rate=rl_refill_rate)
    app.add_middleware(
        JWTAuthMiddleware,
        protected_paths=protected_paths or ("/tasks",),
    )


__all__ = [
    "JWTAuthMiddleware",
    "RateLimitMiddleware",
    "install_auth_middlewares",
]
