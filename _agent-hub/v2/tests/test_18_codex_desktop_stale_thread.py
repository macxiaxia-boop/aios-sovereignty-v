# v2/tests/test_18_codex_desktop_stale_thread.py
#
# R286.D test_18: Failure: stale thread.
#
# Acceptance:
#   - probe_codex_desktop_thread returns reachable=False when the marker is
#     older than ttl_seconds (state="stale"); no false-negative reachability.
#   - probe_codex_desktop_thread returns reachable=True when the marker is
#     fresh (state="fresh"); no false-positive reachability.
#   - probe_codex_desktop_thread writes a deterministic evidence JSON file
#     under v2/reports/ when the feature gate is ON, with thread_id,
#     state, age_seconds, ttl_seconds, evidence_path.
#   - When the feature gate is OFF, the probe is a no-op (reachable=None,
#     no evidence file), preserving the existing R286.A reachable oracle
#     (codex.reachable decided solely by relay_port_open).
#   - Stale thread is NOT mistakenly reported as reachable.
#   - Test is isolated, deterministic, never invokes a real model or desktop app.
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Always isolate marker files under a temp dir so this test never pollutes
# the LIVE v2 root (D:\AIOS\_agent-hub\v2) even when run directly without
# `run_all_tests.py` (conftest.py sets AIOS_V2_ROOT in the bundled runner).
# Fall back to AIOS_V2_ROOT if conftest already set it; only use a fresh
# tempdir as a last resort.
if "AIOS_V2_ROOT" not in os.environ:
    _test_root = Path(tempfile.mkdtemp(prefix="aiosv2_test18_")).resolve()
    os.environ["AIOS_V2_ROOT"] = str(_test_root)
from src.paths import ensure_dirs  # noqa: E402
ensure_dirs()

from src.v2_consumer import probe_codex_desktop_thread


def _set_stale_thread_gate(on: bool):
    import src.v2_consumer as _vc
    _vc.STALE_THREAD_PROBE_ENABLED = on
    os.environ["AIOS_V2_STALE_THREAD_PROBE_ENABLED"] = "1" if on else "0"
    return _vc.STALE_THREAD_PROBE_ENABLED


def _write_marker(path: Path, age_seconds: int):
    """Write a last_seen_at marker with age_seconds in the past."""
    ts = (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    path.write_text(
        json.dumps({"last_seen_at": ts, "thread_id": "test-thread"},
                   ensure_ascii=False),
        encoding="utf-8",
    )


def test_stale_thread_probe_disabled_by_default():
    """Without setting the env gate, the probe is a no-op."""
    saved = os.environ.get("AIOS_V2_STALE_THREAD_PROBE_ENABLED")
    try:
        if saved is not None:
            del os.environ["AIOS_V2_STALE_THREAD_PROBE_ENABLED"]
        import src.v2_consumer as _vc
        _vc.STALE_THREAD_PROBE_ENABLED = False

        result = probe_codex_desktop_thread("codex-desktop-default-off")
        assert result["reachable"] is None, (
            f"with gate OFF, reachable must be None; got {result!r}"
        )
        assert result["state"] == "gate_off"
        assert result["thread_id"] == "codex-desktop-default-off"
        assert result["evidence_path"] is None
    finally:
        if saved is not None:
            os.environ["AIOS_V2_STALE_THREAD_PROBE_ENABLED"] = saved
        import src.v2_consumer as _vc
        _vc.STALE_THREAD_PROBE_ENABLED = (
            os.environ.get("AIOS_V2_STALE_THREAD_PROBE_ENABLED", "0") == "1"
        )


def test_stale_thread_marker_older_than_ttl_is_not_reachable():
    """Marker older than ttl_seconds → reachable=False, state='stale',
       evidence JSON written with the documented keys."""
    saved = _set_stale_thread_gate(True)
    tmp_marker = Path(os.environ.get("AIOS_V2_ROOT", str(ROOT))) / "stale_thread_marker.json"
    # Age = 600s, ttl = 120s → must be stale
    _write_marker(tmp_marker, age_seconds=600)

    try:
        result = probe_codex_desktop_thread(
            "codex-desktop-test-stale",
            marker_path=tmp_marker,
            ttl_seconds=120,
        )
        assert result["reachable"] is False, (
            f"stale thread (age=600s > ttl=120s) MUST be unreachable; got {result!r}"
        )
        assert result["state"] == "stale"
        assert result["thread_id"] == "codex-desktop-test-stale"
        assert result["ttl_seconds"] == 120
        assert result["age_seconds"] is not None and result["age_seconds"] >= 600 - 1
        assert result["evidence_path"] is not None

        ev_path = Path(result["evidence_path"])
        assert ev_path.exists(), f"evidence JSON must exist at {ev_path}"
        ev_obj = json.loads(ev_path.read_text(encoding="utf-8"))
        for key in ("reachable", "state", "thread_id", "last_seen_at",
                     "age_seconds", "ttl_seconds"):
            assert key in ev_obj, (
                f"evidence JSON missing key {key!r}; got {ev_obj!r}"
            )
        assert ev_obj["reachable"] is False
        assert ev_obj["state"] == "stale"
        assert ev_obj["thread_id"] == "codex-desktop-test-stale"
        # No raw binary / secret-like content
        assert "secret" not in json.dumps(ev_obj).lower()
        assert "password" not in json.dumps(ev_obj).lower()
    finally:
        _set_stale_thread_gate(False)
        if tmp_marker.exists():
            tmp_marker.unlink()


def test_stale_thread_fresh_marker_is_reachable():
    """Fresh marker (age < ttl) → reachable=True, state='fresh'."""
    saved = _set_stale_thread_gate(True)
    tmp_marker = Path(os.environ.get("AIOS_V2_ROOT", str(ROOT))) / "fresh_thread_marker.json"
    _write_marker(tmp_marker, age_seconds=5)

    try:
        result = probe_codex_desktop_thread(
            "codex-desktop-test-fresh",
            marker_path=tmp_marker,
            ttl_seconds=120,
        )
        assert result["reachable"] is True, (
            f"fresh thread (age=5s < ttl=120s) MUST be reachable; got {result!r}"
        )
        assert result["state"] == "fresh"
        assert result["thread_id"] == "codex-desktop-test-fresh"
        assert result["evidence_path"] is not None

        ev_path = Path(result["evidence_path"])
        assert ev_path.exists()
        ev_obj = json.loads(ev_path.read_text(encoding="utf-8"))
        assert ev_obj["reachable"] is True
        assert ev_obj["state"] == "fresh"
    finally:
        _set_stale_thread_gate(False)
        if tmp_marker.exists():
            tmp_marker.unlink()


def test_stale_thread_no_marker_does_not_false_positive():
    """No marker file → state='no_marker', reachable=True (no false-positive)."""
    saved = _set_stale_thread_gate(True)
    missing_marker = Path(os.environ.get("AIOS_V2_ROOT", str(ROOT))) / "definitely_missing_marker.json"
    if missing_marker.exists():
        missing_marker.unlink()

    try:
        result = probe_codex_desktop_thread(
            "codex-desktop-test-nomarker",
            marker_path=missing_marker,
            ttl_seconds=120,
        )
        assert result["reachable"] is True, (
            f"missing marker must NOT trigger false-positive staleness; got {result!r}"
        )
        assert result["state"] == "no_marker"
        assert result["thread_id"] == "codex-desktop-test-nomarker"
        assert result["evidence_path"] is not None
        ev_path = Path(result["evidence_path"])
        assert ev_path.exists()
        ev_obj = json.loads(ev_path.read_text(encoding="utf-8"))
        assert ev_obj["state"] == "no_marker"
        assert ev_obj["reachable"] is True
    finally:
        _set_stale_thread_gate(False)


def test_stale_thread_corrupt_marker_is_not_reachable():
    """A marker that cannot be parsed → state='marker_corrupt', reachable=False.
       The probe leaves a clear failure-evidence JSON so an operator can
       diagnose WHY a thread was reported stale."""
    saved = _set_stale_thread_gate(True)
    tmp_marker = Path(os.environ.get("AIOS_V2_ROOT", str(ROOT))) / "corrupt_marker.json"
    tmp_marker.write_text("not valid json {{{", encoding="utf-8")

    try:
        result = probe_codex_desktop_thread(
            "codex-desktop-test-corrupt",
            marker_path=tmp_marker,
            ttl_seconds=120,
        )
        assert result["reachable"] is False, (
            f"corrupt marker must NOT be reported as reachable; got {result!r}"
        )
        assert result["state"] == "marker_corrupt"
        assert result["evidence_path"] is not None
        ev_path = Path(result["evidence_path"])
        assert ev_path.exists()
        ev_obj = json.loads(ev_path.read_text(encoding="utf-8"))
        assert ev_obj["state"] == "marker_corrupt"
        assert ev_obj["reachable"] is False
    finally:
        _set_stale_thread_gate(False)
        if tmp_marker.exists():
            tmp_marker.unlink()


def test_stale_thread_does_not_modify_marker_file():
    """The probe must be READ-ONLY on the marker — no mutation."""
    saved = _set_stale_thread_gate(True)
    tmp_marker = Path(os.environ.get("AIOS_V2_ROOT", str(ROOT))) / "read_only_marker.json"
    _write_marker(tmp_marker, age_seconds=600)
    before_bytes = tmp_marker.read_bytes()

    try:
        probe_codex_desktop_thread(
            "codex-desktop-test-readonly",
            marker_path=tmp_marker,
            ttl_seconds=120,
        )
        after_bytes = tmp_marker.read_bytes()
        assert before_bytes == after_bytes, (
            f"probe must NOT modify the marker file; "
            f"before={before_bytes!r}, after={after_bytes!r}"
        )
    finally:
        _set_stale_thread_gate(False)
        if tmp_marker.exists():
            tmp_marker.unlink()


def test_stale_thread_probe_gate_off_writes_no_evidence():
    """With gate OFF, probe must not write any evidence file even if a
       marker is present.  This preserves the R286.A reachable oracle
       contract (codex.reachable decided solely by relay_port_open)."""
    saved = _set_stale_thread_gate(False)
    tmp_marker = Path(os.environ.get("AIOS_V2_ROOT", str(ROOT))) / "off_marker.json"
    _write_marker(tmp_marker, age_seconds=600)

    try:
        result = probe_codex_desktop_thread(
            "codex-desktop-test-off",
            marker_path=tmp_marker,
            ttl_seconds=120,
        )
        assert result["reachable"] is None
        assert result["state"] == "gate_off"
        assert result["evidence_path"] is None

        # No evidence file should have been written for this thread_id
        from src.paths import v2_root
        ev_path = v2_root() / "reports" / "codex_desktop_thread_probe_codex-desktop-test-off.json"
        assert not ev_path.exists(), (
            f"with gate OFF, no evidence file must be written; found {ev_path}"
        )
    finally:
        _set_stale_thread_gate(False)
        if tmp_marker.exists():
            tmp_marker.unlink()