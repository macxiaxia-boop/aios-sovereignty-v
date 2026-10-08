#!/usr/bin/env python3
# v2/src/start_consumer_real.py — start v2_consumer with REAL claude -p adapter + mutex
from __future__ import annotations

import argparse
import atexit
import msvcrt
import os
import re
import sys
import time
from pathlib import Path

# Ensure src package import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import psutil
except ImportError:
    psutil = None

from src import v2_consumer
from src.claude_adapter import _claude_dispatch_adapter


_LOCK_FD = None


def _lock_path() -> Path:
    v2_root = Path(os.environ.get("AIOS_V2_ROOT", r"D:\AIOS\_agent-hub\v2")).resolve()
    return v2_root / "state" / ".aios_v2_consumer.lock"


def _same_consumer_process(pid: int) -> bool:
    if psutil is None:
        return False
    try:
        if not psutil.pid_exists(pid):
            return False
        cmdline = " ".join(psutil.Process(pid).cmdline())
        return "start_consumer_real" in cmdline or "src.v2_consumer" in cmdline
    except (psutil.Error, OSError, ValueError):
        return False


def _another_consumer_process() -> int | None:
    """Find a live peer even when an older consumer predates the lock file."""
    if psutil is None:
        return None
    current = os.getpid()
    for proc in psutil.process_iter(["pid", "cmdline"]):
        try:
            pid = int(proc.info.get("pid") or 0)
            if pid == current:
                continue
            cmdline = " ".join(proc.info.get("cmdline") or [])
            if "start_consumer_real" in cmdline or "src.v2_consumer" in cmdline:
                return pid
        except (psutil.Error, OSError, ValueError):
            continue
    return None


def _singleton_check() -> bool:
    """Acquire the Windows byte-range lock; exit 0 if a consumer already owns it."""
    global _LOCK_FD
    lock_path = _lock_path()
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    fd = open(lock_path, "a+b")
    try:
        fd.seek(0)
        if lock_path.stat().st_size == 0:
            fd.write(b" ")
            fd.flush()
        fd.seek(0)
        msvcrt.locking(fd.fileno(), msvcrt.LK_NBLCK, 1)
    except (OSError, IOError):
        try:
            fd.close()
        except OSError:
            pass
        print("[singleton] another consumer owns the lock; exiting", flush=True)
        return False

    # Older consumers did not always create the lock file. Avoid starting a
    # duplicate during the migration window; this never kills an existing peer.
    peer_pid = _another_consumer_process()
    if peer_pid is not None:
        try:
            fd.seek(0)
            msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        try:
            fd.close()
        except OSError:
            pass
        print(f"[singleton] consumer peer already running (PID {peer_pid}); exiting", flush=True)
        return False

    _LOCK_FD = fd
    fd.seek(0)
    fd.truncate()
    fd.write(f"PID={os.getpid()} TIME={time.time()}\n".encode("utf-8"))
    fd.flush()
    print(f"[singleton] acquired PID={os.getpid()}", flush=True)
    return True


def _release_lock() -> None:
    global _LOCK_FD
    fd, _LOCK_FD = _LOCK_FD, None
    if fd is None:
        return
    try:
        fd.seek(0)
        msvcrt.locking(fd.fileno(), msvcrt.LK_UNLCK, 1)
    except OSError:
        pass
    try:
        fd.close()
    except OSError:
        pass


atexit.register(_release_lock)


if __name__ == "__main__":
    if not _singleton_check():
        sys.exit(0)
    v2_consumer.set_dispatcher(_claude_dispatch_adapter)
    p = argparse.ArgumentParser()
    p.add_argument("--interval", type=float, default=3.0)
    p.add_argument("--max-ticks", type=int, default=None)
    p.add_argument("--recipients", default=None)
    args = p.parse_args()
    recipients = [r.strip() for r in args.recipients.split(",")] if args.recipients else None
    print(f"[start_consumer_real] dispatcher = {_claude_dispatch_adapter.__name__}", flush=True)
    print(f"[start_consumer_real] interval={args.interval}s max_ticks={args.max_ticks}", flush=True)
    v2_consumer.watch(recipients=recipients, interval_s=args.interval, max_ticks=args.max_ticks)
