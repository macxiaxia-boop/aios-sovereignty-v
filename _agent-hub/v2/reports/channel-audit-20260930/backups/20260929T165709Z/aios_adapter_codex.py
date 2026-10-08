#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aios_adapter_codex.py · Codex CLI Adapter v4.0（R79 立 · 2026-09-19）

目标: Codex CLI 调用 + 完成检测 + 额度耗尽触发 Handoff
分层: L2 写本地 / 纯 stdlib / 走 Codex CLI subprocess

适配范围:
  - PRIMARY 角色（红线 #21 · AGENT-ROLES.md 工程执行）
  - Codex CLI 已安装并登录（OAuth / API key）
  - profile base → MiniMax-M3 (R244 LOCKED) / profile ollama → Ollama 本地 (R297 fallback) / profile chatgpt → ChatGPT OAuth

红线绑定: #21/#22/#60/#67/#70.5/#75

R297 治本 (2026-09-28): 原 docstring 误说"profile deepseek → 本地 relay 19194 → DeepSeek v4-flash" 已废
  - 真根因: 同 aios_adapter_chatgpt.py R297 治本
"""

from __future__ import annotations

import json
import subprocess
from typing import Optional
from pathlib import Path

from aios_adapter_base import BaseAdapter, emit_trace


class CodexAdapter(BaseAdapter):
    ADAPTER_NAME = "codex"
    TRANSPORT = "codex_cli"
    AUTHORITY = "P"
    STATUS = "active"

    # R293 新增 · session 池 (caller session_key → codex session_id)
    _session_pool: dict[str, str] = {}

    def __init__(self, profile: str = "deepseek", timeout: int = 600):
        super().__init__(name="codex")
        self.profile = profile
        self.timeout = timeout
        self.codex_cmd = self._find_codex()

    def _find_codex(self) -> str:
        """定位 codex CLI（红线 #62 凭据边界 · 不硬编码路径）"""
        candidates = ["codex", "codex.cmd", "codex.exe"]
        for c in candidates:
            try:
                r = subprocess.run([c, "--version"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    return c
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        return "codex"  # fallback PATH

    def execute(self, prompt: str, context: Optional[dict] = None) -> dict:
        """调用 Codex CLI · R293 支持 session 复用"""
        try:
            cmd = [self.codex_cmd, "--profile", self.profile, "exec"]

            # R293 · session 复用: 从 context 拿 session_key, 映射到 codex session_id
            session_key = (context or {}).get("session_key", "").strip()
            if session_key:
                # 同一 session_key 复用同一 codex session_id
                if session_key in self._session_pool:
                    codex_session_id = self._session_pool[session_key]
                    cmd.extend(["--session-id", codex_session_id])
                # else: 让 codex CLI 自己生成, 然后从输出提取

            cmd.append(prompt)
            if context:
                # 过滤掉 session_key (已用), 其他 context 仍传
                ctx_for_codex = {k: v for k, v in context.items() if k != "session_key"}
                if ctx_for_codex:
                    context_str = json.dumps(ctx_for_codex, ensure_ascii=False)
                    cmd.extend(["--context", context_str])

            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
            )
            output = r.stdout.strip()

            # R293 · 从输出提取 codex session_id (首次调用时)
            if session_key and session_key not in self._session_pool:
                # codex CLI 输出通常包含 "session_id: xxx" 或类似
                import re
                m = re.search(r"session[_-]?id[:\s=]+([a-zA-Z0-9-]+)", output, re.IGNORECASE)
                if m:
                    self._session_pool[session_key] = m.group(1)

            # 检测 Codex 特殊信号
            if "quota_exhausted" in output.lower() or "rate limit" in output.lower():
                return {"output": output, "quota_exhausted": True, "stderr": r.stderr.strip()}
            if "session_dead" in output.lower() or "auth expired" in output.lower():
                return {"output": output, "session_dead": True, "stderr": r.stderr.strip()}
            if r.returncode != 0:
                return {"output": output, "error": r.stderr.strip(), "exit_code": r.returncode}

            result = {"output": output, "exit_code": r.returncode}
            if session_key:
                result["session_key"] = session_key
                result["codex_session_id"] = self._session_pool.get(session_key, "")
            return result
        except subprocess.TimeoutExpired:
            return {"error": f"codex timeout after {self.timeout}s", "timeout": True}
        except FileNotFoundError:
            return {"error": "codex CLI not found in PATH", "fatal": True}

    def health_check(self) -> dict:
        """健康检查"""
        try:
            r = subprocess.run([self.codex_cmd, "--version"], capture_output=True, text=True, timeout=5)
            return {"adapter": self.ADAPTER_NAME, "available": r.returncode == 0, "version": r.stdout.strip()}
        except Exception as e:
            return {"adapter": self.ADAPTER_NAME, "available": False, "error": str(e)}


def self_test() -> dict:
    results = {}
    adapter = CodexAdapter()
    h = adapter.health_check()
    results["health_check"] = h.get("available", False)
    results["status"] = adapter.get_status()
    return results


def main() -> None:
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return
    print("Usage: aios_adapter_codex.py --selftest")


if __name__ == "__main__":
    main()