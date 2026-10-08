#!/usr/bin/env python3
# v2/src/claude_adapter.py — real claude -p subprocess adapter for v2 consumer
from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
import time
from pathlib import Path

CLAUDE_CLI = Path(r"D:\npm-global\claude.ps1")


def _claude_dispatch_adapter(env: dict, *, recipient: str) -> dict:
    """For recipient=claudecode + message_type=task: spawn real `claude -p`.

    For other recipients/types: passthrough (echo only).
    Uses PowerShell -EncodedCommand to avoid quote-escaping issues.
    """
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
    # Build PS script that includes both the invocation AND the prompt as a
    # single script block, so -EncodedCommand does not collide with -args.
    ps_script = (
        "& 'D:\\npm-global\\claude.ps1' -p "
        + "'" + prompt.replace("'", "''") + "'"
        + " --add-dir '" + workdir + "'"
    )
    encoded = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
    start = time.time()
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-EncodedCommand", encoded],
            capture_output=True, timeout=300,
        )
        try:
            sout = r.stdout.decode("utf-8", errors="replace") if r.stdout else ""
            serr = r.stderr.decode("utf-8", errors="replace") if r.stderr else ""
            # PowerShell often emits GBK on Windows-cn hosts; try GBK if UTF-8 decode produced too many replacements
            if r.stdout and sout.count("�") > 4:
                try: sout = r.stdout.decode("gbk", errors="replace")
                except Exception: pass
        except Exception:
            sout = ""; serr = ""
        duration = int((time.time() - start) * 1000)
        return {
            "ok": r.returncode == 0,
            "transport": "claude_p_subprocess",
            "exit_code": r.returncode,
            "stdout_tail": (sout or "")[-1000:],
            "stderr_tail": (serr or "")[-500:],
            "duration_ms": duration,
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "transport": "claude_p_subprocess",
                "error": "timeout_300s", "duration_ms": 300000}
    except Exception as e:
        return {"ok": False, "transport": "claude_p_subprocess",
                "error": f"{type(e).__name__}: {e}"}


_claude_dispatch_adapter.__name__ = "claude_p_adapter"