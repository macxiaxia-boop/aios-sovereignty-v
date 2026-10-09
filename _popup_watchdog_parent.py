#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_popup_watchdog_parent.py - R268 立 (2026-09-29)

根因: R267 multi-watchdog + popup cure / stage watchdog 都被 SCM 30s restart on crash
      反复杀, 形成死亡循环. popup_cure 启动后 5-15s 必死 (PID 文件 mtime = LOG mtime = 硬终止)

R268 治本:
- 完全独立于 SCM, 用 schtasks /sc onstart /ru SYSTEM 注册开机自启
- watchdog_parent.py 自身用 Popen + DETACHED_PROCESS 启动 3 个 watchdog (与 watchdog_parent 完全解耦)
- 每 5s 检查 PID 文件 mtime, 超过 60s 没更新 = watchdog 死了, 重启
- watchdog_parent 自己不写 LOG 到 popup cure 同目录 (避免文件锁冲突)
- watchdog_parent 不被杀: schtasks /sc onstart 1 minute check, 死了 schtasks 1 分钟内自动拉起

架构:
  schtasks /sc onstart -> pythonw.exe _popup_watchdog_parent.py
     -> Popen (DETACHED) -> _popup_cure_watchdog.py  (独立进程组)
     -> Popen (DETACHED) -> _stage_watchdog.py        (独立进程组)
     -> Popen (DETACHED) -> _aios_daemon_watchdog.py  (独立进程组)
  watchdog_parent 每 5s 看 PID 文件 mtime, 死了重启 (用 Popen 不杀子进程)
"""
import subprocess
import os
import sys
import time
import ctypes
import argparse
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

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

# R268: watchdog_parent 自己的 PID 文件 + 日志, 完全独立目录
WD_PARENT_DIR = Path(r"D:\AIOS")
WD_PARENT_LOG = WD_PARENT_DIR / "_popup_watchdog_parent.log"
WD_PARENT_PID = WD_PARENT_DIR / "_popup_watchdog_parent.pid"
WD_PARENT_STATE = WD_PARENT_DIR / "_popup_watchdog_parent_state.json"

WATCHDOGS = [
    {
        "name": "popup_cure",
        "script": r"D:\Tools\TikTokDownloader\watchdog\_popup_cure_watchdog.py",
        "args": [],
        "cwd": r"D:\Tools\TikTokDownloader\watchdog",
        "pid_file": r"D:\Tools\TikTokDownloader\watchdog\popup_cure_watchdog.pid",
    },
    {
        "name": "stage_watchdog",
        "script": r"D:\Tools\TikTokDownloader\watchdog\_stage_watchdog.py",
        "args": [],
        "cwd": r"D:\Tools\TikTokDownloader\watchdog",
        "pid_file": r"D:\Tools\TikTokDownloader\watchdog\stage_watchdog.pid",
    },
    {
        "name": "hide_console_windows",
        "script": r"D:\AIOS\_hide_console_windows.py",
        "args": [],
        "cwd": r"D:\AIOS",
        "pid_file": r"D:\AIOS\_hide_console_windows.pid",
    },
    # R271 移除: aios_daemon = _aios_daemon_watchdog.py 是 spawn 工厂,
    #            启动它会拉 14+ 个 bridge polling daemon 子进程 = 控制台窗口闪烁真凶
]

# watchdog 死了 = PID 文件 mtime 超 N 秒没更新 (或 PID 进程死了)
WATCHDOG_DEAD_THRESHOLD_SECONDS = 60  # popup_cure 每 10s 写 PID, 60s 没更新=死了
MIN_RESTART_INTERVAL_SECONDS = 60  # 同 watchdog 1 分钟内只重启 1 次

_last_restart: dict = {}  # name -> last restart time


def log(msg):
    line = "[" + datetime.now().isoformat() + "] " + str(msg)
    try:
        with open(WD_PARENT_LOG, "a", encoding="utf-8") as f:
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
        with open(WD_PARENT_STATE, "w", encoding="utf-8") as f:
            import json
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def alive_pid(pid):
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


def read_pid(pid_file):
    p = Path(pid_file)
    if not p.exists():
        return None, 0
    try:
        import json
        data = json.loads(p.read_text(encoding="utf-8"))
        return int(data.get("pid", 0)), p.stat().st_mtime
    except Exception:
        try:
            return int(p.read_text(encoding="utf-8").strip()), p.stat().st_mtime
        except Exception:
            return None, 0


def check_throttle(name):
    last = _last_restart.get(name, 0)
    if time.time() - last < MIN_RESTART_INTERVAL_SECONDS:
        return True
    return False


def start_watchdog(wd):
    """R268: 用 Popen + DETACHED_PROCESS + CREATE_NO_WINDOW 启动 watchdog
    不杀旧进程 (让 watchdog 死亡自决), 只确保新进程起来了
    """
    if check_throttle(wd["name"]):
        log(f"R268 THROTTLE [{wd['name']}] 1min 内已重启过, 跳过")
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
        log(f"R268 RESTART [{wd['name']}] PID={proc.pid} cmd={' '.join(cmd)}")
        _last_restart[wd["name"]] = time.time()
        time.sleep(2)
        if not alive_pid(proc.pid):
            log(f"R268 VERIFY_FAIL [{wd['name']}] PID={proc.pid} 2s 内死了")
            return False
        return True
    except Exception as e:
        log(f"R268 ERR [{wd['name']}] restart: {repr(e)}")
        return False


def check_watchdog(wd):
    """检查 watchdog: 进程死了 OR PID 文件 mtime 超阈值 = 死了"""
    pid, mtime = read_pid(wd["pid_file"])
    name = wd["name"]
    now = time.time()

    # 1. PID 文件不存在
    if pid is None:
        log(f"R268 [{name}] PID 文件不存在")
        return False

    # 2. 进程死了
    if not alive_pid(pid):
        log(f"R268 [{name}] PID={pid} 进程已死")
        return False

    # 3. PID 文件 mtime 超阈值 (说明 watchdog 没在 tick)
    age = now - mtime
    if age > WATCHDOG_DEAD_THRESHOLD_SECONDS:
        log(f"R268 [{name}] PID={pid} 进程活着但 PID 文件 {int(age)}s 没更新 (阈值 {WATCHDOG_DEAD_THRESHOLD_SECONDS}s) - watchdog 卡住或死了")
        return False

    return True


def main_loop(interval):
    log("=" * 60)
    log("R268 _popup_watchdog_parent v1 (2026-09-29)")
    log(f"监管 {len(WATCHDOGS)} 个 watchdog:")
    for wd in WATCHDOGS:
        log(f"  - {wd['name']}: {wd['script']}")
    log(f"检查间隔: {interval}s, dead_threshold: {WATCHDOG_DEAD_THRESHOLD_SECONDS}s, PID: {os.getpid()}")
    log("=" * 60)

    # 启动时写 PID 文件
    try:
        WD_PARENT_PID.write_text(str(os.getpid()), encoding="utf-8")
    except Exception:
        pass

    cycle = 0
    while True:
        cycle += 1
        try:
            watchdog_states = []
            for wd in WATCHDOGS:
                alive = check_watchdog(wd)
                pid, mtime = read_pid(wd["pid_file"])
                watchdog_states.append({
                    "name": wd["name"],
                    "pid": pid,
                    "alive": alive,
                    "pid_mtime_age": int(time.time() - mtime) if mtime else -1,
                })
                if not alive:
                    if start_watchdog(wd):
                        log(f"R268 [{wd['name']}] restarted OK")
                    else:
                        log(f"R268 [{wd['name']}] restart FAILED or THROTTLED")

            import json
            state = {
                "cycle": cycle,
                "ts": datetime.now().isoformat(),
                "watchdogs": watchdog_states,
            }
            write_state(state)

            # 每 12 cycle (1min) 更新 PID 文件 mtime (让 schtasks 知道 watchdog_parent 还活着)
            if cycle % 12 == 0:
                try:
                    WD_PARENT_PID.write_text(str(os.getpid()), encoding="utf-8")
                except Exception:
                    pass
                summary = " | ".join(
                    f"{w['name']}={'ALIVE' if w['alive'] else 'DEAD'}"
                    for w in watchdog_states
                )
                log(f"[CYCLE {cycle}] {summary}")
        except Exception as e:
            log(f"[CYCLE {cycle}] ERR: {repr(e)}")

        time.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="R268 watchdog parent (independent of SCM)")
    parser.add_argument("--interval", type=int, default=5, help="检查间隔秒数")
    args = parser.parse_args()
    main_loop(args.interval)
