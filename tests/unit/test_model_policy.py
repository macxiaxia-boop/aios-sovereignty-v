"""test_model_policy.py — Unit tests for AIOS-SOVEREIGNTY-V ModelPolicy package."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives import serialization

from aios_kernel.governance.model_policy.snapshot import (
    PolicySnapshot,
    load_policy,
    sign_yaml,
    verify_signature,
)
from aios_kernel.governance.model_policy.adapter_base import (
    DriftReport,
    ModelPolicyAdapter,
)
from aios_kernel.governance.model_policy.codex_adapter import CodexAdapter
from aios_kernel.governance.model_policy.claude_code_adapter import ClaudeCodeAdapter
from aios_kernel.governance.model_policy.openclaw_adapter import OpenClawAdapter
from aios_kernel.governance.model_policy.hermes_adapter import HermesAdapter
from aios_kernel.governance.model_policy.reconciler import reconcile


@pytest.fixture
def sample_policy_yaml(tmp_path):
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
    pub_path.write_bytes(pub_bytes)
    priv_path.write_bytes(priv_bytes)

    yaml_path.write_text(
        """policy_id: test-001
schema_version: "1.0.0"
created_at: "2026-10-09T00:00:00+08:00"
created_by: test
authorizer: test
status: DRAFT
allowlist:
  providers:
    - id: TestProvider
      models:
        - id: MiniMax-M3
        - id: M-B
  denylist:
    - { id: "denied-X" }
  optional:
    - { id: "opt-Y" }
enforcement:
  cc_switch:
    common_config_claude:
      ANTHROPIC_DEFAULT_SONNET_MODEL: "MiniMax-M3"
  openclaw: {}
  hermes:
    cli_config_provider_first: ["minimax"]
    cli_config_provider_denylist: ["openrouter"]
""",
        encoding="utf-8",
    )
    sign_yaml(yaml_path, priv_path)
    return yaml_path, pub_path


@pytest.fixture
def sample_policy(sample_policy_yaml):
    yaml_path, pub_path = sample_policy_yaml
    return load_policy(yaml_path, pub_path)


# ============================================================
# 1. snapshot
# ============================================================

def test_load_policy_with_valid_signature(sample_policy):
    p = sample_policy
    assert p.policy_id == "test-001"
    assert "MiniMax-M3" in p.allowlist
    assert "M-B" in p.allowlist
    assert "denied-X" in p.denylist
    assert "opt-Y" in p.optional
    assert p.sig_ed25519


def test_load_policy_unsigned_raises(tmp_path):
    yaml_path = tmp_path / "unsigned.yaml"
    yaml_path.write_text(
        """policy_id: unsigned-001
schema_version: "1.0.0"
created_at: "2026-10-09T00:00:00+08:00"
allowlist:
  providers: []
  denylist: []
  optional: []
""",
        encoding="utf-8",
    )
    fake_pub = tmp_path / "fake.pub"
    fake_pub.write_bytes(b"ssh-ed25519 AAAA test@local\n")
    with pytest.raises(ValueError, match="Signature verification failed"):
        load_policy(yaml_path, fake_pub)


def test_verify_signature_roundtrip(sample_policy_yaml):
    yaml_path, pub_path = sample_policy_yaml
    assert verify_signature(yaml_path, pub_path) is True


def test_verify_signature_tamper_fails(sample_policy_yaml):
    """Modify the parsed dict (which changes canonical yaml) and verify fails."""
    import yaml
    yaml_path, pub_path = sample_policy_yaml
    # Mutate a value, not append comment (comment doesn't change canonical YAML)
    raw = yaml_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(raw)
    parsed["policy_id"] = "TAMPERED-002"
    new_raw = yaml.safe_dump(parsed, sort_keys=True, default_flow_style=False)
    yaml_path.write_text(new_raw, encoding="utf-8")
    assert verify_signature(yaml_path, pub_path) is False


# ============================================================
# 2. adapter_base
# ============================================================

def test_drift_report_severity_escalation():
    r_ok = DriftReport(adapter_name="x", severity="ok")
    r_warn = DriftReport(adapter_name="x", severity="warn")
    r_fail = DriftReport(adapter_name="x", severity="fail_closed")
    assert r_ok.severity == "ok"
    assert r_warn.severity == "warn"
    assert r_fail.severity == "fail_closed"


# ============================================================
# 3. codex_adapter
# ============================================================

def test_codex_adapter_profile_drift_warns(sample_policy, tmp_path):
    config_toml = tmp_path / "config.toml"
    config_toml.write_text(
        """[profiles.ollama]
model = "denied-X"
[profiles.safe]
model = "MiniMax-M3"
""",
        encoding="utf-8",
    )
    cc_db = tmp_path / "cc-switch.db"
    db = sqlite3.connect(str(cc_db))
    db.execute("CREATE TABLE settings (key TEXT, value TEXT)")
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("common_config_codex", 'model_reasoning_effort = "high"')
    )
    db.commit()
    db.close()

    adapter = CodexAdapter(
        config_toml_path=config_toml,
        cc_switch_db_path=cc_db,
        auth_json_path=tmp_path / "auth.json",
    )
    drift = adapter.verify(sample_policy)
    assert drift.severity == "warn"
    assert drift.recommended_action == "warn"
    assert any("ollama" in p for p in drift.affected_paths)


# ============================================================
# 4. claude_code_adapter
# ============================================================

def test_claude_code_adapter_settings_frozen_warn(sample_policy, tmp_path):
    settings_json = tmp_path / "settings.json"
    settings_json.write_text(json.dumps({
        "_meta": {"frozen_at": "2026-09-01T16:05:00"},
        "env": {"ANTHROPIC_MODEL": "denied-X"}
    }))
    cc_db = tmp_path / "cc-switch.db"
    db = sqlite3.connect(str(cc_db))
    db.execute("CREATE TABLE settings (key TEXT, value TEXT)")
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("common_config_claude", '{}')
    )
    db.commit()
    db.close()

    adapter = ClaudeCodeAdapter(
        settings_json_path=settings_json,
        cc_switch_db_path=cc_db,
    )
    drift = adapter.verify(sample_policy)
    assert drift.severity == "warn"
    assert drift.recommended_action == "warn"


def test_claude_code_adapter_common_config_reverts(sample_policy, tmp_path):
    settings_json = tmp_path / "settings.json"
    settings_json.write_text(json.dumps({
        "_meta": {"frozen_at": "2026-09-01T16:05:00"},
        "env": {"ANTHROPIC_MODEL": "MiniMax-M3"}
    }))
    cc_db = tmp_path / "cc-switch.db"
    db = sqlite3.connect(str(cc_db))
    db.execute("CREATE TABLE settings (key TEXT, value TEXT)")
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("common_config_claude", json.dumps({"env": {"ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK": "denied-X"}}))
    )
    db.commit()
    db.close()

    adapter = ClaudeCodeAdapter(
        settings_json_path=settings_json,
        cc_switch_db_path=cc_db,
    )
    drift = adapter.verify(sample_policy)
    assert drift.severity == "fail_closed"
    assert drift.recommended_action == "revert"

    new_drift = adapter.apply(sample_policy, dry_run=False)
    db = sqlite3.connect(str(cc_db))
    val = db.execute(
        "SELECT value FROM settings WHERE key='common_config_claude'"
    ).fetchone()[0]
    db.close()
    cfg = json.loads(val)
    assert cfg["env"]["ANTHROPIC_DEFAULT_SONNET_MODEL"] == "MiniMax-M3"


# ============================================================
# 5. openclaw_adapter
# ============================================================

def test_openclaw_adapter_missing_policy_reverts(sample_policy, tmp_path):
    db_path = tmp_path / "openclaw.sqlite"
    db = sqlite3.connect(str(db_path))
    db.close()
    yaml_mirror = tmp_path / "policy.yaml"
    env_path = tmp_path / ".env"
    env_path.write_text("MINIMAX_API_KEY=stub\n", encoding="utf-8")

    adapter = OpenClawAdapter(
        openclaw_db_path=db_path,
        policy_yaml_path=yaml_mirror,
        env_path=env_path,
    )
    drift = adapter.verify(sample_policy)
    assert drift.severity == "fail_closed"
    assert drift.recommended_action == "revert"

    adapter.apply(sample_policy, dry_run=False)
    db = sqlite3.connect(str(db_path))
    cur = db.cursor()
    cur.execute("SELECT model_id, category FROM policy_allowlist WHERE policy_id = ?", ("test-001",))
    rows = cur.fetchall()
    db.close()
    assert ("MiniMax-M3", "allowlist") in rows
    assert yaml_mirror.exists()


def test_openclaw_adapter_denylist_drift(sample_policy, tmp_path):
    db_path = tmp_path / "openclaw.sqlite"
    db = sqlite3.connect(str(db_path))
    cur = db.cursor()
    cur.execute("""
        CREATE TABLE policy_allowlist (
            policy_id TEXT, model_id TEXT, category TEXT, created_at INTEGER,
            UNIQUE(policy_id, model_id)
        )
    """)
    cur.execute("INSERT INTO policy_allowlist VALUES ('old', 'denied-X', 'allowlist', 0)")
    db.commit()
    db.close()
    adapter = OpenClawAdapter(
        openclaw_db_path=db_path,
        policy_yaml_path=tmp_path / "policy.yaml",
        env_path=tmp_path / ".env",
    )
    drift = adapter.verify(sample_policy)
    assert drift.severity == "fail_closed"
    assert any("denylisted" in p for p in drift.affected_paths)


# ============================================================
# 6. hermes_adapter
# ============================================================

def test_hermes_adapter_provider_drift_warns(sample_policy, tmp_path):
    cli_config = tmp_path / "cli-config.yaml"
    cli_config.write_text(
        """model:
  provider: "openrouter"
  default: "openrouter/auto"
""",
        encoding="utf-8",
    )
    adapter = HermesAdapter(cli_config_path=cli_config)
    drift = adapter.verify(sample_policy)
    assert drift.severity == "warn"
    assert drift.recommended_action == "warn"


def test_hermes_adapter_minimax_provider_ok(sample_policy, tmp_path):
    cli_config = tmp_path / "cli-config.yaml"
    cli_config.write_text(
        """model:
  provider: "minimax"
  default: "MiniMax-M3"
""",
        encoding="utf-8",
    )
    adapter = HermesAdapter(cli_config_path=cli_config)
    drift = adapter.verify(sample_policy)
    assert drift.severity == "ok"


# ============================================================
# 7. reconciler aggregate
# ============================================================

def test_reconciler_aggregate_severity_fails_closed_when_one_adapter_fails(sample_policy):
    class FailingAdapter(ModelPolicyAdapter):
        name = "failing"
        def current_state(self): return {}
        def verify(self, policy):
            return DriftReport(adapter_name="failing", severity="fail_closed",
                               recommended_action="revert")
        def apply(self, policy, dry_run=False):
            return self.verify(policy)
    class OkAdapter(ModelPolicyAdapter):
        name = "ok"
        def current_state(self): return {}
        def verify(self, policy):
            return DriftReport(adapter_name="ok", severity="ok")
        def apply(self, policy, dry_run=False):
            return self.verify(policy)

    reports = reconcile(sample_policy, adapters=[OkAdapter(), FailingAdapter(), OkAdapter()])
    severities = [r.severity for r in reports]
    assert "fail_closed" in severities
    assert severities.count("ok") == 2


def test_reconciler_aggregate_warn_only(sample_policy):
    class WarnAdapter(ModelPolicyAdapter):
        name = "warn"
        def current_state(self): return {}
        def verify(self, policy):
            return DriftReport(adapter_name="warn", severity="warn",
                               recommended_action="warn")
        def apply(self, policy, dry_run=False):
            return self.verify(policy)
    class OkAdapter(ModelPolicyAdapter):
        name = "ok"
        def current_state(self): return {}
        def verify(self, policy):
            return DriftReport(adapter_name="ok", severity="ok")
        def apply(self, policy, dry_run=False):
            return self.verify(policy)
    reports = reconcile(sample_policy, adapters=[WarnAdapter(), OkAdapter()])
    severities = [r.severity for r in reports]
    assert "fail_closed" not in severities
    assert "warn" in severities
