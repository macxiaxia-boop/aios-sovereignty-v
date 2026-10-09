#!/usr/bin/env python3
# v2/tests/test_p8_t19.py - P8 T19: GoalGuard hook does not block real hermes dispatch
#
# Verifies that a valid (non-malicious) hermes envelope still passes through
# the GoalGuard hook and reaches the adapter. The goal_guard step is only
# appended when it BLOCKS; absence of a goal_guard step is the success signal.
from __future__ import annotations

import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import build_envelope
from src.v2_consumer import dispatch_envelope, set_dispatcher
from src.paths import INBOX
from src.message_queue import enqueue
from src.hermes_adapter import make_hermes_adapter


def test_t19_goalguard_allows_normal_hermes_task():
    """A normal task to hermes must pass GoalGuard and reach the adapter."""
    set_dispatcher(make_hermes_adapter())
    try:
        env = build_envelope(
            "codex", "hermes", "task",
            {"title": "Hermes version sanity", "args": ["version"],
             "note": "p8-t19-sanity",
             "evidence_marker": "P8-T19-" + uuid.uuid4().hex[:8]},
        )
        res = enqueue(env)
        assert res["file"] is not None, f"envelope deduped: {res}"
        target = INBOX / Path(res["file"]).name
        assert target.exists(), f"envelope file missing: {target}"
        out = dispatch_envelope(target, env)
        assert out["ok"] is True, f"dispatch failed: {out}"
        steps = {s["step"]: s for s in out["steps"]}
        # goal_guard step is ONLY appended when it blocks; absence = success.
        # The dispatch step MUST exist and be ok=True (proves goal_guard didn't block).
        assert steps.get("dispatch", {}).get("ok") is True, \
            f"dispatch step failed or missing: {steps.get('dispatch')}"
        # If goal_guard block did happen, the result would NOT have these steps.
        assert "claim" in steps, f"missing claim step: {list(steps.keys())}"
        assert "result_envelope" in steps, f"missing result_envelope: {list(steps.keys())}"
        result = {"ok": True,
                "goal_guard_blocked": "goal_guard" in steps and not steps["goal_guard"]["ok"],
                "dispatch_transport": "hermes_subprocess"}
        assert result
    finally:
        set_dispatcher(None)

if __name__ == "__main__":
    test_t19_goalguard_allows_normal_hermes_task()
    print("PASS: test_t19_goalguard_allows_normal_hermes_task")
