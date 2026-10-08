#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aios_adapter_mcp_bridge.py · R129 立 · 2026-09-21
MCP HTTP 桥 → BaseAdapter 包装 · 通用 HTTP→stdio MCP 转发

红线 #95 EXTEND 而非新建:
  - 继承 BaseAdapter
  - 复用 _aios_mcp_endpoint_bridge.call_mcp_stdio / run_server / self_test

prompt 格式: "call_stdio::<method>::<params_json>"
"""
from __future__ import annotations

import sys
import json
from pathlib import Path
from typing import Optional

AIOS_HOME = Path(r"D:\个人文件\AI\Operator")
sys.path.insert(0, str(AIOS_HOME))

from aios_tools.aios_adapter_base import BaseAdapter
from aios_tools._aios_mcp_endpoint_bridge import call_mcp_stdio, self_test as mcp_self_test


class MCPBridgeAdapter(BaseAdapter):
    ADAPTER_NAME = "mcp_bridge"
    TRANSPORT = "http"
    AUTHORITY = "S"
    STATUS = "active"

    def execute(self, prompt: str, context: Optional[dict] = None) -> dict:
        ctx = context or {}
        parts = prompt.split("::", 2)
        action = parts[0] if parts else "call_stdio"
        if action == "call_stdio":
            method = parts[1] if len(parts) > 1 else ctx.get("method", "")
            try:
                params = json.loads(parts[2]) if len(parts) > 2 else ctx.get("params", {})
            except (json.JSONDecodeError, TypeError):
                params = {}
            try:
                result = call_mcp_stdio(method, params)
                return {"action": action, "method": method, "result": result, "status": "ok"}
            except Exception as e:
                return {"action": action, "method": method, "error": f"{type(e).__name__}: {e}", "status": "error"}
        elif action == "self_test":
            try:
                result = mcp_self_test()
                return {"action": action, "result": str(result), "status": "ok"}
            except Exception as e:
                return {"action": action, "error": f"{type(e).__name__}: {e}", "status": "error"}
        return {"error": f"Unknown action: {action}", "available": ["call_stdio", "self_test"]}

    def health_check(self) -> dict:
        return {
            "adapter": self.ADAPTER_NAME,
            "transport": self.TRANSPORT,
            "module": "aios_tools._aios_mcp_endpoint_bridge",
            "functions": ["call_mcp_stdio", "self_test"],
            "server_entry": "run_server(port=18798)",
            "status": self.STATUS,
        }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--health-check", action="store_true")
    args = parser.parse_args()
    a = MCPBridgeAdapter(name="mcp_bridge")
    if args.health_check:
        print(json.dumps(a.health_check(), ensure_ascii=False, indent=2))
