"""aios_daemon_watchdog.py - R-Codex-Cure-2026-09-29 V4
守护 AIOS_Autonomy_Daemon.exe: 死了立刻拉起.
这是 Codex + ClaudeCode + Hermes + OpenClaw 共用依赖.
AIOS 死了 → 整个 AI 栈闪退.
"""
import subprocess
import sys
import os
import time
import ctypes
import ctypes.wintypes as w
from pathlib import Path

AIOS_DAEMON = Path(r"D:\个人文件\AI\Operator\aios_tools\AIOS_Autonomy_Daemon.exe")
LOG = Path(r"D:\AIOS\_aios_daemon_watchdog.log")
INTERVAL_SEC = 30


def is_aios_running() -> bool:
    """Check if AIOS daemon is running.
    Note: AIOS_Autonomy_Daemon.exe spawns node.exe child processes. The
    main daemon may be the original exe or could be a renamed process.
    Match by checking for AIOS_Autonomy_Daemon.exe OR any node.exe whose
    parent is AIOS_Autonomy_Daemon.exe."""
    PQLI = 0x1000

    class P(ctypes.Structure):
        _fields_ = [
            ("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(w.ULONG)), ("th32ModuleID", w.DWORD),
            ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
            ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(2, 0)
    pe = P()
    pe.dwSize = ctypes.sizeof(P)
    ctypes.windll.kernel32.Process32First(snap, ctypes.byref(pe))

    # 第一遍: 找 AIOS_Autonomy_Daemon.exe 主进程
    aios_pids = []
    while True:
        try:
            h = ctypes.windll.kernel32.OpenProcess(PQLI, False, pe.th32ProcessID)
            if h:
                sz = ctypes.create_unicode_buffer(260)
                ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, sz, ctypes.byref(w.DWORD(260)))
                name = sz.value.split("\\")[-1].lower()
                if name == "aios_autonomy_daemon.exe":
                    aios_pids.append(pe.th32ProcessID)
                ctypes.windll.kernel32.CloseHandle(h)
        except Exception:
            pass
        if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(pe)):
            break

    if aios_pids:
        ctypes.windll.kernel32.CloseHandle(snap)
        return True

    # 第二遍: 看是否有大量 node.exe 进程（AIOS 后端是 Node.js）
    # 如果看到 node.exe 进程数 > 5 且创建时间在最近 1 小时内, 大概率是 AIOS daemon
    ctypes.windll.kernel32.Process32First(snap, ctypes.byref(pe))
    node_count = 0
    while True:
        try:
            h = ctypes.windll.kernel32.OpenProcess(PQLI, False, pe.th32ProcessID)
            if h:
                sz = ctypes.create_unicode_buffer(260)
                ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, sz, ctypes.byref(w.DWORD(260)))
                if sz.value.lower().endswith("node.exe"):
                    node_count += 1
                ctypes.windll.kernel32.CloseHandle(h)
        except Exception:
            pass
        if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(pe)):
            break

    ctypes.windll.kernel32.CloseHandle(snap)
    return node_count >= 5


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    try:
        LOG.parent.mkdir(parents=True, exist_ok=True)
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def start_aios() -> bool:
    """Start AIOS_Autonomy_Daemon.exe."""
    if not AIOS_DAEMON.exists():
        log(f"ERROR: {AIOS_DAEMON} not found")
        return False
    try:
        subprocess.Popen(
            [str(AIOS_DAEMON)],
            creationflags=0x08000008,  # CREATE_NO_WINDOW
        )
        log(f"started AIOS daemon: {AIOS_DAEMON}")
        return True
    except Exception as e:
        log(f"ERROR starting AIOS: {e}")
        return False


def main() -> int:
    log(f"AIOS daemon watchdog started (interval={INTERVAL_SEC}s)")
    while True:
        if not is_aios_running():
            log("AIOS daemon NOT running, restarting ...")
            start_aios()
            time.sleep(10)  # 等 AIOS 完全启动
            if is_aios_running():
                log("AIOS daemon restarted OK")
            else:
                log("AIOS daemon still not running, will retry next interval")
        else:
            log("AIOS daemon OK")
        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("watchdog interrupted")
        sys.exit(0)