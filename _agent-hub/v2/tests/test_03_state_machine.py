# v2/tests/test_03_state_machine.py
# Acceptance: 状态机合法转换 + 拒绝非法 (完工标准 6 部分)
#
# R320.1: removed `import pytest` / `pytest.raises` — replaced with try/except.
from src.state_machine import cancel, list_tasks, submit_task, transition


def _expect_value_error(fn, *args, **kwargs):
    try:
        fn(*args, **kwargs)
    except ValueError:
        return True
    return False


def test_submit_task_default_queued():
    t = submit_task(title="x", assignee="codex", owner="claudecode")
    assert t["state"] == "queued"
    assert t["retry_count"] == 0


def test_valid_transition_queued_to_running():
    t = submit_task(title="x", assignee="codex", owner="claudecode")
    after = transition(t["task_id"], "running", actor="claudecode")
    assert after["state"] == "running"
    assert after["lease_expires_at"] is not None
    assert after["heartbeat_at"] is not None


def test_invalid_transition_queued_to_succeeded_rejected():
    t = submit_task(title="x", assignee="codex", owner="claudecode")
    assert _expect_value_error(transition, t["task_id"], "succeeded", actor="claudecode")


def test_running_to_succeeded_allowed():
    t = submit_task(title="x", assignee="codex", owner="claudecode")
    transition(t["task_id"], "running", actor="claudecode")
    after = transition(t["task_id"], "succeeded", actor="codex",
                        output_payload={"answer": 42})
    assert after["state"] == "succeeded"
    assert after["output_payload"]["answer"] == 42


def test_terminal_state_blocks_transition():
    t = submit_task(title="x", assignee="codex", owner="claudecode")
    transition(t["task_id"], "running", actor="claudecode")
    transition(t["task_id"], "succeeded", actor="codex")
    assert _expect_value_error(transition, t["task_id"], "running", actor="codex")


def test_cancel_from_queued():
    t = submit_task(title="x", assignee="codex", owner="claudecode")
    after = cancel(t["task_id"], actor="claudecode")
    assert after["state"] == "cancelled"


def test_failed_can_retry_to_queued():
    t = submit_task(title="x", assignee="codex", owner="claudecode")
    transition(t["task_id"], "running", actor="claudecode")
    transition(t["task_id"], "failed", actor="codex", error={"code": "X"})
    after = transition(t["task_id"], "queued", actor="supervisor")
    assert after["state"] == "queued"


def test_list_tasks_filter_by_state():
    t1 = submit_task(title="a", assignee="codex", owner="claudecode")
    t2 = submit_task(title="b", assignee="codex", owner="claudecode")
    transition(t2["task_id"], "running", actor="claudecode")
    queued = list_tasks(state="queued")
    running = list_tasks(state="running")
    assert any(t["task_id"] == t1["task_id"] for t in queued)
    assert all(t["task_id"] != t2["task_id"] for t in queued)
    assert any(t["task_id"] == t2["task_id"] for t in running)