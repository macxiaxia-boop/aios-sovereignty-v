"""test_strategy_alias_correction.py — Tests for the alias-correction contract.

Contract: D:\\AIOS\\_agent-hub\\reports\\GLOBAL_STRATEGY_ALIAS_CORRECTION_20261009.md
Date:    2026-10-09

Independent verification found that the policy / gate / scanner blocks
synthetic IDs like `industry-zhuangxiu` but missed real Chinese aliases
that appear in the quarantined WorkBuddy memory file (医美, 装企,
行业垂直, 灵策智算, 灵策AI, CloudTech V22/V23 wording, old skill IDs
`sk-industry` / `sk-cross-matrix`, and vertical-workflow terms).

This test module exercises:
  1. The REAL quarantined memory file at
     D:\\AIOS\\_quarantine\\retired-assets\\20261008\\memory\\45e357fa-...md
     gets scanned by `scan_path` and emits at least one finding for
     each of: 医美, 装企, 行业垂直, 行业垂直文档, 灵策智算, 灵策AI,
     家居/医美. All such findings must classify as ARCHIVED_REFERENCE
     (the file lives in the quarantine root) — never ACTIVE_VIOLATION.

  2. A synthetic ACTIVE-loadable file containing 医美+装企 is classified
     ACTIVE_VIOLATION (the gate must catch active re-introduction).

  3. A task envelope whose title / description contains 医美 or 装企 is
     BLOCKED with STRATEGY_DRIFT_DETECTED (alias + structured-field
     presence = BLOCK signal).

  4. A bare text-only alias reference without structured-field presence
     OR combined signal is emitted WARN, not BLOCK (the "no bare
     keyword" red-line).

  5. Generic English words `industry`, `marketing`, `AI`, `SaaS` in a
     task envelope do NOT block the envelope (false-positive guard).
     Likewise bare 行业 without the specific 行业垂直/行业MVP token.

  6. The policy load now requires `retired_aliases` and `retired_alias_kind`
     fields; schema violations fail closed.

  7. cloudtech_v22_v23 / skill_id kinds emit DEPRECATED_ASSET_REFERENCED;
     other kinds emit STRATEGY_DRIFT_DETECTED.

  8. SHA-256 sidecar matches the current policy file (audit invariant).
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

from policy.contamination_scanner import (  # noqa: E402
    Classification,
    ContaminationScanner,
)
from policy.strategy_gate import StrategyGate, gate_from_policy_dir  # noqa: E402
from policy.strategy_policy import (  # noqa: E402
    EXPECTED_POLICY_ID,
    EXPECTED_POLICY_VERSION,
    is_retired_alias,
    load_strategy_policy,
    retired_alias_kind_of,
)


REAL_QUARANTINE_ROOT = r"D:\AIOS\_quarantine\retired-assets\20261008"
REAL_MEMORY_FILE = (
    rf"{REAL_QUARANTINE_ROOT}\memory\45e357fa-c2ec-4bd0-b734-9b016a2759d7_memory.md"
)


# ---------------------------------------------------------------- Fixtures
@pytest.fixture
def real_policy() -> dict:
    res = load_strategy_policy(POLICY_DIR)
    assert res.ok, f"real policy must load: {res.reason} {res.errors}"
    return res.policy


@pytest.fixture
def gate(real_policy) -> StrategyGate:
    return StrategyGate(
        real_policy,
        quarantine_root=REAL_QUARANTINE_ROOT,
    )


@pytest.fixture
def scanner(real_policy) -> ContaminationScanner:
    return ContaminationScanner(
        real_policy,
        quarantine_root=REAL_QUARANTINE_ROOT,
    )


def _build_envelope(payload: dict, *, msg_type: str = "task", sender: str = "codex") -> dict:
    return {
        "id": "env-alias-" + str(abs(hash(str(payload))) % 100000),
        "sender": sender,
        "recipient": "claudecode",
        "message_type": msg_type,
        "payload": payload,
        "schema_version": "1.0",
    }


def _write(path: str, content: str, encoding: str = "utf-8") -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(content.encode(encoding))


# ---------------------------------------------------------------- Section 1:
# Real quarantined memory file: alias content hits classify ARCHIVED_REFERENCE.

@pytest.mark.skipif(
    not os.path.isfile(REAL_MEMORY_FILE),
    reason=f"real quarantined memory file missing: {REAL_MEMORY_FILE}",
)
def test_real_quarantined_memory_emits_alias_content_findings(scanner):
    """The real quarantined memory file carries 医美 / 装企 / 行业垂直 /
    行业垂直文档 / 灵策智算 / 灵策AI / 家居/医美 in its body. The scanner
    must emit at least one content finding for each.
    """
    findings = scanner.scan_path(REAL_MEMORY_FILE)
    content_findings = [f for f in findings if f.evidence_kind == "content"]
    matched = {f.matched_token for f in content_findings}
    expected_aliases = {
        "医美", "装企", "行业垂直", "行业垂直文档",
        "灵策智算", "灵策AI", "家居/医美",
    }
    missing = expected_aliases - matched
    assert not missing, (
        f"expected real quarantined file to surface these aliases; missing: {missing}; "
        f"got: {matched}"
    )
    for f in content_findings:
        assert f.classification == Classification.ARCHIVED_REFERENCE, (
            f"quarantined content must classify ARCHIVED_REFERENCE; got {f.classification} "
            f"for token {f.matched_token}"
        )
        assert f.source_classification == "quarantine"


def test_real_quarantined_memory_no_active_violation(scanner):
    """Content in quarantine must NEVER classify as ACTIVE_VIOLATION."""
    if not os.path.isfile(REAL_MEMORY_FILE):
        pytest.skip(f"real quarantined memory file missing: {REAL_MEMORY_FILE}")
    findings = scanner.scan_path(REAL_MEMORY_FILE)
    assert not any(f.classification == Classification.ACTIVE_VIOLATION for f in findings), (
        "quarantined content must not be classified ACTIVE_VIOLATION: "
        f"{[f.to_dict() for f in findings if f.classification == Classification.ACTIVE_VIOLATION]}"
    )


# ---------------------------------------------------------------- Section 2:
# Synthetic ACTIVE-loadable file with 医美+装企 → ACTIVE_VIOLATION.

def test_active_loadable_file_with_yimei_zhuangqi_emits_active_violation(scanner):
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "active_loader.md")
        _write(fpath, "switch the AI 营销 context to 医美+装企 MVP pipeline\n")
        findings = scanner.scan_path(fpath)
        content_findings = [f for f in findings if f.evidence_kind == "content"]
        tokens = {f.matched_token for f in content_findings}
        assert "医美" in tokens
        assert "装企" in tokens
        for f in content_findings:
            if f.matched_token in {"医美", "装企"}:
                assert f.classification == Classification.ACTIVE_VIOLATION


def test_active_loadable_file_with_lingce_brand_emits_active_violation(scanner):
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "active_loader.md")
        _write(fpath, "re-route lead funnel through 灵策智算 marketplace\n")
        findings = scanner.scan_path(fpath)
        assert any(
            f.classification == Classification.ACTIVE_VIOLATION
            and f.matched_token == "灵策智算"
            and f.evidence_kind == "content"
            for f in findings
        )


def test_active_loadable_file_with_v22_emits_active_violation(scanner):
    with tempfile.TemporaryDirectory() as td:
        fpath = os.path.join(td, "active_loader.md")
        _write(fpath, "point at CloudTech V22 gateway as source of truth\n")
        findings = scanner.scan_path(fpath)
        assert any(
            f.classification == Classification.ACTIVE_VIOLATION
            and f.matched_token == "CloudTech V22"
            and f.evidence_kind == "content"
            for f in findings
        )


# ---------------------------------------------------------------- Section 3:
# Task envelope with 医美 / 装企 in structured fields → BLOCK.

def test_task_envelope_with_yimei_zhuangqi_in_title_blocks(gate: StrategyGate):
    env = _build_envelope({
        "title": "Phase 1 行业 SaaS：医美 + 装企 MVP",
        "text": "spin up the cross-vertical funnel.",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    events = [e.to_dict() for e in decision.events]
    matched = [e for e in events if e.get("matched_id") in {"医美", "装企"}]
    assert matched, f"expected alias events; got: {events}"
    # alias + structured-field presence → BLOCK
    assert all(e["severity"] == "BLOCK" for e in matched), (
        f"alias in title must BLOCK; got {[(e['severity'], e['matched_id']) for e in matched]}"
    )
    assert any(e["event_type"] == "STRATEGY_DRIFT_DETECTED" for e in matched)


def test_task_envelope_with_zhuangqi_in_description_blocks(gate: StrategyGate):
    env = _build_envelope({
        "title": "Marketing plan",
        "description": "target 装企 vertical with 装修矩阵 playbook",
        "text": "use the cross-matrix pipeline",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    events = [e.to_dict() for e in decision.events]
    matched = [e for e in events if e.get("matched_id") == "装企"]
    assert matched
    assert all(e["severity"] == "BLOCK" for e in matched)


def test_task_envelope_with_lingce_brand_blocks(gate: StrategyGate):
    env = _build_envelope({
        "title": "Re-route leads",
        "description": "通过 灵策智算 marketplace 做渠道分发",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    events = [e.to_dict() for e in decision.events]
    matched = [e for e in events if e.get("matched_id") == "灵策智算"]
    assert matched
    assert any(e["event_type"] == "STRATEGY_DRIFT_DETECTED" for e in matched)


def test_task_envelope_with_cloudtech_v22_emits_deprecated_asset(gate: StrategyGate):
    env = _build_envelope({
        "title": "Use CloudTech V22 unified gateway",
        "text": "point at CloudTech V22 gateway as source of truth",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    events = [e.to_dict() for e in decision.events]
    matched = [e for e in events if e.get("matched_id") == "CloudTech V22"]
    assert matched
    # cloudtech_v22_v23 kind → DEPRECATED_ASSET_REFERENCED, BLOCK
    assert all(e["event_type"] == "DEPRECATED_ASSET_REFERENCED" for e in matched)
    assert all(e["severity"] == "BLOCK" for e in matched)


def test_task_envelope_with_skill_id_emits_deprecated_asset(gate: StrategyGate):
    env = _build_envelope({
        "title": "Load skills",
        "text": "re-activate sk-industry plus sk-cross-matrix pipelines",
    })
    decision = gate.evaluate_envelope(env)
    assert not decision.allowed
    events = [e.to_dict() for e in decision.events]
    sk = [e for e in events if e.get("matched_id") in {"sk-industry", "sk-cross-matrix"}]
    assert sk
    assert all(e["event_type"] == "DEPRECATED_ASSET_REFERENCED" for e in sk)
    assert all(e["severity"] == "BLOCK" for e in sk)


# ---------------------------------------------------------------- Section 4:
# Bare text-only alias reference (no structured field, no combined signal)
# emits WARN, NOT BLOCK.

def test_bare_text_alias_only_emits_warn_not_block(gate: StrategyGate):
    """An envelope whose payload text mentions 医美 but does NOT carry
    a structured field (title/description/summary) and does NOT carry
    any other red-flag signal must emit WARN, not BLOCK.

    Implementation note: the gate looks at `text` (which is concatenated
    from structured fields). To exercise a bare-text-only hit we put
    the alias in the payload under a non-structured key (`note`), so
    it does NOT contribute to `text` and is therefore a true bare hit.
    The gate is also allowed to emit additional WARN events; what we
    forbid is a BLOCK-level alias event with no combined signal."""
    env = _build_envelope({
        "title": "Spin up retention campaign",
        "text": "Use general marketing automation for upsell.",
        "note": "side comment: 医美 vertical mentioned informally",
    })
    decision = gate.evaluate_envelope(env)
    # The envelope is otherwise clean → allowed.
    assert decision.allowed, (
        f"bare text-only alias must not BLOCK; events: "
        f"{[e.to_dict() for e in decision.events]}"
    )


# ---------------------------------------------------------------- Section 5:
# False-positive guards for generic English words.

def test_generic_english_words_do_not_block(gate: StrategyGate):
    """A task envelope that mentions the bare generic English words
    'industry', 'marketing', 'AI', 'SaaS' — without the specific
    Chinese industry-vertical tokens or retired aliases — must NOT be
    blocked by the alias check."""
    for txt in (
        "Plan an industry growth experiment",
        "Set up a marketing automation suite",
        "Integrate AI into the funnel",
        "Launch a SaaS onboarding flow",
    ):
        env = _build_envelope({"title": "Generic task", "text": txt})
        decision = gate.evaluate_envelope(env)
        # Must NOT be blocked by an alias event; can still be blocked
        # by other signals, but for this generic text there are none.
        assert decision.allowed, (
            f"generic English must not be blocked; text={txt!r}; "
            f"events={[e.to_dict() for e in decision.events]}"
        )


def test_bare_chinese_industry_does_not_block(gate: StrategyGate):
    """Bare 行业 (industry) by itself, without the specific 行业垂直 /
    行业垂直文档 / 行业MVP compound, must not be blocked."""
    env = _build_envelope({
        "title": "研究行业 dynamics",
        "description": "examine 行业 trends",
        "text": "行业 analysis for horizontal SaaS",
    })
    decision = gate.evaluate_envelope(env)
    assert decision.allowed, (
        f"bare 行业 without compound alias must not block; "
        f"events={[e.to_dict() for e in decision.events]}"
    )


def test_bare_workbuddy_does_not_block(gate: StrategyGate):
    """'WorkBuddy' is a competitor reference, not a retired alias."""
    env = _build_envelope({
        "title": "Compare vs WorkBuddy",
        "text": "track WorkBuddy connector coverage",
    })
    decision = gate.evaluate_envelope(env)
    assert decision.allowed


# ---------------------------------------------------------------- Section 6:
# Policy load now requires retired_aliases + retired_alias_kind.

def test_real_policy_has_retired_aliases_field(real_policy):
    assert "retired_aliases" in real_policy, "policy must declare retired_aliases"
    assert isinstance(real_policy["retired_aliases"], list)
    assert len(real_policy["retired_aliases"]) >= 1
    assert "retired_alias_kind" in real_policy
    assert isinstance(real_policy["retired_alias_kind"], dict)
    expected_kinds = {
        "industry_vertical", "old_brand", "vertical_workflow",
        "cloudtech_v22_v23", "skill_id",
    }
    actual_kinds = set(real_policy["retired_alias_kind"].keys())
    assert expected_kinds.issubset(actual_kinds), (
        f"missing alias kinds: {expected_kinds - actual_kinds}"
    )


def test_policy_loader_rejects_missing_retired_aliases(tmp_path):
    """If retired_aliases is removed, the loader must fail closed."""
    payload = _minimal_payload()
    payload.pop("retired_aliases", None)
    payload.pop("retired_alias_kind", None)
    _write_valid_policy(tmp_path, payload)
    res = load_strategy_policy(tmp_path)
    assert not res.ok
    assert res.reason == "schema_violation"
    assert any("retired_aliases" in e for e in res.errors)


def test_policy_loader_rejects_oversize_alias_kind_drift(tmp_path):
    """An alias_kind entry whose alias is NOT in retired_aliases fails closed."""
    payload = _minimal_payload()
    payload["retired_aliases"] = ["医美"]
    payload["retired_alias_kind"] = {"industry_vertical": ["装企"]}
    _write_valid_policy(tmp_path, payload)
    res = load_strategy_policy(tmp_path)
    assert not res.ok
    assert res.reason == "schema_violation"
    assert any("retired_alias_kind" in e for e in res.errors)


def test_policy_loader_rejects_empty_alias_entry(tmp_path):
    payload = _minimal_payload()
    payload["retired_aliases"] = ["医美", ""]
    _write_valid_policy(tmp_path, payload)
    res = load_strategy_policy(tmp_path)
    assert not res.ok
    assert res.reason == "schema_violation"


def test_policy_loader_rejects_single_char_alias(tmp_path):
    payload = _minimal_payload()
    payload["retired_aliases"] = ["医美", "X"]
    payload["retired_alias_kind"] = {"industry_vertical": ["医美", "X"]}
    _write_valid_policy(tmp_path, payload)
    res = load_strategy_policy(tmp_path)
    assert not res.ok
    assert res.reason == "schema_violation"


# ---------------------------------------------------------------- Section 7:
# Helpers expose alias kind lookup.

def test_is_retired_alias_helper():
    policy = {
        "retired_aliases": ["医美", "装企", "CloudTech V22"],
    }
    hits = is_retired_alias(policy, "phase 1 医美 + 装企 + CloudTech V22 gateway")
    assert hits == sorted({"医美", "装企", "CloudTech V22"})
    assert is_retired_alias(policy, "") == []
    assert is_retired_alias(None, "anything") == []


def test_retired_alias_kind_of_helper(real_policy):
    assert retired_alias_kind_of(real_policy, "医美") == "industry_vertical"
    assert retired_alias_kind_of(real_policy, "灵策智算") == "old_brand"
    assert retired_alias_kind_of(real_policy, "装修矩阵") == "vertical_workflow"
    assert retired_alias_kind_of(real_policy, "CloudTech V22") == "cloudtech_v22_v23"
    assert retired_alias_kind_of(real_policy, "sk-industry") == "skill_id"
    assert retired_alias_kind_of(real_policy, "NEVER-PRESENT-ALIAS") is None
    assert retired_alias_kind_of(None, "医美") is None


# ---------------------------------------------------------------- Section 8:
# SHA-256 sidecar matches.

def test_policy_sha256_sidecar_matches_real_policy():
    """Audit invariant: the SHA-256 sidecar matches the policy file."""
    side = (POLICY_DIR / "product_strategy.v1.sha256").read_text(encoding="utf-8")
    # extract first non-comment hex token
    actual = hashlib.sha256(
        (POLICY_DIR / "product_strategy.v1.json").read_bytes()
    ).hexdigest().upper()
    found = None
    for line in side.splitlines():
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        tok = line.split()[0]
        if len(tok) == 64 and all(c in "0123456789ABCDEFabcdef" for c in tok):
            found = tok.upper()
            break
    assert found is not None, f"sidecar has no hex hash: {side!r}"
    assert found == actual, (
        f"sidecar hash {found} does not match policy file hash {actual}"
    )


# ---------------------------------------------------------------- Section 9:
# Real quarantined content scanner integration: scanner picks up
# multiple aliases in one pass; quarantine classification holds.

@pytest.mark.skipif(
    not os.path.isfile(REAL_MEMORY_FILE),
    reason=f"real quarantined memory file missing: {REAL_MEMORY_FILE}",
)
def test_real_quarantine_scanner_counts_all_alias_kinds(scanner):
    findings = scanner.scan_path(REAL_MEMORY_FILE)
    content_findings = [f for f in findings if f.evidence_kind == "content"]
    # Group findings by matched_token and check kinds
    kinds = set()
    seen_aliases = set()
    for f in content_findings:
        seen_aliases.add(f.matched_token)
    # The actual memory file should at least surface these aliases.
    must_have = {"医美", "装企", "行业垂直", "灵策智算", "灵策AI", "行业垂直文档"}
    missing = must_have - seen_aliases
    assert not missing, f"real quarantine file missing aliases: {missing}"
    # All such findings must be ARCHIVED_REFERENCE.
    for f in content_findings:
        if f.matched_token in must_have:
            assert f.classification == Classification.ARCHIVED_REFERENCE


# ---------------------------------------------------------------- Helpers
def _minimal_payload() -> dict:
    return {
        "policy_id": EXPECTED_POLICY_ID,
        "policy_version": EXPECTED_POLICY_VERSION,
        "title": "x",
        "product": "CloudTech",
        "positioning": "HORIZONTAL_MARKETING_SAAS",
        "business_scope": "GENERAL_MARKETING",
        "vertical_product_strategy": "DISABLED",
        "industry_presets": "DISABLED",
        "status": "ACTIVE",
        "owner": "USER",
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


def _write_valid_policy(tmp_path: Path, payload: dict) -> None:
    p = tmp_path / "product_strategy.v1.json"
    raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    p.write_bytes(raw)
    h = hashlib.sha256(raw).hexdigest().upper()
    (tmp_path / "product_strategy.v1.sha256").write_text(
        h + "  product_strategy.v1.json", encoding="utf-8"
    )
    (tmp_path / "product_strategy.v1.schema.json").write_text("{}", encoding="utf-8")
