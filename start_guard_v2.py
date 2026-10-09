"""start_guard_v2.py - 启动 guard v2 (DETACHED_PROCESS 完全脱离)."""
import subprocess
import sys

GUARD = r"D:\AIOS\aios_guard_v2.py"
PYTHON = r"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe"

# DETACHED_PROCESS | CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP
flags = 0x00000008 | 0x08000008 | 0x00000200

p = subprocess.Popen(
    [PYTHON, "-u", GUARD],
    creationflags=flags,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    close_fds=True,
)
print(f"guard v2 PID={p.pid}")
# 不要等它退出 - 它是守护进程, 必须独立
p._detach() if hasattr(p, "_detach") else None
print("guard v2 已脱离, 持续运行守护 AIOS daemon")
sys.exit(0)