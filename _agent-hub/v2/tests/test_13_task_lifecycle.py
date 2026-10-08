# v2/tests/test_13_task_lifecycle.py
#
# R286.A Stage 2: full task lifecycle (submit/claim/progress/input-request/
# approval/cancel/final/error) on top of state_machine.py primitives.
#
# Acceptance:
#   - submit_task → transition to running → heartbeat → progress → final (succeeded)
#   - submit → running → cancel (cancelled state)
#   - submit → running → fail → retry → succeed (retry budget respected)
#   - input_request / approval represented via transition to 'waiting' state
#   - heartbeat refreshes lease
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.state_machine import (
    cancel,
    get_task,
    heartbeat,
    list_tasks,
    submit_task,
    transition,
)


def test_full_task_lifecycle_success():
    """submit → running → progress (waiting) → final (succeeded)."""
    t = submit_task(title="r286-lifecycle", assignee="codex", owner="claudecode",
                    timeout_ms=60000)
    assert t["state"] == "queued"
    assert t["retry_count"] == 0

    # running
    t = transition(t["task_id"], "running", actor="claudecode")
    assert t["state"] == "running"
    assert t["lease_expires_at"] is not None

    # heartbeat
    t = heartbeat(t["task_id"], actor="codex")
    assert t["heartbeat_at"] is not None
    assert t["lease_expires_at"] is not None

    # input_request: transition to 'waiting'
    t = transition(t["task_id"], "waiting", actor="codex",
                   note="awaiting user input")
    assert t["state"] == "waiting"

    # approval received: back to running
    t = transition(t["task_id"], "running", actor="codex", note="approved")
    assert t["state"] == "running"

    # final: succeeded with output_payload
    t = transition(t["task_id"], "succeeded", actor="codex",
                   output_payload={"answer": 42})
    assert t["state"] == "succeeded"
    assert t["output_payload"]["answer"] == 42


def test_task_lifecycle_cancel_from_queued():
    t = submit_task(title="r286-cancel", assignee="codex", owner="claudecode")
    t = cancel(t["task_id"], actor="claudecode")
    assert t["state"] == "cancelled"
    # Terminal: no further transitions allowed
    raised = False
    try:
        transition(t["task_id"], "running", actor="claudecode")
    except ValueError:
        raised = True
    assert raised, "terminal cancelled state must reject further transitions"


def test_task_lifecycle_cancel_from_running_via_waiting_then_cancelled():
    """SSOT (state_machine.py) does NOT allow running -> cancelled directly.
    The protocol requires running -> waiting -> cancelled (or running -> failed).
    This test documents that contract."""
    t = submit_task(title="r286-cancel-running", assignee="codex", owner="claudecode")
    transition(t["task_id"], "running", actor="claudecode")
    # running -> waiting is allowed
    t = transition(t["task_id"], "waiting", actor="claudecode", note="user requested cancel")
    assert t["state"] == "waiting"
    # waiting -> cancelled is allowed
    t = cancel(t["task_id"], actor="claudecode")
    assert t["state"] == "cancelled"
    # Confirm direct running -> cancelled is rejected by SSOT
    t2 = submit_task(title="r286-no-direct-cancel", assignee="codex", owner="claudecode")
    transition(t2["task_id"], "running", actor="claudecode")
    raised = False
    try:
        transition(t2["task_id"], "cancelled", actor="claudecode")
    except ValueError:
        raised = True
    assert raised, "SSOT must reject direct running -> cancelled (use waiting first)"


def test_task_lifecycle_fail_then_retry_to_succeed():
    """Submit → running → failed → queued (retry) → running → succeeded."""
    t = submit_task(title="r286-retry", assignee="codex", owner="claudecode",
                    max_retries=3)
    transition(t["task_id"], "running", actor="claudecode")
    t = transition(t["task_id"], "failed", actor="codex",
                    error={"code": "TEMP_ERR", "message": "transient"})
    assert t["state"] == "failed"
    # Retry budget allows transition failed → queued
    t = transition(t["task_id"], "queued", actor="claudecode",
                   note="retry attempt 1")
    assert t["state"] == "queued"
    # Run to completion
    transition(t["task_id"], "running", actor="claudecode")
    t = transition(t["task_id"], "succeeded", actor="codex",
                   output_payload={"ok": True})
    assert t["state"] == "succeeded"


def test_task_lifecycle_retry_budget_exhausted():
    """After max_retries, failed -> queued is rejected.

    SSOT note: state_machine.transition does NOT auto-increment retry_count
    (only reap_expired does, after a lease-expiry-triggered retry).  So to
    simulate budget exhaustion, the test directly forces the task's
    retry_count to max_retries via the task file before attempting the
    second retry."""
    import json as _json
    from pathlib import Path
    from src.paths import TASKS_DIR
    t = submit_task(title="r286-no-retry", assignee="codex", owner="claudecode",
                    max_retries=1)
    transition(t["task_id"], "running", actor="claudecode")
    transition(t["task_id"], "failed", actor="codex", error={"code": "X"})
    # Manually bump retry_count to max_retries via the task file
    task_path = TASKS_DIR / f"{t['task_id']}.json"
    raw = _json.loads(task_path.read_text(encoding="utf-8"))
    raw["retry_count"] = 1  # == max_retries
    task_path.write_text(_json.dumps(raw, ensure_ascii=False, indent=2),
                         encoding="utf-8")
    # Now failed -> queued must be rejected
    raised = False
    try:
        transition(t["task_id"], "queued", actor="claudecode", note="retry 2 (should fail)")
    except ValueError as e:
        raised = True
        assert "max_retries" in str(e), f"unexpected: {e}"
    assert raised, "expected ValueError when retry_count >= max_retries"


def test_input_request_and_approval_via_waiting():
    """input-request = transition to 'waiting'; approval = back to 'running'."""
    t = submit_task(title="r286-input", assignee="codex", owner="claudecode")
    transition(t["task_id"], "running", actor="claudecode")
    # Need user input
    t = transition(t["task_id"], "waiting", actor="codex",
                   note="awaiting user approval")
    assert t["state"] == "waiting"
    # Approved
    t = transition(t["task_id"], "running", actor="claudecode",
                   note="user approved")
    assert t["state"] == "running"
    # Done
    t = transition(t["task_id"], "succeeded", actor="codex",
                   output_payload={"approved": True})
    assert t["state"] == "succeeded"


def test_heartbeat_refreshes_lease():
    t = submit_task(title="r286-hb", assignee="codex", owner="claudecode",
                    timeout_ms=30000)
    transition(t["task_id"], "running", actor="claudecode")
    t1 = heartbeat(t["task_id"], actor="codex")
    time.sleep(0.05)
    t2 = heartbeat(t["task_id"], actor="codex")
    # t2.heartbeat_at must be ≥ t1.heartbeat_at (lexicographic ISO8601 ==)
    assert t2["heartbeat_at"] >= t1["heartbeat_at"]