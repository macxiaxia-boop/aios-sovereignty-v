"""diagnose_aios_v2.py - 用 Popen 异步启动 AIOS, 读 stdout/stderr"""
import subprocess
import time
import os

AIOS = r"D:\个人文件\AI\Operator\aios_tools\AIOS_Autonomy_Daemon.exe"

print(f"Starting {AIOS}...")
try:
    p = subprocess.Popen(
        [AIOS],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL,
        creationflags=0x08000008 | 0x00000008,  # CREATE_NO_WINDOW | DETACHED_PROCESS
    )
    print(f"started PID={p.pid}")

    # 等 5s
    time.sleep(5)

    # 看进程还在不在
    poll = p.poll()
    print(f"poll result: {poll}")
    if poll is not None:
        # 进程已退出
        try:
            stdout, stderr = p.communicate(timeout=2)
            print(f"stdout ({len(stdout)} bytes):")
            print(stdout[:3000].decode('gbk', errors='replace'))
            print(f"stderr ({len(stderr)} bytes):")
            print(stderr[:3000].decode('gbk', errors='replace'))
        except Exception as e:
            print(f"communicate error: {e}")
    else:
        print("still running after 5s")
        p.kill()
        stdout, stderr = p.communicate(timeout=2)
        print(f"after kill, stderr: {stderr[:1000].decode('gbk', errors='replace')}")

except Exception as e:
    print(f"ERROR: {e}")