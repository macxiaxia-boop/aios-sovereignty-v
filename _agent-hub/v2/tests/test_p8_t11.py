#!/usr/bin/env python3
# v2/tests/test_p8_t11.py — P8 T11: WorkBuddy probe with daemon DOWN
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.workbuddy_adapter import _workbuddy_dispatch_adapter


def test_t11_workbuddy_probe_returns_honest_evidence():
    """Probe must return ok=False with evidence when daemon is stale/down."""
    env = {
        "id": "t11-probe",
        "sender": "codex",
        "recipient": "workbuddy",
        "message_type": "task",
        "payload": {"action": "probe"},
    }
    out = _workbuddy_dispatch_adapter(env, recipient="workbuddy")
    # Current state on host: daemon stale 4+ hours, 0 processes -> alive=False
    assert out["transport"] == "workbuddy_probe"
    assert out["action"] == "probe"
    # probe dict MUST exist with real evidence
    assert "probe" in out
    probe = out["probe"]
    assert "checks" in probe
    assert "daemon_log" in probe["checks"]
    # root SHOULD exist (workbuddy is installed) — this is the install evidence
    assert probe["checks"]["root_exists"] is True
    # processes SHOULD be empty (daemon not running)
    procs = probe["checks"]["processes"]
    assert isinstance(procs, dict)
    assert procs["count"] == 0, f"expected 0 workbuddy processes, got {procs}"
    # daemon_log SHOULD be marked stale
    log = probe["checks"]["daemon_log"]
    assert log["exists"] is True
    assert log["stale"] is True
    # alive should be False (composite)
    assert probe["alive"] is False
    # outer ok should be False (probe returns ok = probe.alive)
    assert out["ok"] is False
    return out


if __name__ == "__main__":
    r = test_t11_workbuddy_probe_returns_honest_evidence()
    print("T11: alive=", r["probe"]["alive"], "stale=", r["probe"]["checks"]["daemon_log"]["stale"])
