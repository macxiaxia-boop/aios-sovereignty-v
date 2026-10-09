#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_proc_snoop.py v2 - 轮询 Win32_Process 找出杀手

每 1s 查一次所有进程, 比对上次记录, 找出消失的进程 (被杀的)
消失时记录: PID + Name + PPID + 父进程 cmdline

写到 _proc_snoop.log + _proc_kill.log
"""
import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime

LOG = Path(r"D:\AIOS\_proc_snoop.log")
KILL_LOG = Path(r"D:\AIOS\_proc_kill.log")
STATE_FILE = Path(r"D:\AIOS\_proc_snoop_state.json")

DURATION = 300  # 5 分钟

def log(msg):
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

def log_kill(msg):
    try:
        with open(KILL_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass

log(f"_proc_snoop v2 START PID={os.getpid()}")

try:
    import win32com.client
    pythoncom = __import__("pythoncom")
except ImportError:
    log("pywin32 not available, exit")
    sys.exit(1)

pythoncom.CoInitialize()
try:
    wmi = win32com.client.Dispatch("WbemScripting.SWbemLocator")
    svc = wmi.ConnectServer(".", "root\\cimv2")
    log("✓ WMI 连接成功")
except Exception as e:
    log(f"✗ WMI 连接失败: {e}")
    sys.exit(1)


def query_all_procs():
    """返回 {PID: (Name, PPID, CmdLine)}"""
    result = {}
    try:
        q = svc.ExecQuery("SELECT ProcessId, Name, ParentProcessId, CommandLine FROM Win32_Process")
        for p in q:
            try:
                pid = int(p.ProcessId)
                name = str(p.Name)
                ppid = int(p.ParentProcessId) if p.ParentProcessId else 0
                cmd = str(p.CommandLine or "")[:200]
                result[pid] = (name, ppid, cmd)
            except Exception:
                continue
    except Exception as e:
        log(f"query err: {e}")
    return result


def lookup_parent(ppid, procs):
    """反查父进程名+cmdline"""
    if ppid in procs:
        return procs[ppid]
    # 不在本次列表里 (父进程也死了), 返回 None
    return (None, None, None)


# 启动: 第一轮记录全部进程 (避免第一轮就被判为"被杀")
log("=== 第一轮 (基线) ===")
prev = query_all_procs()
log(f"基线进程数: {len(prev)}")

# 持续轮询
end_time = time.time() + DURATION
log(f"开始监控 {DURATION} 秒...")
tick = 0
try:
    while time.time() < end_time:
        time.sleep(1)
        tick += 1
        curr = query_all_procs()
        # 找出消失的进程 (prev 有但 curr 没有)
        gone = set(prev.keys()) - set(curr.keys())
        if gone:
            for pid in gone:
                if pid in prev:
                    name, ppid, cmd = prev[pid]
                    # 只记录 watchdog/heartbeat 相关
                    interesting = any(k in (name + cmd).lower() for k in [
                        'python', 'watchdog', 'heartbeat', 'popup_cure',
                        'stage_watchdog', 'aios_daemon'
                    ])
                    marker = "💀" if interesting else "  "
                    msg = f"{marker} KILL PID={pid:>6} Name={name:25} PPID={ppid:>6} Cmd={cmd[:120]}"
                    log(msg)
                    log_kill(msg)
                    # 反查杀手父进程
                    if ppid and ppid in prev:
                        pname, pppid, pcmd = prev[ppid]
                        killer_msg = f"   KILLER PID={ppid} Name={pname} Cmd={pcmd[:120]}"
                        log(killer_msg)
                        log_kill(killer_msg)
        prev = curr

        # 每 30s 输出一次 alive 摘要
        if tick % 30 == 0:
            log(f"[t={tick}s] alive={len(curr)} killed_in_window={len(gone)}")

except KeyboardInterrupt:
    log("KeyboardInterrupt")
except Exception as e:
    log(f"loop err: {e}")
    import traceback
    log(traceback.format_exc())

log("_proc_snoop DONE")
pythoncom.CoUninitialize()
