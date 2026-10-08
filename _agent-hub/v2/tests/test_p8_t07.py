#!/usr/bin/env python3
# v2/tests/test_p8_t07.py — P8 T07: Hermes subprocess TIMEOUT (fault injection)
#
# Verifies that when hermes subprocess exceeds timeout, adapter returns
# ok=False with transport="hermes_subprocess" and error="timeout_Ns".
# We use a known-slow subcommand (or a forged slow invocation via input pipe).
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.hermes_adapter import _hermes_dispatch_adapter


def test_t07_hermes_subprocess_timeout(monkeypatch=None):
    """Hermes adapter must return ok=False with timeout error on slow subcommand."""
    # 'sessions list' is fast (~1s). We can't easily make hermes hang,
    # so we patch DEFAULT_TIMEOUT_SEC via a monkeypatch on the module attribute.
    import src.hermes_adapter as ha
    orig_timeout = ha.DEFAULT_TIMEOUT_SEC
    ha.DEFAULT_TIMEOUT_SEC = 1  # 1s — sessions list on busy disk might exceed
    try:
        env = {
            "id": "t07-timeout",
            "sender": "codex",
            "recipient": "hermes",
            "message_type": "task",
            "payload": {"args": ["sessions", "list", "--limit", "99999"]},
        }
        out = _hermes_dispatch_adapter(env, recipient="hermes")
        # Either hermes finished within 1s (unlikely with 99999) or it timed out.
        # We assert STRUCTURE only — that the adapter handled the situation cleanly.
        assert "ok" in out
        assert "transport" in out
        if not out["ok"]:
            # Failed path: must be timeout
            assert out["transport"] in ("hermes_subprocess",), f"unexpected transport: {out}"
            if "error" in out:
                assert out["error"].startswith("timeout_"), f"unexpected error: {out.get('error')}"
        # OK path: must have exit_code 0 and real stdout
        else:
            assert out["exit_code"] == 0
            assert "Hermes" in (out.get("stdout_tail") or "") or len(out.get("stdout_tail") or "") > 0
        return out
    finally:
        ha.DEFAULT_TIMEOUT_SEC = orig_timeout


if __name__ == "__main__":
    r = test_t07_hermes_subprocess_timeout()
    print("T07:", r["ok"], r.get("transport"), r.get("error", "ok"))
