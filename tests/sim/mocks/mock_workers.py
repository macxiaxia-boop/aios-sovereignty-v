"""mock_workers.py - 6 mock worker adapters for AIOS Kernel simulation harness.

6 worker types are designed to expose distinct failure modes required by the
Phase A acceptance criteria and downstream test cards:

- SuccessWorker:       normal happy path (T0036 100-task loop)
- FakeDoneWorker:      reports Done with empty evidence (T0036 False Completion)
- CrashWorker:         raises WorkerCrashException mid-execute (T0037)
- TimeoutWorker:       sleeps past the deadline (T0037)
- RetryableFailWorker: first 2 attempts fail, 3rd succeeds (T0033 retry)
- PermanentFailWorker: every attempt fails (T0037 + T0036 negative path)

All workers share a common protocol so the runner can drive them uniformly.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional


# ---------- Custom exception hierarchy ---------------------------------------


class WorkerError(Exception):
    """Base worker error."""


class WorkerCrashException(WorkerError):
    """Raised by CrashWorker to simulate a process-level crash mid-execute."""


class WorkerTimeoutException(WorkerError):
    """Raised when worker exceeds its allowed deadline."""


class WorkerFakeDoneException(WorkerError):
    """Raised by FakeDoneWorker — reports done but evidence is empty."""


# ---------- Common artifact / result types -----------------------------------


@dataclass
class Artifact:
    id: str
    task_id: str
    payload: str
    evidence_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "task_id": self.task_id,
            "payload": self.payload,
            "evidence_ids": list(self.evidence_ids),
        }


@dataclass
class WorkerResult:
    success: bool
    artifact: Optional[Artifact] = None
    error: Optional[str] = None
    crash: bool = False
    fake_done: bool = False
    timed_out: bool = False
    attempts: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "crash": self.crash,
            "fake_done": self.fake_done,
            "timed_out": self.timed_out,
            "attempts": self.attempts,
            "error": self.error,
            "artifact": self.artifact.to_dict() if self.artifact else None,
        }


# ---------- 6 worker adapters ------------------------------------------------


class SuccessWorker:
    name = "SuccessWorker"

    def execute(self, task: Dict[str, Any]) -> WorkerResult:
        return WorkerResult(
            success=True,
            artifact=Artifact(
                id=f"art-{task['id']}-ok",
                task_id=task["id"],
                payload=f"SUCCESS::{task['type']}::{task.get('payload', {})}",
                evidence_ids=[f"ev-{task['id']}"],
            ),
        )


class FakeDoneWorker:
    """Reports success but evidence list is empty — should be rejected by Verifier."""

    name = "FakeDoneWorker"

    def execute(self, task: Dict[str, Any]) -> WorkerResult:
        return WorkerResult(
            success=True,
            artifact=Artifact(
                id=f"art-{task['id']}-fake",
                task_id=task["id"],
                payload=f"FAKE_DONE::{task['type']}",
                evidence_ids=[],  # intentionally empty
            ),
            fake_done=True,
        )


class CrashWorker:
    name = "CrashWorker"
    crash_after_artifact: bool = False  # default: crash before producing anything

    def execute(self, task: Dict[str, Any]) -> WorkerResult:
        if self.crash_after_artifact:
            # produce an artifact, then crash mid-execute
            partial = Artifact(
                id=f"art-{task['id']}-partial",
                task_id=task["id"],
                payload="partial payload",
                evidence_ids=[],
            )
            raise WorkerCrashException(f"kernel crash while finalizing {task['id']}")
        raise WorkerCrashException(f"kernel crash on {task['id']}")


class TimeoutWorker:
    name = "TimeoutWorker"
    default_timeout_s: float = 0.05  # 50ms; runner does not enforce here

    def execute(self, task: Dict[str, Any]) -> WorkerResult:
        time.sleep(self.default_timeout_s * 100)  # sleep 5s — definitely past 50ms
        return WorkerResult(
            success=False,
            error="timeout exceeded",
            timed_out=True,
        )


class RetryableFailWorker:
    """Fails the first `fail_count` attempts; succeeds on the (fail_count+1)-th.

    Per spec, fail_count=2 → third attempt succeeds. State is per-task so the
    runner can drive `try_for(retries=3)` semantics.
    """

    name = "RetryableFailWorker"
    fail_count: int = 2

    def __init__(self) -> None:
        self._seen: Dict[str, int] = {}

    def execute(self, task: Dict[str, Any]) -> WorkerResult:
        seen = self._seen.get(task["id"], 0) + 1
        self._seen[task["id"]] = seen
        if seen <= self.fail_count:
            return WorkerResult(
                success=False,
                error=f"retryable fail attempt={seen}",
                attempts=seen,
            )
        return WorkerResult(
            success=True,
            attempts=seen,
            artifact=Artifact(
                id=f"art-{task['id']}-retry",
                task_id=task["id"],
                payload=f"RETRY_OK::{task['type']}::attempts={seen}",
                evidence_ids=[f"ev-{task['id']}-r{seen}"],
            ),
        )


class PermanentFailWorker:
    name = "PermanentFailWorker"

    def execute(self, task: Dict[str, Any]) -> WorkerResult:
        return WorkerResult(
            success=False,
            error="permanent failure",
            attempts=1,
        )


# ---------- Factory ----------------------------------------------------------

WORKER_REGISTRY = {
    cls.name: cls for cls in (
        SuccessWorker,
        FakeDoneWorker,
        CrashWorker,
        TimeoutWorker,
        RetryableFailWorker,
        PermanentFailWorker,
    )
}


def get_worker(name: str):
    if name not in WORKER_REGISTRY:
        raise KeyError(f"unknown worker {name!r}; known: {sorted(WORKER_REGISTRY)}")
    return WORKER_REGISTRY[name]()


if __name__ == "__main__":
    # smoke
    t = {"id": "task-x", "type": "math_calc"}
    assert isinstance(SUCCESS := SuccessWorker().execute(t), WorkerResult)
    assert SUCCESS.success and SUCCESS.artifact and SUCCESS.artifact.evidence_ids
    fake = FakeDoneWorker().execute(t)
    assert fake.success and fake.artifact and not fake.artifact.evidence_ids
    try:
        CrashWorker().execute(t)
    except WorkerCrashException:
        pass
    else:
        raise AssertionError("CrashWorker must raise")
    print("OK: all 6 workers behave correctly (smoke)")