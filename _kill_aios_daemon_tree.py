#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_kill_aios_daemon_tree.py v2 - R271 修正过滤逻辑

根因: _aios_daemon_watchdog.py spawn 14+ 个 bridge polling daemon 子进程
      每个子进程 spawn cmd.exe 控制台窗口 = 任务栏闪烁真凶

修正: 不依赖字符串 and 短路, 直接用 or
"""
import ctypes
import sys
import time
from ctypes import wintypes
from pathlib import Path
from datetime import datetime

PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

TH32CS_SNAPPROCESS = 0x00000002
class PE32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.c_uint32), ('cntUsage', ctypes.c_uint32),
                ('th32ProcessID', ctypes.c_uint32), ('th32DefaultHeapID', ctypes.c_void_p),
                ('th32ModuleID', ctypes.c_uint32), ('cntThreads', ctypes.c_uint32),
                ('th32ParentProcessID', ctypes.c_uint32), ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', ctypes.c_uint32), ('szExeFile', ctypes.c_char*260)]

k = ctypes.windll.kernel32

def log(msg):
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(r"D:\AIOS\_kill_aios_daemon_tree.log", "a", encoding="utf-8") as f:
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

def get_cmd(pid):
    h = k.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h: return '?'
    buf = ctypes.create_unicode_buffer(2048)
    size = ctypes.c_ulong(2048)
    if k.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
        k.CloseHandle(h)
        return buf.value
    k.CloseHandle(h)
    return '?'

def kill_pid(pid):
    h = k.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not h: return False
    try:
        result = k.TerminateProcess(h, 1)
        return result != 0
    finally:
        k.CloseHandle(h)


log("=== _kill_aios_daemon_tree v2 START (R271) ===")

# 找出所有 _aios_daemon_watchdog.py / aios_tools/ 下的 python 脚本
procs = get_all_procs()

def is_aios_target(cmd):
    """判断是否是 AIOS daemon 子进程"""
    if not cmd: return False
    cmd_lower = cmd.lower()
    # 必须是 aios_tools 下的脚本
    if '/aios_tools/' not in cmd_lower and '\\aios_tools\\' not in cmd_lower:
        return False
    # 排除我们自己 (kill 脚本本身)
    if '_kill_aios_daemon' in cmd_lower:
        return False
    return True

# 第一步: 找所有 aios_tools/ 下的 python 进程 (包括 _aios_daemon_watchdog 和它 spawn 的)
all_aios_pids = set()
for pid, (exe, ppid) in procs.items():
    if exe.lower() not in ['python.exe', 'pythonw.exe']:
        continue
    cmd = get_cmd(pid)
    if is_aios_target(cmd):
        all_aios_pids.add(pid)

log(f"找到 {len(all_aios_pids)} 个 aios_tools python 进程")

# 第二步: 找出 PID 15408 (已知根进程) 或其他 _aios_daemon_watchdog.py
roots = set()
for pid in all_aios_pids:
    cmd = get_cmd(pid)
    if '_aios_daemon_watchdog.py' in cmd:
        roots.add(pid)

log(f"找到 {len(roots)} 个 _aios_daemon_watchdog 根: {roots}")

# 第三步: BFS 找所有子孙 (cmd.exe / conhost.exe / powershell.exe)
def find_descendants(root_pid, procs):
    children = {}
    for pid, (exe, ppid) in procs.items():
        children.setdefault(ppid, []).append(pid)
    queue = [root_pid]
    descendants = set()
    while queue:
        cur = queue.pop()
        for child in children.get(cur, []):
            if child not in descendants:
                descendants.add(child)
                queue.append(child)
    return descendants

all_to_kill = set(all_aios_pids)
for root in roots:
    desc = find_descendants(root, procs)
    all_to_kill.update(desc)
    log(f"  Root PID={root} 子孙={len(desc)} 个")

# 加额外: 直接是 cmd.exe / powershell.exe / conhost.exe 的 PPID 都在 all_to_kill 里
# 因为 spawn 它们的就是 aios_daemon 子进程
# (已经在 BFS 里包含)

log(f"\n共 {len(all_to_kill)} 个进程待杀")

# 杀 (倒序 = 先杀叶子)
killed = 0
for pid in sorted(all_to_kill, reverse=True):
    exe = procs.get(pid, ('?', '?'))[0]
    cmd = get_cmd(pid)
    if kill_pid(pid):
        killed += 1
        log(f"  ✓ KILLED PID={pid} {exe}  {cmd[:80]}")
    else:
        log(f"  ✗ FAILED PID={pid} {exe}")

log(f"\n=== DONE: 杀 {killed}/{len(all_to_kill)} 个进程 ===")
