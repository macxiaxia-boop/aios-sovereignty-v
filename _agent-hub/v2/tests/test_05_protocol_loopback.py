# v2/tests/test_05_protocol_loopback.py
#
# *** DISCLAIMER (R320.1) ***
# This test exercises the v2 file-queue + envelope semantics in a SINGLE PROCESS
# loopback (sender=claudecode / recipient=codex, both running as Python functions
# in this test process). It is NOT a real round-trip between two distinct agent
# runtimes, and it is NOT a real Codex↔Claude Code call.
#
# R320.3 fix: locate the target envelope via `res["file"]` returned from
# `enqueue()`, not via `list_unclaimed(limit=10)` (which can be truncated by
# earlier tests' residue). The earlier test modules leave many envelopes in
# the shared temp inbox; `limit=10` was returning only unrelated envelopes.
#
# R320.3 ADDITION: cross-agent routing isolation — A's envelopes must NOT
# leak into B's receive. This protects the protocol's multi-agent semantics
# before any real two-process round-trip is attempted.
import json
from pathlib import Path

from src.envelope import build_envelope, reply_envelope
from src.paths import INBOX, OUTBOX, STATE_FILE, EVENTS_LOG, TASKS_DIR
from src.message_queue import ack as q_ack, claim as q_claim, enqueue, list_unclaimed
from src.state_machine import build_state_snapshot, save_state_snapshot, submit_task, transition


def test_protocol_loopback_task_envelope_to_result():
    """Loopback: submit_task → enqueue task envelope → claim → reply result → ack.
    R320.3: use res['file'] to locate the envelope, not list_unclaimed(limit=10)."""
    # 1. CC submits a task and enqueues a task envelope to codex
    task = submit_task(title="loopback-demo", assignee="codex",
                        owner="claudecode", timeout_ms=15000)
    transition(task["task_id"], "running", actor="claudecode")

    task_env = build_envelope(
        sender="claudecode",
        recipient="codex",
        message_type="task",
        payload={"task_id": task["task_id"], "title": task["title"],
                  "instruction": "probe 127.0.0.1:18792"},
    )
    res = enqueue(task_env)
    assert res["deduped"] is False, f"first enqueue must be fresh, got {res!r}"
    assert res["file"] is not None, "res['file'] must be set on fresh enqueue"

    # 2. R320.3: locate target via res['file'], not via list_unclaimed(limit=10)
    target_path = INBOX / Path(res["file"]).name
    assert target_path.exists(), (
        f"expected target_path={target_path} to exist after enqueue"
    )

    # 3. Claim the envelope
    claimed = q_claim(target_path)
    assert claimed is not None, f"claim returned None for {target_path}"
    assert not target_path.exists(), "claim should rename the file (original gone)"

    # 4. "codex" produces a result envelope
    result_env = reply_envelope(
        original=task_env,
        sender="codex",
        message_type="result",
        payload={"task_id": task["task_id"], "output": {"port": "closed"}},
    )
    enqueue(result_env, dest="outbox")

    # 5. "CC" acks the original task envelope
    assert q_ack(claimed), "q_ack returned False"

    # 6. Audit trail
    outbox_files = list(OUTBOX.glob("*.json"))
    outbox_files = [p for p in outbox_files if ".tmp." not in p.name]
    assert any(result_env["id"] in p.name for p in outbox_files), (
        f"outbox should contain result envelope {result_env['id']}"
    )

    events_text = EVENTS_LOG.read_text(encoding="utf-8")
    assert "task.submitted" in events_text, "events.ndjson should record task.submitted"
    assert "task.transition" in events_text, "events.ndjson should record task.transition"

    save_state_snapshot(build_state_snapshot())
    snap = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    assert task["task_id"] in snap["tasks"], (
        f"state snapshot must include task {task['task_id']}"
    )


def test_protocol_loopback_dedup_blocks_double_send():
    env = build_envelope("claudecode", "codex", "message", {"text": "ping"})
    r1 = enqueue(env)
    r2 = enqueue(env)
    assert r1["deduped"] is False
    assert r2["deduped"] is True
    # R320.3: locate via res['file'], not list_unclaimed
    matches = list(INBOX.glob(f"{env['id']}__*.json"))
    matches = [m for m in matches if ".tmp." not in m.name and ".claimed." not in m.name]
    assert len(matches) == 1, f"expected 1 committed envelope, got {len(matches)}"


def test_protocol_loopback_ack_emits_ack_envelope():
    env = build_envelope("claudecode", "codex", "message", {"text": "hi"})
    res = enqueue(env)
    # R320.3: locate via res['file']
    target_path = INBOX / Path(res["file"]).name
    claimed = q_claim(target_path)
    assert q_ack(claimed), "q_ack returned False"
    # R320.6 NOTE: explicit outbox path — kept as a regression guard for the
    # `--dest outbox` audit-only override. Default behavior (no --dest) now
    # writes ack to INBOX; see test_r3206_ack_default_lands_in_inbox below.
    ack_env = reply_envelope(env, "codex", "ack", {"ack_of": env["id"], "note": "received"})
    enqueue(ack_env, dest="outbox")
    out = [p for p in OUTBOX.glob(f"{ack_env['id']}__*.json")]
    out = [p for p in out if ".tmp." not in p.name]
    assert len(out) == 1, f"expected 1 ack envelope in outbox, got {len(out)}"
    j = json.loads(out[0].read_text(encoding="utf-8"))
    assert j["correlation_id"] == env["id"]
    assert j["message_type"] == "ack"


# ---------------------------------------------------------------- R320.6
# Fix for the R320.6 protocol gap exposed by the first real two-process
# round-trip (Codex → CC ack → Codex). Before the fix, cmd_ack wrote the
# ack envelope to OUTBOX, but CLI receive only reads INBOX and there is no
# dispatcher. So acks were un-deliverable.
#
# These tests are at the src/ level (no subprocess) so they pin the
# envelope-shape contract that the CLI relies on.
def test_r3206_ack_default_lands_in_inbox_not_outbox():
    """R320.6: ack envelope (the one cmd_ack writes by default) MUST land
    in INBOX with recipient=original.sender so it can be delivered. The
    OUTBOX must NOT receive it."""
    from src.envelope import envelope_from_json
    task_env = build_envelope("claudecode", "codex", "task", {"x": 1})
    res = enqueue(task_env)
    target_path = INBOX / Path(res["file"]).name
    claimed = q_claim(target_path)

    # Mirror the body of cmd_ack: reply_envelope + enqueue(dest="inbox")
    ack_env = reply_envelope(task_env, sender="codex", message_type="ack",
                              payload={"ack_of": task_env["id"], "note": "r3206"})
    ack_res = enqueue(ack_env, dest="inbox")
    assert ack_res["deduped"] is False

    # Must be in inbox
    inbox_matches = [p for p in INBOX.glob(f"{ack_env['id']}__*.json")
                     if ".tmp." not in p.name]
    assert len(inbox_matches) == 1, (
        f"ack must land in INBOX; got {len(inbox_matches)} matches"
    )
    on_disk = envelope_from_json(inbox_matches[0].read_text(encoding="utf-8"))
    assert on_disk["recipient"] == "claudecode", (
        f"ack.recipient must equal original.sender=claudecode; "
        f"got {on_disk['recipient']!r}"
    )
    assert on_disk["correlation_id"] == task_env["id"], (
        f"ack.correlation_id must equal original.id; got {on_disk['correlation_id']!r}"
    )
    assert on_disk["in_reply_to"] == task_env["id"], (
        f"ack.in_reply_to must equal original.id; got {on_disk['in_reply_to']!r}"
    )
    assert on_disk["message_type"] == "ack"

    # Must NOT be in outbox (outbox is audit-only and has no dispatcher)
    outbox_matches = [p for p in OUTBOX.glob(f"{ack_env['id']}__*.json")
                      if ".tmp." not in p.name]
    assert len(outbox_matches) == 0, (
        f"ack must NOT be in OUTBOX by default; found {outbox_matches}"
    )

    # Finalize the original claim
    assert q_ack(claimed)


def test_r3206_build_envelope_propagates_correlation_id_and_in_reply_to():
    """R320.6: build_envelope MUST accept correlation_id + in_reply_to kwargs
    so cmd_send can pass them through (CLI flag wiring). Omission → no field.

    Note (R320.6 Codex verification): schema requires correlation_id to be
    a uuid4 hex string (`^[0-9a-fA-F]{8}-...-[0-9a-fA-F]{12}$`). Pseudo
    values like "abc-123" are correctly rejected. This test uses real
    `uuid.uuid4()` values to match what `reply_envelope` always produces
    and what cmd_send should pass through."""
    import uuid
    cid = str(uuid.uuid4())
    irt = str(uuid.uuid4())
    # Sanity guard: cid/irt must actually look like uuid4, otherwise the
    # test would itself mask a schema-rejection bug. Hyphens at indices
    # 8, 13, 18, 23 (uuid4 = 8-4-4-4-12 hex with 4 hyphens).
    assert len(cid) == 36 and cid[8] == "-" and cid[13] == "-" and cid[18] == "-" and cid[23] == "-", (
        f"cid must be uuid4 hex; got {cid!r}"
    )
    assert len(irt) == 36 and irt[8] == "-" and irt[13] == "-" and irt[18] == "-" and irt[23] == "-", (
        f"irt must be uuid4 hex; got {irt!r}"
    )

    env_full = build_envelope(
        "claudecode", "codex", "result",
        {"out": "ok"},
        correlation_id=cid, in_reply_to=irt,
    )
    assert env_full["correlation_id"] == cid, (
        f"build_envelope must propagate correlation_id unchanged; "
        f"expected {cid!r}, got {env_full.get('correlation_id')!r}"
    )
    assert env_full["in_reply_to"] == irt, (
        f"build_envelope must propagate in_reply_to unchanged; "
        f"expected {irt!r}, got {env_full.get('in_reply_to')!r}"
    )

    # Also verify the realistic case: pass through an actual envelope's id.
    parent = build_envelope("claudecode", "codex", "task", {"x": 1})
    env_reply = build_envelope(
        "codex", "claudecode", "result",
        {"y": 2},
        correlation_id=parent["id"], in_reply_to=parent["id"],
    )
    assert env_reply["correlation_id"] == parent["id"]
    assert env_reply["in_reply_to"] == parent["id"]

    # Omission → fields absent (R320 / R320.1 compat)
    env_min = build_envelope("claudecode", "codex", "message", {"text": "hi"})
    assert "correlation_id" not in env_min, (
        f"omitting correlation_id must leave the field absent; got {env_min.get('correlation_id')!r}"
    )
    assert "in_reply_to" not in env_min, (
        f"omitting in_reply_to must leave the field absent; got {env_min.get('in_reply_to')!r}"
    )


def test_r3206_ack_of_ack_does_not_create_loop():
    """R320.6: protocol does NOT require ack-of-ack. After B acks A's task,
    exactly ONE new ack envelope exists. No auto-ack mechanism in cmd_ack
    or cmd_send. Steady state is the sender receiving the single ack.

    Uses unique recipient names (`*_r3206`) so residue from earlier tests
    in the same session cannot inflate the ack count.
    """
    a_id = "claudecode_r3206"
    b_id = "codex_r3206"
    task_env = build_envelope(a_id, b_id, "task", {"loop_test": True})
    res = enqueue(task_env)
    target_path = INBOX / Path(res["file"]).name
    claimed = q_claim(target_path)

    # B emits ack via the same call cmd_ack makes
    ack_env = reply_envelope(task_env, sender=b_id, message_type="ack",
                              payload={"ack_of": task_env["id"], "note": "loop-guard"})
    enqueue(ack_env, dest="inbox")
    assert q_ack(claimed)

    # Now A=claudecode_r3206 looks for acks in inbox addressed to itself.
    from src.message_queue import list_unclaimed
    items = list_unclaimed(INBOX, limit=1000, recipient=a_id)
    ack_envs = [e for _, e in items if e["message_type"] == "ack"]
    assert len(ack_envs) == 1, (
        f"steady-state: exactly one ack envelope addressed to {a_id}; "
        f"got {len(ack_envs)}. Auto-ack would indicate a protocol loop."
    )
    assert ack_envs[0]["id"] == ack_env["id"]


# ---------------------------------------------------------------- R320.6
def test_r3206_correlation_id_filter_isolates_replies_per_original():
    """R320.6: reply_envelope produces a unique (id, correlation_id) pair.
    Two distinct originals MUST NOT share the same ack envelope id, even
    if their payloads are identical (idempotency_key differs because the
    recipient of the ack differs when the sender of the original differs)."""
    a1 = build_envelope("alice", "bob", "task", {"x": 1})
    a2 = build_envelope("carol", "bob", "task", {"x": 1})  # same payload to different sender
    ack1 = reply_envelope(a1, sender="bob", message_type="ack",
                          payload={"ack_of": a1["id"], "note": ""})
    ack2 = reply_envelope(a2, sender="bob", message_type="ack",
                          payload={"ack_of": a2["id"], "note": ""})
    assert ack1["correlation_id"] == a1["id"]
    assert ack2["correlation_id"] == a2["id"]
    assert ack1["id"] != ack2["id"], (
        f"two distinct acks MUST have distinct ids; both {ack1['id']!r}"
    )
    assert ack1["recipient"] == "alice"
    assert ack2["recipient"] == "carol"


# ---------------------------------------------------------------- R320.3
# Cross-agent routing isolation. This is the protocol invariant that
# protects multi-agent semantics BEFORE any real two-process round-trip.
def test_protocol_loopback_routing_a_to_a_only_a_receives():
    """A's envelopes MUST NOT appear in B's filtered receive."""
    a_to_a = build_envelope("alpha", "alpha", "message", {"for": "alpha-only"})
    b_to_b = build_envelope("beta", "beta", "message", {"for": "beta-only"})
    enqueue(a_to_a)
    enqueue(b_to_b)

    # Alpha's receive — filter applied BEFORE limit
    alpha_items = list_unclaimed(INBOX, limit=1000, recipient="alpha")
    alpha_env_ids = [e["id"] for _, e in alpha_items]
    assert a_to_a["id"] in alpha_env_ids, (
        f"alpha must see its own message {a_to_a['id']}; got {len(alpha_items)} items"
    )
    assert b_to_b["id"] not in alpha_env_ids, (
        f"alpha MUST NOT see beta's message {b_to_b['id']}; routing leak"
    )

    # Beta's receive
    beta_items = list_unclaimed(INBOX, limit=1000, recipient="beta")
    beta_env_ids = [e["id"] for _, e in beta_items]
    assert b_to_b["id"] in beta_env_ids
    assert a_to_a["id"] not in beta_env_ids, (
        "beta MUST NOT see alpha's message; routing leak"
    )


def test_protocol_loopback_routing_broadcast_seen_by_all():
    """A broadcast envelope MUST appear in any recipient's filtered receive."""
    broadcast = build_envelope("alpha", "broadcast", "message", {"for": "everyone"})
    enqueue(broadcast)
    for r in ("alpha", "beta", "claudecode", "codex", "workbuddy", "hermes", "openclaw"):
        items = list_unclaimed(INBOX, limit=1000, recipient=r)
        ids = [e["id"] for _, e in items]
        assert broadcast["id"] in ids, (
            f"broadcast must be visible to recipient={r}"
        )


def test_protocol_loopback_routing_no_filter_sees_all():
    """recipient=None (or 'any') MUST return all unclaimed, regardless of recipient."""
    extra = build_envelope("gamma", "gamma", "message", {"for": "gamma-only"})
    enqueue(extra)
    items = list_unclaimed(INBOX, limit=10000, recipient=None)
    ids = [e["id"] for _, e in items]
    assert extra["id"] in ids, "recipient=None must see gamma's message"
    items_any = list_unclaimed(INBOX, limit=10000, recipient="any")
    ids_any = [e["id"] for _, e in items_any]
    assert extra["id"] in ids_any, "recipient='any' must see gamma's message"