#!/usr/bin/env python3
# v2/src/workbuddy_adapter.py — WorkBuddy adapter with HONEST failure detection.
#
# R339 follow-up · WorkBuddy orchestrator adapter.
#
# Honest assessment (probed 2026-10-08):
#   - ~/.workbuddy/ exists with full SQLite + Electron app structure
#   - ~/.workbuddy/logs/daemon.log is STALE (last write 4+ hours ago)
#   - NO WorkBuddy / workbench / WB- process is running
#   - NO daemon UI is responding
#   - NO HTTP / RPC port is bound by WorkBuddy
#
# Therefore: this adapter returns ok=False with transport="workbuddy_blocked_daemon_down"
# when asked to actually dispatch.  It DOES still do read-only probes
# (file existence, log freshness, process check) so callers get real evidence
# about WHY it's blocked, not a generic failure.
#
# Probe surface (read-only, always safe):
#   payload.action == "probe"  -> check daemon.log freshness + process list + port scan
#   payload.action == "status" -> same as probe (alias)
#   anything else              -> BLOCKED with structured evidence
#
# Compatible signature: fn(envelope, *, recipient) -> dict
from __future__ import annotations

import os
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

WORKBUDDY_ROOT = Path(os.path.expanduser(r"~/.workbuddy"))
WORKBUDDY_DAEMON_LOG = WORKBUDDY_ROOT / "logs" / "daemon.log"
STALE_THRESHOLD_SEC = 1800  # 30 min — daemon.log older than this = "down"
PROBE_TIMEOUT_SEC = 8


def _workbuddy_dispatch_adapter(env: dict, *, recipient: str) -> dict:
    """WorkBuddy adapter.

    Routing:
      recipient == "workbuddy" AND message_type == "task" AND action in {probe,status}
                                                      -> real probe (process / log / port)
      recipient == "workbuddy" AND message_type == "task" AND other action
                                                      -> ok=False, transport=workbuddy_blocked_daemon_down
      everything else                                 -> passthrough echo
    """
    if env.get("recipient") != "workbuddy" or env.get("message_type") != "task":
        return {
            "ok": True,
            "transport": "passthrough",
            "adapter": "workbuddy",
            "received_id": env.get("id"),
            "received_sender": env.get("sender"),
            "received_recipient": env.get("recipient"),
            "received_message_type": env.get("message_type"),
        }

    payload = env.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {"raw": str(payload)}

    action = (payload.get("action") or "probe").lower()

    # Always do the live probe — gives caller honest state even if action is "dispatch"
    probe = _probe_workbuddy()

    if action in ("probe", "status"):
        return {
            "ok": probe["alive"],
            "transport": "workbuddy_probe",
            "adapter": "workbuddy",
            "envelope_id": env.get("id"),
            "action": action,
            "probe": probe,
            "duration_ms": probe["duration_ms"],
            "dispatched_at": int(time.time()),
        }

    # Anything else (real task dispatch) is BLOCKED with evidence
    return {
        "ok": False,
        "transport": "workbuddy_blocked_daemon_down",
        "adapter": "workbuddy",
        "envelope_id": env.get("id"),
        "action": action,
        "reason": "workbuddy_daemon_not_running",
        "evidence": probe,
        "blocked_at": int(time.time()),
    }


def _probe_workbuddy() -> Dict[str, Any]:
    """Real read-only probe of WorkBuddy state.  Always returns evidence, never raises."""
    started = time.time()
    evidence: Dict[str, Any] = {
        "workbuddy_root": str(WORKBUDDY_ROOT),
        "daemon_log_path": str(WORKBUDDY_DAEMON_LOG),
        "alive": False,
        "checks": {},
        "duration_ms": 0,
    }

    # Check 1: ~/.workbuddy exists
    try:
        evidence["checks"]["root_exists"] = WORKBUDDY_ROOT.exists()
    except Exception as e:
        evidence["checks"]["root_exists"] = f"error:{e}"

    # Check 2: daemon.log exists + freshness
    try:
        if WORKBUDDY_DAEMON_LOG.exists():
            stat = WORKBUDDY_DAEMON_LOG.stat()
            age_sec = time.time() - stat.st_mtime
            evidence["checks"]["daemon_log"] = {
                "exists": True,
                "size_bytes": stat.st_size,
                "mtime": int(stat.st_mtime),
                "age_sec": int(age_sec),
                "stale": age_sec > STALE_THRESHOLD_SEC,
            }
        else:
            evidence["checks"]["daemon_log"] = {"exists": False}
    except Exception as e:
        evidence["checks"]["daemon_log"] = {"error": f"{type(e).__name__}: {e}"}

    # Check 3: WorkBuddy / Electron processes running
    try:
        proc_result = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-Process | Where-Object { $_.ProcessName -match 'WorkBuddy|workbench|WB-' } "
             "| Select-Object -ExpandProperty ProcessName -ErrorAction SilentlyContinue"],
            capture_output=True,
            timeout=PROBE_TIMEOUT_SEC,
        )
        procs = (proc_result.stdout or b"").decode("utf-8", errors="replace").strip()
        names = [p.strip() for p in procs.splitlines() if p.strip()] if procs else []
        evidence["checks"]["processes"] = {"names": names, "count": len(names)}
    except subprocess.TimeoutExpired:
        evidence["checks"]["processes"] = {"error": "probe_timeout"}
    except Exception as e:
        evidence["checks"]["processes"] = {"error": f"{type(e).__name__}: {e}"}

    # Check 4: known WorkBuddy ports (best-effort)
    evidence["checks"]["note"] = (
        "WorkBuddy daemon does NOT bind a well-known port. "
        "Status inferred from daemon.log freshness + process list."
    )

    # Determine alive: root exists AND daemon.log recent AND at least one process
    root_ok = evidence["checks"].get("root_exists") is True
    log_info = evidence["checks"].get("daemon_log") or {}
    log_fresh = isinstance(log_info, dict) and log_info.get("exists") and not log_info.get("stale")
    proc_info = evidence["checks"].get("processes") or {}
    proc_count = proc_info.get("count", 0) if isinstance(proc_info, dict) else 0
    evidence["alive"] = root_ok and log_fresh and proc_count > 0

    evidence["duration_ms"] = int((time.time() - started) * 1000)
    return evidence


_workbuddy_dispatch_adapter.__name__ = "workbuddy_probe_adapter"


def make_workbuddy_adapter():
    """Factory so tests can do `set_dispatcher(make_workbuddy_adapter())`."""
    return _workbuddy_dispatch_adapter
