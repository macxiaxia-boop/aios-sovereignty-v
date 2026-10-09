#!/usr/bin/env python3
# v2/tests/test_p8_t22.py - P8 T22: REAL WorkBuddy probe (daemon down)
#
# Honest verification: daemon is down so probe returns ok=False with
# structured evidence. The result envelope MUST be written regardless of
# adapter ok (since dispatcher ran without exception).
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
from src.message_queue import enqueue
from src.workbuddy_adapter import make_workbuddy_adapter


def test_t22_real_workbuddy_probe_end_to_end():
    """Real workbuddy probe (daemon down) - verify evidence is in result envelope."""
    set_dispatcher(make_workbuddy_adapter())
    try:
        env = build_envelope(
            "codex", "workbuddy", "task",
            {"title": "WorkBuddy probe e2e", "action": "probe",
             "evidence_marker": "P8-T22-" + uuid.uuid4().hex[:8]},
        )
        res = enqueue(env)
        assert res["file"] is not None, f"envelope deduped: {res}"
        target = INBOX / Path(res["file"]).name
        assert target.exists(), f"envelope file missing: {target}"
        out = dispatch_envelope(target, env)
        # Dispatch envelope succeeded (dispatcher ran cleanly even though daemon is down)
        assert out["ok"] is True, f"dispatch failed: {out}"
        result_id = next(s["result_id"] for s in out["steps"] if s["step"] == "result_envelope")
        result_files = [p for p in INBOX.glob(f"{result_id}__*.json") if ".tmp." not in p.name]
        assert len(result_files) == 1, f"result envelope count != 1: {result_files}"
        result = json.loads(result_files[0].read_text(encoding="utf-8"))
        adapter_result = result["payload"].get("output", result["payload"])
        assert adapter_result["transport"] == "workbuddy_probe", \
            f"unexpected transport: {adapter_result.get('transport')}"
        assert adapter_result["probe"]["alive"] is False  # daemon is down
        assert adapter_result["probe"]["checks"]["daemon_log"]["stale"] is True
        result = {"ok": True, "alive": adapter_result["probe"]["alive"],
                "daemon_age_sec": adapter_result["probe"]["checks"]["daemon_log"]["age_sec"],
                "transport": adapter_result["transport"]}
        assert result
    finally:
        set_dispatcher(None)

if __name__ == "__main__":
    test_t22_real_workbuddy_probe_end_to_end()
    print("PASS: test_t22_real_workbuddy_probe_end_to_end")
