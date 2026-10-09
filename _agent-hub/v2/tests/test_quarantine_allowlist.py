"""test_quarantine_allowlist.py — Tests for quarantine manifest + allowlist.

Verifies:
  - `apply_quarantine(move=False)` (dry-run) returns deterministic manifest.
  - Real (move=True) quarantine moves files and writes manifest + DO_NOT_INDEX.
  - All `quarantine_paths` from the policy end up in the manifest.
  - SHA-256 of moved files matches expected.
  - `is_quarantine_root` correctly identifies the quarantine subtree.
  - Missing paths are recorded under `missing` (and `ok=False`).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POLICY_DIR = ROOT.parent / "policy"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT.parent))

from policy.quarantine import (  # noqa: E402
    DEFAULT_QUARANTINE_ROOT,
    DO_NOT_INDEX_FILENAME,
    MANIFEST_FILENAME,
    apply_quarantine,
    is_quarantine_root,
    write_do_not_index_marker,
)
from policy.strategy_policy import load_strategy_policy  # noqa: E402


@pytest.fixture
def policy() -> dict:
    res = load_strategy_policy(POLICY_DIR)
    assert res.ok, res.errors
    return res.policy


def test_dry_run_manifest_is_consistent(tmp_path):
    """Dry-run (move=False) computes manifest without filesystem side effects."""
    # Build a synthetic policy with local files we control.
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    f1 = src_dir / "f1.txt"
    f2 = src_dir / "f2.txt"
    f1.write_text("alpha", encoding="utf-8")
    f2.write_text("beta", encoding="utf-8")
    fake_policy = {
        "policy_id": "GLOBAL_PRODUCT_STRATEGY",
        "policy_version": "2026-10-08",
        "quarantine_paths": [str(f1), str(f2)],
        "deprecated_requirement_ids": ["R-001"],
    }
    res = apply_quarantine(
        policy=fake_policy,
        quarantine_root=tmp_path / "q",
        move=False,
    )
    assert res["ok"] is True, res["missing"]
    assert len(res["entries"]) == 2
    # Sources must still exist (dry-run)
    assert f1.exists()
    assert f2.exists()
    # Each entry has SHA + restore instructions
    for entry in res["entries"]:
        assert entry["sha256"] is not None
        assert entry["restore_instructions"]
        assert entry["policy_id"] == "GLOBAL_PRODUCT_STRATEGY"


def test_quarantine_dry_run_records_missing_paths(tmp_path):
    fake_policy = {
        "policy_id": "GLOBAL_PRODUCT_STRATEGY",
        "policy_version": "2026-10-08",
        "quarantine_paths": [
            str(tmp_path / "ghost-file-1"),
            str(tmp_path / "ghost-file-2"),
        ],
        "deprecated_requirement_ids": ["R-001"],
    }
    res = apply_quarantine(
        policy=fake_policy,
        quarantine_root=tmp_path / "q",
        move=False,
    )
    assert res["ok"] is False
    assert len(res["missing"]) == 2


def test_quarantine_real_move_creates_marker_and_manifest(tmp_path):
    """End-to-end: create fake source files, run move=True, verify result."""
    fake_policy = {
        "policy_id": "GLOBAL_PRODUCT_STRATEGY",
        "policy_version": "2026-10-08",
        "quarantine_paths": [],
        "deprecated_requirement_ids": ["R-001"],
    }
    # Set up fake sources
    src_a = tmp_path / "src-a.txt"
    src_b = tmp_path / "src-b.txt"
    src_a.write_text("hello", encoding="utf-8")
    src_b.write_text("world", encoding="utf-8")
    fake_policy["quarantine_paths"] = [str(src_a), str(src_b)]

    qroot = tmp_path / "q"
    res = apply_quarantine(
        policy=fake_policy,
        quarantine_root=qroot,
        move=True,
    )
    assert res["ok"]
    # Sources must be gone
    assert not src_a.exists()
    assert not src_b.exists()
    # Quarantine manifest + marker must exist
    assert (qroot / MANIFEST_FILENAME).exists()
    assert (qroot / DO_NOT_INDEX_FILENAME).exists()
    # Manifest contains entries
    manifest = json.loads((qroot / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert len(manifest["entries"]) == 2
    for entry in manifest["entries"]:
        # SHA matches what we'd compute against the original file content
        sha = hashlib.sha256(b"hello" if "src-a" in entry["source_path"] else b"world").hexdigest().upper()
        assert entry["sha256"] == sha


def test_is_quarantine_root():
    qroot = r"D:\AIOS\_quarantine\retired-assets\20261008"
    assert is_quarantine_root(rf"{qroot}\foo\bar.md", qroot)
    assert not is_quarantine_root(r"D:\AIOS\kernel\src\foo.py", qroot)


def test_default_quarantine_root_matches_contract():
    """The default quarantine root must match the contract path."""
    assert DEFAULT_QUARANTINE_ROOT == r"D:\AIOS\_quarantine\retired-assets\20261008"


def test_do_not_index_marker_text(tmp_path):
    marker = write_do_not_index_marker(tmp_path)
    text = marker.read_text(encoding="utf-8")
    assert "DO_NOT_INDEX" in text
    assert "GLOBAL_PRODUCT_STRATEGY" in text
    assert "ARCHIVED_REFERENCE" in text


def test_real_quarantine_root_has_marker_and_manifest():
    """The actual quarantine directory must have the marker + manifest."""
    qroot = Path(DEFAULT_QUARANTINE_ROOT)
    if not qroot.exists():
        pytest.skip("real quarantine not yet applied")
    assert (qroot / DO_NOT_INDEX_FILENAME).exists()
    assert (qroot / MANIFEST_FILENAME).exists()
    manifest = json.loads((qroot / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    assert manifest["policy_id"] == "GLOBAL_PRODUCT_STRATEGY"
    assert manifest["ok"] is True
    assert len(manifest["entries"]) == 5  # 5 quarantined WorkBuddy assets