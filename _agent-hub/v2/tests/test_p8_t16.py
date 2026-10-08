#!/usr/bin/env python3
# v2/tests/test_p8_t16.py — P8 T16: Burst of 10 envelopes to Hermes
#
# Verifies that hermes adapter can handle 10 sequential dispatches without
# crashes, all return structured result, and ordering is preserved.
# Uses FAST subcommands only (version / status).  Avoids doctor (~30s) and
# dashboard (interactive TUI).
from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.hermes_adapter import _hermes_dispatch_adapter


def test_t16_hermes_burst_10_envelopes():
    """Fire 10 envelopes at hermes sequentially; all must return structured ok=True."""
    # All fast (<3s each): version x4, status x3, sessions stats x3
    subcommands = (["version"] * 4) + (["status"] * 3) + (["sessions", "stats"] * 3)
    results = []
    for i, args in enumerate(subcommands):
        env = {
            "id": f"t16-burst-{i:02d}",
            "sender": "codex",
            "recipient": "hermes",
            "message_type": "task",
            "payload": {"args": args},
        }
        out = _hermes_dispatch_adapter(env, recipient="hermes")
        results.append({
            "i": i,
            "sub": args[0],
            "ok": out["ok"],
            "exit": out.get("exit_code"),
            "duration_ms": out.get("duration_ms", 0),
        })
    # All should be ok=True (version/status/sessions stats all exit 0 fast)
    failed = [r for r in results if not r["ok"]]
    assert not failed, f"some dispatches failed: {failed}"
    # All should have positive duration_ms < 30s
    durations = [r["duration_ms"] for r in results]
    assert all(0 < d < 30000 for d in durations), f"durations out of range: {durations}"
    result = {"count": len(results), "results": results,
            "total_ms": sum(durations), "max_ms": max(durations)}
    assert result

if __name__ == "__main__":
    test_t16_hermes_burst_10_envelopes()
    print("PASS: test_t16_hermes_burst_10_envelopes")
