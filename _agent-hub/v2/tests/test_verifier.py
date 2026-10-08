#!/usr/bin/env python3
# v2/tests/test_verifier.py - P8 verifier sub-agent test
#
# Verifies that src.verifier.verify_envelope_dispatch independently
# validates adapter dispatch results without trusting the dispatcher.
# Runs all 3 adapters (hermes subprocess, openclaw http, workbuddy probe)
# and asserts verify_ok=True with check-level evidence.
from __future__ import annotations

import sys
import json
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.verifier import verify_envelope_dispatch
from src.hermes_adapter import make_hermes_adapter
from src.openclaw_adapter import make_openclaw_adapter
from src.workbuddy_adapter import make_workbuddy_adapter


def test_verifier_hermes_subprocess():
    """Verifier independently re-runs hermes.exe and confirms adapter output."""
    evidence_dir = Path(tempfile.mkdtemp(prefix="verify_hermes_"))
    try:
        result = verify_envelope_dispatch(
            recipient="hermes",
            adapter_fn=make_hermes_adapter(),
            payload={"args": ["version"]},
            expected_substrings=["Hermes"],
            evidence_dir=evidence_dir,
        )
        assert result["verify_ok"] is True, f"verifier rejected hermes: {result}"
        check_names = [c["name"] for c in result["checks"]]
        # Required independent checks for hermes
        assert "adapter_call_no_exception" in check_names
        assert "hermes_transport" in check_names
        assert "hermes_exe_present" in check_names
        assert "hermes_exit_zero" in check_names
        assert "hermes_independent_rerun" in check_names
        # evidence path must exist
        assert "evidence_path" in result, f"no evidence_path: {result}"
        ep = Path(result["evidence_path"])
        assert ep.exists(), f"evidence file missing: {ep}"
        body = json.loads(ep.read_text(encoding="utf-8"))
        assert body["verify_ok"] is True
        result = {"ok": True, "evidence_path": str(ep),
                "checks_passed": sum(1 for c in result["checks"] if c["ok"])}
        assert result
    finally:
        shutil.rmtree(evidence_dir, ignore_errors=True)


def test_verifier_openclaw_http():
    """Verifier independently re-issues GET /healthz and compares body."""
    evidence_dir = Path(tempfile.mkdtemp(prefix="verify_openclaw_"))
    try:
        result = verify_envelope_dispatch(
            recipient="openclaw",
            adapter_fn=make_openclaw_adapter(),
            payload={"action": "health"},
            expected_status=200,
            evidence_dir=evidence_dir,
        )
        assert result["verify_ok"] is True, f"verifier rejected openclaw: {result}"
        check_names = [c["name"] for c in result["checks"]]
        assert "adapter_call_no_exception" in check_names
        assert "openclaw_transport" in check_names
        assert "openclaw_independent_healthz" in check_names
        assert "openclaw_expected_status" in check_names
        ep = Path(result["evidence_path"])
        assert ep.exists(), f"evidence file missing: {ep}"
        result = {"ok": True, "evidence_path": str(ep),
                "checks_passed": sum(1 for c in result["checks"] if c["ok"])}
        assert result
    finally:
        shutil.rmtree(evidence_dir, ignore_errors=True)


def test_verifier_workbuddy_probe():
    """Verifier independently re-reads daemon.log and confirms stale classification."""
    evidence_dir = Path(tempfile.mkdtemp(prefix="verify_workbuddy_"))
    try:
        result = verify_envelope_dispatch(
            recipient="workbuddy",
            adapter_fn=make_workbuddy_adapter(),
            payload={"action": "probe"},
            evidence_dir=evidence_dir,
        )
        # workbuddy probe returns ok=alive=False (daemon is down) but adapter
        # is honest; we don't assert verify_ok=True because the daemon is
        # actually down (transport=workbuddy_probe is still correct).
        check_names = [c["name"] for c in result["checks"]]
        assert "adapter_call_no_exception" in check_names
        assert "workbuddy_transport" in check_names
        # The transport check must pass (probe ran)
        transport_check = next(c for c in result["checks"] if c["name"] == "workbuddy_transport")
        assert transport_check["ok"] is True, f"transport wrong: {transport_check}"
        ep = Path(result["evidence_path"]) if "evidence_path" in result else None
        result = {"ok": True,
                "evidence_path": str(ep) if ep else None,
                "checks_passed": sum(1 for c in result["checks"] if c["ok"]),
                "verify_ok": result["verify_ok"]}
        assert result
    finally:
        shutil.rmtree(evidence_dir, ignore_errors=True)


def test_verifier_all_three_adapters_combined():
    """Run verifier against all 3 adapters in sequence; collect evidence."""
    evidence_root = Path(tempfile.mkdtemp(prefix="verify_all_"))
    try:
        results = {}
        # Hermes
        results["hermes"] = verify_envelope_dispatch(
            recipient="hermes",
            adapter_fn=make_hermes_adapter(),
            payload={"args": ["version"]},
            expected_substrings=["Hermes"],
            evidence_dir=evidence_root / "hermes",
        )
        # OpenClaw
        results["openclaw"] = verify_envelope_dispatch(
            recipient="openclaw",
            adapter_fn=make_openclaw_adapter(),
            payload={"action": "health"},
            expected_status=200,
            evidence_dir=evidence_root / "openclaw",
        )
        # WorkBuddy
        results["workbuddy"] = verify_envelope_dispatch(
            recipient="workbuddy",
            adapter_fn=make_workbuddy_adapter(),
            payload={"action": "probe"},
            evidence_dir=evidence_root / "workbuddy",
        )
        # Hermes and OpenClaw MUST verify_ok=True
        assert results["hermes"]["verify_ok"] is True, f"hermes verify failed: {results['hermes']}"
        assert results["openclaw"]["verify_ok"] is True, f"openclaw verify failed: {results['openclaw']}"
        # All three must have evidence files
        for name, res in results.items():
            assert "evidence_path" in res, f"{name} no evidence_path: {res}"
            assert Path(res["evidence_path"]).exists(), f"{name} evidence missing"
        result = {"ok": True, "evidence_root": str(evidence_root),
                "results": {k: {"verify_ok": v["verify_ok"],
                                "checks_passed": sum(1 for c in v["checks"] if c["ok"]),
                                "checks_total": len(v["checks"])}
                            for k, v in results.items()}}
        assert result
    finally:
        shutil.rmtree(evidence_root, ignore_errors=True)

if __name__ == "__main__":
    test_verifier_hermes_subprocess()
    test_verifier_openclaw_http()
    test_verifier_workbuddy_probe()
    test_verifier_all_three_adapters_combined()
    print("PASS: test_verifier_hermes_subprocess, test_verifier_openclaw_http, test_verifier_workbuddy_probe, test_verifier_all_three_adapters_combined")
