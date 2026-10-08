from __future__ import annotations

import threading
import time
from types import SimpleNamespace

from src import dispatch_runtime


def test_subprocess_retry_uses_exponential_backoff(monkeypatch):
    calls = []
    sleeps = []

    def fake_run(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(returncode=1 if len(calls) == 1 else 0, stdout=b"ok", stderr=b"")

    monkeypatch.setattr(dispatch_runtime.subprocess, "run", fake_run)
    proc, meta = dispatch_runtime.run_subprocess_with_retry(
        ["fake"], sleeper=sleeps.append
    )

    assert proc.returncode == 0
    assert len(calls) == 2
    assert meta["attempts"] == 2
    assert len(sleeps) == 1
    assert 1000 <= sleeps[0] * 1000 <= 1250


def test_subprocess_parallelism_is_capped_at_three(monkeypatch):
    active = 0
    peak = 0
    lock = threading.Lock()

    def fake_run(*args, **kwargs):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.02)
        with lock:
            active -= 1
        return SimpleNamespace(returncode=0, stdout=b"ok", stderr=b"")

    monkeypatch.setattr(dispatch_runtime.subprocess, "run", fake_run)
    threads = [
        threading.Thread(target=dispatch_runtime.run_subprocess_with_retry, args=(["fake"],))
        for _ in range(6)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert peak <= dispatch_runtime.MAX_PARALLEL_SUBPROCESS
