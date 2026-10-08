#!/usr/bin/env python3
# v2/tests/test_p8_t21.py - P8 T21: REAL OpenClaw HTTP dispatch
#
# Real HTTP GET /healthz dispatch. Result envelope must contain the parsed
# /healthz body and status=200.
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


def test_t21_real_openclaw_dispatch_end_to_end():
    """Real HTTP GET /healthz dispatch via set_dispatcher."""
    set_dispatcher(make_openclaw_adapter())
    try:
        env = build_envelope(
            "codex", "openclaw", "task",
            {"action": "health",
             "evidence_marker": "P8-T21-" + uuid.uuid4().hex[:8]},
        )
        res = enqueue(env)
        assert res["file"] is not None, f"envelope deduped: {res}"
        target = INBOX / Path(res["file"]).name
        assert target.exists(), f"envelope file missing: {target}"
        out = dispatch_envelope(target, env)
        assert out["ok"] is True, f"dispatch failed: {out}"
        result_id = next(s["result_id"] for s in out["steps"] if s["step"] == "result_envelope")
        result_files = [p for p in INBOX.glob(f"{result_id}__*.json") if ".tmp." not in p.name]
        assert len(result_files) == 1, f"result envelope count != 1: {result_files}"
        result = json.loads(result_files[0].read_text(encoding="utf-8"))
        # Result envelope payload is {"output": adapter_result}; unwrap one level
        adapter_result = result["payload"].get("output", result["payload"])
        assert adapter_result["transport"] == "openclaw_http", \
            f"unexpected transport: {adapter_result.get('transport')}"
        assert adapter_result["status"] == 200, \
            f"unexpected status: {adapter_result.get('status')}"
        assert adapter_result.get("body_json") == {"ok": True, "status": "live"}, \
            f"unexpected body_json: {adapter_result.get('body_json')}"
        return {"ok": True, "status": adapter_result["status"],
                "body_json": adapter_result["body_json"],
                "transport": adapter_result["transport"]}
    finally:
        set_dispatcher(None)


if __name__ == "__main__":
    r = test_t21_real_openclaw_dispatch_end_to_end()
    print(f"T21: ok={r['ok']} transport={r['transport']} status={r['status']}")