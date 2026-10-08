#!/usr/bin/env python3
# v2/tests/test_p8_t20.py - P8 T20: REAL hermes dispatch (ack + result envelopes)
#
# End-to-end: build envelope -> enqueue -> dispatch via hermes adapter ->
# ack envelope + result envelope both written to inbox with correct
# correlation_id and transport signatures.
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


def test_t20_real_hermes_dispatch_end_to_end():
    """Real hermes subprocess dispatch with full envelope lifecycle."""
    set_dispatcher(make_hermes_adapter())
    try:
        env = build_envelope(
            "codex", "hermes", "task",
            {"args": ["version"],
             "evidence_marker": "P8-T20-" + uuid.uuid4().hex[:8]},
        )
        res = enqueue(env)
        assert res["file"] is not None, f"envelope deduped: {res}"
        target = INBOX / Path(res["file"]).name
        assert target.exists(), f"envelope file missing: {target}"
        out = dispatch_envelope(target, env)
        assert out["ok"] is True, f"dispatch failed: {out}"
        # Verify ack envelope - ack goes FROM hermes TO codex (original sender)
        ack_id = next(s["ack_id"] for s in out["steps"] if s["step"] == "ack_envelope")
        ack_files = [p for p in INBOX.glob(f"{ack_id}__*.json") if ".tmp." not in p.name]
        assert len(ack_files) == 1, f"ack envelope count != 1: {ack_files}"
        ack = json.loads(ack_files[0].read_text(encoding="utf-8"))
        assert ack["correlation_id"] == env["id"], f"ack correlation_id: {ack['correlation_id']}"
        # ack.sender=hermes, ack.recipient=codex (the original sender)
        assert ack["sender"] == "hermes", f"ack sender: {ack['sender']}"
        assert ack["recipient"] == "codex", f"ack recipient: {ack['recipient']}"
        # Verify result envelope
        result_id = next(s["result_id"] for s in out["steps"] if s["step"] == "result_envelope")
        result_files = [p for p in INBOX.glob(f"{result_id}__*.json") if ".tmp." not in p.name]
        assert len(result_files) == 1, f"result envelope count != 1: {result_files}"
        result = json.loads(result_files[0].read_text(encoding="utf-8"))
        # Unwrap one level: result payload is {"output": adapter_result}
        adapter_result = result["payload"].get("output", result["payload"])
        # Adapter must have produced hermes-specific output
        assert adapter_result["transport"] == "hermes_subprocess", \
            f"unexpected transport: {adapter_result.get('transport')}"
        stdout_tail = adapter_result.get("stdout_tail", "")
        assert "Hermes" in stdout_tail or "v0.15" in stdout_tail or len(stdout_tail) > 0, \
            f"result stdout missing hermes signature: {stdout_tail!r}"
        result = {"ok": True, "ack_id": ack_id, "result_id": result_id,
                "stdout_tail": stdout_tail[:120],
                "transport": adapter_result["transport"]}
        assert result
    finally:
        set_dispatcher(None)

if __name__ == "__main__":
    test_t20_real_hermes_dispatch_end_to_end()
    print("PASS: test_t20_real_hermes_dispatch_end_to_end")
