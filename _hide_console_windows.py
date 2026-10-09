#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_hide_console_windows.py - R269 立 (2026-09-29)

根因: VSCode/Claude Code/Codex CLI 启动 MCP server 时 spawn cmd.exe 控制台窗口
      → 任务栏闪一下 = 用户感受到的"弹窗真凶"

R269 治本:
- 不杀进程 (杀进程会让 MCP server 启动失败)
- 只用 ShowWindow(SW_HIDE) 隐藏控制台窗口
- 同时监控所有可见 ConsoleWindowClass 窗口
- 新窗口出现立即隐藏
- 1s tick

弹窗真凶 (11:07 实测):
- 11 个 cmd.exe 父进程都是 Code.exe (VSCode)
- spawn: playwright-mcp, atlascloud-mcp, filesystem, memory, sequential-thinking
- Claude Code 配置 18 个 MCP server (spawn node.exe 无 cmd 但 VSCode 启它们时也走 cmd)
"""
import ctypes
import sys
import time
import json
from pathlib import Path
from datetime import datetime

LOG = Path(r"D:\AIOS\_hide_console_windows.log")
PID = Path(r"D:\AIOS\_hide_console_windows.pid")
SW_HIDE = 0
SW_SHOW = 5

def log(msg):
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def write_pid():
    try:
        PID.write_text(json.dumps({"pid": __import__('os').getpid()}, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def main():
    user32 = ctypes.windll.user32
    EnumWindows = user32.EnumWindows
    GetClassNameW = user32.GetClassNameW
    GetWindowTextW = user32.GetWindowTextW
    IsWindowVisible = user32.IsWindowVisible
    ShowWindow = user32.ShowWindow

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)

    hidden_count = 0

    def callback(hwnd, lParam):
        nonlocal hidden_count
        cls_buf = ctypes.create_unicode_buffer(256)
        GetClassNameW(hwnd, cls_buf, 256)
        cls = cls_buf.value
        # ConsoleWindowClass = cmd.exe/powershell.exe/python.exe 的控制台窗口
        if cls == "ConsoleWindowClass" and IsWindowVisible(hwnd):
            # 隐藏它
            if ShowWindow(hwnd, SW_HIDE):
                hidden_count += 1
        return True

    log(f"_hide_console_windows START PID={__import__('os').getpid()}")
    write_pid()  # 立即写 PID 文件给 supervisor 监管

    tick = 0
    while True:
        tick += 1
        try:
            before = hidden_count
            EnumWindows(WNDENUMPROC(callback), 0)
            now_hidden = hidden_count - before
            if now_hidden > 0 and tick % 60 == 1:
                log(f"tick={tick} hidden {now_hidden} 个新控制台窗口 (总 {hidden_count})")
            # 每 30 tick 更新 PID 文件 mtime (让 supervisor 知道还活着)
            if tick % 30 == 0:
                write_pid()
        except Exception as e:
            log(f"tick {tick} ERR: {e}")
        time.sleep(1)


if __name__ == "__main__":
    main()
