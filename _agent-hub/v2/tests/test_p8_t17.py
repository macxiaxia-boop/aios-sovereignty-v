#!/usr/bin/env python3
# v2/tests/test_p8_t17.py — P8 T17: Burst of 10 envelopes to OpenClaw
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.openclaw_adapter import _openclaw_dispatch_adapter


def test_t17_openclaw_burst_10_envelopes():
    """Fire 10 HTTP envelopes at openclaw; all should return 200."""
    actions = ["health"] * 6 + ["ui"] * 2 + ["capabilities"] * 2
    results = []
    for i, action in enumerate(actions):
        env = {
            "id": f"t17-burst-{i:02d}",
            "sender": "codex",
            "recipient": "openclaw",
            "message_type": "task",
            "payload": {"action": action},
        }
        out = _openclaw_dispatch_adapter(env, recipient="openclaw")
        results.append({
            "i": i,
            "action": action,
            "ok": out["ok"],
            "status": out.get("status"),
            "duration_ms": out.get("duration_ms", 0),
        })
    # health & ui return 200; capabilities is HTML so also 200
    failed = [r for r in results if not r["ok"]]
    assert not failed, f"some HTTP calls failed: {failed}"
    # All should be 200
    statuses = [r["status"] for r in results]
    assert all(s == 200 for s in statuses), f"non-200 statuses: {statuses}"
    return {"count": len(results), "statuses": statuses}


if __name__ == "__main__":
    r = test_t17_openclaw_burst_10_envelopes()
    print(f"T17: {r['count']} ok, statuses={set(r['statuses'])}")
