#!/usr/bin/env python3
# v2/tests/test_p8_t23.py - P8 T23: Resume after partial failure
#
# Scenario: dispatcher raises mid-way through dispatch. Consumer must
# deadletter the failed envelope (with an `error` envelope tied to the
# original correlation_id) and continue processing the NEXT envelope in
# the queue. We pre-set retry_count=MAX so the first dispatch goes
# straight to the deadletter+error branch (not the silent retry branch).
from __future__ import annotations

import sys
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import build_envelope
from src.v2_consumer import dispatch_envelope, set_dispatcher, MAX_RETRIES_PER_ENVELOPE
from src.paths import INBOX
from src.message_queue import enqueue
from src.hermes_adapter import make_hermes_adapter


def _failing_dispatcher(env, *, recipient):
    """Raises an exception to simulate partial-failure mid-dispatch."""
    raise RuntimeError("simulated dispatcher crash")


def test_t23_resume_after_partial_failure():
    """Consumer must record error envelope AND continue processing next envelope."""
    # Step 1: failing dispatcher; pre-set retry_count to MAX so deadletter+error
    set_dispatcher(_failing_dispatcher)
    env1 = build_envelope(
        "codex", "hermes", "task",
        {"title": "P8-T23-fail resume", "args": ["version"],
         "marker": "p8-t23-fail",
         "evidence_marker": "P8-T23-FAIL-" + uuid.uuid4().hex[:8]},
    )
    env1["retry_count"] = MAX_RETRIES_PER_ENVELOPE  # force deadletter path
    res1 = enqueue(env1)
    assert res1["file"] is not None, f"env1 deduped: {res1}"
    target1 = INBOX / Path(res1["file"]).name
    assert target1.exists(), f"env1 file missing: {target1}"
    out1 = dispatch_envelope(target1, env1)
    # dispatch_envelope returns ok=False when dispatcher raises / deadlettered
    assert out1["ok"] is False, f"expected ok=False after dispatch failure, got {out1}"
    # Error envelope should exist with correlation_id == env1.id
    # Filename pattern: <error_uuid>__hermes__codex__error.json
    error_files = [p for p in INBOX.glob(f"*__error.json") if ".tmp." not in p.name]
    err_correlated = [p for p in error_files if env1["id"] in json.loads(p.read_text())["correlation_id"]]
    assert len(err_correlated) >= 1, f"no error envelope for {env1['id']}; found {len(error_files)} errors total"

    # Step 2: switch back to real hermes, send another envelope - must succeed (resume)
    set_dispatcher(make_hermes_adapter())
    env2 = build_envelope(
        "codex", "hermes", "task",
        {"title": "P8-T23-OK resume", "args": ["version"], "marker": "p8-t23-resume",
         "evidence_marker": "P8-T23-OK-" + uuid.uuid4().hex[:8]},
    )
    res2 = enqueue(env2)
    assert res2["file"] is not None, f"env2 deduped: {res2}"
    target2 = INBOX / Path(res2["file"]).name
    assert target2.exists(), f"env2 file missing: {target2}"
    out2 = dispatch_envelope(target2, env2)
    assert out2["ok"] is True, f"resume failed: {out2}"
    set_dispatcher(None)
    result = {"first_ok": out1["ok"], "resume_ok": out2["ok"],
            "first_error_count": len(err_correlated)}
    assert result

if __name__ == "__main__":
    test_t23_resume_after_partial_failure()
    print("PASS: test_t23_resume_after_partial_failure")
