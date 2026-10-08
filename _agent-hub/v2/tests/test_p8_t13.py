#!/usr/bin/env python3
# v2/tests/test_p8_t13.py — P8 T13: Parallel dispatch via 3 different adapters
#
# Verifies that all 3 adapters can be invoked concurrently via threading.
# This catches any global state / lock contention issues.
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.hermes_adapter import _hermes_dispatch_adapter
from src.openclaw_adapter import _openclaw_dispatch_adapter
from src.workbuddy_adapter import _workbuddy_dispatch_adapter


def test_t13_parallel_dispatch_all_adapters():
    """Run all 3 adapters concurrently; collect results, assert each completed."""
    results = {}

    def run(name, fn, env):
        t0 = time.time()
        out = fn(env, recipient=env["recipient"])
        results[name] = {"out": out, "elapsed_ms": int((time.time() - t0) * 1000)}

    threads = [
        threading.Thread(target=run, args=(
            "hermes", _hermes_dispatch_adapter,
            {"id": "t13-hermes", "sender": "codex", "recipient": "hermes",
             "message_type": "task", "payload": {"args": ["version"]}}
        )),
        threading.Thread(target=run, args=(
            "openclaw", _openclaw_dispatch_adapter,
            {"id": "t13-openclaw", "sender": "codex", "recipient": "openclaw",
             "message_type": "task", "payload": {"action": "health"}}
        )),
        threading.Thread(target=run, args=(
            "workbuddy", _workbuddy_dispatch_adapter,
            {"id": "t13-workbuddy", "sender": "codex", "recipient": "workbuddy",
             "message_type": "task", "payload": {"action": "probe"}}
        )),
    ]
    for t in threads: t.start()
    for t in threads: t.join(timeout=60)

    assert "hermes" in results, "hermes thread did not complete"
    assert "openclaw" in results, "openclaw thread did not complete"
    assert "workbuddy" in results, "workbuddy thread did not complete"

    # Hermes: real subprocess call should succeed
    assert results["hermes"]["out"]["ok"] is True
    assert results["hermes"]["out"]["transport"] == "hermes_subprocess"
    # OpenClaw: real HTTP /healthz should be 200
    assert results["openclaw"]["out"]["ok"] is True
    assert results["openclaw"]["out"]["status"] == 200
    # WorkBuddy: probe returns ok=alive, currently False on this host
    assert results["workbuddy"]["out"]["transport"] == "workbuddy_probe"
    assert results["workbuddy"]["out"]["probe"]["alive"] is False
    return results


if __name__ == "__main__":
    r = test_t13_parallel_dispatch_all_adapters()
    for name, info in r.items():
        print(f"T13 {name}: ok={info['out']['ok']} elapsed={info['elapsed_ms']}ms")
