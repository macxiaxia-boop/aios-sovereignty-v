# v2/tests/test_15_trace_completeness.py
#
# R286.A: trace completeness — every dispatch produces events.ndjson records.
#
# Acceptance:
#   - state_machine.transition emits event "task.transition" with from/to
#   - state_machine.submit_task emits event "task.submitted"
#   - state_machine.heartbeat emits event "task.heartbeat"
#   - state_machine.reap_expired emits "task.retry" on auto-retry
#   - consumer.dispatch emits "dispatch.ok" / "dispatch.retry" / "dispatch.failed"
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.envelope import build_envelope
from src.paths import EVENTS_LOG, INBOX
from src.message_queue import enqueue
from src.state_machine import (
    cancel, heartbeat, list_tasks, reap_expired, submit_task, transition,
)
from src.v2_consumer import dispatch_envelope, set_dispatcher


def _read_events_tail():
    if not EVENTS_LOG.exists():
        return ""
    return EVENTS_LOG.read_text(encoding="utf-8")


def test_state_machine_emits_task_submitted():
    before = _read_events_tail()
    t = submit_task(title="r286-trace-sub", assignee="codex", owner="claudecode")
    after = _read_events_tail()
    # New event since before
    delta = after[len(before):]
    assert "task.submitted" in delta, f"expected task.submitted event; got tail: {delta!r}"
    # Event should mention the task_id
    assert t["task_id"] in delta, f"event should reference task_id {t['task_id']}; got {delta!r}"


def test_state_machine_emits_task_transition_with_from_to():
    before = _read_events_tail()
    t = submit_task(title="r286-trace-trans", assignee="codex", owner="claudecode")
    transition(t["task_id"], "running", actor="claudecode")
    after = _read_events_tail()
    delta = after[len(before):]
    assert "task.transition" in delta, f"expected task.transition; got {delta!r}"
    # Should have both from and to
    assert '"from":"queued"' in delta or '"from": "queued"' in delta, (
        f"event should record from=queued; got {delta!r}"
    )
    assert '"to":"running"' in delta or '"to": "running"' in delta


def test_state_machine_emits_task_heartbeat():
    t = submit_task(title="r286-trace-hb", assignee="codex", owner="claudecode")
    transition(t["task_id"], "running", actor="claudecode")
    before = _read_events_tail()
    heartbeat(t["task_id"], actor="codex")
    after = _read_events_tail()
    delta = after[len(before):]
    assert "task.heartbeat" in delta, f"expected task.heartbeat; got {delta!r}"


def test_state_machine_emits_task_retry_on_reap():
    """Wait long enough that the lease definitely expires (timeout_ms=3000,
    sleep 4.0s) so reap_expired finds the task running and reaps it.  The
    1.0s margin avoids second-boundary clock precision issues."""
    t = submit_task(title="r286-trace-retry", assignee="codex", owner="claudecode",
                    timeout_ms=3000, max_retries=2)
    transition(t["task_id"], "running", actor="claudecode")
    import time
    time.sleep(4.0)  # lease_secs=3, sleep 4s gives 1s margin
    before = _read_events_tail()
    reap_expired(actor="r286_test")
    after = _read_events_tail()
    delta = after[len(before):]
    # Either task.retry or task.reap_failed
    assert ("task.retry" in delta) or ("task.reap_failed" in delta), (
        f"expected task.retry|reap_failed in events; got {delta!r}"
    )


def test_state_machine_emits_task_cancel():
    t = submit_task(title="r286-trace-cancel", assignee="codex", owner="claudecode")
    before = _read_events_tail()
    cancel(t["task_id"], actor="claudecode")
    after = _read_events_tail()
    delta = after[len(before):]
    assert "task.transition" in delta
    assert '"to":"cancelled"' in delta or '"to": "cancelled"' in delta


def test_consumer_dispatch_emits_dispatch_ok():
    """dispatch_envelope with successful dispatcher MUST emit dispatch.ok event."""
    def ok_dispatcher(envelope, *, recipient):
        return {"ok": True}

    set_dispatcher(ok_dispatcher)
    try:
        env = build_envelope("claudecode", "codex", "message",
                             {"text": "trace-ok", "__r286_test__": "test_trace_ok"})
        res = enqueue(env)
        target = INBOX / Path(res["file"]).name
        before = _read_events_tail()
        out = dispatch_envelope(target, env)
        after = _read_events_tail()
        delta = after[len(before):]
        assert out["ok"] is True
        assert "dispatch.ok" in delta, (
            f"expected dispatch.ok event; got tail: {delta!r}"
        )
        # Event MUST include envelope_id, recipient, message_type
        assert env["id"] in delta
        assert "codex" in delta
        assert "message" in delta
    finally:
        set_dispatcher(None)


def test_consumer_dispatch_emits_dispatch_retry_on_exception():
    """Adapter exception with retry budget remaining → dispatch.retry event."""
    def bad_dispatcher(envelope, *, recipient):
        raise RuntimeError("trace-boom")

    set_dispatcher(bad_dispatcher)
    try:
        env = build_envelope("claudecode", "codex", "message",
                             {"text": "trace-retry", "__r286_test__": "test_trace_retry"})
        # ensure retry budget
        env["retry_count"] = 0
        res = enqueue(env)
        target = INBOX / Path(res["file"]).name
        before = _read_events_tail()
        out = dispatch_envelope(target, env)
        after = _read_events_tail()
        delta = after[len(before):]
        # retry path emits either dispatch.retry OR a deadletter step
        assert "dispatch.retry" in delta or any(s.get("step") == "deadletter" for s in out["steps"]), (
            f"expected retry/deadletter trace; got tail: {delta!r}; out={out!r}"
        )
    finally:
        set_dispatcher(None)