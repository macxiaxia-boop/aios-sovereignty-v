"""state_machine.py - Generic finite state machine (R1503-002).

Provides a typed finite state machine usable by Workflow and Task status
transitions. Transitions are declarative; the machine enforces them at
runtime. This is the kernel-side primitive the Task 8-state and Workflow
5-state machines in domain/task.py + workflows/workflow.py are built on.

R1503-002 acceptance:
  - Generic typed FSM (S = enum, E = event)
  - Declarative transitions (raise on illegal)
  - Guard predicates
  - Side-effect hooks (on_enter / on_exit)
  - History (current_state + last_n)

Co-Authored-By: Claude Code <noreply@anthropic.com>
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, TypeVar

log = logging.getLogger("aios_kernel.state_machine")

S = TypeVar("S")
E = TypeVar("E")


def _label(value: object) -> str:
    """Return the human-readable label for either an Enum member or a plain value."""
    v = getattr(value, "value", None)
    if v is None:
        return str(value)
    return v if isinstance(v, str) else str(v)


@dataclass
class Transition(Generic[S, E]):
    """One row of the FSM transition table."""

    src: S
    event: E
    dst: S
    guard: Callable[[Any], bool] | None = None
    on_exit: Callable[[S, Any], None] | None = None
    on_enter: Callable[[S, Any], None] | None = None


class IllegalTransition(RuntimeError):
    """Raised when no transition matches (src, event) or guard rejects."""


@dataclass
class FSMachine(Generic[S, E]):
    """Typed finite state machine."""

    name: str
    initial: S
    transitions: list[Transition[S, E]] = field(default_factory=list)
    _state: S | None = field(default=None, init=False)
    _history: list[tuple[S, float]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        if self._state is None:
            self._state = self.initial
            self._history.append((self.initial, 0.0))

    # ----- public surface -------------------------------------------------

    @property
    def state(self) -> S:
        assert self._state is not None
        return self._state

    @property
    def history(self) -> list[tuple[S, float]]:
        """Returns [(state, ts_repr), ...] newest last."""
        return list(self._history)

    def can_fire(self, event: E, ctx: Any = None) -> bool:
        for t in self.transitions:
            if t.src == self._state and t.event == event:
                if t.guard is None or t.guard(ctx):
                    return True
        return False

    def fire(self, event: E, ctx: Any = None) -> S:
        """Fire an event; return new state. Raises IllegalTransition if no rule."""
        for t in self.transitions:
            if t.src != self._state or t.event != event:
                continue
            if t.guard is not None and not t.guard(ctx):
                continue
            # matched
            old_state = self._state
            if t.on_exit is not None:
                try:
                    t.on_exit(old_state, ctx)
                except Exception:  # noqa: BLE001
                    log.exception("on_exit hook raised for %s/%s", self.name, event)
            self._state = t.dst
            import time
            self._history.append((self._state, time.time()))
            if t.on_enter is not None:
                try:
                    t.on_enter(self._state, ctx)
                except Exception:  # noqa: BLE001
                    log.exception("on_enter hook raised for %s/%s", self.name, event)
            log.info(
                "fsm.fire: name=%s event=%s %s → %s",
                self.name, _label(event), _label(old_state), _label(self._state),
            )
            return self._state
        raise IllegalTransition(
            f"{self.name}: no transition from {_label(self._state)} on event {_label(event)}"
        )

    def reset(self) -> None:
        self._state = self.initial
        self._history = [(self.initial, 0.0)]


__all__ = [
    "FSMachine",
    "Transition",
    "IllegalTransition",
]


# ----- Concrete FSMs binding WorkflowStatus + TaskStatus --------------------

from aios_kernel.domain.task import TaskStatus, TaskType  # noqa: E402
from aios_kernel.workflows.workflow import WorkflowStatus  # noqa: E402


# Workflow FSM: PENDING → RUNNING → COMPLETED|FAILED|CANCELLED
WORKFLOW_FSM_TRANSITIONS: list[Transition[WorkflowStatus, Any]] = [
    Transition(WorkflowStatus.PENDING, "start", WorkflowStatus.RUNNING),
    Transition(WorkflowStatus.RUNNING, "complete", WorkflowStatus.COMPLETED),
    Transition(WorkflowStatus.RUNNING, "fail", WorkflowStatus.FAILED),
    Transition(WorkflowStatus.RUNNING, "cancel", WorkflowStatus.CANCELLED),
    Transition(WorkflowStatus.PENDING, "cancel", WorkflowStatus.CANCELLED),
]


# Task FSM: PENDING → RUNNING → VERIFYING → DONE|FAILED|BLOCKED
TASK_FSM_TRANSITIONS: list[Transition[TaskStatus, Any]] = [
    Transition(TaskStatus.PENDING, "start", TaskStatus.RUNNING),
    Transition(TaskStatus.RUNNING, "verify", TaskStatus.VERIFYING),
    Transition(TaskStatus.VERIFYING, "done", TaskStatus.DONE),
    Transition(TaskStatus.VERIFYING, "redo", TaskStatus.RUNNING),
    Transition(TaskStatus.VERIFYING, "fail", TaskStatus.FAILED),
    Transition(TaskStatus.RUNNING, "fail", TaskStatus.FAILED),
    Transition(TaskStatus.PENDING, "block", TaskStatus.BLOCKED),
    Transition(TaskStatus.RUNNING, "block", TaskStatus.BLOCKED),
    Transition(TaskStatus.BLOCKED, "unblock", TaskStatus.RUNNING),
]


def workflow_fsm() -> FSMachine[WorkflowStatus, str]:
    """Returns a fresh Workflow FSM instance."""
    return FSMachine(
        name="workflow",
        initial=WorkflowStatus.PENDING,
        transitions=WORKFLOW_FSM_TRANSITIONS,  # type: ignore[list-item]
    )


def task_fsm() -> FSMachine[TaskStatus, str]:
    """Returns a fresh Task FSM instance."""
    return FSMachine(
        name="task",
        initial=TaskStatus.PENDING,
        transitions=TASK_FSM_TRANSITIONS,  # type: ignore[list-item]
    )