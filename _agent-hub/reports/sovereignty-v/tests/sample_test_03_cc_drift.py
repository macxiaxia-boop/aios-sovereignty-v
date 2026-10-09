"""Sample test draft · 单元 03 · CC Adapter drift detection

Validates: ClaudeCodeAdapter.verify() returns fail_closed when settings.json or
common_config_claude contains a model not in allowlist (denylist hit).
"""
import sqlite3, json
from pathlib import Path
import pytest
from aios_kernel.governance.model_policy.snapshot import PolicySnapshot
from aios_kernel.governance.model_policy.claude_code_adapter import ClaudeCodeAdapter


@pytest.fixture
def policy():
    return PolicySnapshot(
        policy_id="mp-test-001",
        sha256="0" * 64,
        sig_ed25519="0" * 128,
        allowlist=["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
        denylist=["deepseek-v4-pro", "deepseek-v4-flash"],
        optional=[],
    )


def test_settings_json_drift_fail_closed(tmp_path, policy):
    settings_json = tmp_path / "settings.json"
    settings_json.write_text(json.dumps({
        "_meta": {"frozen": True, "modify_protocol": "any change requires ask_user"},
        "env": {"ANTHROPIC_MODEL": "deepseek-v4-pro"}
    }))
    cc_db = tmp_path / "cc-switch.db"
    db = sqlite3.connect(cc_db)
    db.execute("CREATE TABLE settings (key TEXT, value TEXT)")
    db.execute("INSERT INTO settings VALUES ('common_config_claude', '{}')")
    db.commit(); db.close()

    adapter = ClaudeCodeAdapter(settings_json_path=settings_json, cc_switch_db_path=cc_db)
    drift = adapter.verify(policy)

    assert drift.severity == "fail_closed"
    assert drift.recommended_action == "warn"  # 因为 settings.json frozen, 不强覆盖
    assert "deepseek-v4-pro" in str(drift.affected_paths)


def test_common_config_drift_fail_closed_revert(tmp_path, policy):
    """common_config_claude 可写, drift 必须 revert"""
    settings_json = tmp_path / "settings.json"
    settings_json.write_text(json.dumps({"env": {"ANTHROPIC_MODEL": "MiniMax-M3"}}))
    cc_db = tmp_path / "cc-switch.db"
    db = sqlite3.connect(cc_db)
    db.execute("CREATE TABLE settings (key TEXT, value TEXT)")
    db.execute(
        "INSERT INTO settings VALUES ('common_config_claude', ?)",
        json.dumps({"ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK": "deepseek-v4-flash"})
    )
    db.commit(); db.close()

    adapter = ClaudeCodeAdapter(settings_json_path=settings_json, cc_switch_db_path=cc_db)
    drift = adapter.verify(policy)

    assert drift.severity == "fail_closed"
    assert drift.recommended_action == "revert"
    # Apply 应把 common_config_claude 写回 allowlist
    new_drift = adapter.apply(policy, dry_run=False)
    db = sqlite3.connect(cc_db)
    val = db.execute("SELECT value FROM settings WHERE key='common_config_claude'").fetchone()[0]
    db.close()
    cfg = json.loads(val)
    assert cfg["ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK"] == "MiniMax-M2.7"
