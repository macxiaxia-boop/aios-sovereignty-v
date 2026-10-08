#!/usr/bin/env python3
# v2/src/claude_adapter.py — real claude -p subprocess adapter for v2 consumer
from __future__ import annotations

import base64
import json
import os
import subprocess
import time
from pathlib import Path

from .dispatch_runtime import run_subprocess_with_retry

CLAUDE_CLI = Path(r"D:\npm-global\claude.ps1")
DEFAULT_TIMEOUT_SEC = 300


def _claude_dispatch_adapter(env: dict, *, recipient: str) -> dict:
    """Spawn real ``claude -p`` with bounded concurrency and retry/backoff."""
    if env.get("recipient") != "claudecode" or env.get("message_type") != "task":
        return {
            "ok": True,
            "transport": "passthrough",
            "received_id": env.get("id"),
            "received_sender": env.get("sender"),
            "received_recipient": env.get("recipient"),
            "received_message_type": env.get("message_type"),
        }
    payload = env.get("payload", {})
    if not isinstance(payload, dict):
        payload = {"raw": str(payload)}
    workdir = payload.get("workdir") or payload.get("cwd") or r"D:\AIOS\_agent-hub\reports"
    task_lines = [f"{k}: {v}" for k, v in payload.items() if k not in ("workdir", "cwd")]
    if not task_lines:
        task_lines = [json.dumps(payload, ensure_ascii=False)]
    prompt = "\n".join([f"ENV_ID={env.get('id')}", f"SENDER={env.get('sender')}", ""] + task_lines)
    ps_script = (
        "& 'D:\\npm-global\\claude.ps1' -p "
        + "'" + prompt.replace("'", "''") + "'"
        + " --add-dir '" + workdir + "'"
    )
    encoded = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
    command = [
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-EncodedCommand", encoded,
    ]
    started = time.time()
    try:
        proc, retry = run_subprocess_with_retry(command, timeout=DEFAULT_TIMEOUT_SEC)
        try:
            sout = proc.stdout.decode("utf-8", errors="replace") if proc.stdout else ""
            serr = proc.stderr.decode("utf-8", errors="replace") if proc.stderr else ""
            if proc.stdout and sout.count("\ufffd") > 4:
                sout = proc.stdout.decode("gbk", errors="replace")
        except Exception:
            sout, serr = "", ""
        return {
            "ok": proc.returncode == 0,
            "transport": "claude_p_subprocess",
            "exit_code": proc.returncode,
            "stdout_tail": (sout or "")[-1000:],
            "stderr_tail": (serr or "")[-500:],
            "duration_ms": int((time.time() - started) * 1000),
            **retry,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "transport": "claude_p_subprocess",
            "error": f"timeout_{DEFAULT_TIMEOUT_SEC}s",
            "duration_ms": int((time.time() - started) * 1000),
            "attempts": 3,
        }
    except Exception as e:
        return {
            "ok": False,
            "transport": "claude_p_subprocess",
            "error": f"{type(e).__name__}: {e}",
            "duration_ms": int((time.time() - started) * 1000),
        }


_claude_dispatch_adapter.__name__ = "claude_p_adapter"
