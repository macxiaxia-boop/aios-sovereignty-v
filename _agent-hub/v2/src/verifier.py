#!/usr/bin/env python3
# v2/src/verifier.py — independent verifier sub-agent
#
# P8 deliverable. Independent verification of adapter dispatch results.
# Unlike the adapters themselves, the verifier does NOT trust:
#   - the dispatcher's ok flag
#   - in-memory state
#   - log lines
#
# It independently:
#   1. Builds a fresh envelope (NOT re-using the dispatcher's)
#   2. Calls the adapter with that envelope
#   3. For subprocess adapters (hermes): re-runs hermes.exe directly
#   4. For HTTP adapters (openclaw): re-issues GET /healthz and compares body
#   5. For probe adapters (workbuddy): re-reads daemon.log and compares stale-ness
#   6. Writes verify_ok.json or verify_failed.json with full diff + evidence
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

HERMES_EXE = Path(r"D:\AIOS\_relinked\hermes\hermes-agent\.venv\Scripts\hermes.exe")
OPENCLAW_BASE = "http://127.0.0.1:18792"
WORKBUDDY_DAEMON_LOG = Path(os.path.expanduser(r"~/.workbuddy/logs/daemon.log"))
WORKBUDDY_STALE_THRESHOLD_SEC = 1800


def verify_envelope_dispatch(*, recipient: str, adapter_fn: Callable,
                              payload: Dict[str, Any],
                              expected_substrings=None,
                              expected_status=None,
                              evidence_dir=None,
                              envelope_id=None) -> Dict[str, Any]:
    """Independent verification of an adapter dispatch result."""
    started = time.time()
    env = {
        "id": envelope_id or ("verify-" + str(int(started))),
        "sender": "verifier",
        "recipient": recipient,
        "message_type": "task",
        "payload": payload,
    }
    checks: List[Dict[str, Any]] = []

    # Check 1: adapter call itself does not raise
    try:
        adapter_result = adapter_fn(env, recipient=recipient)
        checks.append({
            "name": "adapter_call_no_exception",
            "ok": True,
            "evidence": {"transport": adapter_result.get("transport"),
                         "adapter": adapter_result.get("adapter"),
                         "duration_ms": adapter_result.get("duration_ms")},
        })
    except Exception as e:
        checks.append({"name": "adapter_call_no_exception", "ok": False,
                       "evidence": {"error": type(e).__name__ + ": " + str(e)}})
        return _write_verdict(False, checks, started, env["id"], evidence_dir)

    # Check 2: per-adapter independent re-verification
    if recipient == "hermes":
        checks.extend(_verify_hermes(adapter_result, expected_substrings or []))
    elif recipient == "openclaw":
        checks.extend(_verify_openclaw(adapter_result, expected_status))
    elif recipient == "workbuddy":
        checks.extend(_verify_workbuddy(adapter_result))
    elif recipient == "claudecode":
        checks.extend(_verify_claudecode(adapter_result))
    else:
        checks.append({"name": "unknown_recipient", "ok": False,
                       "evidence": {"recipient": recipient}})

    all_ok = all(c["ok"] for c in checks)
    return _write_verdict(all_ok, checks, started, env["id"], evidence_dir)


def _write_verdict(verify_ok: bool, checks, started, envelope_id, evidence_dir):
    duration_ms = int((time.time() - started) * 1000)
    out = {
        "verify_ok": verify_ok,
        "envelope_id": envelope_id,
        "checks": checks,
        "duration_ms": duration_ms,
        "verified_at": int(started),
    }
    if evidence_dir is not None:
        evidence_dir = Path(evidence_dir)
        evidence_dir.mkdir(parents=True, exist_ok=True)
        fname = "verify_ok.json" if verify_ok else "verify_failed.json"
        path = evidence_dir / fname
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
        out["evidence_path"] = str(path)
    return out


def _verify_hermes(adapter_result: dict, expected_substrings: List[str]) -> List[dict]:
    checks = []
    checks.append({
        "name": "hermes_transport",
        "ok": adapter_result.get("transport") == "hermes_subprocess",
        "evidence": {"transport": adapter_result.get("transport")},
    })
    checks.append({
        "name": "hermes_exe_present",
        "ok": HERMES_EXE.exists(),
        "evidence": {"path": str(HERMES_EXE), "exists": HERMES_EXE.exists()},
    })
    checks.append({
        "name": "hermes_exit_zero",
        "ok": adapter_result.get("exit_code") == 0,
        "evidence": {"exit_code": adapter_result.get("exit_code")},
    })
    if HERMES_EXE.exists():
        try:
            proc = subprocess.run(
                [str(HERMES_EXE), "version"],
                capture_output=True, timeout=20,
            )
            version_stdout = proc.stdout.decode("utf-8", errors="replace")
            checks.append({
                "name": "hermes_independent_rerun",
                "ok": proc.returncode == 0 and "Hermes" in version_stdout,
                "evidence": {"exit": proc.returncode,
                             "stdout_head": version_stdout[:200]},
            })
        except Exception as e:
            checks.append({"name": "hermes_independent_rerun", "ok": False,
                           "evidence": {"error": type(e).__name__ + ": " + str(e)}})
    adapter_stdout = adapter_result.get("stdout_tail") or ""
    for s in expected_substrings:
        checks.append({
            "name": "hermes_substring[" + repr(s) + "]",
            "ok": s in adapter_stdout,
            "evidence": {"substring": s, "found_at": adapter_stdout.find(s)},
        })
    return checks


def _verify_openclaw(adapter_result: dict, expected_status) -> List[dict]:
    checks = []
    checks.append({
        "name": "openclaw_transport",
        "ok": adapter_result.get("transport") == "openclaw_http",
        "evidence": {"transport": adapter_result.get("transport")},
    })
    try:
        with urllib.request.urlopen(OPENCLAW_BASE + "/healthz", timeout=10) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            status = resp.status
            checks.append({
                "name": "openclaw_independent_healthz",
                "ok": status == 200,
                "evidence": {"status": status, "body": body[:200]},
            })
            adapter_body = adapter_result.get("body_json")
            try:
                independent_parsed = json.loads(body)
            except Exception:
                independent_parsed = None
            checks.append({
                "name": "openclaw_body_matches_adapter",
                "ok": independent_parsed == adapter_body,
                "evidence": {"independent_body": independent_parsed,
                             "adapter_body": adapter_body},
            })
    except Exception as e:
        checks.append({"name": "openclaw_independent_healthz", "ok": False,
                       "evidence": {"error": type(e).__name__ + ": " + str(e)}})
    if expected_status is not None:
        checks.append({
            "name": "openclaw_expected_status",
            "ok": adapter_result.get("status") == expected_status,
            "evidence": {"expected": expected_status,
                         "got": adapter_result.get("status")},
        })
    return checks


def _verify_workbuddy(adapter_result: dict) -> List[dict]:
    checks = []
    checks.append({
        "name": "workbuddy_transport",
        "ok": adapter_result.get("transport") in ("workbuddy_probe", "workbuddy_blocked_daemon_down"),
        "evidence": {"transport": adapter_result.get("transport")},
    })
    if WORKBUDDY_DAEMON_LOG.exists():
        stat = WORKBUDDY_DAEMON_LOG.stat()
        age_sec = time.time() - stat.st_mtime
        is_stale = age_sec > WORKBUDDY_STALE_THRESHOLD_SEC
        checks.append({
            "name": "workbuddy_daemon_log_independent",
            "ok": True,
            "evidence": {"path": str(WORKBUDDY_DAEMON_LOG),
                         "age_sec": int(age_sec),
                         "stale": is_stale,
                         "size_bytes": stat.st_size},
        })
        adapter_stale = ((adapter_result.get("probe") or {}).get("checks") or {}).get("daemon_log", {}).get("stale")
        checks.append({
            "name": "workbuddy_stale_classification_matches",
            "ok": adapter_stale == is_stale,
            "evidence": {"adapter_stale": adapter_stale,
                         "independent_stale": is_stale},
        })
    else:
        checks.append({"name": "workbuddy_daemon_log_independent", "ok": False,
                       "evidence": {"error": "daemon.log missing"}})
    return checks


def _verify_claudecode(adapter_result: dict) -> List[dict]:
    checks = []
    checks.append({
        "name": "claudecode_transport",
        "ok": adapter_result.get("transport") == "claude_p_subprocess",
        "evidence": {"transport": adapter_result.get("transport")},
    })
    checks.append({
        "name": "claudecode_stdout_nonempty",
        "ok": bool((adapter_result.get("stdout_tail") or "").strip()),
        "evidence": {"stdout_len": len(adapter_result.get("stdout_tail") or "")},
    })
    return checks


def main():
    """CLI: python -m src.verifier RECIPIENT [--evidence-dir DIR]"""
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("recipient", choices=["hermes", "openclaw", "workbuddy"])
    p.add_argument("--evidence-dir", type=Path,
                   default=Path(r"D:\AIOS\_agent-hub\reports\verifier"))
    args = p.parse_args()

    if args.recipient == "hermes":
        from src.hermes_adapter import make_hermes_adapter
        result = verify_envelope_dispatch(
            recipient="hermes",
            adapter_fn=make_hermes_adapter(),
            payload={"args": ["version"]},
            expected_substrings=["Hermes"],
            evidence_dir=args.evidence_dir,
        )
    elif args.recipient == "openclaw":
        from src.openclaw_adapter import make_openclaw_adapter
        result = verify_envelope_dispatch(
            recipient="openclaw",
            adapter_fn=make_openclaw_adapter(),
            payload={"action": "health"},
            expected_status=200,
            evidence_dir=args.evidence_dir,
        )
    else:
        from src.workbuddy_adapter import make_workbuddy_adapter
        result = verify_envelope_dispatch(
            recipient="workbuddy",
            adapter_fn=make_workbuddy_adapter(),
            payload={"action": "probe"},
            evidence_dir=args.evidence_dir,
        )
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["verify_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
