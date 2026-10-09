"""R267 治本 + R268: 用 pythonw.exe spawn watchdog (python.exe 是 console subsystem, 即使 CREATE_NO_WINDOW 也闪)
"""
import subprocess, time, os, sys

CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
PYTHONW = r"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\pythonw.exe"

# R267: 检查禁用 sentinel 文件
DISABLE_SENTINEL = r"D:\Tools\TikTokDownloader\watchdog\watchdog_wrapper_disabled.flag"

def run_once(script):
    if os.path.exists(DISABLE_SENTINEL):
        sys.exit(0)
    try:
        # 用 pythonw.exe (windows subsystem, 无 console) + DETACHED_PROCESS + CREATE_NO_WINDOW
        subprocess.run([PYTHONW, "-u", script, "60"],
                       creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
                       timeout=55)
    except Exception as e:
        print(f"[{script}] err: {e}", flush=True)

if __name__ == "__main__":
    while True:
        run_once(r"D:\AIOS\_openclaw_18792_watchdog.py")
        run_once(r"D:\AIOS\_openai_codex_desktop_watchdog.py")
        run_once(r"D:\AIOS\_openai_codex_beta_watchdog.py")
        time.sleep(60)