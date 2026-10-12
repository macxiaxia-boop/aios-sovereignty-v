"""gateway/auth.py - JWT auth + token bucket rate limit (R1503-009).

R1503-009 acceptance:
  - JWTAuth.verify(token) -> claims dict or raises
  - RateLimiter.try_acquire(worker_id) -> bool
  - token bucket per worker
  - Tests >= 80% coverage

Co-Authored-By: Claude Code (Agent 3 / OpenClaw) via AIOS R1503
"""
from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

log = logging.getLogger("aios_kernel.gateway.auth")


# ---------- JWT (HMAC-SHA256, no external deps) ------------------------------


class InvalidToken(Exception):
    pass


def _b64url_encode(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(s: str) -> bytes:
    import base64

    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def _hmac_sha256(key: bytes, msg: bytes) -> str:
    import hashlib
    import hmac

    return _b64url_encode(hmac.new(key, msg, hashlib.sha256).digest())


def sign_jwt(payload: dict, secret: bytes, *, ttl_s: int = 3600) -> str:
    """Compact JWT (HS256)."""
    import base64
    import json

    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = dict(payload)
    payload.setdefault("iat", now)
    payload.setdefault("exp", now + ttl_s)
    h = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    p = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{h}.{p}".encode()
    sig = _hmac_sha256(secret, signing_input)
    return f"{h}.{p}.{sig}"


def verify_jwt(token: str, secret: bytes) -> dict:
    """Verify HS256 JWT. Raises InvalidToken on any failure. Returns claims."""
    import json

    try:
        h, p, s = token.split(".")
    except ValueError as exc:
        raise InvalidToken(f"malformed token: {exc}") from exc
    expected_sig = _hmac_sha256(secret, f"{h}.{p}".encode())
    if expected_sig != s:
        raise InvalidToken("bad signature")
    try:
        header = json.loads(_b64url_decode(h))
        payload = json.loads(_b64url_decode(p))
    except Exception as exc:  # noqa: BLE001
        raise InvalidToken(f"bad payload: {exc}") from exc
    if header.get("alg") != "HS256":
        raise InvalidToken("unsupported alg")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise InvalidToken("expired")
    return payload


# ---------- Rate Limiter (token bucket per worker) -----------------------


@dataclass
class _BucketState:
    tokens: float
    last_refill_ts: float


class RateLimiter:
    """Per-worker token bucket rate limiter.

    capacity = max tokens (refills to this)
    refill_rate = tokens per second
    """

    def __init__(self, *, capacity: float = 100.0, refill_rate: float = 10.0) -> None:
        self._capacity = capacity
        self._refill_rate = refill_rate
        self._buckets: dict[str, _BucketState] = {}
        self._lock = threading.Lock()

    def try_acquire(self, worker_id: str, cost: float = 1.0) -> bool:
        with self._lock:
            now = time.time()
            st = self._buckets.get(worker_id)
            if st is None:
                st = _BucketState(tokens=self._capacity, last_refill_ts=now)
                self._buckets[worker_id] = st
            # refill
            elapsed = now - st.last_refill_ts
            st.tokens = min(
                self._capacity, st.tokens + elapsed * self._refill_rate
            )
            st.last_refill_ts = now
            if st.tokens >= cost:
                st.tokens -= cost
                return True
            return False

    def reset(self, worker_id: str) -> None:
        with self._lock:
            self._buckets.pop(worker_id, None)


__all__ = [
    "JWTAuth",
    "InvalidToken",
    "RateLimiter",
    "sign_jwt",
    "verify_jwt",
]