#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_watchdog_alive_check_multi.py - R267 立 (2026-09-29)

根因 R259 旧版 _watchdog_alive_check.py 只监控 _aios_daemon_watchdog.py,
popup cure / stage watchdog 死了 4 天没人重启.

R267 治本: 同时监控 3 个 watchdog (popup cure + stage + aios daemon),
任一死 -> 30s 内自动重启.

架构 (R70 + #103 + #60 + #78 + #82):
  - 本脚本由 SCM "AIOSWatchdogAliveCheck" 服务启 (30s restart on crash)
  - 每 30s 用 ctypes 检查 3 个 watchdog PID
  - 任意 watchdog 死 -> 用 Popen + CREATE_NO_WINDOW|DETACHED_PROCESS 启
  - 节流: 同一 watchdog 5min 内只重启 1 次 (避免重启风暴)
  - 本脚本不死 (简单 loop + sleep, 不调外部)

触达红线: #101 · #103 · #108 · #22 L5 · #60 · #70 · #95 · #78 · #82 · #29
"""
import subprocess
import os
import sys
import json
import time
import ctypes
import argparse
from ctypes import wintypes
from datetime import datetime, timedelta

# R203 治本: ctypes 直接调 Win32 API (零子进程调用)
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008

_kernel32 = ctypes.windll.kernel32
_OpenProcess = _kernel32.OpenProcess
_OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_bool, ctypes.c_uint32]
_OpenProcess.restype = ctypes.c_void_p
_GetExitCodeProcess = _kernel32.GetExitCodeProcess
_GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(wintypes.DWORD)]
_GetExitCodeProcess.restype = ctypes.c_bool
_CloseHandle = _kernel32.CloseHandle
_CloseHandle.argtypes = [ctypes.c_void_p]
_CloseHandle.restype = ctypes.c_bool

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PYTHONW = r"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\pythonw.exe"

# R267 治本: 同时监控 3 个 watchdog
WATCHDOGS = [
    {
        "name": "popup_cure",
        "script": r"D:\Tools\TikTokDownloader\watchdog\_popup_cure_watchdog.py",
        "args": [],
        "cwd": r"D:\Tools\TikTokDownloader\watchdog",
        "pid_file": r"D:\Tools\TikTokDownloader\watchdog\popup_cure_watchdog.pid",
        "log": r"D:\Tools\TikTokDownloader\watchdog\popup_cure_watchdog.log",
    },
    {
        "name": "stage_watchdog",
        "script": r"D:\Tools\TikTokDownloader\watchdog\_stage_watchdog.py",
        "args": [],
        "cwd": r"D:\Tools\TikTokDownloader\watchdog",
        "pid_file": r"D:\Tools\TikTokDownloader\watchdog\stage_watchdog.pid",
        "log": r"D:\Tools\TikTokDownloader\watchdog\stage_watchdog.log",
    },
    {
        "name": "aios_daemon",
        "script": r"D:\个人文件\AI\Operator\aios_tools\_aios_daemon_watchdog.py",
        "args": ["--interval", "30"],
        "cwd": r"D:\个人文件\AI\Operator\aios_tools",
        "pid_file": r"D:\个人文件\AI\Operator\handoff\watchdog\_aios_daemon_watchdog.pid",
        "log": r"D:\个人文件\AI\Operator\aios_tools\_watchdog_alive_check.log",
    },
]

LOG_FILE = r"D:\AIOS\_watchdog_alive_check_multi.log"
STATE_FILE = r"D:\AIOS\_watchdog_alive_check_multi_state.json"
RESTART_HISTORY_FILE = r"D:\AIOS\_watchdog_alive_check_multi_history.json"
MIN_RESTART_INTERVAL_SECONDS = 300


def alive_pid(pid):
    """R203 ctypes OpenProcess + GetExitCodeProcess 检查 PID"""
    try:
        h = _OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return False
        try:
            code = wintypes.DWORD(0)
            if _GetExitCodeProcess(h, ctypes.byref(code)):
                return code.value == STILL_ACTIVE
            return False
        finally:
            _CloseHandle(h)
    except Exception:
        return False


def read_pid_file(pid_file):
    if not os.path.exists(pid_file):
        return None
    try:
        with open(pid_file, "r", encoding="utf-8") as f:
            data = f.read().strip()
            # 支持 JSON {"pid": xxx} 或纯数字
            if data.startswith("{"):
                return int(json.loads(data).get("pid", 0))
            return int(data)
    except Exception:
        return None


def clean_pid_file(pid_file):
    try:
        if os.path.exists(pid_file):
            os.remove(pid_file)
    except Exception:
        pass


def log(msg):
    line = "[" + datetime.now().isoformat() + "] " + str(msg)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    try:
        sys.stdout.buffer.write((line + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    except Exception:
        pass


def write_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def check_throttle(name):
    """检查是否在节流窗口 (5min 内同 watchdog 只重启 1 次)"""
    if not os.path.exists(RESTART_HISTORY_FILE):
        return False
    try:
        with open(RESTART_HISTORY_FILE, "r", encoding="utf-8") as f:
            history = json.load(f)
    except Exception:
        return False
    one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
    for h in history:
        if h.get("name") == name and h.get("ts", "") >= one_hour_ago:
            try:
                last_dt = datetime.fromisoformat(h["ts"])
                elapsed = (datetime.now() - last_dt).total_seconds()
                if elapsed < MIN_RESTART_INTERVAL_SECONDS:
                    log(f"R267 THROTTLE [{name}] 距上次 restart {int(elapsed)}s, 跳过")
                    return True
            except Exception:
                pass
    return False


def record_restart(name):
    try:
        history = []
        if os.path.exists(RESTART_HISTORY_FILE):
            try:
                with open(RESTART_HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []
        history.append({"name": name, "ts": datetime.now().isoformat()})
        cutoff24 = (datetime.now() - timedelta(hours=24)).isoformat()
        history = [h for h in history if h.get("ts", "") >= cutoff24]
        with open(RESTART_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def start_watchdog(wd):
    """R267 启 watchdog (R203 治本: Popen + CREATE_NO_WINDOW + DETACHED_PROCESS)"""
    if check_throttle(wd["name"]):
        return False
    try:
        cmd = [PYTHONW, "-u", wd["script"]] + wd["args"]
        proc = subprocess.Popen(
            cmd,
            cwd=wd["cwd"],
            creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
        log(f"R267 RESTART [{wd['name']}] PID={proc.pid}")
        record_restart(wd["name"])
        # 1s 后验证 alive
        time.sleep(1)
        if not alive_pid(proc.pid):
            log(f"R267 VERIFY_FAIL [{wd['name']}] PID={proc.pid} T+1s 死了")
            return False
        return True
    except Exception as e:
        log(f"R267 ERR [{wd['name']}] restart: {repr(e)}")
        return False


def main_loop(interval):
    log("=" * 60)
    log("R267 watchdog_alive_check_multi v1 (2026-09-29)")
    log(f"监控 {len(WATCHDOGS)} 个 watchdog:")
    for wd in WATCHDOGS:
        log(f"  - {wd['name']}: {wd['script']}")
    log(f"检查间隔: {interval}s, PID: {os.getpid()}")
    log("=" * 60)

    cycle = 0
    while True:
        cycle += 1
        try:
            watchdog_states = []
            for wd in WATCHDOGS:
                saved_pid = read_pid_file(wd["pid_file"])
                alive_now = saved_pid is not None and alive_pid(saved_pid)
                watchdog_states.append({
                    "name": wd["name"],
                    "pid": saved_pid,
                    "alive": alive_now,
                })
                if not alive_now:
                    if saved_pid is not None:
                        log(f"R267 DETECTED DEAD [{wd['name']}] PID={saved_pid}")
                    else:
                        log(f"R267 DETECTED NO_PID_FILE [{wd['name']}]")
                    if start_watchdog(wd):
                        log(f"R267 [{wd['name']}] restarted OK")
                    else:
                        log(f"R267 [{wd['name']}] restart FAILED or THROTTLED")

            state = {
                "cycle": cycle,
                "ts": datetime.now().isoformat(),
                "watchdogs": watchdog_states,
            }
            write_state(state)

            # 每 60 cycle (30min) 打一次 alive 摘要
            if cycle % 60 == 0:
                summary = " | ".join(
                    f"{w['name']}={'ALIVE' if w['alive'] else 'DEAD'}"
                    for w in watchdog_states
                )
                log(f"[CYCLE {cycle}] {summary}")
        except Exception as e:
            log(f"[CYCLE {cycle}] ERR: {repr(e)}")

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="R267 multi-watchdog alive check")
    parser.add_argument("--interval", type=int, default=30, help="检查间隔秒数")
    args = parser.parse_args()
    main_loop(args.interval)
