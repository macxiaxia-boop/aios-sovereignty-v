"""test_strategy_policy.py — Tests for strategy_policy.py loader/validator.

Verifies that the policy:
  - parses successfully,
  - SHA-256 sidecar matches,
  - schema validation passes,
  - fails CLOSED on missing/malformed/hash-mismatched/policy-violating input,
  - exposes helpers `is_retired_id`, `is_industry_preset_blocked`,
    `is_prohibited_path`.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT.parent / "policy"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))  # _agent-hub

from policy.strategy_policy import (  # noqa: E402
    EXPECTED_POLICY_ID,
    EXPECTED_POLICY_VERSION,
    is_industry_preset_blocked,
    is_prohibited_path,
    is_retired_id,
    load_strategy_policy,
)


def test_real_policy_loads():
    """The SSOT policy under D:\\AIOS\\_agent-hub\\policy loads."""
    res = load_strategy_policy(POLICY_DIR)
    assert res.ok, f"unexpected failure: {res.reason} {res.errors}"
    assert res.policy is not None
    assert res.policy["policy_id"] == EXPECTED_POLICY_ID
    assert res.policy["policy_version"] == EXPECTED_POLICY_VERSION
    assert res.sha256 is not None
    # SHA-256 sidecar matches
    expected = hashlib.sha256((POLICY_DIR / "product_strategy.v1.json").read_bytes()).hexdigest().upper()
    assert res.sha256 == expected


def test_missing_policy_file_fails_closed(tmp_path):
    """A non-existent policy file must fail with reason=missing_policy_file."""
    res = load_strategy_policy(tmp_path)
    assert not res.ok
    assert res.reason == "missing_policy_file"
    assert res.policy is None


def test_malformed_json_fails_closed(tmp_path):
    """A JSON file with bad syntax must fail with reason=malformed_json."""
    (tmp_path / "product_strategy.v1.json").write_text("{not valid", encoding="utf-8")
    (tmp_path / "product_strategy.v1.sha256").write_text("X" * 64, encoding="utf-8")
    res = load_strategy_policy(tmp_path)
    assert not res.ok
    assert res.reason == "malformed_json"


def test_hash_mismatch_fails_closed(tmp_path):
    """A sidecar hash not matching the file must fail closed."""
    payload = {
        "policy_id": EXPECTED_POLICY_ID,
        "policy_version": EXPECTED_POLICY_VERSION,
        "title": "x", "product": "CloudTech",
        "positioning": "HORIZONTAL_MARKETING_SAAS",
        "business_scope": "GENERAL_MARKETING",
        "vertical_product_strategy": "DISABLED",
        "industry_presets": "DISABLED",
        "status": "ACTIVE", "owner": "USER",
        "change_authority": "EXPLICIT_USER_APPROVAL",
        "scope_note": "x",
        "deprecated_requirement_ids": ["R-001"],
        "prohibited_active_assets": [],
        "quarantine_paths": ["X:\\a"],
        "industry_presets_blocked": ["industry-cloudtech"],
        "retired_aliases": ["医美"],
        "retired_alias_kind": {"industry_vertical": ["医美"]},
        "historical_source_prohibited_keys": ["AIOS_SOURCE_OF_TRUTH_FINAL"],
        "gate_event_types": ["POLICY_GATE_REJECTED"],
        "scanner_classifications": ["ACTIVE_VIOLATION"],
    }
    p = tmp_path / "product_strategy.v1.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    (tmp_path / "product_strategy.v1.sha256").write_text("0" * 64, encoding="utf-8")  # WRONG
    res = load_strategy_policy(tmp_path)
    assert not res.ok
    assert res.reason == "hash_mismatch"


def test_missing_sidecar_fails_closed(tmp_path):
    """Missing sidecar → reason=missing_sha256_sidecar."""
    payload = {"policy_id": EXPECTED_POLICY_ID}
    (tmp_path / "product_strategy.v1.json").write_text(json.dumps(payload), encoding="utf-8")
    res = load_strategy_policy(tmp_path)
    assert not res.ok
    assert res.reason == "missing_sha256_sidecar"


def test_policy_identity_mismatch_fails_closed(tmp_path):
    """A policy with wrong owner must fail identity check (owner not in ALLOWED_VALUES)."""
    payload = _minimal_payload(tmp_path)
    payload["owner"] = "AUTO"  # not the required "USER" — bypasses schema by being a free string
    _write_valid(tmp_path, payload)
    res = load_strategy_policy(tmp_path)
    assert not res.ok
    assert res.reason == "policy_identity_mismatch"
    assert any("owner" in e for e in res.errors)


def test_schema_violation_wrong_status(tmp_path):
    """Status outside allowed enum → schema_violation."""
    payload = _minimal_payload(tmp_path)
    payload["status"] = "DELETED"
    _write_valid(tmp_path, payload)
    res = load_strategy_policy(tmp_path)
    assert not res.ok
    assert res.reason == "schema_violation"


def test_is_retired_id_helper():
    policy = {
        "deprecated_requirement_ids": ["R-001", "R-005", "R-020"],
    }
    assert is_retired_id(policy, "R-001")
    assert is_retired_id(policy, "R-005")
    assert not is_retired_id(policy, "R-021")
    assert not is_retired_id(policy, "X-001")
    assert not is_retired_id(None, "R-001")


def test_is_industry_preset_blocked_helper():
    policy = {
        "industry_presets_blocked": ["industry-zhuangxiu", "industry-jiaoyu"],
    }
    assert is_industry_preset_blocked(policy, "industry-zhuangxiu")
    assert is_industry_preset_blocked(policy, "industry-JIAOYU")
    assert not is_industry_preset_blocked(policy, "industry-fintech")
    assert not is_industry_preset_blocked(None, "industry-zhuangxiu")


def test_is_prohibited_path_helper():
    policy = {
        "historical_source_prohibited_keys": [
            "AIOS_SOURCE_OF_TRUTH_FINAL",
            "D:\\CloudTech-Portable",
        ]
    }
    assert is_prohibited_path(policy, r"D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\foo.md")
    assert is_prohibited_path(policy, r"D:/CloudTech-Portable/x.py")
    assert not is_prohibited_path(policy, r"D:\AIOS\kernel\src\foo.py")
    assert not is_prohibited_path(None, r"D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL")


# ---------------------------------------------------------------- Helpers
def _minimal_payload(tmp_path: Path) -> dict:
    return {
        "policy_id": EXPECTED_POLICY_ID,
        "policy_version": EXPECTED_POLICY_VERSION,
        "title": "x", "product": "CloudTech",
        "positioning": "HORIZONTAL_MARKETING_SAAS",
        "business_scope": "GENERAL_MARKETING",
        "vertical_product_strategy": "DISABLED",
        "industry_presets": "DISABLED",
        "status": "ACTIVE", "owner": "USER",
        "change_authority": "EXPLICIT_USER_APPROVAL",
        "scope_note": "x",
        "deprecated_requirement_ids": ["R-001"],
        "prohibited_active_assets": [],
        "quarantine_paths": ["X:\\a"],
        "industry_presets_blocked": ["industry-cloudtech"],
        "retired_aliases": ["医美"],
        "retired_alias_kind": {"industry_vertical": ["医美"]},
        "historical_source_prohibited_keys": ["AIOS_SOURCE_OF_TRUTH_FINAL"],
        "gate_event_types": ["POLICY_GATE_REJECTED"],
        "scanner_classifications": ["ACTIVE_VIOLATION"],
    }


def _write_valid(tmp_path: Path, payload: dict) -> None:
    p = tmp_path / "product_strategy.v1.json"
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    p.write_bytes(raw)
    h = hashlib.sha256(raw).hexdigest().upper()
    (tmp_path / "product_strategy.v1.sha256").write_text(h + "  product_strategy.v1.json", encoding="utf-8")
    (tmp_path / "product_strategy.v1.schema.json").write_text("{}", encoding="utf-8")