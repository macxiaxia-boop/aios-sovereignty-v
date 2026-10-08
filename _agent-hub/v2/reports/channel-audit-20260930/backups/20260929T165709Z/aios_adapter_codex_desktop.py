#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
aios_adapter_codex_desktop.py · Codex Desktop Thread Adapter（R96 治本 · 2026-09-19）

目标: 找"当前这个 Codex Desktop 任务" + 把消息送到指定 thread
分层: L2 写本地 / 纯 stdlib / 走 Codex CLI `queue` 子命令

适配范围:
  - 角色: 交互通道（红线 #21 AGENT-ROLES.md Hermes 治理 / 用户拍板）
  - 区分 aios_adapter_codex.py 的 `codex_cli`（批处理/后台，无人值守）
  - Codex Desktop 必须保持运行（红线 #22 L4 边界）
  - 走 Codex 0.149.1 新增共享 App Server (codex queue --thread --message)

红线绑定: #21/#22/#60/#67/#70.5/#75

WHY 拆出独立 adapter（用户原话 "彻底修复应当把目标拆成两个适配器"):
  - codex_cli: 无人值守、批处理、后台执行 → aios_adapter_codex.py
  - codex_desktop_thread: 找"当前这个我"，用 codex queue --thread ... → 本文件
  - "跟 Codex 交互 / 找 Codex Desktop / 找你" 必须路由本 adapter

L4 后续（用户原话 "还需增加 App Server WebSocket 双向适配器"):
  - codex queue 是异步单向队列，无法自动读取回复
  - 后续需 WebSocket 双向适配器（codex app-server）实现自动编排
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Optional

from aios_adapter_base import BaseAdapter, emit_trace


class CodexDesktopAdapter(BaseAdapter):
    ADAPTER_NAME = "codex_desktop"
    TRANSPORT = "codex_queue"
    AUTHORITY = "P"
    STATUS = "active"

    def __init__(self, thread_id: Optional[str] = None, timeout: int = 30):
        super().__init__(name="codex_desktop")
        self.thread_id = thread_id
        self.timeout = timeout
        self.codex_node_bin = self._resolve_codex_node()

    def _resolve_codex_node(self) -> list[str]:
        """Windows 必走 node 直调（红线 #29 R77 治本 · 避 cmd/bash shim 'M' 错）"""
        configured_js = os.environ.get("CODEX_JS_PATH", "").strip()
        candidates = [
            Path(configured_js) if configured_js else None,
            Path(r"D:/npm-global/node_modules/@openai/codex/bin/codex.js"),
            Path(r"C:/Users/xinzh/.npm-global/node_modules/@openai/codex/bin/codex.js"),
        ]
        node = os.environ.get("CODEX_NODE_PATH") or shutil.which("node") or r"C:/Users/xinzh/node.exe"
        for candidate in candidates:
            if candidate and candidate.exists():
                return [node, str(candidate)]
        # 非 Windows 直接走 codex binary
        found = shutil.which("codex")
        if found:
            return [found]
        raise FileNotFoundError(
            "codex.js not found at D:/npm-global/node_modules/@openai/codex/bin/codex.js. "
            "Install via `npm install -g @openai/codex`."
        )

    def execute(self, prompt: str, context: Optional[dict] = None) -> dict:
        """把消息送到 Codex Desktop 指定 thread。

        Args:
            prompt: 要发送的消息内容
            context: {"thread_id": "<UUID>"} 或默认用 self.thread_id

        Returns:
            {"ok": bool, "queued_message_id": "<UUID>", "output": str, "exit_code": int}
        """
        thread_id = (context or {}).get("thread_id") or self.thread_id
        if not thread_id:
            return {"ok": False, "error": "thread_id required (Codex Desktop session UUID or name)"}
        if not prompt or not prompt.strip():
            return {"ok": False, "error": "prompt is required"}

        try:
            cmd = self.codex_node_bin + [
                "queue", "--thread", thread_id, "--message", prompt,
            ]
            start = time.time()
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                encoding="utf-8",
                errors="replace",
                creationflags=0x08000000,  # R259 v4 治本 (红线 #78)
            )
            elapsed_ms = (time.time() - start) * 1000
            output = r.stdout.strip()
            error = r.stderr.strip()
            # 解析 Codex queue 输出: "Queued message <UUID> for thread <UUID>."
            queued_id = None
            m = re.search(r"queued\s+message\s+([0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12})", output, re.IGNORECASE)
            if m:
                queued_id = m.group(1)

            status = "queued" if r.returncode == 0 and queued_id else ("delivered" if r.returncode == 0 else "error")
            emit_trace(
                adapter_name="codex_desktop",
                action="queue",
                duration_ms=elapsed_ms,
                status=status,
                extra={
                    "thread_id": thread_id,
                    "queued_message_id": queued_id,
                    "prompt_len": len(prompt),
                    "exit_code": r.returncode,
                },
            )

            if r.returncode != 0:
                return {
                    "ok": False,
                    "error": error or output,
                    "exit_code": r.returncode,
                    "thread_id": thread_id,
                }
            if not queued_id:
                return {
                    "ok": False,
                    "error": "codex queue exited successfully but no queued message UUID was found",
                    "output": output,
                    "exit_code": 0,
                    "thread_id": thread_id,
                    "transport_status": "protocol_error",
                }
            return {
                "ok": True,
                "transport_status": "queued",
                "queued_message_id": queued_id,
                "thread_id": thread_id,
                "output": output,
                "exit_code": 0,
            }
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": f"codex queue timeout after {self.timeout}s", "timeout": True, "transport_status": "timeout"}
        except FileNotFoundError as e:
            return {"ok": False, "error": str(e), "fatal": True}

    def health_check(self) -> dict:
        """健康检查: Codex Desktop 进程是否在跑 + codex queue 子命令可用"""
        try:
            # 检查 Codex Desktop 进程
            r = subprocess.run(
                ["tasklist"], capture_output=True, text=True, timeout=5, encoding="utf-8", errors="replace",
                creationflags=0x08000000,  # R259 v4 治本 (红线 #78): tasklist 在 Win10 即使加 CREATE_NO_WINDOW 仍可能闪任务栏
            )
            desktop_running = any(token in r.stdout.lower() for token in ("codex.exe", "codex desktop", "codex-code-mode-host.exe"))

            # 检查 codex queue 子命令
            r2 = subprocess.run(
                self.codex_node_bin + ["queue", "--help"],
                capture_output=True, text=True, timeout=5,
                creationflags=0x08000000,  # R259 v4 治本 (红线 #78)
            )
            queue_available = r2.returncode == 0 and "queue" in r2.stdout.lower()

            return {
                "adapter": self.ADAPTER_NAME,
                "available": desktop_running and queue_available,
                "desktop_running": desktop_running,
                "queue_available": queue_available,
                "thread_id_configured": self.thread_id is not None,
            }
        except Exception as e:
            return {"adapter": self.ADAPTER_NAME, "available": False, "error": str(e)}


def self_test() -> dict:
    """self_test: 健康检查 + 假 thread_id 验证 (不真发消息)"""
    adapter = CodexDesktopAdapter()
    h = adapter.health_check()
    return {
        "health_check": h,
        "status": adapter.get_status(),
        "adapter_name": adapter.ADAPTER_NAME,
        "transport": adapter.TRANSPORT,
    }


def main() -> None:
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return
    if len(sys.argv) > 1 and sys.argv[1] == "--send":
        # python aios_adapter_codex_desktop.py --send <thread_id> <message>
        if len(sys.argv) < 4:
            print("Usage: python aios_adapter_codex_desktop.py --send <thread_id> <message>")
            return
        adapter = CodexDesktopAdapter(thread_id=sys.argv[2])
        result = adapter.execute(sys.argv[3])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    print("Usage: aios_adapter_codex_desktop.py --selftest | --send <thread_id> <message>")


if __name__ == "__main__":
    main()
