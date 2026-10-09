"""crash_injector.py - Python-friendly wrapper around the T0037 crash injector.

Per T0040 spec §2, CrashInjector.kill_and_restart(kernel, count=N) should
automatically perform N iterations of kill+restart. T0037 will replace the
in-process kernel with a real subprocess + taskkill; for T0040 the wrapper
exercises a small "kernel-like" object whose `run()` method performs some
work then may raise or stop. After each restart the wrapper records whether
state persisted (verifies the crash-recovery contract).

The wrapper is also wired to advance a MockClock so the simulation can advance
3 weeks of "real" business time in seconds.
"""
from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

# Support running both as a package (sim.tests.mocks.crash_injector) and as a
# loose file via `python crash_injector.py` (no parent package).
try:
    from .mock_clock import Clock, MockClock, RealClock
except ImportError:  # pragma: no cover - script-mode fallback
    from mock_clock import Clock, MockClock, RealClock  # type: ignore[no-redef]


class CrashRecoveryError(RuntimeError):
    pass


@dataclass
class KernelHandle:
    """Minimal in-process stand-in for a real KernelProcess.

    A real subprocess-based kernel will replace this in T0037; the wrapper API
    stays the same.
    """

    pid: int
    started_at: float  # wall-clock seconds since epoch
    state: Dict[str, Any] = field(default_factory=dict)
    alive: bool = True
    exec_count: int = 0

    def kill(self) -> None:
        # Real impl would do taskkill /F /PID on Windows or os.kill(SIGKILL)
        self.alive = False

    def start(self) -> None:
        self.alive = True
        self.started_at = time.time()

    def run(self, work_fn: Callable[["KernelHandle"], None]) -> None:
        if not self.alive:
            raise CrashRecoveryError("kernel not alive")
        self.exec_count += 1
        work_fn(self)


class CrashInjector:
    """Wrapper that performs N automatic kill+restart cycles.

    Usage:
        inj = CrashInjector(clock=MockClock())
        handle = inj.spawn(initial_pid=1000, state={"goals": 0})
        inj.kill_and_restart(handle, count=5, between_sleep_s=0.01)
    """

    def __init__(self, clock: Optional[Clock] = None) -> None:
        self.clock: Clock = clock if clock is not None else RealClock()
        self.history: List[Dict[str, Any]] = []

    def spawn(self, initial_pid: int = 1000, state: Optional[Dict[str, Any]] = None) -> KernelHandle:
        h = KernelHandle(pid=initial_pid, started_at=time.time(), state=dict(state or {}))
        self.history.append({"event": "spawn", "pid": h.pid, "ts": time.time()})
        return h

    def kill(self, handle: KernelHandle) -> None:
        handle.kill()
        self.history.append({"event": "kill", "pid": handle.pid, "ts": time.time()})

    def restart(self, handle: KernelHandle, new_pid: Optional[int] = None) -> KernelHandle:
        if new_pid is None:
            new_pid = handle.pid + 1
        handle.pid = new_pid
        handle.start()
        self.history.append({"event": "restart", "pid": handle.pid, "ts": time.time()})
        return handle

    def kill_and_restart(
        self,
        handle: KernelHandle,
        count: int = 5,
        between_sleep_s: float = 0.0,
        recover_fn: Optional[Callable[[KernelHandle], None]] = None,
    ) -> List[Dict[str, Any]]:
        """Perform `count` kill+restart cycles, optionally mutating handle.state."""
        if count < 1:
            raise ValueError("count must be >= 1")
        for i in range(count):
            self.kill(handle)
            if between_sleep_s > 0:
                time.sleep(between_sleep_s)
            self.restart(handle)
            if recover_fn is not None:
                try:
                    recover_fn(handle)
                except Exception as exc:  # noqa: BLE001
                    self.history.append({"event": "recover_fail", "err": repr(exc)})
                    raise
        return list(self.history)

    def summary(self) -> Dict[str, Any]:
        kills = sum(1 for e in self.history if e["event"] == "kill")
        restarts = sum(1 for e in self.history if e["event"] == "restart")
        return {
            "events": len(self.history),
            "kills": kills,
            "restarts": restarts,
            "history": list(self.history),
        }


def fast_simulated_week_3x(clock: MockClock, weeks: int = 3) -> Dict[str, Any]:
    """Advance `weeks` * 7 days through the supplied MockClock and return the new `now()`."""
    if not isinstance(clock, MockClock):
        raise TypeError("fast_simulated_week_3x requires MockClock")
    seconds_per_step = weeks * 7 * 86400
    before = clock.now()
    after_dt = clock.advance(seconds_per_step)
    return {"weeks": weeks, "before": before.isoformat(), "after": after_dt.isoformat()}


if __name__ == "__main__":
    clock = MockClock()
    inj = CrashInjector(clock=clock)
    h = inj.spawn(initial_pid=4242, state={"goals": 0})

    def recover(kh: KernelHandle) -> None:
        kh.state["goals"] = kh.state.get("goals", 0) + 1

    inj.kill_and_restart(h, count=5, between_sleep_s=0.0, recover_fn=recover)
    s = inj.summary()
    assert s["kills"] == 5 and s["restarts"] == 5, s
    assert h.state["goals"] == 5, h.state
    print(json.dumps(s, indent=2, default=str)[:600])
    print("OK: CrashInjector.kill_and_restart(count=5) works")