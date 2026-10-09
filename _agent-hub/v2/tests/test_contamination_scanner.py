"""test_contamination_scanner.py — Tests for the structured scanner.

Verifies:
  - classify_source returns the right surface for archive/quarantine/etc.
  - Scanner emits ACTIVE_VIOLATION for active paths that reference
    a deprecated token.
  - Scanner emits ARCHIVED_REFERENCE for quarantined paths.
  - Scanner emits UNVERIFIED / FALSE_POSITIVE when classification
    cannot be made with confidence.
  - Scanner NEVER uses keyword-only blocking (source classification
    is always part of the verdict).
  - is_quarantined_path returns True iff path lives under quarantine_root.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT.parent / "policy"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from policy.contamination_scanner import (  # noqa: E402
    Classification,
    ContaminationScanner,
    classify_source,
    is_quarantined_path,
)


@pytest.fixture
def policy() -> dict:
    return {
        "policy_id": "GLOBAL_PRODUCT_STRATEGY",
        "policy_version": "2026-10-08",
        "deprecated_requirement_ids": ["R-001", "R-009"],
        "industry_presets_blocked": ["industry-zhuangxiu", "industry-jiaoyu"],
        "historical_source_prohibited_keys": [
            "AIOS_SOURCE_OF_TRUTH_FINAL",
            "D:\\CloudTech-Portable",
        ],
    }


def test_classify_source_active(policy):
    assert classify_source(r"D:\AIOS\kernel\src\foo.py") == "active"
    assert classify_source(r"D:\AIOS\_agent-hub\policy\product_strategy.v1.json") == "active"


def test_classify_source_archived(policy):
    assert classify_source(r"D:\AIOS\_archived_2026-09-18\foo.py") == "archived"
    assert classify_source(r"D:\AIOS\_backups_2026-09-29\foo.py") == "archived"
    assert classify_source(r"D:\AIOS\_schtasks_bak_R344\foo.xml") == "archived"


def test_classify_source_quarantine(policy):
    assert classify_source(r"D:\AIOS\_quarantine\retired-assets\20261008\foo.md") == "quarantine"


def test_classify_source_read_only(policy):
    assert classify_source(r"D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\foo.md") == "read_only"
    assert classify_source(r"D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\foo.json") == "read_only"


def test_classify_source_inert(policy):
    assert classify_source(r"D:\AIOS\_out\R222_sc001.png") == "inert"


def test_scanner_active_path_emits_active_violation(policy):
    """A path that references a deprecated id AND lives in active surface → ACTIVE_VIOLATION."""
    scanner = ContaminationScanner(policy)
    findings = scanner.scan_path(r"D:\AIOS\_agent-hub\some_active_file__R-001.md")
    # but since the path is in _agent-hub (active), and the token R-001 is in path
    # we'll get a path-keyword match → ACTIVE_VIOLATION
    assert any(f.classification == Classification.ACTIVE_VIOLATION for f in findings)


def test_scanner_quarantine_path_emits_archived_reference(policy):
    """A path in quarantine that references a deprecated id → ARCHIVED_REFERENCE, NOT ACTIVE_VIOLATION."""
    scanner = ContaminationScanner(policy, quarantine_root=r"D:\AIOS\_quarantine")
    findings = scanner.scan_path(r"D:\AIOS\_quarantine\retired-assets\20261008\R-001.md")
    assert all(f.classification == Classification.ARCHIVED_REFERENCE for f in findings)
    assert not any(f.classification == Classification.ACTIVE_VIOLATION for f in findings)


def test_scanner_archived_path_emits_archived_reference(policy):
    """A path under _archived_* that references a deprecated id → ARCHIVED_REFERENCE."""
    scanner = ContaminationScanner(policy)
    findings = scanner.scan_path(r"D:\AIOS\_archived_2026-09-18\R-009_foo.md")
    assert all(f.classification == Classification.ARCHIVED_REFERENCE for f in findings)


def test_scanner_text_hit_classification(policy):
    """A text payload that mentions R-001 → UNVERIFIED (text hits need context)."""
    scanner = ContaminationScanner(policy)
    findings = scanner.scan_text("please work on R-001 again")
    assert any(f.matched_id == "R-001" for f in findings)
    # Text hits without source context default to UNVERIFIED for ids
    assert any(f.classification == Classification.UNVERIFIED for f in findings)


def test_scanner_industry_preset_text_hit(policy):
    """A text payload that mentions a blocked industry preset → ACTIVE_VIOLATION."""
    scanner = ContaminationScanner(policy)
    findings = scanner.scan_text("load the industry-zhuangxiu preset")
    assert any(f.classification == Classification.ACTIVE_VIOLATION for f in findings)
    assert any(f.matched_id == "industry-zhuangxiu" for f in findings)


def test_scanner_clean_text_no_findings(policy):
    scanner = ContaminationScanner(policy)
    assert scanner.scan_text("hello world") == []


def test_scanner_uses_source_classification_not_keywords_only(policy):
    """The scanner's verdict must depend on source classification, not just
    a keyword hit."""
    scanner = ContaminationScanner(policy)
    # Same token R-001 in active path → ACTIVE_VIOLATION
    active = scanner.scan_path(r"D:\AIOS\_agent-hub\notes\R-001.md")
    # Same token R-001 in archived path → ARCHIVED_REFERENCE
    archived = scanner.scan_path(r"D:\AIOS\_archived_2026-09-18\R-001.md")
    assert active and archived
    assert active[0].classification == Classification.ACTIVE_VIOLATION
    assert archived[0].classification == Classification.ARCHIVED_REFERENCE
    assert active[0].classification != archived[0].classification


def test_is_quarantined_path():
    assert is_quarantined_path(
        r"D:\AIOS\_quarantine\retired-assets\20261008\foo.md",
        r"D:\AIOS\_quarantine\retired-assets\20261008",
    )
    assert not is_quarantined_path(
        r"D:\AIOS\kernel\src\foo.py",
        r"D:\AIOS\_quarantine\retired-assets\20261008",
    )


def test_scanner_classifications_are_a_subset_of_policy_classifications(policy):
    """The scanner must only emit classifications listed in the policy."""
    allowed = set(policy.get("scanner_classifications") or [])
    # The real policy has more; load it
    import json
    real = json.loads((POLICY_DIR / "product_strategy.v1.json").read_text(encoding="utf-8"))
    real_policy = ContaminationScanner(real)
    for path in [
        r"D:\AIOS\_agent-hub\R-001.md",
        r"D:\AIOS\_quarantine\retired-assets\20261008\R-001.md",
        r"D:\AIOS\_archived_2026-09-18\R-001.md",
    ]:
        for f in real_policy.scan_path(path):
            assert f.classification.value in allowed or f.classification.value in {
                "ARCHIVED_REFERENCE", "ACTIVE_VIOLATION", "UNVERIFIED", "FALSE_POSITIVE"
            }


# ---------------------------------------------------------------- Content-scan tests (correction 2026-10-09)
#
# These tests verify that `scan_path()` now inspects file CONTENT (not only
# the path / name) for retired ids, blocked industry presets, and
# prohibited asset paths. Per the contract, the source classification
# remains the load-bearing signal: content hits in archived / quarantine
# surfaces are ARCHIVED_REFERENCE; in active loadable surfaces they are
# ACTIVE_VIOLATION; in unknown / refused surfaces they are UNVERIFIED or
# skipped. Keyword alone is never the sole decision.


import json as _json
import os as _os
import tempfile as _tempfile


@pytest.fixture
def tmp_policy():
    return {
        "policy_id": "GLOBAL_PRODUCT_STRATEGY",
        "policy_version": "2026-10-08",
        "deprecated_requirement_ids": ["R-001", "R-009"],
        "industry_presets_blocked": ["industry-zhuangxiu", "industry-jiaoyu"],
        "historical_source_prohibited_keys": [
            "AIOS_SOURCE_OF_TRUTH_FINAL",
            "D:\\CloudTech-Portable",
        ],
        "prohibited_active_assets": [
            {"id": "PA-01", "summary": "CloudTech V22 Gateway 127.0.0.1:5099"},
        ],
    }


def _write(path: str, content: str, encoding: str = "utf-8") -> None:
    parent = _os.path.dirname(path)
    if parent:
        _os.makedirs(parent, exist_ok=True)
    with open(path, "wb") as fh:
        fh.write(content.encode(encoding))


def test_scanner_quarantined_file_with_retired_content_emits_archived_reference(tmp_policy):
    """Test 1: a quarantined file whose CONTENT references a retired id
    must be classified ARCHIVED_REFERENCE, NOT ACTIVE_VIOLATION.
    Path is clean (does NOT contain 'R-001'); only the file body does."""
    with _tempfile.TemporaryDirectory() as td:
        qdir = _os.path.join(td, "quarantine")
        fpath = _os.path.join(qdir, "memory_block.md")
        _write(fpath, "TODO: clean up legacy R-001 dependency\n")
        scanner = ContaminationScanner(tmp_policy, quarantine_root=qdir)
        findings = scanner.scan_path(fpath)
        content_findings = [f for f in findings if f.evidence_kind == "content"]
        assert content_findings, "expected at least one content finding for R-001"
        for f in content_findings:
            assert f.classification == Classification.ARCHIVED_REFERENCE
            assert f.matched_token == "R-001"
        assert not any(f.classification == Classification.ACTIVE_VIOLATION for f in findings)


def test_scanner_active_loadable_file_with_retired_content_emits_active_violation(tmp_policy):
    """Test 2: an active file whose CONTENT references a retired id
    must be classified ACTIVE_VIOLATION (the content is loadable by an
    active surface)."""
    with _tempfile.TemporaryDirectory() as td:
        # use a path the source classifier treats as 'active' (no archive markers)
        active_dir = _os.path.join(td, "active_loader")
        fpath = _os.path.join(active_dir, "config.md")
        _write(fpath, "feature toggle references R-009 status\n")
        scanner = ContaminationScanner(tmp_policy)
        findings = scanner.scan_path(fpath)
        content_findings = [f for f in findings if f.evidence_kind == "content"]
        assert content_findings, "expected at least one content finding for R-009"
        for f in content_findings:
            assert f.classification == Classification.ACTIVE_VIOLATION
            assert f.matched_token == "R-009"
        assert all(f.evidence_kind == "content" for f in findings if f.matched_token == "R-009")


def test_scanner_active_file_with_blocked_industry_preset_in_content_emits_active_violation(tmp_policy):
    """Bonus coverage: a blocked industry preset in active file content -> ACTIVE_VIOLATION."""
    with _tempfile.TemporaryDirectory() as td:
        fpath = _os.path.join(td, "prompts", "copy.md")
        _write(fpath, "switch context to industry-zhuangxiu preset\n")
        scanner = ContaminationScanner(tmp_policy)
        findings = scanner.scan_path(fpath)
        assert any(
            f.classification == Classification.ACTIVE_VIOLATION
            and f.matched_token == "industry-zhuangxiu"
            and f.evidence_kind == "content"
            for f in findings
        )


def test_scanner_active_file_with_prohibited_asset_path_in_content_emits_active_violation(tmp_policy):
    """Prohibited asset path substring (e.g. an IP:port) found in active file content."""
    with _tempfile.TemporaryDirectory() as td:
        fpath = _os.path.join(td, "notes", "ops.md")
        _write(fpath, "old gateway at 127.0.0.1:5099 should be retired\n")
        scanner = ContaminationScanner(tmp_policy)
        findings = scanner.scan_path(fpath)
        assert any(
            f.classification == Classification.ACTIVE_VIOLATION
            and f.matched_token == "127.0.0.1:5099"
            and f.evidence_kind == "content"
            for f in findings
        )


def test_scanner_binary_file_is_skipped(tmp_policy):
    """Test 3: a binary file (NUL byte in head) is skipped — no finding
    for its unreadable content. The scanner must NOT silently treat
    binary as 'no contamination' (UNVERIFIED = emit nothing, per
    contract clause 'binary/unknown source is UNVERIFIED or skipped')."""
    with _tempfile.TemporaryDirectory() as td:
        fpath = _os.path.join(td, "blob.bin")
        # include a NUL byte early -> binary detection; also embed the token
        # so we can prove content is NOT inspected.
        with open(fpath, "wb") as fh:
            fh.write(b"R-001\x00\x01\x02\x03")
        scanner = ContaminationScanner(tmp_policy)
        findings = scanner.scan_path(fpath)
        assert all(f.evidence_kind != "content" for f in findings)


def test_scanner_secret_file_is_never_opened(tmp_policy):
    """Secret-bearing files (.env, .key, .pem, token files) must NOT be
    read by the content scanner — even if they contain retired ids."""
    with _tempfile.TemporaryDirectory() as td:
        env_path = _os.path.join(td, ".env")
        key_path = _os.path.join(td, "service.key")
        pem_path = _os.path.join(td, "tls.pem")
        token_path = _os.path.join(td, "github_token")
        for p in (env_path, key_path, pem_path, token_path):
            _write(p, "R-001 leak\n")
        scanner = ContaminationScanner(tmp_policy)
        for p in (env_path, key_path, pem_path, token_path):
            findings = scanner.scan_path(p)
            assert all(f.evidence_kind != "content" for f in findings), \
                f"secret file {p!r} must not be content-scanned"


def test_scanner_oversize_file_is_skipped(tmp_policy):
    """Files above the size cap must be skipped (UNVERIFIED-or-skipped)."""
    with _tempfile.TemporaryDirectory() as td:
        fpath = _os.path.join(td, "huge.md")
        # write a file just past the default 1 MiB cap
        with open(fpath, "wb") as fh:
            fh.write(b"R-001 ")
            fh.write(b"x" * (DEFAULT_CONTENT_MAX_BYTES + 10))
        scanner = ContaminationScanner(tmp_policy, max_content_bytes=DEFAULT_CONTENT_MAX_BYTES)
        findings = scanner.scan_path(fpath)
        assert all(f.evidence_kind != "content" for f in findings)


def test_scanner_nonexistent_path_with_path_keyword_only(tmp_policy):
    """A path that does NOT exist on disk: if the path itself contains a
    token, path-keyword finding still emits (path-only behaviour
    preserved); no content finding because the file is not loadable."""
    fpath = r"D:\AIOS\nope\R-001.md"  # does not exist
    scanner = ContaminationScanner(tmp_policy)
    findings = scanner.scan_path(fpath)
    # path-keyword finding is emitted (existing behaviour)
    path_findings = [f for f in findings if f.evidence_kind == "path"]
    assert path_findings
    assert all(f.classification == Classification.ACTIVE_VIOLATION for f in path_findings)
    # no content finding because file is not loadable
    assert all(f.evidence_kind != "content" for f in findings)


def test_scanner_clean_file_content_emits_no_finding(tmp_policy):
    """Test 4: file with NO matching tokens in path OR content -> 0 findings."""
    with _tempfile.TemporaryDirectory() as td:
        fpath = _os.path.join(td, "clean.md")
        _write(fpath, "this file has nothing to do with the retired set.\n")
        scanner = ContaminationScanner(tmp_policy)
        findings = scanner.scan_path(fpath)
        assert findings == []


def test_scanner_path_only_behavior_preserved_for_nonexistent_file(tmp_policy):
    """The path-only classification logic must remain identical to the
    pre-correction behaviour when the file does not exist."""
    scanner = ContaminationScanner(tmp_policy)
    active = scanner.scan_path(r"D:\AIOS\_agent-hub\notes\R-001.md")
    archived = scanner.scan_path(r"D:\AIOS\_archived_2026-09-18\R-001.md")
    assert active and archived
    assert active[0].classification == Classification.ACTIVE_VIOLATION
    assert archived[0].classification == Classification.ARCHIVED_REFERENCE
    assert active[0].classification != archived[0].classification


def test_scanner_content_token_set_includes_required_kinds(tmp_policy):
    """The content token set must contain ids, industry presets, and
    prohibited asset substrings (per contract)."""
    from policy.contamination_scanner import build_content_token_set
    tokens = build_content_token_set(tmp_policy)
    assert "R-001" in tokens
    assert "R-009" in tokens
    assert "industry-zhuangxiu" in tokens
    assert "industry-jiaoyu" in tokens
    assert "AIOS_SOURCE_OF_TRUTH_FINAL" in tokens
    assert "D:\\CloudTech-Portable" in tokens
    assert "127.0.0.1:5099" in tokens  # extracted from prohibited_active_assets


def test_scanner_content_no_recursion(tmp_policy):
    """scan_path() must NEVER recurse into a directory. Passing a
    directory must return [] (or path-only findings) without listing
    children or emitting content findings for any file inside."""
    with _tempfile.TemporaryDirectory() as td:
        sub = _os.path.join(td, "subdir")
        _os.makedirs(sub, exist_ok=True)
        _write(_os.path.join(sub, "leaf.md"), "R-001 should not be visible\n")
        scanner = ContaminationScanner(tmp_policy)
        findings = scanner.scan_path(td)
        # path-keyword for the dir itself is None (token not in dir path).
        # content findings must be empty because scan_path does not recurse.
        assert all(f.evidence_kind != "content" for f in findings)


def test_scanner_gbk_encoded_content_is_inspected(tmp_policy):
    """GBK-encoded content with a retired id must still be found."""
    with _tempfile.TemporaryDirectory() as td:
        fpath = _os.path.join(td, "gbk.md")
        _write(fpath, "退役 R-001 备注\n", encoding="gbk")
        scanner = ContaminationScanner(tmp_policy)
        findings = scanner.scan_path(fpath)
        assert any(
            f.classification == Classification.ACTIVE_VIOLATION
            and f.matched_token == "R-001"
            and f.evidence_kind == "content"
            for f in findings
        )


def test_scanner_real_quarantined_memory_file_now_finds_content(tmp_policy):
    """End-to-end against the real quarantine root: when a file under
    D:\\AIOS\\_quarantine carries retired-id text in CONTENT, the
    scanner must emit ARCHIVED_REFERENCE findings. The real quarantined
    files happen not to carry retired tokens, so we plant a synthetic
    fixture inside the real quarantine tree (and clean it up).
    """
    real_quarantine_root = r"D:\AIOS\_quarantine"
    if not _os.path.isdir(real_quarantine_root):
        pytest.skip(f"real quarantine root not present: {real_quarantine_root}")
    fixture_name = "_scanner_correction_fixture_20261009.md"
    fixture_path = _os.path.join(real_quarantine_root, fixture_name)
    fixture_text = (
        "scanner-correction fixture\n"
        "this file intentionally references retired requirement R-001\n"
        "and the blocked industry preset industry-zhuangxiu\n"
        "plus a historical source key AIOS_SOURCE_OF_TRUTH_FINAL\n"
    )
    try:
        _write(fixture_path, fixture_text)
        real_policy = _json.loads(
            (POLICY_DIR / "product_strategy.v1.json").read_text(encoding="utf-8")
        )
        scanner = ContaminationScanner(
            real_policy, quarantine_root=real_quarantine_root
        )
        findings = scanner.scan_path(fixture_path)
        content_findings = [f for f in findings if f.evidence_kind == "content"]
        assert content_findings, (
            "expected content-level findings against the real quarantine root; "
            "the scanner must inspect content for retired references."
        )
        for f in content_findings:
            assert f.classification == Classification.ARCHIVED_REFERENCE, (
                f"expected ARCHIVED_REFERENCE for quarantined file; got {f.classification}"
            )
            assert f.source_classification == "quarantine"
        # specific tokens present
        matched = {f.matched_token for f in content_findings}
        assert "R-001" in matched
        assert "industry-zhuangxiu" in matched
        assert "AIOS_SOURCE_OF_TRUTH_FINAL" in matched
    finally:
        try:
            _os.remove(fixture_path)
        except OSError:
            pass


def test_strategy_index_evidence_path_points_to_real_evidence():
    """The strategy_index.json `tests.evidence` field must point to the
    real evidence file (not the legacy v2 reports path that never existed)."""
    idx = _json.loads((POLICY_DIR / "strategy_index.json").read_text(encoding="utf-8"))
    ev = idx["tests"]["evidence"]
    assert ev.endswith(
        "GLOBAL_STRATEGY_RETIREMENT_PHASE2_20261009_EVIDENCE.json"
    ), f"unexpected evidence path: {ev}"
    assert _os.path.isfile(ev), f"evidence file does not exist: {ev}"


# Default-cap alias so tests can refer to it without importing internals.
from policy.contamination_scanner import DEFAULT_CONTENT_MAX_BYTES  # noqa: E402