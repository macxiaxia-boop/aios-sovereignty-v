#!/usr/bin/env python3
# v2/tests/test_p8_t08.py — P8 T08: Hermes invalid subcommand routed to doctor
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.hermes_adapter import _hermes_dispatch_adapter


def test_t08_hermes_invalid_subcommand_falls_back_to_doctor():
    """If payload asks for an unsafe/unknown subcommand, adapter falls back to doctor."""
    env = {
        "id": "t08-unknown-sub",
        "sender": "codex",
        "recipient": "hermes",
        "message_type": "task",
        # 'rm-rf' is clearly not a real hermes subcommand and not in SAFE_HERMES_SUBCMDS
        "payload": {"args": ["rm-rf", "/tmp"]},
    }
    out = _hermes_dispatch_adapter(env, recipient="hermes")
    # Either hermes doctor succeeded (exit 0) or failed gracefully — but adapter must NOT crash.
    assert "ok" in out
    assert out["transport"] == "hermes_subprocess", f"unexpected transport: {out.get('transport')}"
    # Because we routed to doctor, subcommand MUST be 'doctor'
    assert out["subcommand"] == "doctor", f"expected fallback to doctor, got {out['subcommand']}"
    # Args should preserve the rejected subcommand so it's visible in evidence
    assert "rm-rf" in out["args"], f"args should preserve rejected subcommand: {out['args']}"
    result = out
    assert result

if __name__ == "__main__":
    test_t08_hermes_invalid_subcommand_falls_back_to_doctor()
    print("PASS: test_t08_hermes_invalid_subcommand_falls_back_to_doctor")
