# v2/tests/test_07_healthcheck.py
# Acceptance: 健康检查端到端可执行 (完工标准 F)
#
# R320.1: subprocess smoke.
# R320.3: assert messages, CLI ack end-to-end (incl. claiming first),
# CLI receive --agent cross-agent routing isolation.
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CLI = ROOT / "cli" / "aiosv2.py"


def run_cli(*args, timeout=60):
    cmd = [sys.executable, str(CLI)] + list(args)
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return p.returncode, p.stdout, p.stderr


def _run_cli_assert_rc(args, *, label, timeout=60):
    rc, out, err = run_cli(*args, timeout=timeout)
    assert rc == 0, (
        f"{label}: rc={rc}, stderr={err!r}, stdout={out!r}"
    )
    return out


def test_cli_init():
    out = _run_cli_assert_rc(["init"], label="init")
    j = json.loads(out)
    assert j["ok"] is True, f"init.ok should be True, got {j!r}"
    assert "v2_root" in j, f"init output must include v2_root, got {j!r}"


def test_cli_status():
    out = _run_cli_assert_rc(["status"], label="status")
    j = json.loads(out)
    for k in ("tasks_total", "tasks_by_state", "inbox_count",
              "outbox_count", "agents_in_registry", "state_file_exists"):
        assert k in j, f"status missing key {k}; got {j!r}"


def test_cli_health_returns_five_agents_with_4_levels():
    out = _run_cli_assert_rc(["health"], label="health")
    j = json.loads(out)
    ids = sorted(a["agent_id"] for a in j["agents"])
    assert ids == ["claudecode", "codex", "hermes", "openclaw", "workbuddy"], (
        f"health must list all 5 agents, got {ids}"
    )
    for a in j["agents"]:
        for k in ("configured", "present", "reachable", "healthy"):
            assert k in a, f"{a['agent_id']} missing level {k}"


def test_cli_send_then_receive_then_ack_roundtrip():
    """End-to-end: send → receive --claim → ack.
    R320.3: explicitly verify ack works AFTER claim (previously failed
    because cmd_ack used get_envelope_by_id which excludes .claimed files).
    R320.5: use --agent claudecode --limit 1000 on both receives. Earlier
    concurrent tests in the same suite leave 50+ envelopes in the shared
    inbox temp dir; --limit 50 without a recipient filter truncates and
    the just-sent envelope is missed. The protocol-correct way to read
    your own mail is to filter by your own agent_id."""
    out = _run_cli_assert_rc(
        ["send", "--from", "codex", "--to", "claudecode",
         "--type", "message", "--payload", '{"text":"hello v2"}'],
        label="send",
    )
    env_id = json.loads(out)["envelope_id"]
    assert env_id, f"send did not return envelope_id; got {out!r}"

    # Receive (no claim) — filter by recipient AND raise limit so we
    # are not truncated by other tests' residue.
    out = _run_cli_assert_rc(
        ["receive", "--limit", "1000", "--agent", "claudecode"],
        label="receive (no claim)",
    )
    j = json.loads(out)
    assert j.get("filter", {}).get("agent") == "claudecode", (
        f"receive output must echo filter.agent=claudecode; got {j.get('filter')!r}"
    )
    assert any(item["envelope_id"] == env_id for item in j["items"]), (
        f"just-sent envelope {env_id} should be visible in receive (no claim); "
        f"received {len(j['items'])} items"
    )

    # Receive --claim — same filter
    out = _run_cli_assert_rc(
        ["receive", "--limit", "1000", "--agent", "claudecode", "--claim"],
        label="receive --claim",
    )
    j = json.loads(out)
    assert j.get("filter", {}).get("agent") == "claudecode", (
        f"receive --claim output must echo filter.agent=claudecode; "
        f"got {j.get('filter')!r}"
    )
    target = next((it for it in j["items"] if it["envelope_id"] == env_id), None)
    assert target is not None, (
        f"just-sent envelope {env_id} missing from receive --claim output; "
        f"received {len(j['items'])} items"
    )
    assert target.get("claimed") is not None, (
        f"receive --claim should set claimed; got {target!r}"
    )

    out = _run_cli_assert_rc(["ack", env_id, "--actor", "claudecode",
                              "--note", "healthcheck-ack"],
                              label="ack")
    j = json.loads(out)
    assert j["ok"] is True, f"ack.ok should be True, got {j!r}"
    assert j["acked_envelope_id"] == env_id, (
        f"ack.acked_envelope_id should be {env_id}, got {j!r}"
    )


def test_cli_submit_then_update_task_full_lifecycle():
    out = _run_cli_assert_rc(
        ["submit-task", "--title", "test-cli", "--assignee", "codex",
         "--owner", "claudecode", "--timeout-ms", "10000"],
        label="submit-task",
    )
    task_id = json.loads(out)["task_id"]
    assert task_id, f"submit-task did not return task_id; got {out!r}"

    out = _run_cli_assert_rc(
        ["update-task", "--task-id", task_id, "--action", "transition",
         "--state", "running", "--actor", "claudecode"],
        label="update-task -> running",
    )
    assert json.loads(out)["state"] == "running", \
        f"expected state=running, got {json.loads(out)!r}"

    out = _run_cli_assert_rc(
        ["update-task", "--task-id", task_id, "--action", "heartbeat",
         "--actor", "codex"],
        label="update-task heartbeat",
    )
    assert "heartbeat_at" in json.loads(out), \
        f"heartbeat response must include heartbeat_at; got {json.loads(out)!r}"

    out = _run_cli_assert_rc(
        ["update-task", "--task-id", task_id, "--action", "transition",
         "--state", "succeeded", "--actor", "codex",
         "--output-payload", '{"result":"ok"}'],
        label="update-task -> succeeded",
    )
    assert json.loads(out)["state"] == "succeeded", \
        f"expected state=succeeded, got {json.loads(out)!r}"


# ---------------------------------------------------------------- R320.3
def test_cli_receive_agent_filter_isolates_agents():
    """R320.3: CLI receive --agent must actually filter.
    Two envelopes, two recipients; receiver-A must NOT see receiver-B's message."""
    rc, out, _ = run_cli("send", "--from", "codex", "--to", "alpha-test-cli",
                         "--type", "message", "--payload", '{"for":"alpha"}')
    assert rc == 0, f"send to alpha failed: rc={rc}, out={out!r}"
    rc, out, _ = run_cli("send", "--from", "codex", "--to", "beta-test-cli",
                         "--type", "message", "--payload", '{"for":"beta"}')
    assert rc == 0, f"send to beta failed: rc={rc}, out={out!r}"

    # Alpha receive — must NOT see beta's envelope
    rc, out, _ = run_cli("receive", "--limit", "1000", "--agent", "alpha-test-cli")
    assert rc == 0, f"receive alpha failed: {out!r}"
    j = json.loads(out)
    assert j["filter"]["agent"] == "alpha-test-cli", (
        f"receive output should echo filter.agent; got {j['filter']!r}"
    )
    ids = [item["envelope_id"] for item in j["items"]]
    for env_id in ids:
        # No item in alpha's filtered receive should have recipient != alpha (and != broadcast)
        # Find the actual envelope by id
        rc2, out2, _ = run_cli("receive", "--limit", "1000")  # unfiltered
        assert rc2 == 0
        all_items = json.loads(out2)["items"]
        matched = next((x for x in all_items if x["envelope_id"] == env_id), None)
        if matched:
            assert matched["recipient"] in ("alpha-test-cli", "broadcast"), (
                f"alpha's filtered receive leaked envelope with recipient="
                f"{matched['recipient']!r}"
            )


def test_cli_ack_returns_error_when_not_claimed():
    """R320.3: CLI ack on a never-claimed envelope must return rc=2 with explicit error."""
    rc, out, _ = run_cli("send", "--from", "codex", "--to", "claudecode",
                         "--type", "message", "--payload", '{"text":"never-claim"}')
    assert rc == 0, f"send failed: rc={rc}"
    env_id = json.loads(out)["envelope_id"]

    # ack without prior --claim
    rc, out, _ = run_cli("ack", env_id, "--actor", "claudecode")
    assert rc == 2, (
        f"ack without prior --claim must return rc=2 (NOT_FOUND), got rc={rc} out={out!r}"
    )
    j = json.loads(out)
    assert j["ok"] is False, f"ack.ok should be False, got {j!r}"
    assert "no claimed file" in j.get("error", "").lower() or "must run" in j.get("error", "").lower(), (
        f"ack error must explain the precondition; got {j!r}"
    )


# ---------------------------------------------------------------- R320.6
# CLI subprocess tests for the R320.6 protocol gap. These exercise the
# `aiosv2.py send --correlation-id/--in-reply-to` flag wiring and the
# `cmd_ack` inbox-routing default. They drive a separate Python process
# so they validate the full CLI contract, not just the src/ helpers.
def test_cli_send_with_correlation_id_and_in_reply_to_writes_them():
    """R320.6: CLI `send --correlation-id X --in-reply-to Y` MUST write
    both fields into the on-disk envelope JSON, and the CLI stdout must
    echo them back."""
    cid = "11111111-1111-1111-1111-111111111111"
    irt = "22222222-2222-2222-2222-222222222222"
    out = _run_cli_assert_rc(
        ["send", "--from", "codex", "--to", "claudecode",
         "--type", "result", "--payload", '{"ok": true}',
         "--correlation-id", cid, "--in-reply-to", irt],
        label="send with --correlation-id/--in-reply-to",
    )
    j = json.loads(out)
    env_id = j["envelope_id"]
    assert j["correlation_id"] == cid, (
        f"send stdout must echo correlation_id={cid}; got {j!r}"
    )
    assert j["in_reply_to"] == irt, (
        f"send stdout must echo in_reply_to={irt}; got {j!r}"
    )

    # On-disk JSON must also carry the fields
    from src.paths import INBOX
    matches = [p for p in INBOX.glob(f"{env_id}__*.json")
               if ".tmp." not in p.name and ".claimed." not in p.name]
    assert len(matches) == 1, f"expected 1 envelope file; got {len(matches)}"
    on_disk = json.loads(matches[0].read_text(encoding="utf-8"))
    assert on_disk["correlation_id"] == cid
    assert on_disk["in_reply_to"] == irt


def test_cli_ack_default_writes_to_inbox_receivable_by_sender():
    """R320.6 end-to-end via CLI:
      1. A=codex sends a task to B=claudecode
      2. B receives and claims it
      3. B acks with default dest (must land in inbox)
      4. A=codex receives the ack via --agent codex filter
      5. Ack MUST NOT appear in outbox
    This is the exact path that was broken before R320.6.
    """
    # 1) codex -> claudecode
    out = _run_cli_assert_rc(
        ["send", "--from", "codex", "--to", "claudecode",
         "--type", "message", "--payload", '{"text":"r3206 e2e"}'],
        label="1) send codex->claudecode",
    )
    env_id = json.loads(out)["envelope_id"]

    # 2) claudecode receive + claim
    out = _run_cli_assert_rc(
        ["receive", "--limit", "1000", "--agent", "claudecode", "--claim"],
        label="2) claudecode receive --claim",
    )
    j = json.loads(out)
    assert any(it["envelope_id"] == env_id for it in j["items"]), (
        f"claudecode receive missing envelope {env_id}; got {len(j['items'])} items"
    )

    # 3) claudecode acks (default dest=inbox)
    out = _run_cli_assert_rc(
        ["ack", env_id, "--actor", "claudecode", "--note", "r3206-e2e-ack"],
        label="3) claudecode ack",
    )
    j = json.loads(out)
    assert j["ok"] is True, f"ack.ok must be True; got {j!r}"
    assert j["ack_dest"] == "inbox", (
        f"R320.6 default must write ack to inbox; got j['ack_dest']={j['ack_dest']!r}"
    )
    assert j["ack_recipient"] == "codex", (
        f"ack envelope must target original.sender=codex; got {j['ack_recipient']!r}"
    )
    ack_id = j["ack_envelope_id"]

    # 4) codex receives the ack via --agent codex filter
    out = _run_cli_assert_rc(
        ["receive", "--limit", "1000", "--agent", "codex"],
        label="4) codex receive ack via inbox",
    )
    j = json.loads(out)
    ack_items = [it for it in j["items"] if it["envelope_id"] == ack_id]
    assert ack_items, (
        f"codex MUST see ack {ack_id} in inbox via --agent codex filter; "
        f"received {len(j['items'])} items, none matching ack_id"
    )
    ack_item = ack_items[0]
    assert ack_item["sender"] == "claudecode", (
        f"ack envelope's sender must be claudecode (the acker); got {ack_item['sender']!r}"
    )
    assert ack_item["recipient"] == "codex", (
        f"ack envelope's recipient must be codex (original.sender); got {ack_item['recipient']!r}"
    )
    assert ack_item["message_type"] == "ack", (
        f"ack envelope's message_type must be 'ack'; got {ack_item['message_type']!r}"
    )

    # 5) Ack MUST NOT be in outbox
    from src.paths import OUTBOX
    outbox_matches = [p for p in OUTBOX.glob(f"{ack_id}__*.json")
                      if ".tmp." not in p.name]
    assert not outbox_matches, (
        f"ack by default must NOT be in outbox; found {outbox_matches}"
    )


def test_cli_ack_correlation_id_and_in_reply_to_match_original():
    """R320.6: ack envelope on disk has correlation_id == in_reply_to == original.id."""
    out = _run_cli_assert_rc(
        ["send", "--from", "codex", "--to", "claudecode",
         "--type", "task", "--payload", '{"task":"r3206-corr"}'],
        label="send task",
    )
    original_id = json.loads(out)["envelope_id"]

    out = _run_cli_assert_rc(
        ["receive", "--limit", "1000", "--agent", "claudecode", "--claim"],
        label="receive --claim",
    )
    out = _run_cli_assert_rc(
        ["ack", original_id, "--actor", "claudecode", "--note", "corr-check"],
        label="ack",
    )
    j = json.loads(out)
    assert j["ack_correlation_id"] == original_id, (
        f"CLI ack stdout ack_correlation_id must equal original.id; "
        f"got {j['ack_correlation_id']!r} vs {original_id!r}"
    )
    assert j["ack_in_reply_to"] == original_id, (
        f"CLI ack stdout ack_in_reply_to must equal original.id; "
        f"got {j['ack_in_reply_to']!r} vs {original_id!r}"
    )

    # Verify on-disk envelope, not just CLI echo
    from src.envelope import envelope_from_json
    from src.paths import INBOX
    ack_id = j["ack_envelope_id"]
    matches = [p for p in INBOX.glob(f"{ack_id}__*.json")
               if ".tmp." not in p.name]
    assert len(matches) == 1, f"expected 1 ack envelope on disk; got {len(matches)}"
    on_disk = envelope_from_json(matches[0].read_text(encoding="utf-8"))
    assert on_disk["correlation_id"] == original_id
    assert on_disk["in_reply_to"] == original_id
    assert on_disk["recipient"] == "codex"


def test_cli_ack_of_ack_does_not_create_loop():
    """R320.6: after B acks A's task, no automatic ack-of-ack is emitted.
    The system reaches steady state: only B's ack envelope is NEW in inbox.

    Trace:
      Before: inbox has only prior residue
      After send:           inbox = residue + task_env.json
      After receive --claim: inbox = residue  (task_env.json renamed to .claimed.*)
      After ack:            inbox = residue + ack_env.json
                            (.claimed.* file removed by q_ack; ack_env enqueued)

    So new inbox files = {ack_env.json} (exactly 1, not 2 — the original
    task envelope was renamed to .claimed.* and so is excluded from the
    unclaimed glob set).

    We do NOT exercise acking the ack — the protocol does not require it
    and the CLI does not auto-emit one."""
    from src.paths import INBOX, OUTBOX
    # Snapshot counts before
    before_inbox = {p.name for p in INBOX.glob("*.json")
                    if ".tmp." not in p.name
                    and ".claimed." not in p.name
                    and ".dead." not in p.name}
    before_outbox = {p.name for p in OUTBOX.glob("*.json")
                     if ".tmp." not in p.name}

    out = _run_cli_assert_rc(
        ["send", "--from", "codex", "--to", "claudecode",
         "--type", "task", "--payload", '{"loop":"guard"}'],
        label="send task",
    )
    task_env_id = json.loads(out)["envelope_id"]
    out = _run_cli_assert_rc(
        ["receive", "--limit", "1000", "--agent", "claudecode", "--claim"],
        label="receive --claim",
    )
    out = _run_cli_assert_rc(
        ["ack", task_env_id, "--actor", "claudecode", "--note", "loop-guard"],
        label="ack",
    )
    ack_env_id = json.loads(out)["ack_envelope_id"]

    after_inbox = {p.name for p in INBOX.glob("*.json")
                   if ".tmp." not in p.name
                   and ".claimed." not in p.name
                   and ".dead." not in p.name}
    after_outbox = {p.name for p in OUTBOX.glob("*.json")
                    if ".tmp." not in p.name}

    # Steady state: exactly 1 new inbox file = the ack envelope.
    # (The original task envelope was renamed to .claimed.* and then
    # removed by q_ack, so it does NOT appear in the unclaimed glob set.)
    new_inbox = after_inbox - before_inbox
    assert len(new_inbox) == 1, (
        f"steady-state: exactly 1 new inbox file (the ack); got {len(new_inbox)}: "
        f"{new_inbox}. More than 1 would indicate a protocol loop."
    )
    assert ack_env_id in [n.split("__")[0] for n in new_inbox], (
        f"new inbox file must be the ack envelope {ack_env_id}; got {new_inbox}"
    )

    # No new outbox files (ack by default does NOT touch outbox)
    new_outbox = after_outbox - before_outbox
    assert len(new_outbox) == 0, (
        f"steady-state: no new outbox files; got {new_outbox}. "
        f"Default ack dest is inbox."
    )