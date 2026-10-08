#!/usr/bin/env python3
# v2/tests/test_p8_t18.py - P8 T18: Idempotency / retry envelope
#
# Dispatch the same envelope twice; second dispatch must NOT crash and MUST
# return a structured dispatch dict. evidence_marker is unique so the
# payload's idempotency_key is unique across the test session.
from __future__ import annotations

import sys
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import build_envelope
from src.v2_consumer import dispatch_envelope, set_dispatcher
from src.paths import INBOX
from src.queue import enqueue
from src.openclaw_adapter import make_openclaw_adapter


def test_t18_idempotent_retry_of_same_envelope():
    """Dispatch the same envelope twice; consumer must NOT crash on second attempt."""
    set_dispatcher(make_openclaw_adapter())
    try:
        env = build_envelope(
            "codex", "openclaw", "task",
            {"action": "health",
             "evidence_marker": "P8-T18-" + uuid.uuid4().hex[:8]},
        )
        res = enqueue(env)
        assert res["file"] is not None, f"envelope deduped: {res}"
        target = INBOX / Path(res["file"]).name
        assert target.exists(), f"envelope file missing after enqueue: {target}"
        out1 = dispatch_envelope(target, env)
        assert out1["ok"] is True, f"first dispatch failed: {out1}"
        try:
            out2 = dispatch_envelope(target, env)
        except Exception as e:
            raise AssertionError(f"second dispatch raised: {e}")
        assert "ok" in out2
        assert "steps" in out2
        return {"first_ok": out1["ok"], "second_ok": out2["ok"],
                "second_steps": [s.get("step") for s in out2["steps"]]}
    finally:
        set_dispatcher(None)


if __name__ == "__main__":
    r = test_t18_idempotent_retry_of_same_envelope()
    print("T18:", r)