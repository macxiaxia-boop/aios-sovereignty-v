"""test_strategy_hook_integration.py — Tests the integration of strategy gate
inside `goal_guard_hook.guard_dispatch()`.

Verifies that:
  - guard_dispatch still PASSes terminal envelopes (backwards compat).
  - guard_dispatch now BLOCKS envelopes that reference retired ids.
  - guard_dispatch now BLOCKS envelopes that reference industry presets.
  - guard_dispatch now BLOCKS envelopes that reference deprecated assets.
  - guard_dispatch FAIL-CLOSES when the policy file is missing.
  - v2_consumer.py is NOT modified (v2_consumer diff = 0 lines).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT.parent / "policy"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from src.goal_guard_hook import guard_dispatch, clear_strategy_gate_cache  # noqa: E402


def _env(sid: str, payload: dict, msg_type: str = "task") -> dict:
    return {
        "id": sid,
        "sender": "codex",
        "recipient": "claudecode",
        "message_type": msg_type,
        "payload": payload,
        "schema_version": "1.0",
    }


@pytest.fixture(autouse=True)
def _reset_cache():
    clear_strategy_gate_cache()
    yield
    clear_strategy_gate_cache()


def test_hook_passes_terminal_envelopes():
    """Backwards compat: terminal envelopes must never be blocked."""
    for t in ("result", "ack", "status", "heartbeat", "error"):
        env = _env(f"term-{t}", {"note": f"terminal {t}"}, msg_type=t)
        allowed, risk = guard_dispatch(env)
        assert allowed
        assert risk is None


def test_hook_blocks_retired_id_envelope():
    env = _env(
        "retired-001",
        {
            "title": "Plan for R-001 reactivation",
            "text": "Please re-activate R-001 in the planning loop.",
        },
    )
    allowed, risk = guard_dispatch(env)
    assert not allowed
    assert risk is not None
    assert risk["envelope_type"] == "strategy_gate_risk"
    assert any(e["event_type"] == "RETIRED_REQUIREMENT_REACTIVATED"
               for e in risk["events"])


def test_hook_blocks_industry_preset_envelope():
    env = _env(
        "industry-001",
        {"title": "vertical preset",
         "text": "load the industry-zhuangxiu preset now"},
    )
    allowed, risk = guard_dispatch(env)
    assert not allowed
    assert any(e["event_type"] == "STRATEGY_DRIFT_DETECTED"
               for e in risk["events"])


def test_hook_blocks_deprecated_asset_envelope():
    env = _env(
        "asset-001",
        {"title": "Use old gateway",
         "text": "Use D:\\CloudTech-Portable\\gateway_v22.py as the entry."},
    )
    allowed, risk = guard_dispatch(env)
    assert not allowed
    assert any(e["event_type"] == "DEPRECATED_ASSET_REFERENCED"
               for e in risk["events"])


def test_hook_allows_valid_horizontal_marketing_envelope():
    env = _env(
        "valid-001",
        {
            "title": "Plan a SaaS retention campaign",
            "text": "Use general marketing automation. No verticals.",
        },
    )
    allowed, risk = guard_dispatch(env)
    assert allowed
    assert risk is None


def test_hook_fails_closed_when_policy_missing(tmp_path, monkeypatch):
    """When the policy file is missing, the hook must fail closed for any
    non-terminal envelope and return a policy_load_failed risk envelope."""
    fake_dir = tmp_path / "empty-policy"
    fake_dir.mkdir()
    monkeypatch.setenv("AIOS_STRATEGY_POLICY_DIR", str(fake_dir))
    clear_strategy_gate_cache()

    env = _env(
        "no-policy-001",
        {"title": "Some task", "text": "hello"},
    )
    allowed, risk = guard_dispatch(env)
    assert not allowed
    assert risk["reason"] == "policy_load_failed"
    assert any(e["event_type"] == "POLICY_GATE_REJECTED" for e in risk["events"])


def test_v2_consumer_diff_is_zero_lines():
    """The v2_consumer.py must not have been modified by this Phase-2 work.
    This is the red-line enforcement. We check via subprocess running
    `git diff --stat` and assert the diff for v2_consumer.py is empty."""
    aios_root = ROOT.parent.parent  # _agent-hub/v2/tests -> _agent-hub/v2 -> _agent-hub -> AIOS
    # Run git diff against HEAD; if no diff exists, output is empty.
    out = subprocess.run(
        ["git", "diff", "--stat", "HEAD", "--",
         str(aios_root / "_agent-hub" / "v2" / "src" / "v2_consumer.py")],
        cwd=str(aios_root),
        capture_output=True,
        text=True,
    )
    assert out.returncode == 0, out.stderr
    assert out.stdout.strip() == "", (
        f"v2_consumer.py must not change in Phase-2; got:\n{out.stdout}\n"
        f"stderr:\n{out.stderr}"
    )


def test_risk_envelope_is_persisted_to_messages_risk(tmp_path, monkeypatch):
    """When the hook blocks, write_risk_envelope() must persist the risk."""
    from src.goal_guard_hook import write_risk_envelope
    monkeypatch.setenv("AIOS_V2_ROOT", str(tmp_path))
    env = _env(
        "persist-001",
        {"title": "Re-activate R-001", "text": "do R-001"},
    )
    allowed, risk = guard_dispatch(env)
    assert not allowed
    p = write_risk_envelope(tmp_path, risk)
    assert p is not None
    assert p.exists()
    saved = json.loads(p.read_text(encoding="utf-8"))
    assert saved["envelope_type"] == "strategy_gate_risk"