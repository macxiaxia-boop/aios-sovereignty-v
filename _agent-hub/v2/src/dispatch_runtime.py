"""Shared retry and bounded-concurrency primitives for v2 adapters."""
from __future__ import annotations

import random
import subprocess
import threading
import time
from typing import Any, Callable, Mapping, Optional

RETRY_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 2.0, 4.0)
MAX_PARALLEL_SUBPROCESS = 3
_SUBPROCESS_SLOTS = threading.BoundedSemaphore(MAX_PARALLEL_SUBPROCESS)
_HTTP_SLOTS = threading.BoundedSemaphore(MAX_PARALLEL_SUBPROCESS)


def backoff_seconds(attempt: int) -> float:
    """Return 1s/2s/4s plus bounded jitter for a one-based failed attempt."""
    base = BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)]
    return base + random.uniform(0.0, min(0.25, base / 4.0))


def sleep_backoff(attempt: int, sleeper: Callable[[float], None] = time.sleep) -> float:
    delay = backoff_seconds(attempt)
    sleeper(delay)
    return delay


def run_subprocess_with_retry(
    command: list[str],
    *,
    cwd: Optional[str] = None,
    env: Optional[Mapping[str, str]] = None,
    timeout: Optional[float] = None,
    shell: bool = False,
    attempts: int = RETRY_ATTEMPTS,
    sleeper: Callable[[float], None] = time.sleep,
) -> tuple[Any, dict]:
    """Run a subprocess at most three times with exponential backoff.

    Non-zero exits and subprocess exceptions are retried. The final exception is
    re-raised so callers can keep their existing structured error contract.
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    started = time.time()
    backoffs: list[float] = []
    last_error: Optional[BaseException] = None
    for attempt in range(1, attempts + 1):
        try:
            with _SUBPROCESS_SLOTS:
                proc = subprocess.run(
                    command,
                    cwd=cwd,
                    env=env,
                    capture_output=True,
                    timeout=timeout,
                    shell=shell,
                )
        except (OSError, subprocess.SubprocessError) as exc:
            last_error = exc
            if attempt >= attempts:
                raise
            backoffs.append(sleep_backoff(attempt, sleeper))
            continue
        meta = {
            "attempts": attempt,
            "backoff_delays_ms": [round(delay * 1000) for delay in backoffs],
            "duration_ms": int((time.time() - started) * 1000),
        }
        if proc.returncode == 0 or attempt >= attempts:
            return proc, meta
        backoffs.append(sleep_backoff(attempt, sleeper))
    raise last_error if last_error else RuntimeError("subprocess retry exhausted")


def http_slot():
    """Context manager-compatible semaphore for bounded HTTP dispatch."""
    return _HTTP_SLOTS
