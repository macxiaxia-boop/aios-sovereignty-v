#!/usr/bin/env python3
# v2/tests/test_p8_t10.py — P8 T10: OpenClaw 404 handling for unknown path
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.openclaw_adapter import _openclaw_dispatch_adapter


def test_t10_openclaw_unknown_action_routes_to_health():
    """Unknown action falls back to 'health' and returns /healthz probe."""
    env = {
        "id": "t10-unknown-action",
        "sender": "codex",
        "recipient": "openclaw",
        "message_type": "task",
        "payload": {"action": "nonexistent_action_xyz"},
    }
    out = _openclaw_dispatch_adapter(env, recipient="openclaw")
    # Should have routed to /healthz (status 200) since action was unknown
    assert "ok" in out
    assert out["transport"] == "openclaw_http"
    assert out["action"] == "health", f"expected fallback to health, got {out['action']}"
    assert out["url"].endswith("/healthz")
    # Real /healthz returns 200 with JSON
    assert out["status"] == 200
    assert "json" in out["content_type"].lower()
    assert out["body_json"] == {"ok": True, "status": "live"}
    result = out
    assert result

if __name__ == "__main__":
    test_t10_openclaw_unknown_action_routes_to_health()
    print("PASS: test_t10_openclaw_unknown_action_routes_to_health")
