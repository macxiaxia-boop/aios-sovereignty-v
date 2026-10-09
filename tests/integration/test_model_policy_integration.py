"""test_model_policy_integration.py — Integration tests (T8 §5 7-10).

Validates SQLite + cc-switch + openclaw integration:
- 7 cc-switch common_config_claude written
- 8 cc-switch common_config_claude drift revert
- 9 openclaw policy_allowlist table rewrite
- 10 openclaw env credential validate
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from aios_kernel.governance.model_policy.snapshot import PolicySnapshot, load_policy, sign_yaml
from aios_kernel.governance.model_policy.claude_code_adapter import ClaudeCodeAdapter
from aios_kernel.governance.model_policy.openclaw_adapter import OpenClawAdapter
from aios_kernel.governance.model_policy.codex_adapter import CodexAdapter


@pytest.fixture
def sample_policy_yaml(tmp_path):
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
    from cryptography.hazmat.primitives import serialization
    priv = Ed25519PrivateKey.generate()
    priv_bytes = priv.private_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PrivateFormat.Raw,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pub = priv.public_key()
    pub_bytes = pub.public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    )
    yaml_path = tmp_path / "policy.yaml"
    pub_path = tmp_path / "policy.pub"
    priv_path = tmp_path / "policy.key"
    pub_path.write_bytes(pub_bytes); priv_path.write_bytes(priv_bytes)
    yaml_path.write_text(
        """policy_id: intg-test-001
schema_version: "1.0.0"
created_at: "2026-10-09T00:00:00+08:00"
created_by: intg-test
authorizer: test
status: DRAFT
allowlist:
  providers:
    - id: TestProvider
      models: [{id: M-A}, {id: M-B}]
  denylist: [{id: "denied-X"}]
  optional: [{id: "opt-Y"}]
enforcement:
  cc_switch:
    common_config_claude:
      ANTHROPIC_DEFAULT_SONNET_MODEL: "M-A"
      ANTHROPIC_DEFAULT_OPUS_MODEL_FALLBACK: "M-A"
      ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK: "M-A"
  openclaw: {}
  hermes:
    cli_config_provider_first: ["minimax"]
    cli_config_provider_denylist: ["openrouter"]
""",
        encoding="utf-8",
    )
    sign_yaml(yaml_path, priv_path)
    return yaml_path, pub_path


# ============================================================
# 7 · cc-switch common_config_claude written (revert from drift)
# ============================================================

def test_cc_switch_common_config_claude_written(sample_policy_yaml, tmp_path):
    yaml_path, pub_path = sample_policy_yaml
    policy = load_policy(yaml_path, pub_path)

    cc_db = tmp_path / "cc.db"
    db = sqlite3.connect(str(cc_db))
    db.execute("CREATE TABLE settings (key TEXT, value TEXT)")
    # Inject denylisted model — triggers fail_closed → revert
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("common_config_claude", json.dumps({"env": {"ANTHROPIC_DEFAULT_SONNET_MODEL": "denied-X"}})),
    )
    db.commit(); db.close()

    adapter = ClaudeCodeAdapter(
        settings_json_path=tmp_path / "settings.json",
        cc_switch_db_path=cc_db,
    )
    drift = adapter.apply(policy, dry_run=False)
    assert drift.severity == "fail_closed"

    db = sqlite3.connect(str(cc_db))
    val = db.execute("SELECT value FROM settings WHERE key='common_config_claude'").fetchone()[0]
    db.close()
    cfg = json.loads(val)
    assert cfg["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "M-A"
    assert cfg["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK"] == "M-A"
    assert cfg["env"]["ANTHROPIC_DEFAULT_OPUS_MODEL_FALLBACK"] == "M-A"


# ============================================================
# 8 · cc-switch common_config_claude drift revert
# ============================================================

def test_cc_switch_drift_revert(sample_policy_yaml, tmp_path):
    yaml_path, pub_path = sample_policy_yaml
    policy = load_policy(yaml_path, pub_path)

    cc_db = tmp_path / "cc.db"
    db = sqlite3.connect(str(cc_db))
    db.execute("CREATE TABLE settings (key TEXT, value TEXT)")
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("common_config_claude", json.dumps({"env": {"ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK": "denied-X"}})),
    )
    db.commit(); db.close()

    adapter = ClaudeCodeAdapter(
        settings_json_path=tmp_path / "settings.json",
        cc_switch_db_path=cc_db,
    )

    drift = adapter.verify(policy)
    assert drift.severity == "fail_closed"
    assert drift.recommended_action == "revert"

    adapter.apply(policy, dry_run=False)

    db = sqlite3.connect(str(cc_db))
    val = db.execute("SELECT value FROM settings WHERE key='common_config_claude'").fetchone()[0]
    db.close()
    cfg = json.loads(val)
    assert cfg["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK"] == "M-A"


# ============================================================
# 9 · openclaw policy_allowlist rewrite on drift
# ============================================================

def test_openclaw_policy_allowlist_rewrite(sample_policy_yaml, tmp_path):
    yaml_path, pub_path = sample_policy_yaml
    policy = load_policy(yaml_path, pub_path)

    db_path = tmp_path / "openclaw.sqlite"
    db = sqlite3.connect(str(db_path)); db.close()
    yaml_mirror = tmp_path / "policy.yaml"
    env_path = tmp_path / ".env"
    env_path.write_text("MINIMAX_API_KEY=stub\n", encoding="utf-8")

    adapter = OpenClawAdapter(
        openclaw_db_path=db_path,
        policy_yaml_path=yaml_mirror,
        env_path=env_path,
    )

    drift = adapter.apply(policy, dry_run=False)

    db = sqlite3.connect(str(db_path))
    cur = db.cursor()
    cur.execute("SELECT model_id, category FROM policy_allowlist WHERE policy_id = ?", ("intg-test-001",))
    rows = cur.fetchall()
    db.close()

    assert ("M-A", "allowlist") in rows
    assert ("M-B", "allowlist") in rows
    assert ("opt-Y", "optional") in rows
    assert yaml_mirror.exists()


# ============================================================
# 10 · openclaw env credential validate (via enforcement.openclaw.auth.env_keys)
# ============================================================

def test_openclaw_env_credential_validate(sample_policy_yaml, tmp_path):
    yaml_path, pub_path = sample_policy_yaml
    policy = load_policy(yaml_path, pub_path)
    policy.enforcement.setdefault("openclaw", {})["auth"] = {
        "env_keys": ["MINIMAX_API_KEY", "MISSING_KEY"]
    }

    env_path = tmp_path / ".env"
    env_path.write_text("MINIMAX_API_KEY=stub\nOTHER_KEY=val\n", encoding="utf-8")

    db_path = tmp_path / "openclaw.sqlite"
    sqlite3.connect(str(db_path)).close()

    adapter = OpenClawAdapter(
        openclaw_db_path=db_path,
        policy_yaml_path=tmp_path / "policy.yaml",
        env_path=env_path,
    )
    drift = adapter.verify(policy)
    paths_str = str(drift.affected_paths)
    assert "MISSING_KEY" in paths_str, f"env.missing for MISSING_KEY not in: {paths_str}"
    assert "MINIMAX_API_KEY" not in paths_str, f"MINIMAX_API_KEY is in .env, should NOT be flagged"
