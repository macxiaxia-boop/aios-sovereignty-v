"""start_aios_guard_daemon.py - 启动 AIOS 守护进程 (DETACHED_PROCESS)."""
import subprocess
import sys
import os

GUARD = r"D:\AIOS\aios_guard_daemon.py"
PYTHON = r"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe"


def main():
    print(f"启动 AIOS guard daemon: {GUARD}")
    # DETACHED_PROCESS | CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
    # 标志 0x00000008 | 0x08000008 | 0x00000200 = 0x08000208
    flags = 0x00000008 | 0x08000008 | 0x00000200
    p = subprocess.Popen(
        [PYTHON, "-u", GUARD],
        creationflags=flags,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    print(f"started PID={p.pid}")
    print("watchdog 已脱离本进程, 会持续运行, 死了就拉起 AIOS + Codex")
    return 0


if __name__ == "__main__":
    sys.exit(main())