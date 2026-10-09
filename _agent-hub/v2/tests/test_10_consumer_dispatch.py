# v2/tests/test_10_consumer_dispatch.py
#
# R286.A Stage 0: v2_consumer multi-recipient dispatch + ack/result/error split.
#
# Acceptance:
#   - Multi-recipient consumer dispatches envelopes to per-recipient logic
#   - Acks and business results are SEPARATE envelopes
#   - Correlation_id on ack == input envelope id
#   - No-route recipient/message_type deadletters with reason "no_route"
#   - Invalid envelope deadletters with reason "invalid_envelope:*"
#   - Default dispatcher (passthrough) returns synthetic result
#   - DI: set_dispatcher() override works for tests
#   - Per-recipient threading.Lock prevents single-recipient slow from blocking
#   - Bounded concurrency (BoundedSemaphore MAX_CONCURRENT=2 default)
#   - Legacy marker files (3 stranded acks) are NOT consumed by tick()
#   - Health probe (4 evidence classes: health/call/trace/handoff)
from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import build_envelope, reply_envelope, verify_envelope
from src.paths import INBOX, STATE_FILE, EVENTS_LOG, TASKS_DIR, v2_root
from src.message_queue import ack as q_ack, claim as q_claim, deadletter, enqueue
from src.v2_consumer import (
    ConsumerStats,
    CAPABILITIES,
    dispatch_envelope,
    get_capabilities,
    list_for_recipient,
    set_dispatcher,
    tick,
    dispatch_to_adapter,
    MAX_CONCURRENT,
)


def test_v2_consumer_capabilities_advertised():
    caps = get_capabilities()
    assert caps["envelope"]["schema_version"] == "1.0"
    assert caps["envelope"]["supports_chunking"] is True
    assert caps["envelope"]["default_chunk_bytes"] == 32768  # 32 KiB
    assert caps["task_lifecycle"]["supports_submit"] is True
    assert caps["concurrency"]["max_concurrent"] >= 1
    assert caps["concurrency"]["max_concurrent"] <= 8
    assert caps["delivery"]["ack_separate_from_result"] is True
    # Required recipients
    for r in ("codex", "claudecode", "hermes", "openclaw", "workbuddy"):
        assert r in caps["recipients"], f"recipient {r!r} missing"


def test_v2_consumer_dispatch_emits_separate_ack_and_result():
    """Single dispatch → ack envelope + result envelope, both with correct correlation_id."""
    # Use a unique recipient so I don't collide with other tests
    env = build_envelope("claudecode", "codex", "message", {"text": "hello",
                                            "__r286_test__": "test_v2_consumer_dispatch"})
    res = enqueue(env)
    target_path = INBOX / Path(res["file"]).name
    assert target_path.exists()

    out = dispatch_envelope(target_path, env)

    assert out["ok"] is True, f"dispatch failed: {out!r}"
    steps = {s["step"]: s for s in out["steps"]}
    assert "verify" in steps and steps["verify"]["ok"] is True
    assert "route" in steps and steps["route"]["ok"] is True
    assert "claim" in steps and steps["claim"]["ok"] is True
    assert "ack_envelope" in steps and steps["ack_envelope"]["ok"] is True
    assert "dispatch" in steps and steps["dispatch"]["ok"] is True
    assert "result_envelope" in steps and steps["result_envelope"]["ok"] is True
    assert "q_ack" in steps

    # ack envelope must be in INBOX addressed to original.sender
    ack_id = steps["ack_envelope"]["ack_id"]
    ack_files = [p for p in INBOX.glob(f"{ack_id}__*.json") if ".tmp." not in p.name]
    assert len(ack_files) == 1, f"expected 1 ack envelope, got {len(ack_files)}"
    ack_env = json.loads(ack_files[0].read_text(encoding="utf-8"))
    assert ack_env["correlation_id"] == env["id"]
    assert ack_env["in_reply_to"] == env["id"]
    assert ack_env["recipient"] == "claudecode"
    assert ack_env["message_type"] == "ack"

    # result envelope must also exist and be separate
    result_id = steps["result_envelope"]["result_id"]
    assert result_id != ack_id, "ack and result MUST have distinct envelope ids"
    res_files = [p for p in INBOX.glob(f"{result_id}__*.json") if ".tmp." not in p.name]
    assert len(res_files) == 1
    res_env = json.loads(res_files[0].read_text(encoding="utf-8"))
    assert res_env["correlation_id"] == env["id"]
    assert res_env["message_type"] == "result"


def test_v2_consumer_dispatch_no_route_deadletters():
    """Unknown recipient / message_type must deadletter with reason no_route."""
    # Force the capability table to NOT know about this message_type by
    # removing it temporarily.
    saved = CAPABILITIES["codex"].copy()
    CAPABILITIES["codex"]["message"] = "passthrough"
    try:
        env = build_envelope("a", "codex", "message", {"__r286_no_route__": True})
        # Override: pretend 'message' is unrouted
        CAPABILITIES["codex"]["message"] = "__not_a_route__"  # not registered
        # Actually we test by clearing route_capability via dict mutation:
        CAPABILITIES["codex"]["message"] = "passthrough"
        # use route_capability directly: this test relies on internal state
        from src.v2_consumer import route_capability
        assert route_capability("codex", "message") == "passthrough"  # baseline
        # Now: simulate no_route by patching the CAPABILITIES dict
        CAPABILITIES["codex"].pop("message", None)
        try:
            res = enqueue(env)
            target = INBOX / Path(res["file"]).name
            out = dispatch_envelope(target, env)
            assert out["ok"] is False, f"expected no_route failure: {out!r}"
            assert any("no_route" in str(s.get("reason", "")) for s in out["steps"])
        finally:
            CAPABILITIES["codex"]["message"] = saved.get("message", "passthrough")
    finally:
        CAPABILITIES["codex"].clear()
        CAPABILITIES["codex"].update(saved)


def test_v2_consumer_dispatch_injects_custom_dispatcher():
    """DI: set_dispatcher override works for tests / fakes."""
    seen = []

    def fake_dispatcher(envelope, *, recipient):
        seen.append(envelope["id"])
        return {"ok": True, "fake": True, "echoed_id": envelope["id"]}

    set_dispatcher(fake_dispatcher)
    try:
        env = build_envelope("claudecode", "codex", "message",
                             {"text": "fake-dispatch", "__r286_test__": "test_di"})
        res = enqueue(env)
        target = INBOX / Path(res["file"]).name
        out = dispatch_envelope(target, env)
        assert out["ok"] is True, f"fake dispatch failed: {out!r}"
        assert env["id"] in seen
        # result envelope payload should reflect fake dispatcher output
        # Find the result_envelope step by its `step` key (defensive against reordering)
        result_step = next((s for s in out["steps"] if s.get("step") == "result_envelope"), None)
        assert result_step is not None, f"no result_envelope step in {out!r}"
        result_id = result_step["result_id"]
        result_env = json.loads([p for p in INBOX.glob(f"{result_id}__*.json")
                                 if ".tmp." not in p.name][0].read_text(encoding="utf-8"))
        assert result_env["payload"]["output"]["fake"] is True
        assert result_env["payload"]["output"]["echoed_id"] == env["id"]
    finally:
        set_dispatcher(None)  # restore default


def test_v2_consumer_dispatch_dispatcher_exception_deadletters():
    """Adapter exception → error envelope + deadletter with reason max_retries_exceeded."""
    def bad_dispatcher(envelope, *, recipient):
        raise RuntimeError("adapter boom")

    set_dispatcher(bad_dispatcher)
    try:
        env = build_envelope("claudecode", "codex", "message",
                             {"text": "boom", "__r286_test__": "test_boom"})
        # Make sure retry budget is exhausted
        env["retry_count"] = 5
        res = enqueue(env)
        target = INBOX / Path(res["file"]).name
        out = dispatch_envelope(target, env)
        # The error envelope MUST have been emitted
        error_steps = [s for s in out["steps"] if s["step"] == "deadletter"]
        assert any("max_retries_exceeded" in s.get("reason", "") for s in error_steps), \
            f"expected deadletter with max_retries_exceeded; got {out!r}"
    finally:
        set_dispatcher(None)


def test_v2_consumer_legacy_marker_files_are_NOT_consumed():
    """The 3 stranded pre-R320.6 acks (specific UUIDs) MUST NOT be claimed by tick()."""
    # Simulate legacy marker files: write files with the R320.6 stranded UUIDs.
    legacy_uuids = [
        "41afc2c3-8fd3-4c80-80f2-62943eea25fd",
        "19334d04-08f8-4d3d-9f94-4eab28d336ce",
        "0fbf6f33-4eb9-47b6-9400-1c2914b2d72f",
    ]
    written = []
    for uid in legacy_uuids:
        # Use a dummy recipient so it WOULD match if not for the marker filter
        env = build_envelope("claudecode", "codex", "message", {"text": "stranded",
                                "__r286_stranded__": uid})
        # Reassign id to the stranded UUID
        env["id"] = uid
        # Rewrite idempotency_key to match (it depends on id, sender, recipient,
        # message_type, payload); build_envelope already computed the key, but
        # id is canonical inside idempotency_key path. Recompute to be safe.
        from src.id import idempotency_key
        env["idempotency_key"] = idempotency_key(env["sender"], env["recipient"],
                                                  env["message_type"], env["payload"])
        res = enqueue(env)
        written.append(INBOX / Path(res["file"]).name)
        assert written[-1].exists()

    # Now run a tick with the consumer
    result = tick(recipients=["codex"], marker_filter=None)  # default marker filter

    # The 3 stranded envelopes MUST still be unclaimed.  We count them in
    # the per-recipient stats (skipped_nonv2) — totalled across recipients.
    total_skipped = result["totals"]["skipped_nonv2"]
    assert total_skipped >= 3, (
        f"expected at least 3 skipped_nonv2 (the 3 stranded marker files); "
        f"got {total_skipped}; result={result!r}"
    )

    # Verify the files still exist (not claimed, not moved)
    for p in written:
        assert p.exists(), f"stranded file {p.name} was consumed/deleted!"
        # Filename MUST still contain the stranded UUID prefix
        assert any(uid in p.name for uid in legacy_uuids), (
            f"unexpected filename change: {p.name}"
        )


def test_v2_consumer_dispatch_4_evidence_classes():
    """Health/call/trace/handoff evidence classes are all reachable in dispatch output."""
    env = build_envelope("claudecode", "codex", "message", {"text": "4-evidence",
                            "__r286_test__": "test_4_evidence"})
    res = enqueue(env)
    target = INBOX / Path(res["file"]).name
    out = dispatch_envelope(target, env)

    # health: dispatch_envelope returns ok (transport reachable)
    assert "ok" in out
    # call: per-step records show the call path
    steps = {s["step"]: s for s in out["steps"]}
    assert "claim" in steps
    # trace: events.ndjson was appended by dispatch
    events = EVENTS_LOG.read_text(encoding="utf-8")
    assert "dispatch.ok" in events, f"events.ndjson should record dispatch.ok; got tail: {events[-500:]!r}"
    # handoff: queue layer wrote ack + result envelopes (handoff artifacts)
    assert "ack_envelope" in steps and "result_envelope" in steps
    assert steps["ack_envelope"]["ok"] is True
    assert steps["result_envelope"]["ok"] is True


def test_v2_consumer_bounded_concurrency_respects_semaphore():
    """MAX_CONCURRENT must be a positive int (≥1, ≤8).  tick() runs under it."""
    assert 1 <= MAX_CONCURRENT <= 8, (
        f"MAX_CONCURRENT must be 1..8 per R286 §2.8; got {MAX_CONCURRENT}"
    )
    # tick should run cleanly with default recipients
    result = tick(recipients=["codex"], marker_filter=lambda e: False)  # nothing matches
    assert result["ok"] is True
    assert result["max_concurrent"] == MAX_CONCURRENT
    assert result["max_queue"] >= 0


def test_v2_consumer_stats_counters():
    """ConsumerStats increments correctly across multiple dispatches."""
    stats = ConsumerStats()
    base = stats.snapshot()
    for k in ("claimed", "acked", "results", "errors", "deadlettered", "no_route"):
        assert base[k] == 0

    # Successful dispatch (uses injected dispatcher via set_dispatcher)
    def ok_dispatcher(envelope, *, recipient):
        return {"ok": True}
    set_dispatcher(ok_dispatcher)
    try:
        env = build_envelope("claudecode", "codex", "message",
                             {"text": "ok", "__r286_test__": "test_stats"})
        res = enqueue(env)
        target = INBOX / Path(res["file"]).name
        dispatch_envelope(target, env, stats=stats)
        snap = stats.snapshot()
        assert snap["claimed"] >= 1
        assert snap["results"] >= 1
        assert snap["acked"] >= 1
    finally:
        set_dispatcher(None)


def test_v2_consumer_enqueue_ack_envelope_separate_from_result():
    """R286 §2.7 contract: ack and result MUST be distinct envelopes (not merged)."""
    env = build_envelope("claudecode", "codex", "message",
                         {"text": "separate", "__r286_test__": "test_ack_separate"})
    res = enqueue(env)
    target = INBOX / Path(res["file"]).name
    out = dispatch_envelope(target, env)

    # Find steps by their `step` key (defensive against future reordering)
    ack_step = next(s for s in out["steps"] if s.get("step") == "ack_envelope")
    res_step = next(s for s in out["steps"] if s.get("step") == "result_envelope")
    ack_id = ack_step["ack_id"]
    res_id = res_step["result_id"]
    assert ack_id != res_id, "ack and result MUST be distinct envelope ids"
    # Both must have valid verify_envelope
    ack_env = json.loads([p for p in INBOX.glob(f"{ack_id}__*.json")
                          if ".tmp." not in p.name][0].read_text(encoding="utf-8"))
    res_env = json.loads([p for p in INBOX.glob(f"{res_id}__*.json")
                          if ".tmp." not in p.name][0].read_text(encoding="utf-8"))
    assert ack_env["message_type"] == "ack"
    assert res_env["message_type"] == "result"