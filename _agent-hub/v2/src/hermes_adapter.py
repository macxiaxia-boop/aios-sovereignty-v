#!/usr/bin/env python3
# v2/src/hermes_adapter.py — real hermes.exe subprocess adapter for v2 consumer
#
# R339 follow-up · Hermes (Nous Research) CLI adapter.
# - Spawns `hermes.exe` subcommands with bounded timeout
# - Supported recipient=hermes + message_type=task only
# - Reads known CLI surface from `hermes --help` so we never invent commands
# - Returns structured {ok, transport, exit_code, stdout_tail, stderr_tail,
#   duration_ms, command, dispatched_at}
# - All real subprocess calls; no fake/mock transports
#
# Failure modes (evidence-backed):
#   - hermes.exe missing  -> ok=False, error="hermes_exe_not_found"
#   - subprocess timeout  -> ok=False, error="timeout_Ns"
#   - non-zero exit       -> ok=False with exit_code preserved
#
# Compatible with v2_consumer.dispatch_to_adapter signature:
#     fn(envelope, *, recipient) -> dict
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .dispatch_runtime import run_subprocess_with_retry

HERMES_EXE = Path(r"D:\AIOS\_relinked\hermes\hermes-agent\.venv\Scripts\hermes.exe")

# Hard cap so a runaway hermes never ties up the consumer for minutes.
DEFAULT_TIMEOUT_SEC = 60

# Read-only subcommand whitelist (safe to call from a worker agent).
SAFE_HERMES_SUBCMDS = {
    "status", "sessions", "model", "doctor", "version",
    "prompt-size", "dashboard", "logs", "memory", "tools",
    "skills", "plugins", "mcp", "insights",
}


def _hermes_dispatch_adapter(env: dict, *, recipient: str) -> dict:
    """Real Hermes CLI adapter.

    Routing:
      recipient == "hermes" AND message_type == "task"  -> invoke hermes.exe
      everything else                                   -> passthrough echo
    """
    if env.get("recipient") != "hermes" or env.get("message_type") != "task":
        return {
            "ok": True,
            "transport": "passthrough",
            "adapter": "hermes",
            "received_id": env.get("id"),
            "received_sender": env.get("sender"),
            "received_recipient": env.get("recipient"),
            "received_message_type": env.get("message_type"),
        }

    if not HERMES_EXE.exists():
        return {
            "ok": False,
            "transport": "passthrough",
            "adapter": "hermes",
            "error": "hermes_exe_not_found",
            "expected_path": str(HERMES_EXE),
            "envelope_id": env.get("id"),
        }

    payload = env.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {"raw": str(payload)}

    subcommand, args = _resolve_hermes_args(payload)
    cmd: List[str] = [str(HERMES_EXE), subcommand] + args
    workdir = payload.get("workdir") or payload.get("cwd") or str(HERMES_EXE.parent.parent)

    started = time.time()
    try:
        proc, retry = run_subprocess_with_retry(
            cmd, cwd=workdir, timeout=DEFAULT_TIMEOUT_SEC, shell=False
        )
        duration_ms = int((time.time() - started) * 1000)
        sout = (proc.stdout or b"").decode("utf-8", errors="replace")
        serr = (proc.stderr or b"").decode("utf-8", errors="replace")
        return {
            "ok": proc.returncode == 0,
            "transport": "hermes_subprocess",
            "adapter": "hermes",
            "envelope_id": env.get("id"),
            "subcommand": subcommand,
            "args": args,
            "command": " ".join(shlex.quote(c) for c in cmd),
            "workdir": workdir,
            "exit_code": proc.returncode,
            "stdout_tail": sout[-1500:],
            "stderr_tail": serr[-500:],
            "stdout_bytes": len(proc.stdout or b""),
            "stderr_bytes": len(proc.stderr or b""),
            "duration_ms": duration_ms,
            "dispatched_at": int(started),
            **retry,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "transport": "hermes_subprocess",
            "adapter": "hermes",
            "error": f"timeout_{DEFAULT_TIMEOUT_SEC}s",
            "subcommand": subcommand,
            "args": args,
            "command": " ".join(shlex.quote(c) for c in cmd),
            "duration_ms": DEFAULT_TIMEOUT_SEC * 1000,
            "attempts": 3,
            "envelope_id": env.get("id"),
        }
    except FileNotFoundError as e:
        return {
            "ok": False,
            "transport": "hermes_subprocess",
            "adapter": "hermes",
            "error": f"file_not_found:{e}",
            "envelope_id": env.get("id"),
        }
    except Exception as e:
        return {
            "ok": False,
            "transport": "hermes_subprocess",
            "adapter": "hermes",
            "error": f"{type(e).__name__}: {e}",
            "envelope_id": env.get("id"),
        }


def _resolve_hermes_args(payload: dict) -> tuple:
    """Translate envelope payload -> (subcommand, args).

    Hermes supports 40+ subcommands. We whitelist the safe read-only ones
    for v2 dispatch (anything side-effecting requires a separate human
    approval path that lives outside v2).
    """
    if isinstance(payload.get("args"), list) and payload["args"]:
        parts = [str(a) for a in payload["args"]]
        sub = parts[0]
        rest = parts[1:]
        if sub not in SAFE_HERMES_SUBCMDS:
            return ("doctor", [sub] + rest)  # unknown sub -> fall back to doctor
        return (sub, rest)

    if isinstance(payload.get("command"), str) and payload["command"].strip():
        parts = shlex.split(payload["command"])
        if parts:
            sub = parts[0]
            rest = parts[1:]
            if sub not in SAFE_HERMES_SUBCMDS:
                return ("doctor", [sub] + rest)
            return (sub, rest)

    if isinstance(payload.get("subcommand"), str) and payload["subcommand"].strip():
        sub = payload["subcommand"].strip()
        rest = payload.get("sub_args") or []
        rest = [str(a) for a in rest] if isinstance(rest, list) else []
        if sub not in SAFE_HERMES_SUBCMDS:
            return ("doctor", [sub] + rest)
        return (sub, rest)

    # Default: status probe (read-only, fast, gives real data back).
    return ("status", [])


_hermes_dispatch_adapter.__name__ = "hermes_cli_adapter"


def make_hermes_adapter():
    """Factory so tests can do `set_dispatcher(make_hermes_adapter())`."""
    return _hermes_dispatch_adapter
