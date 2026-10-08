#!/usr/bin/env python3
# v2/src/openclaw_adapter.py — real HTTP adapter for OpenClaw Gateway (port 18792)
#
# R339 follow-up · OpenClaw channel-gateway adapter.
# - Talks to http://127.0.0.1:18792 over plain HTTP (urllib stdlib, no extra deps)
# - Supported recipient=openclaw + message_type=task only
# - Action surface (real probes observed 2026-10-08):
#     payload.action == "health"   -> GET  /healthz   (returns JSON {"ok":true,...})
#     payload.action == "capabilities" -> GET  /capabilities (HTML control UI shell, NOT a JSON API)
#     payload.action == "ui"       -> GET  /          (HTML control UI)
#     payload.action == "dashboard"-> GET  /dashboard (HTML)
#     payload.action == "agents"   -> GET  /agents    (HTML)
#
# Honest assessment:
#   The OpenClaw HTTP server exposes only the control UI + /healthz.
#   It does NOT expose a JSON-RPC MCP tool execution endpoint over HTTP
#   (verified by probing /mcp, /sse, /jsonrpc, /v1/tools, /api/tools, /rpc
#   all return 404).  Tool execution happens via in-process MCP bridge
#   (port 18801 mcp_bridge, stdio-spawned).
#   Therefore: this adapter handles health + UI probes as real work;
#   for "task" dispatches that need tool execution we return ok=False with
#   transport="openclaw_blocked_no_jsonrpc" and the evidence URL the caller
#   can curl to verify.
#
# Compatible signature: fn(envelope, *, recipient) -> dict
from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .dispatch_runtime import RETRY_ATTEMPTS, http_slot, sleep_backoff

OPENCLAW_BASE = "http://127.0.0.1:18792"
DEFAULT_TIMEOUT_SEC = 15
ALLOWED_ACTIONS = {"health", "capabilities", "ui", "dashboard", "agents", "root", "tool", "mcp", "invoke", "openclaw_health", "aios_status"}


def _openclaw_dispatch_adapter(env: dict, *, recipient: str) -> dict:
    """Real OpenClaw HTTP adapter.

    Routing:
      recipient == "openclaw" AND message_type == "task" -> curl-style HTTP call
      everything else                                    -> passthrough echo
    """
    if env.get("recipient") != "openclaw" or env.get("message_type") != "task":
        return {
            "ok": True,
            "transport": "passthrough",
            "adapter": "openclaw",
            "received_id": env.get("id"),
            "received_sender": env.get("sender"),
            "received_recipient": env.get("recipient"),
            "received_message_type": env.get("message_type"),
        }

    payload = env.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {"raw": str(payload)}

    action = (payload.get("action") or "health").lower()
    if action in ("tool", "mcp", "invoke", "openclaw_health", "aios_status"):
        return _mcp_tool_call(payload, envelope_id=env.get("id"))
    if action not in ALLOWED_ACTIONS:
        action = "health"

    path = {
        "health": "/healthz",
        "capabilities": "/capabilities",
        "ui": "/",
        "dashboard": "/dashboard",
        "agents": "/agents",
        "root": "/",
    }[action]
    url = OPENCLAW_BASE + path
    method = (payload.get("method") or "GET").upper()
    if method not in ("GET", "HEAD"):
        method = "GET"

    return _http_call(
        url=url,
        method=method,
        envelope_id=env.get("id"),
        action=action,
        timeout=DEFAULT_TIMEOUT_SEC,
        extra_headers=payload.get("headers") or {},
    )


def _http_call_once(url: str, method: str, *, envelope_id, action: str,
                    timeout: float, extra_headers: Dict[str, str],
                    body: Optional[bytes] = None) -> dict:
    started = time.time()
    headers = {
        "Accept": "application/json, text/html;q=0.9, */*;q=0.5",
        "User-Agent": "aios-v2-openclaw-adapter/1.1",
        **extra_headers,
    }
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    transport = "openclaw_mcp" if action in ("tool", "mcp", "invoke") else "openclaw_http"
    try:
        with http_slot():
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body_bytes = resp.read()
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
        duration_ms = int((time.time() - started) * 1000)
        decoded = body_bytes[:12000].decode("utf-8", errors="replace")
        ok = 200 <= status < 300
        out: Dict[str, Any] = {
            "ok": ok,
            "transport": transport,
            "adapter": "openclaw",
            "envelope_id": envelope_id,
            "action": action,
            "url": url,
            "method": method,
            "status": status,
            "content_type": content_type,
            "duration_ms": duration_ms,
            "body_preview": decoded[:1200],
            "body_bytes": len(body_bytes),
            "dispatched_at": int(started),
        }
        if "json" in content_type.lower() or (decoded.startswith("{") and decoded.endswith("}")):
            try:
                out["body_json"] = json.loads(decoded)
            except Exception:
                pass
        return out
    except urllib.error.HTTPError as e:
        return {
            "ok": False, "transport": transport, "adapter": "openclaw",
            "envelope_id": envelope_id, "action": action, "url": url,
            "method": method, "status": e.code, "error": f"http_{e.code}",
            "duration_ms": int((time.time() - started) * 1000),
        }
    except urllib.error.URLError as e:
        return {
            "ok": False, "transport": transport, "adapter": "openclaw",
            "envelope_id": envelope_id, "action": action, "url": url,
            "method": method, "error": f"url_error:{e.reason}",
            "duration_ms": int((time.time() - started) * 1000),
        }
    except socket.timeout:
        return {
            "ok": False, "transport": transport, "adapter": "openclaw",
            "envelope_id": envelope_id, "action": action, "url": url,
            "method": method, "error": f"socket_timeout_{timeout}s",
            "duration_ms": int(timeout * 1000),
        }
    except Exception as e:
        return {
            "ok": False, "transport": transport, "adapter": "openclaw",
            "envelope_id": envelope_id, "action": action, "url": url,
            "method": method, "error": f"{type(e).__name__}: {e}",
            "duration_ms": int((time.time() - started) * 1000),
        }


def _http_call(url: str, method: str, *, envelope_id, action: str,
               timeout: float, extra_headers: Dict[str, str],
               body: Optional[bytes] = None) -> dict:
    """HTTP/MCP dispatch with 3 attempts and jittered 1/2/4s backoff."""
    started = time.time()
    delays: list[float] = []
    result: dict = {}
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        result = _http_call_once(
            url, method, envelope_id=envelope_id, action=action,
            timeout=timeout, extra_headers=extra_headers, body=body,
        )
        status = result.get("status")
        retryable = (
            result.get("ok") is not True
            and (status is None or status == 429 or status >= 500)
        )
        if not retryable or attempt >= RETRY_ATTEMPTS:
            result["attempts"] = attempt
            result["backoff_delays_ms"] = [round(delay * 1000) for delay in delays]
            result["duration_ms_total"] = int((time.time() - started) * 1000)
            return result
        delays.append(sleep_backoff(attempt))
    return result


def _mcp_tool_call(payload: dict, *, envelope_id) -> dict:
    """Call the real R307 MCP bridge: POST /mcp/<tool_name>."""
    tool = str(payload.get("tool") or "aios_status").strip()
    if not tool or "/" in tool or tool.startswith(".."):
        tool = "aios_status"
    args = payload.get("arguments")
    if not isinstance(args, dict):
        args = payload.get("params")
    if not isinstance(args, dict):
        args = {}
    body = json.dumps(args, ensure_ascii=False).encode("utf-8")
    base = os.environ.get("AIOS_OPENCLAW_MCP_BASE", "http://127.0.0.1:18801").rstrip("/")
    url = f"{base}/mcp/{tool}"
    result = _http_call(
        url, "POST", envelope_id=envelope_id, action="tool",
        timeout=DEFAULT_TIMEOUT_SEC,
        extra_headers={"Content-Type": "application/json"},
        body=body,
    )
    result["tool"] = tool
    result["arguments"] = args
    evidence_path = Path(
        os.environ.get(
            "AIOS_OPENCLAW_EVIDENCE_PATH",
            str(Path(__file__).resolve().parent.parent / "reports" / "openclaw_mcp_dispatch_evidence.json"),
        )
    )
    try:
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        result["evidence_path"] = str(evidence_path)
    except OSError as exc:
        result["evidence_error"] = f"{type(exc).__name__}: {exc}"
    return result


_openclaw_dispatch_adapter.__name__ = "openclaw_http_adapter"


def make_openclaw_adapter():
    """Factory so tests can do `set_dispatcher(make_openclaw_adapter())`."""
    return _openclaw_dispatch_adapter
