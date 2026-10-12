"""test_state_machine.py - Unit tests for FSMachine (R1503-002).

Covers:
  - Initial state
  - Basic transition
  - Guard predicate accept/reject
  - Illegal transition raises
  - Reset
  - Workflow + Task FSMs
  - on_enter / on_exit hooks
"""
from __future__ import annotations

import pytest

from aios_kernel.domain.task import TaskStatus
from aios_kernel.state_machine import (
    FSMachine,
    IllegalTransition,
    Transition,
    task_fsm,
    workflow_fsm,
)
from aios_kernel.workflows.workflow import WorkflowStatus


class _E(str):
    pass


def _make_machine() -> FSMachine:
    class _S(str):
        pass

    # Use plain string enums for the test (FSMachine is generic).
    S = type("S", (), {"A": "a", "B": "b", "C": "c"})
    E = type("E", (), {"NEXT": "next", "BACK": "back"})

    transitions = [
        Transition(src=S.A, event=E.NEXT, dst=S.B),
        Transition(src=S.B, event=E.NEXT, dst=S.C),
        Transition(src=S.A, event=E.BACK, dst=S.A),  # no-op
    ]
    return FSMachine(name="test", initial=S.A, transitions=transitions)


def test_fsm_initial_state():
    fsm = _make_machine()
    assert fsm.state == "a"


def test_fsm_basic_transition():
    fsm = _make_machine()
    new = fsm.fire("next")
    assert new == "b"


def test_fsm_chained_transitions():
    fsm = _make_machine()
    fsm.fire("next")
    fsm.fire("next")
    assert fsm.state == "c"


def test_fsm_illegal_transition_raises():
    fsm = _make_machine()
    fsm.fire("next")  # A → B
    with pytest.raises(IllegalTransition):
        fsm.fire("back")  # B has no BACK transition → illegal


def test_fsm_can_fire():
    fsm = _make_machine()
    assert fsm.can_fire("next") is True
    fsm.fire("next")
    # B has no BACK transition
    assert fsm.can_fire("back") is False


def test_fsm_guard_accept():
    class _S(str):
        pass

    S = type("S", (), {"A": "a", "B": "b"})
    E = type("E", (), {"GO": "go"})
    transitions = [
        Transition(src=S.A, event=E.GO, dst=S.B, guard=lambda ctx: ctx.get("ok")),
    ]
    fsm = FSMachine(name="g", initial=S.A, transitions=transitions)
    assert fsm.can_fire("go", ctx={"ok": False}) is False
    new = fsm.fire("go", ctx={"ok": True})
    assert new == "b"


def test_fsm_on_enter_hook_called():
    calls = []

    class _S(str):
        pass

    S = type("S", (), {"A": "a", "B": "b"})
    E = type("E", (), {"GO": "go"})

    def on_enter(state, ctx):
        calls.append(("enter", state))

    transitions = [Transition(src=S.A, event=E.GO, dst=S.B, on_enter=on_enter)]
    fsm = FSMachine(name="hook", initial=S.A, transitions=transitions)
    fsm.fire("go")
    assert calls == [("enter", "b")]


def test_fsm_on_exit_hook_called():
    calls = []

    class _S(str):
        pass

    S = type("S", (), {"A": "a", "B": "b"})
    E = type("E", (), {"GO": "go"})

    def on_exit(state, ctx):
        calls.append(("exit", state))

    transitions = [Transition(src=S.A, event=E.GO, dst=S.B, on_exit=on_exit)]
    fsm = FSMachine(name="hook", initial=S.A, transitions=transitions)
    fsm.fire("go")
    assert calls == [("exit", "a")]


def test_fsm_reset():
    fsm = _make_machine()
    fsm.fire("next")
    fsm.reset()
    assert fsm.state == "a"


def test_workflow_fsm_pending_to_running_to_completed():
    fsm = workflow_fsm()
    assert fsm.state == WorkflowStatus.PENDING
    fsm.fire("start")
    assert fsm.state == WorkflowStatus.RUNNING
    fsm.fire("complete")
    assert fsm.state == WorkflowStatus.COMPLETED


def test_task_fsm_full_lifecycle():
    fsm = task_fsm()
    assert fsm.state == TaskStatus.PENDING
    fsm.fire("start")
    assert fsm.state == TaskStatus.RUNNING
    fsm.fire("verify")
    assert fsm.state == TaskStatus.VERIFYING
    fsm.fire("done")
    assert fsm.state == TaskStatus.DONE


def test_task_fsm_block_unblock_cycle():
    fsm = task_fsm()
    fsm.fire("start")
    fsm.fire("block")
    assert fsm.state == TaskStatus.BLOCKED
    fsm.fire("unblock")
    assert fsm.state == TaskStatus.RUNNING


def test_task_fsm_redo():
    """VERIFYING → RUNNING (redo) is allowed."""
    fsm = task_fsm()
    fsm.fire("start")
    fsm.fire("verify")
    fsm.fire("redo")
    assert fsm.state == TaskStatus.RUNNING