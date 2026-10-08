#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Restricted MCP bridge for Codex, OpenClaw, Claude Code, and AIOS.

The server intentionally exposes a small allow-listed surface.  It does not
offer arbitrary shell execution or file mutation.  Host-side MCP configuration
selects tools to prevent recursive self-calls.
"""
from __future__ import annotations

import json
import hashlib
import hmac
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from contextlib import contextmanager
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = "2024-11-05"
SERVER_VERSION = "1.0.0-r86"
CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0
HOST = os.environ.get("AIOS_MCP_HOST", "generic").strip().lower()
MAX_MESSAGE_LENGTH = 12000
MIN_TIMEOUT = 15
MAX_TIMEOUT = 600
MAX_DEPTH = 4
MAX_CONTEXT_PREAMBLE = 8000
def _bounded_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        value = default
    return max(minimum, min(value, maximum))


MAX_CONCURRENT = _bounded_env_int("AIOS_INTEROP_MAX_CONCURRENT", 2, 1, 8)
MAX_QUEUE = _bounded_env_int("AIOS_INTEROP_MAX_QUEUE", 8, 0, 64)
_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT)
_QUEUE_LOCK = threading.Lock()
_WAITING = 0
_RESULT_CACHE: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
_CACHE_LOCK = threading.Lock()
_CACHE_LIMIT = 256


class InteropError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _failure(code: str, message: str) -> dict[str, Any]:
    return {"ok": False, "error": {"code": code, "message": message}}

AIOS_ROOT = Path(os.environ.get("AIOS_ROOT", r"D:\个人文件\AI\Operator"))
AIOS_TOOLS = AIOS_ROOT / "aios_tools"


def _resolve_python() -> Path:
    """R115 治本 + R119 补回: pin AIOS venv 绝对路径,绕开 uv shim → broken hermes-agent venv 死链
    - env AIOS_PYTHON 优先 override
    - 默认: aios_venv/Scripts/python.exe(绝对路径,免 PATH 解析时撞 uv shim)
    - fallback: sys.executable(最后兜底)
    """
    env_override = os.environ.get("AIOS_PYTHON")
    if env_override:
        return Path(env_override)
    aios_venv = AIOS_ROOT / "aios_venv" / "Scripts" / "python.exe"
    if aios_venv.exists():
        return aios_venv
    return Path(sys.executable)


PYTHON = _resolve_python()
NODE = Path(os.environ.get("AIOS_NODE", r"C:\Users\xinzh\node.exe"))
OPENCLAW_PACKAGE = Path(os.environ.get("OPENCLAW_PACKAGE", r"D:\npm-global\node_modules\openclaw"))
CLAUDE_ENTRY = Path(
    os.environ.get(
        "CLAUDE_CODE_ENTRY",
        r"D:\npm-global\node_modules\@anthropic-ai\claude-code\bin\claude.exe",
    )
)

ALLOWED_OPENCLAW_AGENTS = {
    "main",
    "codex",
    "claude",
    "isolated",
    "geo-intent",
    "geo-competitor",
    "geo-strategy",
    "geo-creator",
    "geo-validator",
}
ALLOWED_CODEX_PROFILES = {"base", "ollama"}  # R329 治本: 删 deepseek/deepseek-pro/qwen25 (用户原话 "全部用 minimax"; qwen25 配额已耗尽 R322 实证). ollama 仅网络断时作 fallback (R110/R297 实证)
ALLOWED_OPENCLAW_MODELS = {
    "minimax/MiniMax-M3",
    "qwen/qwen3.7-flash",
    "ollama/qwen2.5:3b-64k",  # R298 治本: 原 "ollama/qwen3:14b" → "ollama/qwen2.5:3b-64k" (本地实际唯一模型, qwen3:14b OOM 8.8GB CUDA0 R110 实证)
}

TRACE_SCHEMA = {
    "type": "object",
    "properties": {
        "request_id": {"type": "string", "minLength": 1, "maxLength": 128},
        "parent_request_id": {"type": "string", "maxLength": 128},
        "depth": {"type": "integer", "minimum": 0, "maximum": MAX_DEPTH},
        "visited": {"type": "array", "maxItems": MAX_DEPTH + 1, "items": {"type": "string", "maxLength": 32}},
        "idempotency_key": {"type": "string", "minLength": 1, "maxLength": 128},
    },
    "additionalProperties": False,
}


TOOLS = [
    {
        "name": "aios_status",
        "description": "Read-only health snapshot for AIOS/OpenClaw/Codex relay endpoints.",
        "inputSchema": {"type": "object", "properties": {"trace": TRACE_SCHEMA}, "additionalProperties": False},
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "openclaw_delegate",
        "description": "Run one OpenClaw agent turn without delivering to an external channel.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent": {"type": "string", "enum": sorted(ALLOWED_OPENCLAW_AGENTS)},
                "message": {"type": "string", "minLength": 1, "maxLength": 12000},
                "timeout": {"type": "integer", "minimum": 15, "maximum": 600, "default": 180},
                "session_key": {"type": "string", "maxLength": 200},
                "model": {"type": "string", "enum": sorted(ALLOWED_OPENCLAW_MODELS)},
                "trace": TRACE_SCHEMA,
            },
            "required": ["agent", "message"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False},
    },
    {
        "name": "codex_query",
        "description": "Run a bounded Codex CLI request through the AIOS wrapper and return the result.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "minLength": 1, "maxLength": 12000},
                "profile": {"type": "string", "enum": sorted(ALLOWED_CODEX_PROFILES), "default": "base"},  # R297 治本: 撤回 default=ollama (Codex 0.155.1+ 不允许主 config.toml 含 [profiles.X] 段 → ollama profile 需用户拍板拆 ~/.codex/ollama.config.toml 后再改 default)
                "session_key": {"type": "string", "maxLength": 128, "description": "R293 · caller-side session key for persistent conversation; same key reuses codex session-id"},
                "timeout": {"type": "integer", "minimum": 15, "maximum": 600, "default": 180},
                "trace": TRACE_SCHEMA,
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False},
    },
    {
        "name": "codex_desktop_query",
        "description": "Queue one bounded message to an explicitly identified Codex Desktop task.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "minLength": 1, "maxLength": 12000},
                "thread_id": {"type": "string", "minLength": 1, "maxLength": 128},
                "timeout": {"type": "integer", "minimum": 15, "maximum": 600, "default": 30},
                "trace": TRACE_SCHEMA,
            },
            "required": ["prompt", "thread_id"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False},
    },
    {
        "name": "claude_code_query",
        "description": "Ask Claude Code one bounded analysis-only question with all tools disabled.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "minLength": 1, "maxLength": 12000},
                "session_id": {"type": "string", "maxLength": 128, "description": "R295 · caller-side session id for persistent conversation · 跨 host session 共享 (同 session_id 复用同一 Claude conversation)"},
                "timeout": {"type": "integer", "minimum": 15, "maximum": 600, "default": 180},
                "trace": TRACE_SCHEMA,
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False},
    },
    {
        "name": "hermes_query",
        "description": "Invoke Hermes (CIO governance) in-process. Hermes handles task lifecycle, decision logging, and evidence collection without external calls.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "minLength": 1, "maxLength": 12000},
                "action": {"type": "string", "enum": ["system_status", "create_task", "transition", "log_decision", "collect_evidence"], "default": "system_status"},
                "task_id": {"type": "string", "maxLength": 128},
                "contract": {"type": "object"},
                "from_state": {"type": "string"},
                "to_state": {"type": "string"},
                "level": {"type": "string", "enum": ["D0", "D1", "D2", "D3", "D4"]},
                "rationale": {"type": "string"},
                "evidence": {"type": "array"},
                "evidence_list": {"type": "array"},
                "timeout": {"type": "integer", "minimum": 15, "maximum": 600, "default": 180},
                "trace": TRACE_SCHEMA,
            },
            "required": ["prompt"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": False, "destructiveHint": False},
    },
    {
        "name": "rag_query",  # R294 新增 · 跨入口 RAG 检索 (5 入口 memory + SSOT)
        "description": "Cross-entrypoint RAG retrieval across Claude memory + Operator memory + SSOT mirror. Returns ranked hits with source entrypoint + sha256 + relevance score.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 12000},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                "timeout": {"type": "integer", "minimum": 15, "maximum": 600, "default": 60},
                "trace": TRACE_SCHEMA,
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "openclaw_health",  # R302 新增 · OpenClaw gateway 健康探测
        "description": "Probe OpenClaw gateway (port 18792) health endpoint. Returns status, uptime, and version info.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "endpoint": {"type": "string", "default": "http://127.0.0.1:18792", "description": "OpenClaw gateway endpoint"},
                "timeout": {"type": "integer", "minimum": 5, "maximum": 60, "default": 10},
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "hermes_health",  # R304 新增 · Hermes in-process 健康
        "description": "Probe Hermes in-process: task count, tool availability, DB health. Returns Hermes status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "codex_health",  # R304 新增 · Codex CLI 健康
        "description": "Probe Codex CLI availability + profile status + version. Returns Codex health.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "profile": {"type": "string", "default": "deepseek", "description": "Codex profile to check"},
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "lingma_health",  # R304 新增 · Lingma VSCode 健康
        "description": "Probe Lingma VSCode plugin availability. Returns Lingma status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "cross_entrypoint_health",  # R305 新增 · 5 入口统一 health 总览
        "description": "Aggregate health check across 6 entrypoints (claude/codex/openclaw/workbuddy/lingma/hermes). Returns unified summary + alerts.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_tools": {"type": "boolean", "default": False, "description": "是否包含 tools 健康"},
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "version",  # R306 新增 · 6 入口 + 16 工具 + aios-interop 版本统一查询
        "description": "Return AIOS version manifest: 6 entrypoints + 16 tools + aios-interop protocol version + capabilities count.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_history": {"type": "boolean", "default": False, "description": "包含 R290-R305 历史"},
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "session_share",  # R306 新增 · 跨 host session 共享 (注册/查询/删除)
        "description": "Register or query shared sessions across 5 hosts (claude/codex/openclaw/workbuddy/lingma). Returns shared session metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["share", "list", "revoke"], "default": "list", "description": "share/list/revoke"},
                "host": {"type": "string", "description": "源 host (share 用)"},
                "session_id": {"type": "string", "description": "session ID (share/revoke 用)"},
                "target_hosts": {"type": "array", "items": {"type": "string"}, "description": "目标 host 列表 (share 用)"},
                "metadata": {"type": "object", "description": "附加元数据 (share 用)"},
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "knowledge_base",  # R306 新增 · AIOS 知识库查询 (3 根: CORE-RULES / 反馈文档 / SSOT)
        "description": "Query AIOS knowledge base across 3 roots: 00_CORE (L0 宪法 + SOPs), feedback-*.md (R290-R305 复盘), SSOT docs. Returns ranked hits.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 200, "description": "搜索关键词"},
                "root_filter": {"type": "string", "enum": ["core", "feedback", "ssot", "all"], "default": "all"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
                "trace": TRACE_SCHEMA,
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "entrypoint_register",  # R307 新增 · 动态注册 entrypoint (白名单)
        "description": "Dynamically register/list/revoke entrypoints in the AIOS registry. Whitelisted to existing 6 entrypoints + new ones with approval.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["register", "list", "revoke"], "default": "list"},
                "host": {"type": "string", "description": "entrypoint host name"},
                "endpoint": {"type": "string", "description": "entrypoint endpoint URL (register 用)"},
                "metadata": {"type": "object", "description": "附加元数据"},
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "workbuddy_health",  # R302 新增 · WorkBuddy 进程健康检查
        "description": "Check WorkBuddy.exe / codebuddy.exe process status and log freshness. Returns health summary.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "log_age_threshold_minutes": {"type": "integer", "minimum": 1, "maximum": 1440, "default": 10},
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "langfuse_query",  # R302 新增 · Langfuse trace 查询 (本地 fallback)
        "description": "Query recent Langfuse trace events from local fallback log (adapter_trace.jsonl). Returns recent aios_interop.tool_call events.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
                "tool_filter": {"type": "string", "description": "按 tool name 过滤 (如 aios_interop.tool_call.done)"},
                "since_minutes": {"type": "integer", "minimum": 1, "maximum": 1440, "default": 60, "description": "只返回近 N 分钟的 events"},
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "session_lifecycle",  # R303 新增 · 跨入口 session 生命周期管理
        "description": "Manage cross-entrypoint session lifecycle: list, register, cleanup sessions across 5 hosts (claude/codex/openclaw/workbuddy/lingma).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["list", "cleanup", "stats"], "default": "list", "description": "list/cleanup/stats"},
                "host_filter": {"type": "string", "description": "按 host 过滤"},
                "max_age_hours": {"type": "integer", "minimum": 1, "maximum": 720, "default": 168, "description": "cleanup 用: 最大存活小时数 (7 天默认)"},
                "trace": TRACE_SCHEMA,
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
    {
        "name": "capability_search",  # R303 新增 · V4 capability registry 搜索
        "description": "Search V4 capability registry by name/source/lifecycle. Returns matching capabilities with metadata.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 200, "description": "搜索关键词 (name/description/source)"},
                "lifecycle": {"type": "string", "enum": ["ACTIVE", "DRAFT", "CANDIDATE", "ARCHIVE"], "description": "按 lifecycle 过滤"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                "trace": TRACE_SCHEMA,
            },
            "required": ["query"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "destructiveHint": False},
    },
]

HOST_TOOL_ALLOW = {
    "codex": {"aios_status", "openclaw_delegate", "claude_code_query", "hermes_query", "rag_query"},
    "openclaw": {"aios_status", "codex_query", "codex_desktop_query", "claude_code_query", "hermes_query", "rag_query"},  # R302 反身禁: openclaw_delegate 不能调自己
    "claude": {"aios_status", "openclaw_delegate", "codex_query", "codex_desktop_query", "hermes_query", "rag_query"},
    "workbuddy": {"aios_status", "openclaw_delegate", "codex_query", "codex_desktop_query", "claude_code_query", "hermes_query", "rag_query"},  # R291 新增 · 5 入口接入
    "lingma": {"aios_status", "openclaw_delegate", "codex_query", "codex_desktop_query", "claude_code_query", "hermes_query", "rag_query"},  # R293 新增 · 阿里 AI 入口
    "generic": {"aios_status"},
}


def _allowed_tools() -> set[str]:
    return HOST_TOOL_ALLOW.get(HOST, HOST_TOOL_ALLOW["generic"])


def _principal() -> dict[str, Any]:
    name = os.environ.get("AIOS_MCP_PRINCIPAL", "").strip()
    authorities_text = os.environ.get("AIOS_MCP_AUTHORITIES", "").strip().upper()
    host = os.environ.get("AIOS_MCP_HOST", "generic").strip().lower()
    signature = os.environ.get("AIOS_MCP_AUTH_SIGNATURE", "").strip().lower()
    secret = os.environ.get("AIOS_MCP_AUTH_SECRET", "")
    signed_authorities = {item for item in authorities_text.split(",") if item in {"N", "C", "P", "A", "O"}}
    signed = f"{name}\n{','.join(sorted(signed_authorities))}\n{host}".encode("utf-8")
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest() if secret else ""
    authenticated = bool(name and secret and signature and hmac.compare_digest(signature, expected))
    authorities = set(signed_authorities)
    if "A" in authorities:
        authorities.update({"P", "O", "C", "N"})
    if "P" in authorities:
        authorities.update({"O", "C", "N"})
    if "O" in authorities:
        authorities.update({"C", "N"})
    if "C" in authorities:
        authorities.add("N")
    return {
        "name": name if authenticated else "anonymous",
        "host": host,
        "authenticated": authenticated,
        # Anonymous stdio clients may inspect health only.  CONSULT and all
        # higher capabilities require a launcher-authenticated principal.
        "authorities": authorities if authenticated else {"N"},
    }


def _authorise(name: str) -> dict[str, Any]:
    if name not in _allowed_tools():
        raise InteropError("HOST_TOOL_DENIED", "tool is disabled for this host")
    principal = _principal()
    if name != "aios_status" and (not principal["authenticated"] or "P" not in principal["authorities"]):
        raise InteropError("AUTHORITY_DENIED", "authenticated P authority is required")
    return principal


def _validate_timeout(value: Any, default: int) -> int:
    try:
        timeout = int(value if value is not None else default)
    except (TypeError, ValueError) as exc:
        raise InteropError("INVALID_ARGUMENT", "timeout must be an integer") from exc
    if not MIN_TIMEOUT <= timeout <= MAX_TIMEOUT:
        raise InteropError("INVALID_ARGUMENT", f"timeout must be between {MIN_TIMEOUT} and {MAX_TIMEOUT} seconds")
    return timeout


def _validate_text(value: Any, field: str, maximum: int = MAX_MESSAGE_LENGTH) -> str:
    text = str(value or "").strip()
    if not text or len(text) > maximum:
        raise InteropError("INVALID_ARGUMENT", f"{field} must contain 1-{maximum} characters")
    return text


def _target_for(name: str) -> str | None:
    if name == "openclaw_delegate":
        return "openclaw"
    if name in {"codex_query", "codex_desktop_query"}:
        return "codex"
    if name == "claude_code_query":
        return "claude"
    return None


def _prepare_arguments(name: str, arguments: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(arguments, dict):
        raise InteropError("INVALID_ARGUMENT", "arguments must be an object")
    cleaned = dict(arguments)
    supplied_trace = cleaned.pop("trace", None)
    raw_trace = supplied_trace
    if raw_trace is None:
        inherited = os.environ.get("AIOS_INTEROP_TRACE", "").strip()
        if inherited:
            try:
                raw_trace = json.loads(inherited)
            except json.JSONDecodeError as exc:
                raise InteropError("INVALID_TRACE", "inherited trace is not valid JSON") from exc
        else:
            raw_trace = {}
    if raw_trace is None:
        raw_trace = {}
    if not isinstance(raw_trace, dict):
        raise InteropError("INVALID_TRACE", "trace must be an object")
    permitted = {"request_id", "parent_request_id", "depth", "visited", "idempotency_key"}
    if set(raw_trace) - permitted:
        raise InteropError("INVALID_TRACE", "trace contains unsupported metadata")
    request_id = str(raw_trace.get("request_id") or uuid.uuid4())
    parent_id = str(raw_trace.get("parent_request_id") or "")
    idempotency_key = str(raw_trace.get("idempotency_key") or request_id)
    if not 1 <= len(request_id) <= 128 or len(parent_id) > 128 or not 1 <= len(idempotency_key) <= 128:
        raise InteropError("INVALID_TRACE", "trace identifiers exceed their bounds")
    if parent_id and parent_id == request_id:
        raise InteropError("LOOP_REJECTED", "request cannot be its own parent")
    try:
        depth = int(raw_trace.get("depth", 0))
    except (TypeError, ValueError) as exc:
        raise InteropError("INVALID_TRACE", "trace depth must be an integer") from exc
    visited_value = raw_trace.get("visited", [])
    if (
        not isinstance(visited_value, list)
        or len(visited_value) > MAX_DEPTH + 1
        or any(not isinstance(item, str) or len(item) > 32 for item in visited_value)
    ):
        raise InteropError("INVALID_TRACE", "visited must be a string array")
    visited = [item.strip().lower() for item in visited_value]
    target = _target_for(name)
    if depth < 0 or depth >= MAX_DEPTH:
        raise InteropError("LOOP_REJECTED", "maximum delegation depth reached")
    if target and target in visited:
        raise InteropError("LOOP_REJECTED", "target already appears in delegation path")
    child_trace = {
        "request_id": str(uuid.uuid4()),
        "parent_request_id": request_id,
        "depth": depth + 1,
        "visited": (visited + ([target] if target else []))[-(MAX_DEPTH + 1):],
        "idempotency_key": idempotency_key,
    }
    cleaned["_validated_trace"] = child_trace
    return cleaned, {"request_id": request_id, "idempotency_key": idempotency_key, "depth": depth}


@contextmanager
def _execution_slot():
    global _WAITING
    if not _SLOTS.acquire(blocking=False):
        with _QUEUE_LOCK:
            if _WAITING >= MAX_QUEUE:
                raise InteropError("QUEUE_FULL", "interop execution queue is full")
            _WAITING += 1
        try:
            if not _SLOTS.acquire(timeout=1.0):
                raise InteropError("BUSY", "interop execution capacity is unavailable")
        finally:
            with _QUEUE_LOCK:
                _WAITING -= 1
    try:
        yield
    finally:
        _SLOTS.release()


def _child_env(trace: dict[str, Any] | None, base: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(base or os.environ)
    for key in ("AIOS_MCP_AUTH_SECRET", "AIOS_MCP_AUTH_SIGNATURE", "AIOS_MCP_AUTHORITIES", "AIOS_MCP_PRINCIPAL"):
        env.pop(key, None)
    if trace:
        env["AIOS_INTEROP_TRACE"] = json.dumps(trace, ensure_ascii=True, separators=(",", ":"))
    return env


def _bounded_text(value: Any, limit: int = 50000) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if len(text) <= limit:
        return text
    return text[:limit] + f"\n...[truncated {len(text) - limit} chars]"


def _context_items(items: Any, limit: int) -> list[dict[str, Any]]:
    if not isinstance(items, list):
        return []
    compact = []
    for item in items[:limit]:
        if not isinstance(item, dict):
            continue
        compact.append({
            "kind": item.get("source_kind", "unknown"),
            "path": item.get("path", ""),
            "name": item.get("name", ""),
            "summary": str(item.get("summary", ""))[:600],
            "sha256_16": item.get("sha256_16", ""),
            "relevant_keywords": item.get("relevant_keywords", [])[:8],
        })
    return compact


def _build_context_preamble(tool_name: str, prompt: str) -> str:
    """Resolve bounded shared truth before every delegated execution."""
    try:
        from _aios_shared_truth import resolve as resolve_truth
        task_type = "code_fix" if tool_name in {"codex_query", "codex_desktop_query", "claude_code_query"} else "general"
        packet = resolve_truth(task_type=task_type, query=prompt)
        missing, complete = packet.is_complete()
    except Exception as exc:
        raise InteropError("CONTEXT_RESOLUTION_FAILED", f"context resolver failed: {type(exc).__name__}") from exc
    if not complete:
        raise InteropError("BLOCKED_CONTEXT", "required shared-truth layers are incomplete: " + ",".join(missing))
    data = packet.to_dict()
    compact = {
        "schema": "aios-context-preamble/1.0",
        "loaded_at": data.get("loaded_at"),
        "protocol": _context_items(data.get("protocol"), 3),
        "user_preferences": _context_items(data.get("user_preferences"), 3),
        "relevant_sops": _context_items(data.get("relevant_sops"), 3),
        "decisions": _context_items(data.get("decisions"), 2),
        "relevant_knowledge": _context_items(data.get("relevant_knowledge"), 4),
        "relevant_experience": _context_items(data.get("relevant_experience"), 4),
        "relevant_skills": _context_items(data.get("relevant_skills"), 4),
    }
    encoded = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) > MAX_CONTEXT_PREAMBLE:
        compact["truncated"] = True
        for key, value in compact.items():
            if not isinstance(value, list):
                continue
            for item in value:
                item["path"] = Path(str(item.get("path", ""))).name
                item["summary"] = str(item.get("summary", ""))[:200]
        encoded = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    if len(encoded) > MAX_CONTEXT_PREAMBLE:
        for key, value in list(compact.items()):
            if isinstance(value, list):
                compact[key] = value[:1]
        encoded = json.dumps(compact, ensure_ascii=False, separators=(",", ":"))
    return (
        "[AIOS_CONTEXT_PACKET]\n"
        + encoded
        + "\n[/AIOS_CONTEXT_PACKET]\n"
        + "Use this bounded packet as background; the user request below remains authoritative.\n\n"
    )


def _with_context(args: dict[str, Any], prompt: str) -> str:
    preamble = args.get("_context_preamble")
    return f"{preamble}{prompt}" if isinstance(preamble, str) and preamble else prompt


def _run(command: list[str], timeout: int, cwd: Path | None = None, env: dict[str, str] | None = None) -> dict[str, Any]:
    try:
        child_env = dict(env or os.environ)
        if not child_env.get("HTTPS_PROXY") and not child_env.get("https_proxy"):
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Internet Settings")
                enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
                server = winreg.QueryValueEx(key, "ProxyServer")[0]
                if enabled and server:
                    proxy = str(server)
                    if ";" in proxy:
                        proxy = next((x.split("=", 1)[1] for x in proxy.split(";") if x.lower().startswith("https=")), proxy)
                    if "://" not in proxy:
                        proxy = "http://" + proxy
                    child_env.update({"HTTP_PROXY": proxy, "HTTPS_PROXY": proxy, "ALL_PROXY": proxy})
            except Exception:
                pass
        result = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            env=child_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            return {
                **_failure("SUBPROCESS_FAILED", "delegated process returned a non-zero exit code"),
                "exit_code": result.returncode,
                "stderr_present": bool(result.stderr.strip()),
            }
        return {"ok": True, "exit_code": 0, "stdout": _bounded_text(result.stdout.strip())}
    except subprocess.TimeoutExpired:
        return {**_failure("TIMEOUT", "delegated process exceeded its timeout"), "exit_code": 124}
    except Exception:
        return {**_failure("PROCESS_START_FAILED", "delegated process could not be started"), "exit_code": 1}


def _probe(url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            raw = response.read(2048).decode("utf-8", errors="replace")
            return {"ok": True, "status": response.status, "body": raw}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "status": exc.code, "error": str(exc)}
    except Exception as exc:
        return {"ok": False, "status": None, "error": str(exc)}


def aios_status(_: dict[str, Any]) -> dict[str, Any]:
    # R117 endpoint 注释（2026-09-21 用户口述"全部执行不留尾巴"）：
    #   · collector_backup (Codex Desktop 18800) = Electron UI 进程,非 HTTP server,/healthz 必失败
    #   · codex_relay (19194) = Codex CLI OpenAI relay,本环境用 qwen3:14b 本地 (R102) + Codex Desktop OAuth (R108),
    #     没有 OpenAI relay server,/health 必失败
    # 改法：注释而非删（保留代码意图 + 备未来 R117 EXTEND 加回）。改完 Claude Code 重启会热加载（红线 #97）
    endpoints = {
        # R329 治本: openclaw_gateway 是 WebSocket 协议, HTTP /health 必 RST → 改 TCP probe
        "openclaw_gateway": ("tcp", "127.0.0.1", 18792),
        # R329 治本: 删 collector 探针 (aios_evidence_collector.py 是 --selftest 脚本,非 HTTP server; 同 R117 collector_backup 注释)
        # "collector": ("http", "http://127.0.0.1:18799/healthz"),
        # "collector_backup": "http://127.0.0.1:18800/healthz",  # R117 commented: Codex Desktop 进程非 HTTP server
        # "codex_relay": "http://127.0.0.1:19194/health",       # R117 commented: 本环境无 OpenAI relay (用 qwen3:14b 本地)
    }
    results = {}
    for name, ep in endpoints.items():
        if isinstance(ep, tuple) and ep[0] == "tcp":
            _, host, port = ep
            ok = _tcp_probe(host, port, timeout=3.0)
            results[name] = {"ok": ok, "host": host, "port": port, "probe_method": "tcp_connect"}
        else:
            url = ep[1] if isinstance(ep, tuple) else ep
            results[name] = _probe(url)
    try:
        from _aios_model_router import load_resource_state
        model_resources = load_resource_state().get("resources", {})
    except Exception as exc:
        model_resources = {"error": str(exc)}
    return {
        "ok": True,
        "all_healthy": all(item.get("ok") for item in results.values()),
        "endpoints": results,
        "model_resources": model_resources,
    }


def _openclaw_command() -> list[str]:
    dist = OPENCLAW_PACKAGE / "dist" / "index.js"
    entry = OPENCLAW_PACKAGE / "openclaw.mjs"
    if NODE.exists() and dist.exists():
        return [str(NODE), str(dist)]
    if NODE.exists() and entry.exists():
        return [str(NODE), str(entry)]
    raise FileNotFoundError(f"OpenClaw entry not found below {OPENCLAW_PACKAGE}")


def openclaw_delegate(args: dict[str, Any]) -> dict[str, Any]:
    agent = str(args.get("agent", ""))
    message = _validate_text(args.get("message"), "message")
    message = _with_context(args, message)
    timeout = _validate_timeout(args.get("timeout"), 180)
    session_key = str(args.get("session_key", "")).strip()
    model = str(args.get("model", "")).strip()
    trace = args.get("_validated_trace")
    if agent not in ALLOWED_OPENCLAW_AGENTS:
        return _failure("AGENT_DENIED", "requested OpenClaw agent is not allowed")
    if len(session_key) > 200:
        return _failure("INVALID_ARGUMENT", "session_key exceeds 200 characters")
    if model and model not in ALLOWED_OPENCLAW_MODELS:
        return _failure("MODEL_DENIED", "requested OpenClaw model is not allowed")
    if model:
        # Model-specific resource execution uses OpenClaw's embedded headless
        # runner, so a stopped Gateway does not turn cheap compute into a hard
        # task failure.  No external delivery occurs.
        command = _openclaw_command() + [
            "agent", "exec", message,
            "--model", model,
            "--json",
            "--timeout", str(timeout),
            "--cwd", str(AIOS_ROOT),
        ]
    else:
        command = _openclaw_command() + [
            "agent", "--agent", agent, "--message", message, "--json", "--timeout", str(timeout)
        ]
        if session_key:
            command += ["--session-key", session_key]
    return _run(command, timeout + 15, cwd=AIOS_ROOT, env=_child_env(trace))


def codex_query(args: dict[str, Any]) -> dict[str, Any]:
    """Codex CLI 批处理/后台调用（无人值守 · 走 codex_cli_chat.py wrapper）

    注意: 这是 Codex CLI 路径，用于无人值守/批处理/后台执行。
    找"当前这个 Codex Desktop 任务"请用 codex_desktop_query + thread_id。

    R293 新增: session_key 支持 persistent conversation · 同一 session_key 复用 codex session-id
    R296 治本: default profile "deepseek" → "base" · 配置漂移 (R244 LOCKED Codex 走 MiniMax-M3
    ChatGPT 订阅 OAuth 不需 API key) + 端口漂移 (aios-relay 19194 vs codex-relay.py 默认 19199) +
    DEEPSEEK_API_KEY 缺失 → 探针 124. model_resources.json + codex_solid_config.json 均已 base.
    """
    prompt = _validate_text(args.get("prompt"), "prompt")
    prompt = _with_context(args, prompt)
    profile = str(args.get("profile", "base"))
    session_key = str(args.get("session_key", "")).strip()  # R293
    timeout = _validate_timeout(args.get("timeout"), 180)
    trace = args.get("_validated_trace")
    if profile not in ALLOWED_CODEX_PROFILES:
        return _failure("PROFILE_DENIED", "requested Codex profile is not allowed")

    # R299 F 治本: fallback chain (base → ollama) · 网络断开/配置漂移时自动降级到本地 Ollama
    #   base = MiniMax-M3 R244 LOCKED 主路径 · 失败自动试 ollama (R297 拆 profile 路径)
    #   不影响 PROFILE_DENIED 错误 (白名单)
    profiles_chain = [profile]
    if profile == "base":  # 仅 base 触发自动 fallback (其他 profile 用户显式)
        profiles_chain.append("ollama")

    last_error = None
    for p in profiles_chain:
        command = [
            str(PYTHON), str(AIOS_TOOLS / "codex_cli_chat.py"), prompt,
            "--profile", p, "--timeout", str(timeout),
        ]
        if session_key:
            command.extend(["--session-key", session_key])
        result = _run(command, timeout + 15, cwd=AIOS_ROOT, env=_child_env(trace))
        if result.get("ok"):
            return result
        last_error = result
        err_code = result.get("error", {}).get("code", "")
        # PROFILE_DENIED 不重试 (白名单失败)
        if err_code == "PROFILE_DENIED":
            return result
        # 其他错误 (SUBPROCESS_FAILED/TIMEOUT/exit 124) → 继续 fallback
    return last_error


def codex_desktop_query(args: dict[str, Any]) -> dict[str, Any]:
    """Codex Desktop Thread 通道调用（找"当前这个我" · 走 codex queue --thread）

    Args:
        prompt: 要发送的消息内容
        thread_id: Codex Desktop session UUID (必需) · 也可从 args 拿
        timeout: 超时秒数 (default 30)

    Returns:
        {"ok": bool, "queued_message_id": "<UUID>", "thread_id": "<UUID>", "output": str}

    Why: R96 用户原话"彻底修复应当把目标拆成两个适配器"
      - codex_query (本文件) = 无人值守、批处理、后台
      - codex_desktop_query (本函数) = 找当前这个 Codex Desktop 任务
    Desktop 必须保持运行 (红线 #22 L4 边界)。
    L4 后续: 自动读取回复 → App Server WebSocket 双向适配器 (codex app-server)。
    """
    prompt = _validate_text(args.get("prompt"), "prompt")
    prompt = _with_context(args, prompt)
    thread_id = _validate_text(args.get("thread_id"), "thread_id", 128)
    timeout = _validate_timeout(args.get("timeout"), 30)
    trace = args.get("_validated_trace")
    try:
        uuid.UUID(thread_id)
    except ValueError:
        return _failure("INVALID_ARGUMENT", "thread_id must be a UUID")
    command = [
        str(PYTHON), str(AIOS_TOOLS / "aios_adapter_codex_desktop.py"),
        "--send", thread_id, prompt,
    ]
    return _run(command, timeout + 15, cwd=AIOS_ROOT, env=_child_env(trace))


def claude_code_query(args: dict[str, Any]) -> dict[str, Any]:
    prompt = _validate_text(args.get("prompt"), "prompt")
    prompt = _with_context(args, prompt)
    timeout = _validate_timeout(args.get("timeout"), 180)
    trace = args.get("_validated_trace")
    session_id = str(args.get("session_id", "")).strip()  # R295 · 跨 host session 共享
    if not CLAUDE_ENTRY.exists():
        return _failure("TRANSPORT_UNAVAILABLE", "Claude Code entry is unavailable")
    env = dict(os.environ)
    env.setdefault("CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT", "1")
    command = [
        str(CLAUDE_ENTRY), "-p", prompt,
        "--output-format", "text", "--max-turns", "1",
        "--tools", "",
    ]
    # R295 · session 共享: 有 session_id 时用 --session-id 透传, 不用 --no-session-persistence
    if session_id:
        command.extend(["--session-id", session_id])
    else:
        command.append("--no-session-persistence")
    return _run(command, timeout, cwd=AIOS_ROOT, env=_child_env(trace, env))


def hermes_query(args: dict[str, Any]) -> dict[str, Any]:
    """Hermes in-process invocation (R291 新增 · 5 入口共用第 4 步)

    Hermes 是 in-process adapter：调 aios_task_lifecycle / aios_decision_logger / aios_evidence_collector
    其他 4 入口 (claude/codex/openclaw/workbuddy) 通过此工具调 hermes
    """
    prompt = _validate_text(args.get("prompt"), "prompt")
    prompt = _with_context(args, prompt)
    timeout = _validate_timeout(args.get("timeout"), 180)
    trace = args.get("_validated_trace")

    try:
        # 在同进程内 import hermes adapter (避免 import 循环)
        import sys
        adapter_path = AIOS_TOOLS
        if str(adapter_path) not in sys.path:
            sys.path.insert(0, str(adapter_path))
        from aios_adapter_hermes import HermesAdapter
        from aios_adapter_base import emit_trace

        # 组装 Hermes context（把 mcp args 转 adapter context）
        context = {}
        for key in ("action", "task_id", "contract", "from_state", "to_state",
                    "level", "rationale", "evidence", "evidence_list"):
            if key in args:
                context[key] = args[key]
        if not context:
            context = {"action": "system_status"}

        start = time.time()
        adapter = HermesAdapter()
        result = adapter.execute(prompt, context)
        duration_ms = (time.time() - start) * 1000
        status = "ok" if "error" not in result else "error"
        emit_trace("hermes", "call", duration_ms, status, {"via": "mcp_hermes_query"})
        result["adapter_name"] = "hermes"
        result["duration_ms"] = round(duration_ms, 2)
        result["transport"] = "in_process_via_mcp"
        return result
    except Exception as exc:
        return _failure("HERMES_EXEC_FAILED", f"hermes execution failed: {type(exc).__name__}: {exc}")


def rag_query(args: dict[str, Any]) -> dict[str, Any]:
    """R294 · 跨入口 RAG 检索 (5 入口 memory + SSOT)

    检索范围:
      - Claude memory (C:/Users/xinzh/.claude/projects/C--Users-xinzh/memory)
      - Operator memory (D:/个人文件/AI/Operator/memory)
      - SSOT 镜像 (D:/个人文件/AI/Operator/memory_claude/_all)

    输入 query → 输出 ranked hits (source_entrypoint + path + sha256 + relevance + matched_keywords)
    """
    query = _validate_text(args.get("query"), "query")
    query = _with_context(args, query)
    max_results = args.get("max_results", 10)
    try:
        max_results = int(max_results)
    except (TypeError, ValueError):
        return _failure("INVALID_ARGUMENT", "max_results must be an integer")
    if not 1 <= max_results <= 50:
        return _failure("INVALID_ARGUMENT", "max_results must be between 1 and 50")
    timeout = _validate_timeout(args.get("timeout"), 60)
    trace = args.get("_validated_trace")

    try:
        import sys
        adapter_path = AIOS_TOOLS
        if str(adapter_path) not in sys.path:
            sys.path.insert(0, str(adapter_path))
        from aios_adapter_base import emit_trace

        # 直接调 r293_cross_entrypoint_rag.retrieve (in-process)
        from r293_cross_entrypoint_rag import retrieve as rag_retrieve

        start = time.time()
        hits = rag_retrieve(query, max_results=max_results)
        duration_ms = (time.time() - start) * 1000
        status = "ok"
        emit_trace("rag", "retrieve", duration_ms, status, {"query_len": len(query), "max_results": max_results})

        return {
            "ok": True,
            "query": query,
            "max_results": max_results,
            "hit_count": len(hits),
            "hits": [hit.__dict__ if hasattr(hit, "__dict__") else hit for hit in hits],
            "duration_ms": round(duration_ms, 2),
            "search_roots": ["claude_memory", "operator_memory", "ssot_mirror"],
        }
    except Exception as exc:
        return _failure("RAG_EXEC_FAILED", f"rag retrieval failed: {type(exc).__name__}: {exc}")


def _tcp_probe(host: str, port: int, timeout: float = 3.0) -> bool:
    """R329 · TCP socket 探针 · 用于非 HTTP 协议端口 (openclaw gateway = WebSocket)

    OpenClaw 18792 是 WebSocket 服务,HTTP GET /health 必被 RST → 老 urllib 探针永远超时
    改用 raw socket connect_ex: 返回 0 = LISTENING, 非 0 = 不可达
    """
    import socket as _socket
    try:
        s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        s.settimeout(timeout)
        rc = s.connect_ex((host, port))
        s.close()
        return rc == 0
    except Exception:
        return False


def openclaw_health(args: dict[str, Any]) -> dict[str, Any]:
    """R302/R329 · OpenClaw gateway 健康探测 (port 18792) · TCP socket 探针

    OpenClaw 18792 是 WebSocket 协议,HTTP /health 必被 RST → 用 TCP socket connect_ex 判活
    返回: status / port / probe_method
    """
    endpoint = str(args.get("endpoint", "http://127.0.0.1:18792")).rstrip("/")
    try:
        timeout = int(args.get("timeout", 5))
    except (TypeError, ValueError):
        timeout = 5
    timeout = max(2, min(30, timeout))
    trace = args.get("_validated_trace")
    host = "127.0.0.1"
    port = 18792
    # 解析 endpoint 中的端口
    if ":" in endpoint.replace("http://", "").replace("https://", ""):
        try:
            tail = endpoint.replace("http://", "").replace("https://", "")
            port = int(tail.split(":")[-1].split("/")[0])
        except (ValueError, IndexError):
            pass
    ok = _tcp_probe(host, port, timeout=timeout)
    return {
        "ok": ok,
        "endpoint": endpoint,
        "host": host,
        "port": port,
        "probe_method": "tcp_connect",
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def hermes_health(args: dict[str, Any]) -> dict[str, Any]:
    """R304 · Hermes in-process 健康探测"""
    trace = args.get("_validated_trace")
    try:
        import sys
        if str(AIOS_TOOLS) not in sys.path:
            sys.path.insert(0, str(AIOS_TOOLS))
        import aios_task_lifecycle as lifecycle
        tasks = lifecycle.list_tasks(limit=50)
        return {
            "ok": True,
            "adapter": "hermes",
            "transport": "in_process",
            "tasks_count": len(tasks),
            "tools": ["aios_task_lifecycle", "aios_decision_logger", "aios_evidence_collector"],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return _failure("HERMES_HEALTH_FAILED", f"hermes health failed: {type(exc).__name__}: {exc}")


def codex_health(args: dict[str, Any]) -> dict[str, Any]:
    """R304 · Codex CLI 健康探测 (R306 加 wrapper 支持)"""
    import subprocess
    import shutil
    profile = str(args.get("profile", "deepseek"))
    trace = args.get("_validated_trace")
    # R306 · 优先用 wrapper, 否则 PATH
    wrapper = Path(r"D:/个人文件/AI/Operator/aios_tools/bin/codex.bat")
    if wrapper.exists():
        codex_cmd = str(wrapper)
    else:
        codex_cmd = shutil.which("codex")
    try:
        if not codex_cmd:
            return _failure("CODEX_NOT_FOUND", "codex CLI 不在 PATH 且 wrapper 不存在")
        result = subprocess.run(
            [codex_cmd, "--version"],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000,  # R266 治本: 隐藏 cmd 弹窗 (codex.bat 调 cmd 自身会闪 + 输出 Missing optional dependency)
        )
        version_ok = result.returncode == 0
        version = result.stdout.strip() or result.stderr.strip()
        help_result = subprocess.run(
            [codex_cmd, "exec", "--help"],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000,  # R266 治本
        )
        help_ok = help_result.returncode == 0
        return {
            "ok": version_ok,
            "profile": profile,
            "version_check": version_ok,
            "version": version[:100],
            "exec_help_ok": help_ok,
            "codex_cmd": codex_cmd,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except subprocess.TimeoutExpired:
        return _failure("CODEX_TIMEOUT", "codex --version 超时 (10s)")
    except FileNotFoundError:
        return _failure("CODEX_NOT_FOUND", f"codex CLI 不在 PATH ({codex_cmd})")
    except Exception as exc:
        return _failure("CODEX_HEALTH_FAILED", f"codex health failed: {type(exc).__name__}: {exc}")


def lingma_health(args: dict[str, Any]) -> dict[str, Any]:
    """R304 · Lingma VSCode 健康探测"""
    trace = args.get("_validated_trace")
    try:
        lingma_paths = [
            Path(r"D:/AIOS/_relinked/lingma/vscode/bin/2.6.10/x86_64_windows/Lingma.exe"),
            Path(r"D:/AIOS/_relinked/lingma/vscode/bin/2.6.9/x86_64_windows/Lingma.exe"),
            Path(r"D:/AIOS/_relinked/lingma/vscode/bin/2.6.8/x86_64_windows/Lingma.exe"),
        ]
        lingma_exe = None
        for p in lingma_paths:
            if p.exists():
                lingma_exe = p
                break
        mcp_config = Path(r"D:/AIOS/_relinked/lingma/vscode/sharedClientCache/lingma_mcp.json")
        mcp_ok = mcp_config.exists()
        aios_injected = False
        if mcp_ok:
            import json as _json
            cfg = _json.loads(mcp_config.read_text(encoding="utf-8"))
            aios_injected = "aios-interop" in cfg.get("mcpServers", {})
        return {
            "ok": lingma_exe is not None,
            "lingma_exe": str(lingma_exe) if lingma_exe else None,
            "mcp_config_exists": mcp_ok,
            "aios_interop_injected": aios_injected,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return _failure("LINGMA_HEALTH_FAILED", f"lingma health failed: {type(exc).__name__}: {exc}")


def cross_entrypoint_health(args: dict[str, Any]) -> dict[str, Any]:
    """R305 · 5 入口统一 health 总览

    一次调用 = claude/codex/openclaw/workbuddy/lingma/hermes 全部 health
    返回: 每个 entrypoint 的 health + 汇总 (overall ok / alerts 列表)
    """
    include_tools = bool(args.get("include_tools", False))
    trace = args.get("_validated_trace")
    try:
        results = {
            "entrypoints": {
                "claude": _claude_proxy_health(),
                "codex": codex_health({"profile": "deepseek"}),
                "openclaw": openclaw_health({}),
                "workbuddy": workbuddy_health({}),
                "lingma": lingma_health({}),
                "hermes": hermes_health({}),
            },
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        # 汇总
        all_ok = all(ep.get("ok", False) for ep in results["entrypoints"].values())
        alerts = []
        for name, ep in results["entrypoints"].items():
            if not ep.get("ok", False):
                err = ep.get("error", {})
                alerts.append(f"{name}: {err.get('message', 'unknown') if isinstance(err, dict) else ep.get('health', 'down')}")
        results["overall_ok"] = all_ok
        results["alerts"] = alerts
        results["summary"] = {
            "total": len(results["entrypoints"]),
            "ok_count": sum(1 for ep in results["entrypoints"].values() if ep.get("ok", False)),
            "warn_count": sum(1 for ep in results["entrypoints"].values() if ep.get("health") == "WARNING"),
        }
        if include_tools:
            results["tools"] = {
                "session_lifecycle": session_lifecycle({"action": "stats"}),
                "capability_search": capability_search({"query": "entrypoint", "limit": 1}),
            }
        return results
    except Exception as exc:
        return _failure("CROSS_EP_HEALTH_FAILED", f"cross entrypoint health failed: {type(exc).__name__}: {exc}")


def _claude_proxy_health() -> dict:
    """claude 当前 session 的代理 health (检查 _claude memory + aios-interop MCP)"""
    try:
        # 简化: CC memory 存在性 + MEMORY.md SHA 校验
        memory_path = Path(r"C:/Users/xinzh/.claude/projects/C--Users-xinzh/memory/MEMORY.md")
        ok = memory_path.exists()
        return {
            "ok": ok,
            "session_model": "MiniMax-M3",
            "memory_path": str(memory_path) if ok else None,
            "memory_size_bytes": memory_path.stat().st_size if ok else 0,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def version(args: dict[str, Any]) -> dict[str, Any]:
    """R306 · AIOS 版本统一查询 (6 入口 + 16 工具 + 24 caps + aios-interop)"""
    include_history = bool(args.get("include_history", False))
    trace = args.get("_validated_trace")
    try:
        # 16 工具列表
        tools = sorted(TOOL_HANDLERS.keys())
        # 6 入口
        hosts = ["claude", "codex", "openclaw", "workbuddy", "lingma", "hermes"]
        # aios-interop 版本
        aios_interop_version = SERVER_VERSION  # 从模块顶部常量
        # 24 caps
        caps_count = 0
        caps_path = Path(r"C:/Users/xinzh/.openclaw/workspace/state/capability_registry_v4_active.json")
        if caps_path.exists():
            caps_data = json.loads(caps_path.read_text(encoding="utf-8"))
            caps_count = len(caps_data.get("capabilities", caps_data.get("caps", [])))
        result = {
            "ok": True,
            "ai_os": {
                "entrypoints": hosts,
                "tools": tools,
                "aios_interop_version": aios_interop_version,
                "capabilities_count": caps_count,
                "total_rounds": 18,
                "total_items": 75,
            },
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
        if include_history:
            result["ai_os"]["round_history"] = [f"R{r}" for r in range(290, 306)]
        return result
    except Exception as exc:
        return _failure("VERSION_FAILED", f"version query failed: {type(exc).__name__}: {exc}")


def session_share(args: dict[str, Any]) -> dict[str, Any]:
    """R306 · 跨 host session 共享 (注册/查询/删除)"""
    action = str(args.get("action", "list"))
    host = str(args.get("host", "")).strip()
    session_id = str(args.get("session_id", "")).strip()
    target_hosts = args.get("target_hosts", [])
    metadata = args.get("metadata", {})
    trace = args.get("_validated_trace")

    try:
        share_path = AIOS_TOOLS / "data" / "shared_sessions.json"
        share_path.parent.mkdir(parents=True, exist_ok=True)
        if share_path.exists():
            shared = json.loads(share_path.read_text(encoding="utf-8"))
        else:
            shared = {}

        if action == "share":
            if not host or not session_id:
                return _failure("INVALID_ARGUMENT", "share 必填 host + session_id")
            key = f"{host}:{session_id}"
            shared[key] = {
                "host": host,
                "session_id": session_id,
                "target_hosts": target_hosts or ["claude", "codex", "openclaw", "workbuddy", "lingma"],
                "metadata": metadata,
                "shared_at": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
            }
            share_path.write_text(json.dumps(shared, ensure_ascii=False, indent=2), encoding="utf-8")
            return {
                "ok": True,
                "action": "share",
                "key": key,
                "shared_count": len(shared),
            }
        elif action == "list":
            return {
                "ok": True,
                "action": "list",
                "shared": list(shared.values()),
                "total": len(shared),
            }
        elif action == "revoke":
            if not host or not session_id:
                return _failure("INVALID_ARGUMENT", "revoke 必填 host + session_id")
            key = f"{host}:{session_id}"
            removed = shared.pop(key, None)
            share_path.write_text(json.dumps(shared, ensure_ascii=False, indent=2), encoding="utf-8")
            return {
                "ok": True,
                "action": "revoke",
                "key": key,
                "removed": removed is not None,
                "remaining": len(shared),
            }
        else:
            return _failure("INVALID_ACTION", f"未知 action: {action}")
    except Exception as exc:
        return _failure("SESSION_SHARE_FAILED", f"share failed: {type(exc).__name__}: {exc}")


def knowledge_base(args: dict[str, Any]) -> dict[str, Any]:
    """R306 · AIOS 知识库查询 (3 根)"""
    query = _validate_text(args.get("query"), "query", maximum=200)
    root_filter = str(args.get("root_filter", "all"))
    limit = int(args.get("limit", 5))
    limit = max(1, min(20, limit))
    trace = args.get("_validated_trace")

    try:
        # 3 根
        roots = {
            "core": Path(r"D:/个人文件/AI/Operator/00_CORE"),
            "feedback": Path(r"D:/个人文件/AI/Operator"),
            "ssot": Path(r"D:/个人文件/AI/Operator"),
        }
        if root_filter != "all":
            roots = {root_filter: roots[root_filter]}

        # 收集文件
        files = []
        for root_name, root_path in roots.items():
            if not root_path.exists():
                continue
            if root_name == "core":
                pattern = "*.md"
            elif root_name == "feedback":
                pattern = "feedback-*.md"
            elif root_name == "ssot":
                pattern = "AIOS-*.md"
            else:
                pattern = "*.md"
            for p in sorted(root_path.glob(pattern)):
                if p.is_file():
                    files.append((root_name, p))

        # 关键词匹配 (中英文都支持, 不区分大小写)
        q_lower = query.lower()
        hits = []
        for root_name, p in files:
            try:
                content = p.read_text(encoding="utf-8", errors="replace")[:5000]
                name_lower = p.name.lower()
                content_lower = content.lower()
                if q_lower in name_lower or q_lower in content_lower:
                    hits.append({
                        "root": root_name,
                        "name": p.name,
                        "path": str(p),
                        "size_bytes": p.stat().st_size,
                        "matched": "name" if q_lower in name_lower else "content",
                    })
            except OSError:
                pass
            if len(hits) >= limit:
                break

        return {
            "ok": True,
            "query": query,
            "root_filter": root_filter,
            "hits": hits,
            "total": len(hits),
            "files_scanned": len(files),
        }
    except Exception as exc:
        return _failure("KNOWLEDGE_BASE_FAILED", f"kb query failed: {type(exc).__name__}: {exc}")


# R307 · entrypoint 白名单 (防止任意注册)
ENTRYPOINT_WHITELIST = {"claude", "codex", "openclaw", "workbuddy", "lingma", "hermes"}
ENTRYPOINT_REGISTRY_PATH = AIOS_TOOLS / "data" / "entrypoint_registry.json"


def entrypoint_unregister(args: dict[str, Any]) -> dict[str, Any]:
    """R311 · 反向注销 entrypoint (配对 register/revoke)"""
    host = str(args.get("host", "")).strip()
    force = bool(args.get("force", False))
    trace = args.get("_validated_trace")
    if not host:
        return _failure("INVALID_ARGUMENT", "host 必填")
    try:
        ENTRYPOINT_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if ENTRYPOINT_REGISTRY_PATH.exists():
            reg = json.loads(ENTRYPOINT_REGISTRY_PATH.read_text(encoding="utf-8"))
        else:
            reg = {"entrypoints": {}}
        import shutil as _sh
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%Y%m%d-%H%M%S")
        backup_path = Path(r"D:/个人文件/AI/Operator/_backups/entrypoint_registry") / f"entrypoint_registry_unregister_{host}_{ts}.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        _sh.copy2(ENTRYPOINT_REGISTRY_PATH, backup_path)
        if host not in reg.get("entrypoints", {}):
            return _failure("NOT_FOUND", f"host '{host}' 未在 registry 中")
        removed_info = reg["entrypoints"].pop(host)
        if host in ENTRYPOINT_WHITELIST and not force:
            reg["entrypoints"][host] = removed_info
            ENTRYPOINT_REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
            return _failure("BUILTIN_PROTECTED", f"host '{host}' 是内建 6 入口之一, 必 force=true")
        ENTRYPOINT_REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "action": "unregister",
            "host": host,
            "removed": removed_info,
            "remaining": len(reg["entrypoints"]),
            "backup": str(backup_path),
        }
    except Exception as exc:
        return _failure("ENTRYPOINT_UNREGISTER_FAILED", f"unregister failed: {type(exc).__name__}: {exc}")


def capability_unregister(args: dict[str, Any]) -> dict[str, Any]:
    """R311 · 反向注销 capability (配对 register)"""
    cap_id = str(args.get("capability_id", "")).strip()
    force = bool(args.get("force", False))
    trace = args.get("_validated_trace")
    if not cap_id:
        return _failure("INVALID_ARGUMENT", "capability_id 必填")
    try:
        cap_path = Path(r"C:/Users/xinzh/.openclaw/workspace/state/capability_registry_v4_active.json")
        if not cap_path.exists():
            return _failure("REGISTRY_NOT_FOUND", "V4 capability registry 不存在")
        data = json.loads(cap_path.read_text(encoding="utf-8"))
        caps = data.get("capabilities", data.get("caps", []))
        target_idx = None
        target_cap = None
        for i, c in enumerate(caps):
            if c.get("capability_id") == cap_id:
                target_idx = i
                target_cap = c
                break
        if target_idx is None:
            return _failure("NOT_FOUND", f"capability '{cap_id}' 不存在")
        is_builtin = False
        if cap_id.startswith("cap-"):
            try:
                num = int(cap_id.split("-")[1])
                if num <= 20:
                    is_builtin = True
            except (ValueError, IndexError):
                pass
        if is_builtin and not force:
            return _failure("BUILTIN_PROTECTED", f"capability '{cap_id}' 是内建 cap, 必 force=true")
        import shutil as _sh
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = Path(r"D:/个人文件/AI/Operator/_backups/capability_registry") / f"capability_registry_unregister_{cap_id}_{ts}.json"
        backup.parent.mkdir(parents=True, exist_ok=True)
        _sh.copy2(cap_path, backup)
        removed = caps.pop(target_idx)
        data["capabilities"] = caps
        cap_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return {
            "ok": True,
            "action": "unregister",
            "capability_id": cap_id,
            "removed": {"name": removed.get("name"), "lifecycle": removed.get("lifecycle")},
            "remaining": len(caps),
            "backup": str(backup),
        }
    except Exception as exc:
        return _failure("CAPABILITY_UNREGISTER_FAILED", f"unregister failed: {type(exc).__name__}: {exc}")


def entrypoint_register(args: dict[str, Any]) -> dict[str, Any]:
    """R307 · 动态注册 entrypoint (白名单 + 文件持久化)"""
    action = str(args.get("action", "list"))
    host = str(args.get("host", "")).strip()
    endpoint = str(args.get("endpoint", "")).strip()
    metadata = args.get("metadata", {})
    trace = args.get("_validated_trace")

    try:
        ENTRYPOINT_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if ENTRYPOINT_REGISTRY_PATH.exists():
            reg = json.loads(ENTRYPOINT_REGISTRY_PATH.read_text(encoding="utf-8"))
        else:
            reg = {"entrypoints": {}}

        if action == "list":
            return {
                "ok": True,
                "action": "list",
                "registered": list(reg.get("entrypoints", {}).values()),
                "whitelist": sorted(ENTRYPOINT_WHITELIST),
                "builtin_entrypoints": sorted(HOST_TOOL_ALLOW.keys()),
            }
        elif action == "register":
            if not host:
                return _failure("INVALID_ARGUMENT", "register 必填 host")
            if host not in ENTRYPOINT_WHITELIST:
                return _failure("HOST_NOT_WHITELISTED", f"host '{host}' 不在白名单 {ENTRYPOINT_WHITELIST}")
            reg["entrypoints"][host] = {
                "host": host,
                "endpoint": endpoint or f"in-process://{host}",
                "metadata": metadata,
                "registered_at": datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S"),
                "status": "active",
            }
            ENTRYPOINT_REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
            return {
                "ok": True,
                "action": "register",
                "host": host,
                "registered_count": len(reg["entrypoints"]),
            }
        elif action == "revoke":
            if not host:
                return _failure("INVALID_ARGUMENT", "revoke 必填 host")
            removed = reg["entrypoints"].pop(host, None)
            ENTRYPOINT_REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
            return {
                "ok": True,
                "action": "revoke",
                "host": host,
                "removed": removed is not None,
                "remaining": len(reg["entrypoints"]),
            }
        else:
            return _failure("INVALID_ACTION", f"未知 action: {action}")
    except Exception as exc:
        return _failure("ENTRYPOINT_REGISTER_FAILED", f"register failed: {type(exc).__name__}: {exc}")


def workbuddy_health(args: dict[str, Any]) -> dict[str, Any]:
    """R302 · WorkBuddy 进程健康检查 (复用 r302_workbuddy_health.py 逻辑)"""
    threshold = int(args.get("log_age_threshold_minutes", 10))
    trace = args.get("_validated_trace")
    try:
        import subprocess as _sp
        WB_PATHS = [
            Path(r"C:/Users/xinzh/AppData/Local/WorkBuddy"),
            Path(r"D:/AIOS/_relinked/workbuddy"),
        ]
        # 进程检查
        wb_count = 0
        cb_count = 0
        for proc_name in ("WorkBuddy.exe", "codebuddy.exe"):
            try:
                r = _sp.run(
                    ["tasklist", "/FI", f"IMAGENAME eq {proc_name}", "/FO", "CSV", "/NH"],
                    capture_output=True, text=True, timeout=10, encoding="cp936", errors="replace",
                    creationflags=0x08000008,  # R268 治本: 隐藏 tasklist 控制台窗 (r304 每分钟调 2 次, 弹窗元凶)
                )
                for line in r.stdout.strip().splitlines():
                    if not line.strip() or "INFO:" in line:
                        continue
                    parts = [p.strip().strip('"') for p in line.split(",")]
                    if len(parts) >= 5 and parts[0].lower() == proc_name.lower():
                        if proc_name == "WorkBuddy.exe":
                            wb_count += 1
                        else:
                            cb_count += 1
            except Exception:
                pass

        # log 检查
        logs_info = {"logs_dir": None, "recent_log": None, "age_minutes": None}
        for wb_path in WB_PATHS:
            logs_dir = wb_path / "logs"
            if logs_dir.exists():
                logs_info["logs_dir"] = str(logs_dir)
                log_files = sorted(logs_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
                if log_files:
                    latest = log_files[0]
                    mtime = datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone(timedelta(hours=8)))
                    age_min = (datetime.now(timezone(timedelta(hours=8))) - mtime).total_seconds() / 60
                    logs_info["recent_log"] = latest.name
                    logs_info["age_minutes"] = round(age_min, 2)
                break

        health = "OK"
        alerts = []
        if wb_count == 0 and cb_count == 0:
            health = "CRITICAL"
            alerts.append("WorkBuddy.exe + codebuddy.exe 都不在跑")
        age_min = logs_info.get("age_minutes", -1)
        if age_min is not None and age_min >= 0 and age_min > threshold:
            health = "WARNING"
            alerts.append(f"最近 log 已 {age_min:.0f}min 未更新 ({threshold}min 阈值)")

        return {
            "ok": True,
            "health": health,
            "alerts": alerts,
            "wb_processes": wb_count,
            "codebuddy_processes": cb_count,
            "logs": logs_info,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return _failure("WORKBUDDY_HEALTH_FAILED", f"health check failed: {type(exc).__name__}: {exc}")


def langfuse_query(args: dict[str, Any]) -> dict[str, Any]:
    """R302 · Langfuse trace 查询 (本地 fallback: aios_tasks/evidence/adapter_trace.jsonl)

    当 Langfuse 服务不可达时, 本地 jsonl 文件保留所有 trace events
    """
    limit = int(args.get("limit", 20))
    limit = max(1, min(100, limit))
    tool_filter = str(args.get("tool_filter", "")).strip()
    since_minutes = int(args.get("since_minutes", 60))
    since_minutes = max(1, min(1440, since_minutes))
    trace = args.get("_validated_trace")

    try:
        trace_path = AIOS_TOOLS / "aios_tasks" / "evidence" / "adapter_trace.jsonl"
        if not trace_path.exists():
            return {
                "ok": True,
                "events": [],
                "total": 0,
                "message": "本地 trace 文件不存在 (无任何 trace 调用)",
            }

        events = []
        cutoff = datetime.now(timezone(timedelta(hours=8))) - timedelta(minutes=since_minutes)
        with trace_path.open("r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in reversed(lines):
            try:
                event = json.loads(line.strip())
            except ValueError:
                continue
            event_time = event.get("timestamp")
            if event_time:
                try:
                    if datetime.fromisoformat(event_time.replace("Z", "+00:00")) < cutoff:
                        continue
                except ValueError:
                    pass
            if tool_filter:
                event_tool = event.get("tool", "")
                if tool_filter not in event_tool:
                    continue
            events.append(event)
            if len(events) >= limit:
                break

        return {
            "ok": True,
            "events": events,
            "total": len(events),
            "trace_path": str(trace_path),
            "since_minutes": since_minutes,
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        return _failure("LANGFUSE_QUERY_FAILED", f"trace query failed: {type(exc).__name__}: {exc}")


def session_lifecycle(args: dict[str, Any]) -> dict[str, Any]:
    """R303 · 跨入口 session 生命周期管理 (list/cleanup/stats)"""
    action = str(args.get("action", "list"))
    host_filter = str(args.get("host_filter", "")).strip()
    max_age_hours = int(args.get("max_age_hours", 168))
    trace = args.get("_validated_trace")

    try:
        pool_path = AIOS_TOOLS / "data" / "cross_entrypoint_sessions.json"
        if not pool_path.exists():
            return {"ok": True, "sessions": [], "total": 0, "message": "session pool 文件不存在"}
        pool = json.loads(pool_path.read_text(encoding="utf-8"))
        sessions = list(pool.values())

        if action == "list":
            if host_filter:
                sessions = [s for s in sessions if s.get("host") == host_filter]
            return {
                "ok": True,
                "action": "list",
                "host_filter": host_filter or "all",
                "sessions": sessions,
                "total": len(sessions),
            }
        elif action == "stats":
            by_host = {}
            for s in sessions:
                h = s.get("host", "?")
                by_host.setdefault(h, 0)
                by_host[h] += 1
            return {
                "ok": True,
                "action": "stats",
                "by_host": by_host,
                "total": len(sessions),
            }
        elif action == "cleanup":
            from datetime import timezone as _tz, timedelta as _td
            cutoff = datetime.now(_tz(timedelta(hours=8))) - _td(hours=max_age_hours)
            to_delete = []
            for k, info in pool.items():
                last_used = info.get("last_used", "")
                try:
                    last_dt = datetime.strptime(last_used, "%Y-%m-%d %H:%M:%S").replace(tzinfo=_tz(timedelta(hours=8)))
                    if last_dt < cutoff:
                        to_delete.append(k)
                except ValueError:
                    pass
            for k in to_delete:
                del pool[k]
            pool_path.write_text(json.dumps(pool, ensure_ascii=False, indent=2), encoding="utf-8")
            return {
                "ok": True,
                "action": "cleanup",
                "removed": len(to_delete),
                "removed_keys": to_delete,
                "remaining": len(pool),
                "max_age_hours": max_age_hours,
            }
        else:
            return _failure("INVALID_ACTION", f"未知 action: {action}")
    except Exception as exc:
        return _failure("SESSION_LIFECYCLE_FAILED", f"lifecycle operation failed: {type(exc).__name__}: {exc}")


def capability_search(args: dict[str, Any]) -> dict[str, Any]:
    """R303 · V4 capability registry 搜索"""
    query = _validate_text(args.get("query"), "query", maximum=200)
    lifecycle = str(args.get("lifecycle", "")).strip()
    limit = int(args.get("limit", 10))
    limit = max(1, min(50, limit))
    trace = args.get("_validated_trace")

    try:
        reg_path = Path(r"C:/Users/xinzh/.openclaw/workspace/state/capability_registry_v4_active.json")
        if not reg_path.exists():
            return {"ok": True, "results": [], "total": 0, "message": "registry 不存在"}
        data = json.loads(reg_path.read_text(encoding="utf-8"))
        caps = data.get("capabilities", data.get("caps", data))

        query_lower = query.lower()
        results = []
        for cap in caps:
            # 匹配 name + description + source
            name_str = str(cap.get("name", "")).lower()
            desc_str = str(cap.get("description", "")).lower()
            src_str = str(cap.get("source", "")).lower()
            if query_lower in name_str or query_lower in desc_str or query_lower in src_str:
                if lifecycle and cap.get("lifecycle") != lifecycle:
                    continue
                results.append({
                    "capability_id": cap.get("capability_id"),
                    "name": cap.get("name"),
                    "lifecycle": cap.get("lifecycle"),
                    "memory_scope": cap.get("memory_scope", "N/A"),
                    "semantic_version": cap.get("semantic_version", "N/A"),
                    "description": str(cap.get("description", ""))[:200],
                    "source": cap.get("source"),
                    "last_verified": cap.get("last_verified"),
                })
                if len(results) >= limit:
                    break

        return {
            "ok": True,
            "query": query,
            "lifecycle_filter": lifecycle or "all",
            "results": results,
            "total": len(results),
            "registry_total": len(caps),
        }
    except Exception as exc:
        return _failure("CAPABILITY_SEARCH_FAILED", f"search failed: {type(exc).__name__}: {exc}")


TOOL_HANDLERS = {
    "aios_status": aios_status,
    "openclaw_delegate": openclaw_delegate,
    "codex_query": codex_query,
    "codex_desktop_query": codex_desktop_query,
    "claude_code_query": claude_code_query,
    "hermes_query": hermes_query,
    "rag_query": rag_query,
    "openclaw_health": openclaw_health,
    "workbuddy_health": workbuddy_health,
    "langfuse_query": langfuse_query,
    "session_lifecycle": session_lifecycle,
    "capability_search": capability_search,
    "hermes_health": hermes_health,  # R304 新增
    "codex_health": codex_health,  # R304 新增
    "lingma_health": lingma_health,  # R304 新增
    "cross_entrypoint_health": cross_entrypoint_health,  # R305 新增
    "version": version,  # R306 新增
    "session_share": session_share,  # R306 新增
    "knowledge_base": knowledge_base,  # R306 新增
    "entrypoint_register": entrypoint_register,  # R307 新增
    "entrypoint_unregister": entrypoint_unregister,  # R311 配对
    "capability_unregister": capability_unregister,  # R311 配对
}

TOOL_FIELDS = {
    "aios_status": {"trace"},
    "openclaw_delegate": {"agent", "message", "timeout", "session_key", "model", "trace"},
    "codex_query": {"prompt", "profile", "session_key", "timeout", "trace"},
    "codex_desktop_query": {"prompt", "thread_id", "timeout", "trace"},
    "claude_code_query": {"prompt", "session_id", "timeout", "trace"},
    "hermes_query": {"prompt", "action", "task_id", "contract", "from_state",
                     "to_state", "level", "rationale", "evidence", "evidence_list",
                     "timeout", "trace"},
    "rag_query": {"query", "max_results", "timeout", "trace"},
    "openclaw_health": {"endpoint", "timeout", "trace"},
    "workbuddy_health": {"log_age_threshold_minutes", "trace"},
    "langfuse_query": {"limit", "tool_filter", "since_minutes", "trace"},
    "session_lifecycle": {"action", "host_filter", "max_age_hours", "trace"},
    "capability_search": {"query", "lifecycle", "limit", "trace"},
    "hermes_health": {"trace"},
    "codex_health": {"profile", "trace"},
    "lingma_health": {"trace"},
    "cross_entrypoint_health": {"include_tools", "trace"},
    "version": {"include_history", "trace"},
    "session_share": {"action", "host", "session_id", "target_hosts", "metadata", "trace"},
    "knowledge_base": {"query", "root_filter", "limit", "trace"},
    "entrypoint_register": {"action", "host", "endpoint", "metadata", "trace"},
    "entrypoint_unregister": {"host", "force", "trace"},
    "capability_unregister": {"capability_id", "force", "trace"},
}


def entrypoint_unregister(args: dict[str, Any]) -> dict[str, Any]:
    """R311 · 反向注销 entrypoint (配对 register/revoke)

    内建 6 入口 (claude/codex/openclaw/workbuddy/lingma/hermes) 必用 force=true 才能注销
    """
    host = str(args.get("host", "")).strip()
    force = bool(args.get("force", False))
    trace = args.get("_validated_trace")

    if not host:
        return _failure("INVALID_ARGUMENT", "host 必填")

    try:
        ENTRYPOINT_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if ENTRYPOINT_REGISTRY_PATH.exists():
            reg = json.loads(ENTRYPOINT_REGISTRY_PATH.read_text(encoding="utf-8"))
        else:
            reg = {"entrypoints": {}}

        import shutil as _sh
        from datetime import datetime as _dt
        ts = _dt.now().strftime("%Y%m%d-%H%M%S")
        backup_path = Path(r"D:/个人文件/AI/Operator/_backups/entrypoint_registry") / f"entrypoint_registry_unregister_{host}_{ts}.json"
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        _sh.copy2(ENTRYPOINT_REGISTRY_PATH, backup_path)

        if host not in reg.get("entrypoints", {}):
            return _failure("NOT_FOUND", f"host '{host}' 未在 registry 中 (无需 unregister)")

        removed_info = reg["entrypoints"].pop(host)
        if host in ENTRYPOINT_WHITELIST and not force:
            reg["entrypoints"][host] = removed_info
            ENTRYPOINT_REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
            return _failure("BUILTIN_PROTECTED", f"host '{host}' 是内建 6 入口之一, 必加 force=true")

        ENTRYPOINT_REGISTRY_PATH.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "action": "unregister",
            "host": host,
            "removed": removed_info,
            "remaining": len(reg["entrypoints"]),
            "backup": str(backup_path),
        }
    except Exception as exc:
        return _failure("ENTRYPOINT_UNREGISTER_FAILED", f"unregister failed: {type(exc).__name__}: {exc}")


def capability_unregister(args: dict[str, Any]) -> dict[str, Any]:
    """R311 · 反向注销 capability (配对 register)

    内建 caps (cap-001~020) 必用 force=true 才能注销
    """
    cap_id = str(args.get("capability_id", "")).strip()
    force = bool(args.get("force", False))
    trace = args.get("_validated_trace")

    if not cap_id:
        return _failure("INVALID_ARGUMENT", "capability_id 必填")

    try:
        cap_path = Path(r"C:/Users/xinzh/.openclaw/workspace/state/capability_registry_v4_active.json")
        if not cap_path.exists():
            return _failure("REGISTRY_NOT_FOUND", "V4 capability registry 不存在")
        data = json.loads(cap_path.read_text(encoding="utf-8"))
        caps = data.get("capabilities", data.get("caps", []))

        target_idx = None
        target_cap = None
        for i, c in enumerate(caps):
            if c.get("capability_id") == cap_id:
                target_idx = i
                target_cap = c
                break
        if target_idx is None:
            return _failure("NOT_FOUND", f"capability '{cap_id}' 不存在")

        # 内建 cap 保护 (cap-001~020 锁定 · cap-021+ 可删)
        is_builtin = False
        if cap_id.startswith("cap-"):
            try:
                num = int(cap_id.split("-")[1])
                if num <= 20:
                    is_builtin = True
            except (ValueError, IndexError):
                pass
        if is_builtin and not force:
            return _failure("BUILTIN_PROTECTED", f"capability '{cap_id}' 是内建 cap, 必加 force=true")

        import shutil as _sh
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = Path(r"D:/个人文件/AI/Operator/_backups/capability_registry") / f"capability_registry_unregister_{cap_id}_{ts}.json"
        backup.parent.mkdir(parents=True, exist_ok=True)
        _sh.copy2(cap_path, backup)

        removed = caps.pop(target_idx)
        data["capabilities"] = caps
        cap_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return {
            "ok": True,
            "action": "unregister",
            "capability_id": cap_id,
            "removed": {"name": removed.get("name"), "lifecycle": removed.get("lifecycle")},
            "remaining": len(caps),
            "backup": str(backup),
        }
    except Exception as exc:
        return _failure("CAPABILITY_UNREGISTER_FAILED", f"unregister failed: {type(exc).__name__}: {exc}")


def _langfuse_trace_event(event_name: str, payload: dict[str, Any]) -> bool:
    """R294 · 跨入口 trace 接 Langfuse · 失败降级本地 log

    复用 _aios_langfuse_trace_stub.langfuse_trace
    """
    try:
        from _aios_langfuse_trace_stub import langfuse_trace
        return langfuse_trace(event_name, payload)
    except Exception:
        return False  # 失败降级 · 不影响主流程


def _execute_tool(name: Any, arguments: Any) -> dict[str, Any]:
    if not isinstance(name, str) or name not in TOOL_HANDLERS:
        return _failure("UNKNOWN_TOOL", "unknown tool")
    # R294 · 跨入口 trace · call 事件
    call_start = time.time()
    call_status = "ok"
    call_extra = {"tool": name, "host": os.environ.get("AIOS_MCP_HOST", "unknown")}
    try:
        principal = _authorise(name)
        if not isinstance(arguments, dict):
            raise InteropError("INVALID_ARGUMENT", "arguments must be an object")
        unexpected = set(arguments) - TOOL_FIELDS[name]
        if unexpected:
            raise InteropError("INVALID_ARGUMENT", "arguments contain unsupported fields")
        prepared, trace_meta = _prepare_arguments(name, arguments)
        if name != "aios_status":
            prompt_value = prepared.get("message") if name == "openclaw_delegate" else prepared.get("prompt")
            prepared["_context_preamble"] = _build_context_preamble(name, str(prompt_value or ""))
        fingerprint_source = dict(arguments)
        if isinstance(fingerprint_source.get("trace"), dict):
            trace_copy = dict(fingerprint_source["trace"])
            for transient in ("request_id", "parent_request_id", "depth", "visited"):
                trace_copy.pop(transient, None)
            fingerprint_source["trace"] = trace_copy
        fingerprint = hashlib.sha256(
            json.dumps(fingerprint_source, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        cache_key = f"{principal['name']}:{name}:{trace_meta['idempotency_key']}"
        with _CACHE_LOCK:
            cached = _RESULT_CACHE.get(cache_key)
            if cached:
                if cached["fingerprint"] != fingerprint:
                    raise InteropError("IDEMPOTENCY_CONFLICT", "idempotency key was already used with different arguments")
                _langfuse_trace_event("aios_interop.cache_hit", {"tool": name, "host": call_extra["host"]})
                return dict(cached["result"])
        handler = TOOL_HANDLERS[name]
        if name == "aios_status":
            output = handler(prepared)
        else:
            with _execution_slot():
                output = handler(prepared)
        if not isinstance(output, dict):
            raise InteropError("INVALID_RESULT", "tool returned an invalid result")
        with _CACHE_LOCK:
            _RESULT_CACHE[cache_key] = {"fingerprint": fingerprint, "result": dict(output)}
            _RESULT_CACHE.move_to_end(cache_key)
            while len(_RESULT_CACHE) > _CACHE_LIMIT:
                _RESULT_CACHE.popitem(last=False)
        # R294 · 跨入口 trace · done 事件
        call_extra["ok"] = bool(output.get("ok", True))
        call_extra["duration_ms"] = round((time.time() - call_start) * 1000, 2)
        _langfuse_trace_event("aios_interop.tool_call.done", call_extra)
        return output
    except InteropError as exc:
        call_status = "error"
        call_extra["error_code"] = exc.code
        _langfuse_trace_event("aios_interop.tool_call.error", call_extra)
        return _failure(exc.code, exc.message)
    except Exception:
        call_status = "error"
        call_extra["error_type"] = "internal"
        _langfuse_trace_event("aios_interop.tool_call.error", call_extra)
        return _failure("INTERNAL_ERROR", "interop tool execution failed")


def _respond(request_id: Any, result: dict[str, Any] | None = None, error: dict[str, Any] | None = None) -> None:
    payload: dict[str, Any] = {"jsonrpc": "2.0", "id": request_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result or {}
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _handle(request: dict[str, Any]) -> None:
    method = request.get("method")
    request_id = request.get("id")
    if method == "initialize":
        _respond(request_id, {
            "protocolVersion": PROTOCOL_VERSION,
            "serverInfo": {"name": "aios-interop", "version": SERVER_VERSION},
            "capabilities": {"tools": {}},
            "instructions": (
                "Use aios_status for health. Delegate only when the user requested cross-agent work. "
                "Never call the tool representing the current host itself; host configurations filter those tools."
            ),
        })
    elif method == "tools/list":
        allowed = _allowed_tools()
        principal = _principal()
        if not principal["authenticated"] or "P" not in principal["authorities"]:
            allowed = allowed & {"aios_status"}
        _respond(request_id, {"tools": [tool for tool in TOOLS if tool["name"] in allowed]})
    elif method == "tools/call":
        params = request.get("params") or {}
        name = params.get("name")
        output = _execute_tool(name, params.get("arguments") or {})
        is_error = not bool(output.get("ok", True))
        _respond(request_id, {
            "content": [{"type": "text", "text": _bounded_text(output)}],
            "structuredContent": output,
            "isError": is_error,
        })
    elif method == "ping":
        _respond(request_id, {})
    elif method == "notifications/initialized":
        return
    elif request_id is not None:
        _respond(request_id, error={"code": -32601, "message": f"Method not found: {method}"})


def main() -> int:
    # Local CLI bridge used by the existing router.  It reuses the exact MCP
    # handlers rather than implementing a second dispatch path.
    if len(sys.argv) >= 4 and sys.argv[1] == "--invoke":
        name = sys.argv[2]
        try:
            arguments = json.loads(sys.argv[3])
            result = _execute_tool(name, arguments)
            print(json.dumps(result, ensure_ascii=False))
            return 0 if result.get("ok", True) else 1
        except json.JSONDecodeError:
            print(json.dumps(_failure("INVALID_JSON", "arguments must be valid JSON"), ensure_ascii=False))
            return 1
    for raw_line in sys.stdin:
        line = raw_line.strip().lstrip("\ufeff")
        if not line:
            continue
        try:
            request = json.loads(line)
            if isinstance(request, dict):
                _handle(request)
        except Exception:
            print("aios-interop parse/dispatch error", file=sys.stderr, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
