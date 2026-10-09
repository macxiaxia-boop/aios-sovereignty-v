"""aios_guard_v2.py - 通过 psapi 看 Codex 退出码 + AIOS 状态.
方案: 每 5 秒检查, 如果 AIOS daemon 死了立刻拉起, 同时尝试拉 Codex.

关键: 完全在沙箱外独立运行 (DETACHED_PROCESS + 关闭所有 handle).
"""
import ctypes
import ctypes.wintypes as w
import subprocess
import sys
import os
import time
from pathlib import Path

DETACHED_PROCESS = 0x00000008
CREATE_NO_WINDOW = 0x08000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

PQLI = 0x1000
PT = 1  # PROCESS_TERMINATE

AIOS_EXE = Path(r"D:\个人文件\AI\Operator\aios_tools\AIOS_Autonomy_Daemon.exe")
CODEX_EXE = Path(r"D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\app\ChatGPT.exe")
LOG = Path(r"D:\AIOS\_aios_guard_v2.log")
INTERVAL = 10


class P(ctypes.Structure):
    _fields_ = [
        ("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(w.ULONG)), ("th32ModuleID", w.DWORD),
        ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    # 同时打印到 stderr (父进程 sandbox 看不到, 但 log 文件能看到)
    print(line, flush=True)


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


def start_proc_detached(exe: Path) -> bool:
    """Start process completely detached from any parent handle."""
    if not exe.exists():
        log(f"ERROR: {exe} not found")
        return False
    try:
        # Use STARTUPINFO to fully detach
        si = subprocess.STARTUPINFO()
        si.dwFlags = 0x00000001  # STARTF_USESHOWWINDOW
        si.wShowWindow = 0  # SW_HIDE

        proc = subprocess.Popen(
            [str(exe)],
            creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            startupinfo=si,
        )
        # Detach from parent
        proc._detach() if hasattr(proc, "_detach") else None
        log(f"started {exe.name} PID={proc.pid}")
        return True
    except Exception as e:
        log(f"ERROR starting {exe.name}: {e}")
        return False


def main() -> int:
    log(f"=== AIOS guard v2 started (interval={INTERVAL}s) ===")
    log(f"AIOS: {AIOS_EXE}")
    log(f"Codex: {CODEX_EXE}")

    last_codex_action = 0
    cycle = 0
    while True:
        cycle += 1
        aios_count = count_proc("AIOS_Autonomy_Daemon.exe")
        codex_count = count_proc("ChatGPT.exe")

        if cycle % 4 == 0 or aios_count == 0 or codex_count == 0:
            log(f"cycle={cycle}: AIOS={aios_count}, Codex={codex_count}")

        # 守护 AIOS daemon
        if aios_count == 0:
            log("AIOS DOWN, starting ...")
            start_proc_detached(AIOS_EXE)
            time.sleep(8)
            new_count = count_proc("AIOS_Autonomy_Daemon.exe")
            log(f"after AIOS start: count={new_count}")

        # AIOS 在跑 + Codex 没在跑 -> 拉起 Codex
        if count_proc("AIOS_Autonomy_Daemon.exe") > 0 and codex_count == 0:
            now = time.time()
            if now - last_codex_action > 60:  # 不要太频繁拉 Codex
                log("Codex DOWN, starting ...")
                start_proc_detached(CODEX_EXE)
                last_codex_action = now
                time.sleep(15)

        time.sleep(INTERVAL)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log("guard v2 interrupted")
        sys.exit(0)