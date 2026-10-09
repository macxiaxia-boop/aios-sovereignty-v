#!/usr/bin/env python3
# v2/tests/test_p8_t24.py - P8 T24: End-to-end smoke: 3 adapters + verifier wiring
#
# Sends one real envelope to each adapter (hermes, openclaw, workbuddy) and
# verifies each result envelope exists with matching correlation_id and
# adapter signature. Final ack/result split must be intact for all 3.
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
from src.hermes_adapter import make_hermes_adapter
from src.openclaw_adapter import make_openclaw_adapter
from src.workbuddy_adapter import make_workbuddy_adapter


def _dispatch_and_verify(recipient, dispatcher_fn, payload, marker):
    """Helper: dispatch via dispatcher_fn and verify result envelope on disk."""
    set_dispatcher(dispatcher_fn)
    try:
        env = build_envelope("codex", recipient, "task", payload)
        res = enqueue(env)
        assert res["file"] is not None, f"{recipient} envelope deduped: {res}"
        target = INBOX / Path(res["file"]).name
        assert target.exists(), f"{recipient} envelope missing: {target}"
        out = dispatch_envelope(target, env)
        result_id = next((s["result_id"] for s in out["steps"] if s["step"] == "result_envelope"), None)
        assert result_id, f"{recipient} missing result_envelope step: {out['steps']}"
        result_files = [p for p in INBOX.glob(f"{result_id}__*.json") if ".tmp." not in p.name]
        assert len(result_files) == 1, f"{recipient} result envelope count != 1: {result_files}"
        result = json.loads(result_files[0].read_text(encoding="utf-8"))
        ack_id = next((s["ack_id"] for s in out["steps"] if s["step"] == "ack_envelope"), None)
        assert ack_id and ack_id != result_id, f"{recipient} ack envelope missing or == result_id"
        ack_files = [p for p in INBOX.glob(f"{ack_id}__*.json") if ".tmp." not in p.name]
        assert len(ack_files) == 1, f"{recipient} ack envelope count != 1: {ack_files}"
        assert result["correlation_id"] == env["id"]
        assert result["in_reply_to"] == env["id"]
        adapter_result = result["payload"].get("output", result["payload"])
        return {"recipient": recipient, "ok": out["ok"], "transport": adapter_result["transport"],
                "result_id": result_id, "ack_id": ack_id, "marker": marker}
    finally:
        set_dispatcher(None)


def test_t24_e2e_three_adapters_full_smoke():
    """Full e2e: hermes + openclaw + workbuddy each produce ack + result envelopes."""
    nonce = uuid.uuid4().hex[:8]
    out = {
        "hermes": _dispatch_and_verify(
            "hermes", make_hermes_adapter(),
            {"title": "P8-T24 hermes e2e", "args": ["version"], "evidence_marker": f"P8-T24-HERMES-{nonce}"},
            f"P8-T24-HERMES-{nonce}",
        ),
        "openclaw": _dispatch_and_verify(
            "openclaw", make_openclaw_adapter(),
            {"title": "P8-T24 openclaw e2e", "action": "health", "evidence_marker": f"P8-T24-OPENCLAW-{nonce}"},
            f"P8-T24-OPENCLAW-{nonce}",
        ),
        "workbuddy": _dispatch_and_verify(
            "workbuddy", make_workbuddy_adapter(),
            {"title": "P8-T24 workbuddy e2e", "action": "probe", "evidence_marker": f"P8-T24-WORKBUDDY-{nonce}"},
            f"P8-T24-WORKBUDDY-{nonce}",
        ),
    }
    assert out["hermes"]["transport"] == "hermes_subprocess"
    assert out["hermes"]["ok"] is True
    assert out["openclaw"]["transport"] == "openclaw_http"
    assert out["openclaw"]["ok"] is True
    assert out["workbuddy"]["transport"] == "workbuddy_probe"
    result = out
    assert result

if __name__ == "__main__":
    test_t24_e2e_three_adapters_full_smoke()
    print("PASS: test_t24_e2e_three_adapters_full_smoke")
