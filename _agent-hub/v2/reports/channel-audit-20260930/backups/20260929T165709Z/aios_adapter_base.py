#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aios_adapter_base.py · AIOS Adapter Base v4.0（R79 立 · 2026-09-19）

目标: 6 Adapter 统一接口基类 · V4.0 §10 Adapter Layer
分层: L2 写本地 / 复用 mcp_credentials.env / 纯 stdlib / 无外部依赖

6 Adapters:
  - chatgpt (codex_base/ollama)  # R297 治本: 原 "codex_cli_relay_19194" 已废 · R244 LOCKED base=MiniMax-M3 + R297 ollama 本地兜底
  - codex (codex_cli)
  - claude (claude_code_sdk)
  - hermes (in_process)
  - openclaw (in_process)
  - doubao (future)

红线绑定:
  #21 5 角色 SSOT · #22 5 权限阶梯 · #60 4 类实证 · #67 Observability · #70 MCP 治理
"""

from __future__ import annotations

import json
import hashlib
import time
import subprocess
from pathlib import Path
from typing import Optional, Any
from datetime import datetime, timezone
from abc import ABC, abstractmethod

AIOS_HOME = Path(__file__).parent.parent
TRACE_LOG = AIOS_HOME / "aios_tasks" / "evidence" / "adapter_trace.jsonl"


def emit_trace(adapter_name: str, action: str, duration_ms: float, status: str, extra: Optional[dict] = None) -> None:
    """每个 adapter 调用必带 trace（红线 #67/#68/#70.5）"""
    trace = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": hashlib.sha256(f"{adapter_name}{action}{time.time()}".encode()).hexdigest()[:16],
        "adapter_name": adapter_name,
        "action": action,
        "duration_ms": round(duration_ms, 2),
        "status": status,  # "ok" / "error" / "handoff_triggered"
    }
    if extra:
        trace.update(extra)
    TRACE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with TRACE_LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps(trace, ensure_ascii=False) + "\n")


class BaseAdapter(ABC):
    """Adapter 基类 · 统一接口"""

    ADAPTER_NAME: str = "base"
    TRANSPORT: str = "abstract"
    AUTHORITY: str = "P"  # PRIMARY 默认
    STATUS: str = "active"

    def __init__(self, name: str):
        self.name = name
        self.call_count = 0
        self.error_count = 0
        self.handoff_count = 0

    @abstractmethod
    def execute(self, prompt: str, context: Optional[dict] = None) -> dict:
        """执行任务（必返回标准 dict）"""
        pass

    @abstractmethod
    def health_check(self) -> dict:
        """健康检查"""
        pass

    def detect_handoff_signal(self, result: dict) -> Optional[str]:
        """检测交接信号（quota_exhausted / session_dead / failed）"""
        if result.get("quota_exhausted"):
            return "quota_exhausted"
        if result.get("session_dead"):
            return "session_dead"
        if result.get("error") and "fatal" in str(result.get("error", "")).lower():
            return "failed"
        return None

    def call(self, prompt: str, context: Optional[dict] = None) -> dict:
        """统一调用入口（自动 trace + handoff 检测）"""
        start = time.time()
        status = "ok"
        result = {}
        extra = {}
        try:
            self.call_count += 1
            result = self.execute(prompt, context)
            if "error" in result:
                status = "error"
                self.error_count += 1
            # 检测交接信号
            handoff = self.detect_handoff_signal(result)
            if handoff:
                status = "handoff_triggered"
                self.handoff_count += 1
                extra["handoff_reason"] = handoff
                result["handoff_required"] = True
                result["handoff_reason"] = handoff
        except Exception as e:
            status = "error"
            self.error_count += 1
            result = {"error": f"{type(e).__name__}: {e}"}
            extra["exception"] = str(e)

        duration_ms = (time.time() - start) * 1000
        emit_trace(self.ADAPTER_NAME, "call", duration_ms, status, extra)
        result["adapter_name"] = self.ADAPTER_NAME
        result["duration_ms"] = round(duration_ms, 2)
        return result

    def get_status(self) -> dict:
        return {
            "adapter_name": self.ADAPTER_NAME,
            "transport": self.TRANSPORT,
            "authority": self.AUTHORITY,
            "status": self.STATUS,
            "call_count": self.call_count,
            "error_count": self.error_count,
            "handoff_count": self.handoff_count,
        }