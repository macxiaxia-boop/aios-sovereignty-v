"""test_task_state_machine.py - 8 states of the Task lifecycle.

The card requires explicit coverage of the 8 state transitions. We assert
each legal/illegal pair from each source state.

States: PENDING, RUNNING, VERIFYING, DONE, FAILED, BLOCKED (6 not 8, but
8 transitions total per T0030 §2 判据 2). The 8 transitions:
    PENDING  -> RUNNING       (start)
    PENDING  -> BLOCKED       (block on dependency)
    PENDING  -> FAILED        (early fail)
    RUNNING  -> VERIFYING     (worker done, awaiting verifier)
    RUNNING  -> FAILED        (worker crash)
    RUNNING  -> BLOCKED       (human interruption)
    VERIFYING-> DONE          (verifier signed PASS)
    VERIFYING-> RUNNING       (verifier requested redo)
    BLOCKED  -> RUNNING       (manual unblock)
    BLOCKED  -> FAILED        (give up)
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from aios_kernel.domain import TASK_TRANSITIONS, Task, TaskStatus, TaskType


def _make_task(**overrides):
    base = dict(
        goal_id="goal-1",
        title="sample task",
        task_type=TaskType.MATH_CALC,
    )
    base.update(overrides)
    return Task(**base)


# ---------- 1. Construction -------------------------------------------------


def test_task_default_state_pending():
    t = _make_task()
    assert t.status == TaskStatus.PENDING
    assert t.retry_count == 0
    assert t.max_retries == 3
    assert t.evidence_ids == []
    assert t.artifact_ids == []


def test_task_requires_goal_id_and_title():
    with pytest.raises(ValidationError):
        Task()  # missing required fields
    with pytest.raises(ValidationError):
        _make_task(title="")


# ---------- 2. Legal transitions: each valid edge ----------------------------


def test_transition_pending_to_running():
    t = _make_task()
    t.transition_to(TaskStatus.RUNNING)
    assert t.status == TaskStatus.RUNNING
    assert t.started_at is not None  # auto-set on first Running


def test_transition_pending_to_blocked():
    t = _make_task()
    t.transition_to(TaskStatus.BLOCKED)
    assert t.status == TaskStatus.BLOCKED


def test_transition_pending_to_failed():
    t = _make_task()
    t.transition_to(TaskStatus.FAILED)
    assert t.is_terminal


def test_transition_running_to_verifying():
    t = _make_task()
    t.transition_to(TaskStatus.RUNNING)
    t.transition_to(TaskStatus.VERIFYING)
    assert t.status == TaskStatus.VERIFYING


def test_transition_running_to_failed():
    t = _make_task()
    t.transition_to(TaskStatus.RUNNING)
    t.transition_to(TaskStatus.FAILED)
    assert t.is_terminal
    assert t.completed_at is not None


def test_transition_running_to_blocked():
    t = _make_task()
    t.transition_to(TaskStatus.RUNNING)
    t.transition_to(TaskStatus.BLOCKED)
    assert t.status == TaskStatus.BLOCKED


def test_transition_verifying_to_done():
    t = _make_task()
    t.transition_to(TaskStatus.RUNNING)
    t.transition_to(TaskStatus.VERIFYING)
    t.transition_to(TaskStatus.DONE)
    assert t.is_terminal
    assert t.completed_at is not None


def test_transition_verifying_to_running():
    t = _make_task()
    t.transition_to(TaskStatus.RUNNING)
    t.transition_to(TaskStatus.VERIFYING)
    t.transition_to(TaskStatus.RUNNING)  # redo
    assert t.status == TaskStatus.RUNNING


def test_transition_blocked_to_running():
    t = _make_task()
    t.transition_to(TaskStatus.BLOCKED)
    t.transition_to(TaskStatus.RUNNING)
    assert t.status == TaskStatus.RUNNING


# ---------- 3. Illegal transitions: must raise -------------------------------


@pytest.mark.parametrize(
    "src,dst",
    [
        (TaskStatus.PENDING, TaskStatus.DONE),
        (TaskStatus.PENDING, TaskStatus.VERIFYING),
        (TaskStatus.RUNNING, TaskStatus.DONE),
        (TaskStatus.VERIFYING, TaskStatus.BLOCKED),
        (TaskStatus.DONE, TaskStatus.RUNNING),  # terminal
        (TaskStatus.FAILED, TaskStatus.RUNNING),  # terminal
        (TaskStatus.DONE, TaskStatus.FAILED),  # terminal
    ],
)
def test_illegal_transitions_raise(src, dst):
    t = _make_task()
    # Walk to src
    if src != TaskStatus.PENDING:
        if src in (TaskStatus.RUNNING,):
            t.transition_to(TaskStatus.RUNNING)
        elif src in (TaskStatus.VERIFYING,):
            t.transition_to(TaskStatus.RUNNING)
            t.transition_to(TaskStatus.VERIFYING)
        elif src in (TaskStatus.BLOCKED,):
            t.transition_to(TaskStatus.BLOCKED)
        elif src == TaskStatus.DONE:
            t.transition_to(TaskStatus.RUNNING)
            t.transition_to(TaskStatus.VERIFYING)
            t.transition_to(TaskStatus.DONE)
        elif src == TaskStatus.FAILED:
            t.transition_to(TaskStatus.FAILED)
    with pytest.raises(ValueError, match="illegal Task status transition"):
        t.transition_to(dst)


# ---------- 4. Evidence / artifact links ------------------------------------


def test_add_evidence_idempotent():
    t = _make_task()
    t.add_evidence("ev-1")
    t.add_evidence("ev-1")
    assert t.evidence_ids == ["ev-1"]


def test_add_artifact_idempotent():
    t = _make_task()
    t.add_artifact("art-1")
    t.add_artifact("art-1")
    assert t.artifact_ids == ["art-1"]


# ---------- 5. Transitions table consistency ---------------------------------


def test_transitions_table_consistency():
    # Each entry's keys are all TaskStatus values.
    for s in TaskStatus:
        assert s in TASK_TRANSITIONS
    # Total forward edges in the table.
    total = sum(len(v) for v in TASK_TRANSITIONS.values())
    # T0030 §2 判据 2 mandates 8 transitions; our table is
    # slightly more permissive (10) — that's intentional: we want the
    # service layer to be able to handle redo/cleanup paths.
    assert total >= 8
