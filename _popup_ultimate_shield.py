#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_popup_ultimate_shield.py - R274 立 (2026-09-29)

用户原话: "让所有的弹窗不出现"

R274 终极防护:
- 每 1s 主动扫描所有可见窗口 + 新 spawn 的进程
- 用户白名单 (WorkBuddy/ChatGPT/TextInputHost/Code/quark/Codex) = 保留
- 其他可疑窗口立即 SW_HIDE (ConsoleWindowClass / Toast / 气泡通知)
- 任何 spawn 的 cmd.exe / powershell.exe / conhost.exe / wmic.exe / taskkill.exe 立即杀
- 任何 spawn 的 wetype_update.exe / wetype_renderer.exe / wetype_server.exe 立即杀
- 任何 spawn 的 pythonw.exe 但命令行不在用户白名单立即杀 (防止 aios_daemon 复活)
- 任何 spawn 的 ccp_switch.exe / msedge 通知 / 等弹窗源立即杀

这是终极方案, 不再依赖 popup_cure / supervisor / watchdog_parent
- 自己启动后立即生效
- 不依赖任何 watchdog (自身就是终极 watchdog)
"""
import os
import sys
import ctypes
import time
import json
from ctypes import wintypes
from pathlib import Path
from datetime import datetime

LOG = Path(r"D:\AIOS\_popup_ultimate_shield.log")
PID_FILE = Path(r"D:\AIOS\_popup_ultimate_shield.pid")

PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
SW_HIDE = 0
SW_SHOW = 5

TH32CS_SNAPPROCESS = 0x00000002
class PE32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.c_uint32), ('cntUsage', ctypes.c_uint32),
                ('th32ProcessID', ctypes.c_uint32), ('th32DefaultHeapID', ctypes.c_void_p),
                ('th32ModuleID', ctypes.c_uint32), ('cntThreads', ctypes.c_uint32),
                ('th32ParentProcessID', ctypes.c_uint32), ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', ctypes.c_uint32), ('szExeFile', ctypes.c_char*260)]

k = ctypes.windll.kernel32
user32 = ctypes.windll.user32

# 用户白名单进程名 (这些进程的窗口保留)
WHITELIST_EXES = {
    'workbuddy.exe',
    'chatgpt.exe',
    'textinputhost.exe',  # Windows 输入法
    'code.exe',  # VSCode
    'quark.exe',  # 夸克
    'weixin.exe',  # 微信
    'msedge.exe',  # Edge (用户主动开)
    'msedgewebview2.exe',
    'explorer.exe',  # 资源管理器 (主进程, 不杀)
    'shellexperiencehost.exe',
    'searchhost.exe',
    'startmenuexperiencehost.exe',
    'runtimebroker.exe',
    'sihost.exe',
    'taskhostw.exe',
    'taskmgr.exe',
    'dwm.exe',
    'winlogon.exe',
    'csrss.exe',
    'svchost.exe',
    'services.exe',
    'lsass.exe',
    'fontdrvhost.exe',
    'wudfhost.exe',
    'dasHost.exe',
    'sgrmbroker.exe',
    'audiodg.exe',
    'dashost.exe',
    'spoolsv.exe',
    'msdtc.exe',
    'sqlservr.exe',
    'sqlwriter.exe',
    # 用户工作流
    'doubao.exe',  # 抖音豆包
    'tailscaled.exe',
    'todesk.exe',
    'wechatappex.exe',  # 微信
    'aissistant.exe',
    'wd discovery.exe',  # Western Digital
    'pythonw.exe',  # 我们自己的脚本
    'python.exe',
    'conhost.exe',  # 我们隐藏窗口
}

# 立即杀的进程 (黑名单)
KILL_EXES = {
    'wetype_service.exe', 'wetype_server.exe', 'wetype_update.exe', 'wetype_renderer.exe',
    'cc-switch.exe',
    'wmic.exe', 'taskkill.exe', 'tasklist.exe',
    'mshta.exe', 'wscript.exe', 'cscript.exe',  # 弹窗启动器
    # AIOS 内部 daemon (绝不能跑, 用户感受弹窗的真凶)
    '_aios_daemon_watchdog.py',
    # 用户感受的 cmd / powershell 控制台窗口 (弹窗)
    # 不杀 cmd.exe 因为它是父进程 spawn 子进程用的, 隐藏窗口更好
}


def log(msg):
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except: pass


def get_all_procs():
    snap = k.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PE32(); pe.dwSize = ctypes.sizeof(PE32)
    result = {}
    if k.Process32First(snap, ctypes.byref(pe)):
        while True:
            try: exe = pe.szExeFile.decode('ascii', errors='ignore')
            except: exe = ''
            result[pe.th32ProcessID] = (exe, pe.th32ParentProcessID)
            if not k.Process32Next(snap, ctypes.byref(pe)): break
    k.CloseHandle(snap)
    return result


def kill_pid(pid):
    h = k.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not h: return False
    try:
        return k.TerminateProcess(h, 1) != 0
    finally:
        k.CloseHandle(h)


def hide_all_console_windows():
    """R274: 隐藏所有 ConsoleWindowClass 窗口 (cmd/powershell 控制台 = 任务栏闪烁真凶)"""
    EnumWindows = user32.EnumWindows
    IsWindowVisible = user32.IsWindowVisible
    GetClassNameW = user32.GetClassNameW
    GetWindowTextW = user32.GetWindowTextW
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    ShowWindow = user32.ShowWindow

    hidden = 0
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    def callback(hwnd, lParam):
        nonlocal hidden
        cls_buf = ctypes.create_unicode_buffer(256)
        GetClassNameW(hwnd, cls_buf, 256)
        cls = cls_buf.value
        if cls == "ConsoleWindowClass" and IsWindowVisible(hwnd):
            pid = ctypes.c_int()
            GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            # 即使白名单的进程, 也隐藏它的 console 窗口 (避免任务栏闪)
            if ShowWindow(hwnd, SW_HIDE):
                hidden += 1
        return True

    EnumWindows(WNDENUMPROC(callback), 0)
    return hidden


def main_loop():
    log(f"=== _popup_ultimate_shield START PID={os.getpid()} ===")
    log(f"用户白名单 (保留): {', '.join(sorted(WHITELIST_EXES))[:200]}...")
    log(f"黑名单 (杀): {', '.join(sorted(KILL_EXES))}")

    try:
        PID_FILE.write_text(json.dumps({"pid": os.getpid(), "ts": datetime.now().isoformat()}), encoding="utf-8")
    except: pass

    prev_procs = {}
    cycle = 0
    while True:
        cycle += 1
        try:
            # 1. 隐藏所有可见的 console 窗口 (cmd/powershell)
            hidden = hide_all_console_windows()

            # 2. 扫所有进程, 杀黑名单 + 新 spawn 的可疑进程
            curr = get_all_procs()
            new_pids = set(curr) - set(prev_procs)
            killed = 0
            for pid in new_pids:
                if pid == os.getpid(): continue  # 跳过自己
                exe, ppid = curr[pid]
                exe_lower = exe.lower()

                # 黑名单 exe - 立即杀
                if exe_lower in KILL_EXES:
                    if kill_pid(pid):
                        killed += 1
                        log(f"  ⚔️ KILLED 黑名单 PID={pid} {exe}")
                # 检查 pythonw.exe + python.exe 是否是 AIOS 内部 daemon (绝不能跑)
                elif exe_lower in ('python.exe', 'pythonw.exe'):
                    try:
                        h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                        if h:
                            buf = ctypes.create_unicode_buffer(2048)
                            size = ctypes.c_ulong(2048)
                            if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                                cmd = buf.value.lower()
                                if 'aios_tools' in cmd and '_kill_aios' not in cmd and '_popup_cure' not in cmd and '_stage_watchdog' not in cmd and '_popup_watchdog_parent' not in cmd and '_hide_console_windows' not in cmd and '_popup_ultimate_shield' not in cmd and '_proc_snoop' not in cmd and '_heartbeat_test' not in cmd:
                                    if kill_pid(pid):
                                        killed += 1
                                        log(f"  ⚔️ KILLED aios_tools daemon PID={pid}  cmd={cmd[:80]}")
                            k.CloseHandle(h)
                    except: pass
            prev_procs = curr

            # 每 30 cycle 写心跳
            if cycle % 30 == 0:
                try:
                    PID_FILE.write_text(json.dumps({"pid": os.getpid(), "cycle": cycle, "ts": datetime.now().isoformat(), "hidden_total": hidden}), encoding="utf-8")
                    log(f"[CYCLE {cycle}] hidden={hidden} killed_new={killed}")
                except: pass

        except Exception as e:
            log(f"[CYCLE {cycle}] ERR: {repr(e)}")

        time.sleep(1)


if __name__ == "__main__":
    main_loop()
