#!/usr/bin/env python3
# v2/tests/test_p8_t14.py — P8 T14: Large output handling (hermes sessions list)
#
# Verifies that the adapter correctly truncates large stdout to stdout_tail
# (max 1500 chars) but reports full stdout_bytes for evidence.
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.hermes_adapter import _hermes_dispatch_adapter


def test_t14_hermes_large_output_truncation():
    """`hermes sessions list` returns a large table; adapter must truncate tail."""
    env = {
        "id": "t14-big",
        "sender": "codex",
        "recipient": "hermes",
        "message_type": "task",
        "payload": {"args": ["sessions", "list"]},
    }
    out = _hermes_dispatch_adapter(env, recipient="hermes")
    assert out["ok"] is True
    assert out["exit_code"] == 0
    # stdout_tail must be capped at 1500 chars
    assert len(out["stdout_tail"]) <= 1500, f"stdout_tail too long: {len(out['stdout_tail'])}"
    # stdout_bytes is the real (untruncated) size
    assert "stdout_bytes" in out
    # If hermes actually returned > 1500 bytes (it should, with 100+ sessions in DB),
    # then truncation logic was exercised.
    # We don't hard-assert >1500 because hermes DB could be smaller on test host.
    assert out["stdout_bytes"] >= len(out["stdout_tail"]), \
        f"stdout_bytes ({out['stdout_bytes']}) should be >= stdout_tail ({len(out['stdout_tail'])})"
    return out


if __name__ == "__main__":
    r = test_t14_hermes_large_output_truncation()
    print(f"T14: stdout_bytes={r['stdout_bytes']} tail_len={len(r['stdout_tail'])} exit={r['exit_code']}")
