#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aios_adapter_claude.py · Claude Code SDK Adapter v4.0（R79 立 · 2026-09-19）

目标: Claude Code 调用 + 高级工程任务 + Handoff 触发
分层: L2 写本地 / 纯 stdlib / 走 Claude Code SDK 或 CLI fallback

适配范围:
  - PRIMARY 角色（红线 #21 · 高级工程 / 架构评审）
  - Claude Code 已安装（npm/pip）
  - 可直接调用 SDK 或 subprocess CLI

红线绑定: #21/#22/#60/#67/#70.5/#75
"""

from __future__ import annotations

import json
import subprocess
import os
from typing import Optional
from pathlib import Path

from aios_adapter_base import BaseAdapter


class ClaudeAdapter(BaseAdapter):
    ADAPTER_NAME = "claude"
    TRANSPORT = "claude_code_sdk_or_cli"
    AUTHORITY = "P"
    STATUS = "active"

    def __init__(self, model: str = "claude-sonnet-5", timeout: int = 900):
        super().__init__(name="claude")
        self.model = model
        self.timeout = timeout
        # SDK 优先级 > CLI fallback（红线 #70.3 Streamable HTTP 优先）
        self.transport_mode = self._detect_transport()

    def _detect_transport(self) -> str:
        """优先检测 SDK，fallback CLI"""
        try:
            import claude_code_sdk  # noqa: F401
            return "sdk"
        except ImportError:
            return "cli"

    def execute(self, prompt: str, context: Optional[dict] = None) -> dict:
        """调用 Claude Code"""
        if self.transport_mode == "sdk":
            sdk_result = self._execute_sdk(prompt, context)
            if sdk_result.get("ok"):
                return sdk_result
            return self._execute_cli(prompt, context)
        return self._execute_cli(prompt, context)

    def _execute_sdk(self, prompt: str, context: Optional[dict] = None) -> dict:
        """走 Claude Code SDK"""
        try:
            import claude_code_sdk as sdk
            # SDK releases expose different async APIs.  Until an explicitly
            # supported callable is bound, fail closed and let execute() make
            # a real CLI call instead of claiming a simulated success.
            if not callable(getattr(sdk, "query_sync", None)):
                return {"ok": False, "error": "unsupported Claude SDK API", "error_code": "SDK_UNSUPPORTED"}
            full_prompt = prompt if not context else f"{prompt}\n\nContext: {json.dumps(context, ensure_ascii=False)}"
            output = sdk.query_sync(prompt=full_prompt, model=self.model)
            return {"ok": True, "output": str(output), "transport": "sdk"}
        except Exception as e:
            return {"ok": False, "error": f"sdk execution failed: {type(e).__name__}", "fallback_to_cli": True}

    def _execute_cli(self, prompt: str, context: Optional[dict] = None) -> dict:
        """走 Claude Code CLI fallback"""
        try:
            full_prompt = prompt
            if context:
                full_prompt = f"{prompt}\n\nContext: {json.dumps(context, ensure_ascii=False)}"
            cmd = [
                "claude", "-p", full_prompt, "--model", self.model,
                "--output-format", "text", "--max-turns", "1",
                "--no-session-persistence", "--tools", "",
            ]
            env = os.environ.copy()
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout, env=env)
            output = r.stdout.strip()
            # 检测 Claude Code 信号
            if "rate limit" in output.lower():
                return {"output": output, "quota_exhausted": True, "stderr": r.stderr.strip()}
            if "auth" in output.lower() and "expired" in output.lower():
                return {"output": output, "session_dead": True}
            if r.returncode != 0:
                return {"output": output, "error": r.stderr.strip(), "exit_code": r.returncode}
            return {"ok": True, "output": output, "exit_code": r.returncode, "transport": "cli"}
        except subprocess.TimeoutExpired:
            return {"error": f"claude timeout after {self.timeout}s", "timeout": True}
        except FileNotFoundError:
            return {"error": "claude CLI not found in PATH", "fatal": True}

    def health_check(self) -> dict:
        """健康检查"""
        try:
            cmd = ["claude", "--version"] if self.transport_mode == "cli" else ["python", "-c", "import claude_code_sdk"]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            return {"adapter": self.ADAPTER_NAME, "available": r.returncode == 0, "transport": self.transport_mode}
        except Exception as e:
            return {"adapter": self.ADAPTER_NAME, "available": False, "error": str(e)}


def self_test() -> dict:
    results = {}
    adapter = ClaudeAdapter()
    h = adapter.health_check()
    results["health_check"] = h.get("available", False)
    results["transport"] = h.get("transport")
    results["status"] = adapter.get_status()
    return results


def main() -> None:
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return
    print("Usage: aios_adapter_claude.py --selftest")


if __name__ == "__main__":
    main()

