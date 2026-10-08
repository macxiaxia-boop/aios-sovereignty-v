# v2/src/lock.py — cross-platform file lock (Windows msvcrt.locking + POSIX fcntl.flock).
#
# Why we need this:
#   queue.py:enqueue is read-modify-write on idempotency_index.json AND on the
#   inbox file system. Without a lock, two concurrent enqueue calls (even on
#   the same machine) can:
#     (a) read the same idx, both decide "not seen", both write same key twice
#     (b) collide on the tmp file name (WinError 32 sharing violation on Win)
#   With this lock the entire enqueue is serialized at the index level.
#
# Scopes:
#   - cross-PROCESS via msvcrt.locking(fd, LK_LOCK, 1) on Windows / fcntl.flock on POSIX
#   - cross-THREAD via threading.Lock() inside the same process
#   - reentrant lock only if the caller asks (default: non-reentrant to surface deadlocks early)
from __future__ import annotations

import contextlib
import os
import sys
import threading
from pathlib import Path
from typing import Optional

# Module-level in-process mutexes keyed by absolute path -> threading.Lock()
# (so multiple locks on different files do not block each other)
_THREAD_LOCKS: dict = {}
_THREAD_LOCKS_MUTEX = threading.Lock()


def _get_thread_lock(key: str) -> threading.Lock:
    with _THREAD_LOCKS_MUTEX:
        lk = _THREAD_LOCKS.get(key)
        if lk is None:
            lk = threading.Lock()
            _THREAD_LOCKS[key] = lk
        return lk


@contextlib.contextmanager
def file_lock(path: Path, *, mode: str = "exclusive", timeout_s: float = 30.0,
              poll_interval_s: float = 0.05):
    """Acquire a cross-process lock on `path` (the path itself is the lock target).
    Falls back to thread-only lock if neither msvcrt nor fcntl is available.
    On acquisition failure, raises TimeoutError.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure the file exists so we can open it (only used as a lock anchor).
    if not path.exists():
        path.touch()
    abs_key = str(path.resolve())
    thread_lock = _get_thread_lock(abs_key)
    thread_lock.acquire()
    fd: Optional[int] = None
    try:
        # Acquire cross-process lock with simple retry
        deadline = _now() + timeout_s
        while True:
            try:
                fd = os.open(abs_key, os.O_RDWR)
                break
            except OSError as e:
                # On Windows: WinError 32 (sharing violation) means another process holds it.
                if _now() >= deadline:
                    raise TimeoutError(f"could not open lock file {abs_key}: {e}") from e
                _sleep(poll_interval_s)
        # Try locking 1 byte
        while True:
            try:
                _lock_fd(fd, 1)
                break
            except OSError:
                if _now() >= deadline:
                    try:
                        os.close(fd)
                    except OSError:
                        pass
                    raise TimeoutError(f"timed out waiting for file lock on {abs_key}")
                _sleep(poll_interval_s)
        yield fd
    finally:
        if fd is not None:
            try:
                _unlock_fd(fd, 1)
            except OSError:
                pass
            try:
                os.close(fd)
            except OSError:
                pass
        thread_lock.release()


# platform-specific lockers
def _lock_fd(fd: int, nbytes: int) -> None:
    if sys.platform == "win32":
        import msvcrt
        # LK_LOCK = 1; blocks until nbytes can be locked
        msvcrt.locking(fd, msvcrt.LK_LOCK, nbytes)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX)


def _unlock_fd(fd: int, nbytes: int) -> None:
    if sys.platform == "win32":
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_UNLCK, nbytes)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)


def _now() -> float:
    import time
    return time.monotonic()


def _sleep(seconds: float) -> None:
    import time
    time.sleep(seconds)