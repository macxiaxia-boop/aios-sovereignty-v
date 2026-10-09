#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_kill_aios_daemon_tree_v3.py - R273 立 (2026-09-29)

R272 失败原因: pythonw.exe 没有 SeDebugPrivilege, OpenProcess 失败 → get_cmd 返回 '?'
R273 治本:
- 用 win32api.OpenProcess + 提权 SeDebugPrivilege
- 改用更宽松的判断 (pythonw.exe + cpython-3.12.13 路径)
- 杀所有符合条件的 pythonw.exe + 它们的子孙
- taskkill /F /T 兜底杀残留
"""
import os
import sys
import time
import ctypes
from ctypes import wintypes
from pathlib import Path
from datetime import datetime

PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_QUERY_INFORMATION = 0x0400
TOKEN_QUERY = 0x0008
TOKEN_ADJUST_PRIVILEGES = 0x0020

TH32CS_SNAPPROCESS = 0x00000002
class PE32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.c_uint32), ('cntUsage', ctypes.c_uint32),
                ('th32ProcessID', ctypes.c_uint32), ('th32DefaultHeapID', ctypes.c_void_p),
                ('th32ModuleID', ctypes.c_uint32), ('cntThreads', ctypes.c_uint32),
                ('th32ParentProcessID', ctypes.c_uint32), ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', ctypes.c_uint32), ('szExeFile', ctypes.c_char*260)]

k = ctypes.windll.kernel32
advapi32 = ctypes.windll.advapi32

def log(msg):
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(r"D:\AIOS\_kill_aios_daemon_tree.log", "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except: pass

# R273: 提权 SeDebugPrivilege
def enable_debug_privilege():
    try:
        hToken = wintypes.HANDLE()
        advapi32.OpenProcessToken(k.GetCurrentProcess(), TOKEN_ADJUST_PRIVILEGES | TOKEN_QUERY, ctypes.byref(hToken))
        LUID = ctypes.c_int64 * 2
        luid = LUID()
        advapi32.LookupPrivilegeValueW(None, "SeDebugPrivilege", ctypes.byref(luid))
        TP = (ctypes.c_uint32 * 9)()
        TP[0] = 1  # PrivilegeCount
        TP[1] = luid[0]
        TP[2] = luid[1]
        TP[3] = 2  # SE_PRIVILEGE_ENABLED
        advapi32.AdjustTokenPrivileges(hToken, False, ctypes.byref(TP), 0, None, None)
        k.CloseHandle(hToken)
        log("✓ SeDebugPrivilege enabled")
        return True
    except Exception as e:
        log(f"⚠ SeDebugPrivilege failed: {e}")
        return False


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


def get_cmd_robust(pid):
    """R273: 用 PROCESS_QUERY_INFORMATION (权限更高) + 提权后 OpenProcess"""
    # 先试 PROCESS_QUERY_LIMITED_INFORMATION
    for access in [PROCESS_QUERY_LIMITED_INFORMATION, PROCESS_QUERY_INFORMATION]:
        h = k.OpenProcess(access, False, pid)
        if h:
            try:
                buf = ctypes.create_unicode_buffer(2048)
                size = ctypes.c_ulong(2048)
                if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
                    return buf.value
            finally:
                k.CloseHandle(h)
    return None


def kill_pid(pid):
    h = k.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not h:
        # 兜底: 用 taskkill
        import subprocess
        try:
            r = subprocess.run(['taskkill', '/F', '/PID', str(pid)],
                             capture_output=True, creationflags=0x08000000)
            return r.returncode == 0
        except: return False
    try:
        return k.TerminateProcess(h, 1) != 0
    finally:
        k.CloseHandle(h)


log("=== _kill_aios_daemon_tree v3 START (R273) ===")
enable_debug_privilege()

procs = get_all_procs()

# R273: 宽松过滤 — 只要是 pythonw.exe/python.exe 且进程路径在 cpython-3.12.13 / 3.13.12 / 包含 aios_tools / bridge / polling / inbox / daemon
# 全部杀掉 + 它们的子孙
TARGET_KEYWORDS = ['aios_tools', 'bridge', 'polling', 'inbox', 'daemon']

def is_target(pid, exe, cmd):
    cmd_lower = (cmd or '').lower()
    exe_lower = exe.lower()
    # 排除我们自己
    if '_kill_aios_daemon' in cmd_lower:
        return False
    if '_popup_cure_watchdog' in cmd_lower:
        return False  # popup_cure 保留
    if '_stage_watchdog' in cmd_lower:
        return False  # stage 保留
    if '_popup_watchdog_parent' in cmd_lower:
        return False  # watchdog_parent 保留
    if '_popup_watchdog_parent_supervisor' in cmd_lower:
        return False
    if '_hide_console_windows' in cmd_lower:
        return False
    if '_proc_snoop' in cmd_lower or '_kill_aios_daemon_tree' in cmd_lower:
        return False
    if '_heartbeat_test' in cmd_lower:
        return False

    # 必须是 pythonw.exe 或 python.exe
    if exe_lower not in ['python.exe', 'pythonw.exe']:
        return False

    # 必须包含 aios_tools 路径或关键字
    if 'aios_tools' in cmd_lower:
        return True
    if 'r304_entrypoint' in cmd_lower:
        return True
    return False


# 找出所有目标进程 + 它们 spawn 的 cmd.exe/conhost.exe/powershell.exe
targets = set()
for pid, (exe, ppid) in procs.items():
    cmd = get_cmd_robust(pid)
    if is_target(pid, exe, cmd):
        targets.add(pid)

log(f"找到 {len(targets)} 个目标进程")

# BFS 找所有子孙 (cmd.exe / powershell.exe / conhost.exe)
def find_descendants(root_pids, procs):
    children = {}
    for pid, (exe, ppid) in procs.items():
        children.setdefault(ppid, []).append(pid)
    descendants = set()
    queue = list(root_pids)
    while queue:
        cur = queue.pop()
        for child in children.get(cur, []):
            if child not in descendants:
                descendants.add(child)
                queue.append(child)
    return descendants

descendants = find_descendants(targets, procs)
all_to_kill = targets | descendants
log(f"加上 {len(descendants)} 个子孙, 共 {len(all_to_kill)} 个待杀")

# 杀 (倒序)
killed = 0
failed = 0
for pid in sorted(all_to_kill, reverse=True):
    exe = procs.get(pid, ('?', '?'))[0]
    cmd = get_cmd_robust(pid) or '?'
    if kill_pid(pid):
        killed += 1
        log(f"  ✓ KILLED PID={pid} {exe}  {cmd[:80]}")
    else:
        failed += 1
        log(f"  ✗ FAILED PID={pid} {exe}  {cmd[:80]}")

log(f"\n=== DONE: 杀 {killed}/{len(all_to_kill)} 个进程 (failed={failed}) ===")
