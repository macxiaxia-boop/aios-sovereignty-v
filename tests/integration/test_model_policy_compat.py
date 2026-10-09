"""test_model_policy_compat.py — Compat tests (T8 §5 15-18).

Validates CLI surface compatibility with:
- 15 codex CLI invocation
- 16 claude-code CLI invocation
- 17 openclaw gateway start
- 18 hermes mcp serve
"""
from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def real_policy_paths():
    """Use the real canonical policy + key (after user auth)."""
    return {
        "policy": Path(r"D:\AIOS\kernel\etc\sovereignty\model-policy.v1.yaml"),
        "pub": Path(r"D:\AIOS\kernel\etc\sovereignty\codex_supervisor.ed25519.pub"),
    }


# ============================================================
# 15 · Codex CLI: --model non-allowlist → error
# ============================================================

def test_compat_codex_cli_rejects_denied_model(real_policy_paths):
    """Validate that a 'codex --model=denied-X' invocation would fail.

    We don't actually invoke codex CLI (no test infra for that), but we
    validate the policy correctly rejects the model ID.
    """
    from aios_kernel.governance.model_policy.snapshot import load_policy
    from aios_kernel.governance.model_policy.codex_adapter import CodexAdapter

    if not real_policy_paths["policy"].exists():
        pytest.skip("Canonical policy not yet signed (R2026-10-09 Phase 2 deploy)")

    policy = load_policy(real_policy_paths["policy"], real_policy_paths["pub"])
    assert "deepseek-v4-pro" in policy.denylist

    adapter = CodexAdapter()
    drift = adapter.verify(policy)
    # Profile drift (ollama/qwen25) is in denylist → warn severity
    assert drift.severity in ("warn", "ok")


# ============================================================
# 16 · Claude Code CLI: --model non-allowlist → fallback to MiniMax
# ============================================================

def test_compat_claude_code_settings_frozen(real_policy_paths):
    """CC settings.json _meta.frozen is the canary: any direct env override is WARN.

    CC CLI bootstrap loads settings.json env block — Reconciler only verifies,
    never writes (frozen lock). User cannot accidentally fall back to deepseek
    from settings.json alone; cc-switch's common_config_claude is the lever.
    """
    from aios_kernel.governance.model_policy.snapshot import load_policy
    from aios_kernel.governance.model_policy.claude_code_adapter import ClaudeCodeAdapter

    if not real_policy_paths["policy"].exists():
        pytest.skip("Canonical policy not yet signed")

    policy = load_policy(real_policy_paths["policy"], real_policy_paths["pub"])
    adapter = ClaudeCodeAdapter()
    drift = adapter.verify(policy)

    # In current state, settings.json uses MiniMax-M3 → no drift on env block
    # common_config_claude is canonical → only warn fired on MINIMAX_CN_API_KEY env
    assert "MiniMax-M3" in policy.allowlist
    assert drift.severity in ("warn", "ok")


# ============================================================
# 17 · OpenClaw gateway: starts, policy_allowlist table readable
# ============================================================

def test_compat_openclaw_policy_allowlist_readable():
    """Validate that the policy_allowlist table written by Reconciler is queryable
    by OpenClaw gateway at boot time."""
    db_path = Path.home() / ".openclaw" / "state" / "openclaw.sqlite"
    if not db_path.exists():
        pytest.skip("OpenClaw sqlite not present (R2026-10-09 Phase 2 deploy)")

    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='policy_allowlist'"
    )
    if not cur.fetchone():
        conn.close()
        pytest.skip("policy_allowlist table not yet created")
    cur.execute("SELECT policy_id, model_id, category FROM policy_allowlist")
    rows = cur.fetchall()
    conn.close()

    # At least 1 row expected (allowlist or optional)
    assert len(rows) >= 1, "policy_allowlist must have rows for OpenClaw gateway to read"
    # All MiniMax family + optional entries present
    model_ids = {r[1] for r in rows}
    assert any("MiniMax" in mid for mid in model_ids), "policy_allowlist must include MiniMax family"


# ============================================================
# 18 · Hermes CLI: provider_minimax accepted, provider_openrouter warned
# ============================================================

def test_compat_hermes_provider_acceptance(real_policy_paths):
    """Hermes CLI provider selection: minimax = canonical, openrouter = denied."""
    from aios_kernel.governance.model_policy.snapshot import load_policy
    from aios_kernel.governance.model_policy.hermes_adapter import HermesAdapter

    if not real_policy_paths["policy"].exists():
        pytest.skip("Canonical policy not yet signed")

    policy = load_policy(real_policy_paths["policy"], real_policy_paths["pub"])
    provider_first = policy.enforcement.get("hermes", {}).get(
        "cli_config_provider_first", []
    )
    provider_deny = policy.enforcement.get("hermes", {}).get(
        "cli_config_provider_denylist", []
    )

    assert "minimax" in provider_first
    assert "minimax-cn" in provider_first
    # YAML stores denylist as one big string per line; normalize\n    all_denied = " ".join(provider_deny).replace(" - ", " ").split()\n    assert "openrouter" in all_denied

    # Adapter check
    adapter = HermesAdapter()
    drift = adapter.verify(policy)
    # In current state, ~/.hermes/cli-config.yaml may not exist
    # Adapter gracefully returns ok if no config
    assert drift.severity in ("ok", "warn")

