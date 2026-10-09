# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# _openai_codex_desktop_watchdog.py - R313 Codex Desktop alive + auto restart (with lock cleanup)
import subprocess
import time
import sys
import os

CODEX_EXE = r"C:\Program Files\WindowsApps\OpenAI.Codex_26.924.2738.0_x64__2p2nqsd0c76g0\app\ChatGPT.exe"
CODEX_AUMID = "OpenAI.Codex_2p2nqsd0c76g0!OpenAI.Codex"
CODEX_PACKAGE = r"C:\Users\xinzh\AppData\Local\Packages\OpenAI.Codex_2p2nqsd0c76g0"
CODEX_LOCK = os.path.join(CODEX_PACKAGE, "Settings", "roaming.lock")
CODEX_GPU_CACHE = os.path.join(CODEX_PACKAGE, "AC", "INetCache")
LOG = r"D:\AIOS\_openai_codex_desktop_watchdog.log"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def is_codex_running():
    try:
        r = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=5, creationflags=0x08000008)  # R268 治本: 隐藏 tasklist 控制台窗口
        return "ChatGPT.exe" in r.stdout
    except Exception as e:
        log(f"is_codex_running error: {e}")
        return False

def cleanup_lock():
    """R313 V2: clear Electron single-instance lock + GPU cache"""
    cleared = []
    try:
        if os.path.exists(CODEX_LOCK):
            os.remove(CODEX_LOCK)
            cleared.append("roaming.lock")
    except Exception as e:
        log(f"lock cleanup error: {e}")
    try:
        import shutil
        if os.path.exists(CODEX_GPU_CACHE):
            shutil.rmtree(CODEX_GPU_CACHE, ignore_errors=True)
            cleared.append("GPUCache")
    except Exception as e:
        log(f"GPU cache cleanup error: {e}")
    return cleared

def start_codex():
    """R313 V2: cleanup lock first, then try AUMID launch"""
    cleared = cleanup_lock()
    if cleared:
        log(f"Cleared before restart: {cleared}")
    log("Codex DOWN - restarting via AUMID...")
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-Command",
             f'Start-Process "shell:AppsFolder\\{CODEX_AUMID}"'],
            creationflags=0x08000008
        )
        log("Codex restart issued via AUMID")
    except Exception as e:
        log(f"AUMID restart failed: {e}; please start manually from Start Menu")

if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    log(f"Watchdog started (interval={interval}s) [R313 V2 with lock cleanup]")
    while True:
        if not is_codex_running():
            log("Codex process NOT FOUND")
            start_codex()
            time.sleep(90)
        else:
            log("Codex process OK")
        time.sleep(interval)
