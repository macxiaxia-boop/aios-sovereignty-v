# v2/tests/test_04_heartbeat_timeout_retry.py
# Acceptance: heartbeat / timeout / retry 自动测试 (完工标准 6)
import datetime as dt

from src.id import utc_now_iso
from src.state_machine import (heartbeat, list_tasks, reap_expired,
                                submit_task, transition)
from src.validation import TASK_STATES


def _set_lease_expired(task_id, past_iso):
    """Force a task's lease_expires_at to the past so reap_expired picks it up."""
    from src.paths import TASKS_DIR
    import json, os, uuid
    p = TASKS_DIR / f"{task_id}.json"
    t = json.loads(p.read_text(encoding="utf-8"))
    t["lease_expires_at"] = past_iso
    tmp = p.with_suffix(p.suffix + f".tmp.{uuid.uuid4().hex[:8]}")
    tmp.write_text(json.dumps(t, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(tmp, p)


def test_heartbeat_refreshes_lease():
    t = submit_task(title="x", assignee="codex", owner="claudecode", timeout_ms=10000)
    transition(t["task_id"], "running", actor="claudecode")
    after = heartbeat(t["task_id"], actor="codex")
    assert after["heartbeat_at"] is not None
    assert after["lease_expires_at"] is not None


def test_reap_expired_marks_failed_and_retries():
    t = submit_task(title="x", assignee="codex", owner="claudecode",
                    timeout_ms=5000, max_retries=2)
    transition(t["task_id"], "running", actor="claudecode")
    _set_lease_expired(t["task_id"], "2020-01-01T00:00:00Z")
    reaped = reap_expired(actor="supervisor")
    # reap_expired should put it in failed then back to queued (retry)
    final = [x for x in list_tasks() if x["task_id"] == t["task_id"]][0]
    assert final["state"] == "queued"
    assert final["retry_count"] >= 1
    assert len(reaped) >= 1


def test_reap_expired_respects_max_retries():
    t = submit_task(title="x", assignee="codex", owner="claudecode",
                    timeout_ms=5000, max_retries=0)
    transition(t["task_id"], "running", actor="claudecode")
    _set_lease_expired(t["task_id"], "2020-01-01T00:00:00Z")
    reap_expired(actor="supervisor")
    final = [x for x in list_tasks() if x["task_id"] == t["task_id"]][0]
    assert final["state"] == "failed"  # no retry budget
    assert final["retry_count"] == 0


def test_no_reap_when_lease_fresh():
    t = submit_task(title="x", assignee="codex", owner="claudecode", timeout_ms=60000)
    transition(t["task_id"], "running", actor="claudecode")
    reaped = reap_expired(actor="supervisor")
    final = [x for x in list_tasks() if x["task_id"] == t["task_id"]][0]
    assert final["state"] == "running"
    assert final["task_id"] not in [r["task_id"] for r in reaped]