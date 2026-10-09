"""aios_guard_daemon.py - R-Codex-Cure-2026-09-29 V6
AIOS daemon watchdog: 完全独立进程 (DETACHED_PROCESS), 不依赖 stdin/stderr.
Python watchdog + auto restart AIOS daemon forever.
"""
import ctypes
import ctypes.wintypes as w
import subprocess
import sys
import time
import os
from pathlib import Path

# Windows API constants
DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

PQLI = 0x1000

AIOS_EXE = Path(r"D:\个人文件\AI\Operator\aios_tools\AIOS_Autonomy_Daemon.exe")
CODEX_EXE = Path(r"D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\app\ChatGPT.exe")
LOG = Path(r"D:\AIOS\_aios_guard.log")
INTERVAL = 15


class P(ctypes.Structure):
    _fields_ = [
        ("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(w.ULONG)), ("th32ModuleID", w.DWORD),
        ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


def count_proc(name: str) -> int:
    snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(2, 0)
    pe = P()
    pe.dwSize = ctypes.sizeof(P)
    ctypes.windll.kernel32.Process32First(snap, ctypes.byref(pe))
    n = 0
    while True:
        h = ctypes.windll.kernel32.OpenProcess(PQLI, False, pe.th32ProcessID)
        if h:
            sz = ctypes.create_unicode_buffer(260)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, sz, ctypes.byref(w.DWORD(260)))
            if sz.value.lower().endswith(name.lower()):
                n += 1
            ctypes.windll.kernel32.CloseHandle(h)
        if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(pe)):
            break
    ctypes.windll.kernel32.CloseHandle(snap)
    return n


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)


def start_aios() -> bool:
    if count_proc("AIOS_Autonomy_Daemon.exe") > 0:
        return True
    if not AIOS_EXE.exists():
        log(f"ERROR: {AIOS_EXE} not found")
        return False
    try:
        # DETACHED_PROCESS + CREATE_NO_WINDOW: 完全脱离父进程, 不被杀
        subprocess.Popen(
            [str(AIOS_EXE)],
            creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log("started AIOS daemon")
        return True
    except Exception as e:
        log(f"ERROR starting AIOS: {e}")
        return False


def start_codex() -> bool:
    if count_proc("ChatGPT.exe") > 0:
        return True
    if not CODEX_EXE.exists():
        log(f"ERROR: {CODEX_EXE} not found")
        return False
    try:
        subprocess.Popen(
            [str(CODEX_EXE)],
            creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        log("started Codex")
        return True
    except Exception as e:
        log(f"ERROR starting Codex: {e}")
        return False


def self_daemonize() -> bool:
    """让本进程完全脱离父进程 + 不被杀.
    必须在 main() 开始时调用一次."""
    # 已经 detached 不需要重复
    # 检查 stdin/stdout 是否还有连
    try:
        # 关闭 stdin, 避免父进程关 stdin 时导致 watchdog 退出
        pass
    except Exception:
        pass
    return True


def main() -> int:
    self_daemonize()
    log(f"=== AIOS guard daemon started (interval={INTERVAL}s) ===")
    log(f"AIOS: {AIOS_EXE}")
    log(f"Codex: {CODEX_EXE}")

    last_codex_start = 0
    cycle = 0
    while True:
        cycle += 1
        aios_count = count_proc("AIOS_Autonomy_Daemon.exe")
        codex_count = count_proc("ChatGPT.exe")

        log(f"cycle={cycle}: AIOS={aios_count}, Codex={codex_count}")

        # 1. 检查 AIOS
        if aios_count == 0:
            log("AIOS daemon NOT running, starting ...")
            start_aios()
            time.sleep(5)
            aios_count_new = count_proc("AIOS_Autonomy_Daemon.exe")
            log(f"after start: AIOS={aios_count_new}")
            if aios_count_new == 0:
                log("AIOS still NOT running, will retry next cycle")

        # 2. 如果 AIOS 刚启动 (或重启了), 等 5s 让它初始化, 再启 Codex
        if count_proc("AIOS_Autonomy_Daemon.exe") > 0 and codex_count == 0:
            now = time.time()
            if now - last_codex_start > 30:  # 不要每 15s 启动一次 Codex
                log("AIOS OK but Codex NOT running, starting Codex ...")
                start_codex()
                last_codex_start = now
                time.sleep(15)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("guard interrupted")
        sys.exit(0)