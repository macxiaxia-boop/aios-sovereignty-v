#!/usr/bin/env python3
# v2/tests/test_p8_t09.py — P8 T09: OpenClaw connection refused (wrong port)
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.openclaw_adapter import _openclaw_dispatch_adapter


def test_t09_openclaw_connection_refused():
    """Adapter to a wrong port must return ok=False with url_error."""
    import src.openclaw_adapter as oa
    orig_base = oa.OPENCLAW_BASE
    oa.OPENCLAW_BASE = "http://127.0.0.1:1"  # nothing listening here
    try:
        env = {
            "id": "t09-refused",
            "sender": "codex",
            "recipient": "openclaw",
            "message_type": "task",
            "payload": {"action": "health"},
        }
        out = _openclaw_dispatch_adapter(env, recipient="openclaw")
        assert out["ok"] is False
        assert out["transport"] == "openclaw_http"
        assert "error" in out
        # url_error or socket_timeout — both acceptable for "no server"
        assert ("url_error" in out["error"]) or ("timeout" in out["error"]), \
            f"expected url_error/timeout, got {out['error']}"
        result = out
        assert result
    finally:
        oa.OPENCLAW_BASE = orig_base

if __name__ == "__main__":
    test_t09_openclaw_connection_refused()
    print("PASS: test_t09_openclaw_connection_refused")
