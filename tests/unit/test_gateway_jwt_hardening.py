"""Gateway JWT regression tests; no external services or accounts."""
from __future__ import annotations

import time

import pytest

from aios_kernel.gateway.auth import InvalidToken, sign_jwt, verify_jwt

SECRET = b"aios-local-unit-test-secret-32bytes-and-more"


def _signed(extra=None):
    claims = {"sub": "worker-1", "tenant_id": "tenant-1"}
    if extra:
        claims.update(extra)
    return sign_jwt(claims, SECRET)


def test_signed_token_still_works():
    assert verify_jwt(_signed(), SECRET)["sub"] == "worker-1"


def test_future_nbf_is_not_authorized_even_with_correct_signature():
    with pytest.raises(InvalidToken, match="nbf"):
        verify_jwt(_signed({"nbf": int(time.time()) + 3600}), SECRET)


def test_nbf_in_past_is_authorized():
    token = _signed({"nbf": int(time.time()) - 60})
    assert verify_jwt(token, SECRET)["tenant_id"] == "tenant-1"


def test_future_issued_at_is_not_authorized():
    with pytest.raises(InvalidToken, match="iat"):
        verify_jwt(_signed({"iat": int(time.time()) + 3600}), SECRET)


@pytest.mark.parametrize("claim,value", [
    ("exp", "next-week"), ("exp", True), ("exp", None),
    ("iat", "future"), ("nbf", True),
])
def test_malformed_temporal_claims_fail_closed(claim, value):
    with pytest.raises(InvalidToken):
        verify_jwt(_signed({claim: value}), SECRET)


def test_expired_token_fails_closed():
    with pytest.raises(InvalidToken, match="exp"):
        verify_jwt(_signed({"exp": int(time.time()) - 1}), SECRET)


def test_wrong_secret_still_fails():
    with pytest.raises(InvalidToken, match="signature"):
        verify_jwt(_signed(), b"completely-different-signing-secret-over-32")
