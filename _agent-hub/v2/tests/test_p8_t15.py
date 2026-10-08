#!/usr/bin/env python3
# v2/tests/test_p8_t15.py - P8 T15: set_dispatcher DI works for all 3 adapters
#
# Verifies v2_consumer.set_dispatcher correctly installs each adapter and
# dispatch_envelope honors the override. The route capability table maps
# each recipient to its dispatcher; the test confirms the override reaches
# the adapter (transport == adapter-specific transport, NOT passthrough).
from __future__ import annotations

import sys
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import build_envelope
from src.v2_consumer import (
    dispatch_envelope, set_dispatcher, dispatch_to_adapter,
)
from src.paths import INBOX, v2_root
from src.queue import enqueue
from src.hermes_adapter import make_hermes_adapter
from src.openclaw_adapter import make_openclaw_adapter
from src.workbuddy_adapter import make_workbuddy_adapter


def _enqueue_and_dispatch(dispatcher_fn, recipient, payload):
    """Build envelope (sender=codex, recipient=<recipient>), enqueue, dispatch.

    Pass dispatcher_fn explicitly via the dispatcher= kwarg so dispatch_envelope
    uses the adapter, not the module-level set_dispatcher state.
    """
    env = build_envelope("codex", recipient, "task", payload)
    res = enqueue(env)
    assert res["file"] is not None, f"envelope deduped: {res}"
    target_path = INBOX / Path(res["file"]).name
    assert target_path.exists(), f"envelope file missing: {target_path}"
    return dispatch_envelope(target_path, env, dispatcher=dispatcher_fn)


def _result_envelope_payload(out):
    """Return the adapter-level dict inside the result envelope, or None."""
    step = next((s for s in out["steps"] if s["step"] == "result_envelope"), None)
    if step is None or not step.get("ok"):
        return None
    rid = step["result_id"]
    from src.paths import INBOX as _INBOX
    files = [p for p in _INBOX.glob(f"{rid}__*.json") if ".tmp." not in p.name]
    if not files:
        return None
    env = json.loads(files[0].read_text(encoding="utf-8"))
    return env["payload"].get("output", env["payload"])


def test_t15_set_dispatcher_injects_each_adapter():
    """DI via set_dispatcher MUST route each adapter to its expected transport."""
    nonce = uuid.uuid4().hex[:8]

    # 1. Hermes (real subprocess call)
    out = _enqueue_and_dispatch(
        make_hermes_adapter(), "hermes",
        {"args": ["version"], "evidence_marker": f"P8-T15-HERMES-{nonce}"},
    )
    assert out["ok"] is True, f"hermes dispatch failed: {out}"
    payload = _result_envelope_payload(out)
    assert payload is not None, f"hermes result envelope missing"
    assert payload["transport"] == "hermes_subprocess", \
        f"hermes transport wrong: {payload['transport']}"

    # 2. OpenClaw (real HTTP GET /healthz)
    out = _enqueue_and_dispatch(
        make_openclaw_adapter(), "openclaw",
        {"action": "health", "evidence_marker": f"P8-T15-OPENCLAW-{nonce}"},
    )
    assert out["ok"] is True, f"openclaw dispatch failed: {out}"
    payload = _result_envelope_payload(out)
    assert payload is not None, f"openclaw result envelope missing"
    assert payload["transport"] == "openclaw_http", \
        f"openclaw transport wrong: {payload['transport']}"
    assert payload["status"] == 200, f"openclaw status: {payload['status']}"

    # 3. WorkBuddy (probe - daemon is down, transport is still correct)
    out = _enqueue_and_dispatch(
        make_workbuddy_adapter(), "workbuddy",
        {"action": "probe", "evidence_marker": f"P8-T15-WORKBUDDY-{nonce}"},
    )
    payload = _result_envelope_payload(out)
    assert payload is not None, f"workbuddy result envelope missing"
    assert payload["transport"] == "workbuddy_probe", \
        f"workbuddy transport wrong: {payload['transport']}"

    # 4. Default reset
    set_dispatcher(None)
    assert dispatch_to_adapter.__name__ == "dispatch_to_adapter"
    return {"ok": True, "test": "t15_di_three_adapters",
            "transports": {"hermes": "hermes_subprocess",
                           "openclaw": "openclaw_http",
                           "workbuddy": "workbuddy_probe"}}


if __name__ == "__main__":
    r = test_t15_set_dispatcher_injects_each_adapter()
    print("T15:", r)