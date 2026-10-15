"""mock_clock.py - Deterministic clock with time-compression for simulation.

Design:
- `Clock` is the simulation-time interface kernel time-sensitive code MUST use
  in place of `datetime.now()` (per T0040 spec §1d).
- `time_compression` lets a test step "1 simulated day" by calling
  `advance(86400)` — useful for 3-week phase simulation in < 1 minute wall time.
- `freeze_at(datetime)` pins the clock for deterministic assertions.
- `MockClock` is the in-process implementation; `RealClock` wraps
  `datetime.now()` so production code paths can also inject a Clock.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

# Default: 1 wall-clock second of `advance()` == 1 simulated day (86400s).
DEFAULT_TIME_COMPRESSION: int = 86400


class Clock:
    """Interface that kernel time-sensitive code MUST use (per T0040 spec)."""

    def now(self) -> datetime:
        raise NotImplementedError

    def advance(self, seconds: int | float) -> datetime:
        raise NotImplementedError

    def freeze_at(self, when: datetime) -> None:
        raise NotImplementedError

    def unfreeze(self) -> None:
        raise NotImplementedError


class MockClock(Clock):
    """In-process deterministic clock.

    `time_compression` is recorded so callers can verify the configured ratio
    (e.g. `time_compression == 86400` for 1-second-equals-1-day). The actual
    arithmetic of `now()` is independent of compression — the operator is a
    labeling aid only (so the e2e test can assert the config matches).
    """

    base_time: datetime
    time_compression: int
    _offset: float
    _frozen: bool
    _frozen_at: datetime | None

    def __init__(
        self,
        base_time: datetime | None = None,
        time_compression: int = DEFAULT_TIME_COMPRESSION,
    ) -> None:
        if base_time is None:
            base_time = datetime(2026, 10, 8, 0, 0, 0, tzinfo=UTC)
        elif base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=UTC)
        self.base_time = base_time
        self.time_compression = int(time_compression)
        self._offset = 0.0
        self._frozen = False
        self._frozen_at = None

    def now(self) -> datetime:
        if self._frozen and self._frozen_at is not None:
            return self._frozen_at
        return self.base_time + timedelta(seconds=self._offset)

    def advance(self, seconds: int | float) -> datetime:
        """Advance the clock by `seconds` of simulated time and return the new `now()`."""
        if self._frozen:
            raise RuntimeError("cannot advance a frozen clock; call unfreeze() first")
        seconds = float(seconds)
        if seconds < 0:
            raise ValueError("advance() requires non-negative seconds")
        self._offset += seconds
        return self.now()

    def freeze_at(self, when: datetime) -> None:
        if when.tzinfo is None:
            when = when.replace(tzinfo=UTC)
        self._frozen = True
        self._frozen_at = when
        delta = (when - self.base_time).total_seconds()
        self._offset = delta

    def unfreeze(self) -> None:
        self._frozen = False
        self._frozen_at = None

    def advance_days(self, days: int | float) -> datetime:
        return self.advance(days * 86400)

    def advance_hours(self, hours: int | float) -> datetime:
        return self.advance(hours * 3600)


class RealClock(Clock):
    """Production clock backed by datetime.now(UTC)."""

    def now(self) -> datetime:
        return datetime.now(UTC)

    def advance(self, seconds: int | float) -> datetime:
        # In a real clock, advance() is a no-op (time already passes).
        return self.now()

    def freeze_at(self, when: datetime) -> None:
        raise NotImplementedError("RealClock cannot be frozen")

    def unfreeze(self) -> None:
        raise NotImplementedError("RealClock has no freeze state")


if __name__ == "__main__":
    c = MockClock()
    t0 = c.now()
    assert t0 == c.base_time
    t1 = c.advance_days(1)
    assert (t1 - t0).total_seconds() == 86400
    t2 = c.advance_hours(2)
    assert (t2 - t1).total_seconds() == 7200
    pin = datetime(2026, 12, 31, 23, 59, 59, tzinfo=UTC)
    c.freeze_at(pin)
    assert c.now() == pin
    # advance() must refuse while frozen
    try:
        c.advance(1)
    except RuntimeError:
        pass
    else:
        raise AssertionError("expected RuntimeError when advancing a frozen clock")
    c.unfreeze()
    # compression label sanity
    assert c.time_compression == 86400
    print("OK: now/advance/freeze/unfreeze/advance_days all work")
