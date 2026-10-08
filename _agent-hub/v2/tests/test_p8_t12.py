#!/usr/bin/env python3
# v2/tests/test_p8_t12.py — P8 T12: WorkBuddy dispatch blocked when daemon down
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.workbuddy_adapter import _workbuddy_dispatch_adapter


def test_t12_workbuddy_dispatch_blocked_with_evidence():
    """Non-probe dispatch returns ok=False with workbuddy_blocked_daemon_down."""
    env = {
        "id": "t12-dispatch",
        "sender": "codex",
        "recipient": "workbuddy",
        "message_type": "task",
        "payload": {"action": "send_message", "target": "user@workbuddy"},
    }
    out = _workbuddy_dispatch_adapter(env, recipient="workbuddy")
    assert out["ok"] is False
    assert out["transport"] == "workbuddy_blocked_daemon_down"
    assert out["reason"] == "workbuddy_daemon_not_running"
    assert "evidence" in out
    assert out["evidence"]["alive"] is False
    result = out
    assert result

if __name__ == "__main__":
    test_t12_workbuddy_dispatch_blocked_with_evidence()
    print("PASS: test_t12_workbuddy_dispatch_blocked_with_evidence")
