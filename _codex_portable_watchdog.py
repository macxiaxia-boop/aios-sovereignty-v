# -*- coding: utf-8 -*-
# _codex_portable_watchdog.py - R319 Codex portable watchdog (monitor codex.exe PID)
# Monitor: tasklist IMAGENAME eq codex.exe
# Restart: start "" "D:\...\app\ChatGPT.exe"
# 2026-09-29
import subprocess
import time
import sys
import os

CODEX_PORTABLE_DIR = r"D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】"
CODEX_EXE = os.path.join(CODEX_PORTABLE_DIR, r"app\ChatGPT.exe")
LOG = r"D:\AIOS\_codex_portable_watchdog.log"
POLL_INTERVAL_S = 10
POLL_TIMEOUT_S = 30


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


def is_codex_alive():
    """Check if codex.exe process exists (tasklist)."""
    out = subprocess.run(
        ["cmd", "/c", "tasklist", "/NH", "/FI", "IMAGENAME eq codex.exe"],
        capture_output=True, timeout=10,
    )
    text = out.stdout.decode("utf-8", errors="replace")
    return "codex.exe" in text.lower()


def launch_codex():
    """Launch portable Codex via start (non-blocking)."""
    try:
        subprocess.Popen(
            ["cmd", "/c", "start", "", CODEX_EXE],
            cwd=CODEX_PORTABLE_DIR,
            creationflags=0x08000008,  # CREATE_NO_WINDOW | DETACHED_PROCESS
        )
        log(f"Codex launch issued: {CODEX_EXE}")
        return True
    except Exception as e:
        log(f"Codex launch FAILED: {e}")
        return False


if __name__ == "__main__":
    log(f"=== Codex portable watchdog run start (pid={os.getpid()}) ===")
    if is_codex_alive():
        log("codex.exe ALIVE - OK (no action)")
        log("=== end (exit=0 alive) ===")
        sys.exit(0)

    log("codex.exe DEAD - launching portable Codex")
    launch_codex()

    start_ts = time.time()
    recovered = False
    while time.time() - start_ts < POLL_TIMEOUT_S:
        time.sleep(POLL_INTERVAL_S)
        if is_codex_alive():
            elapsed = int(time.time() - start_ts)
            log(f"codex.exe ALIVE after {elapsed}s - recovered")
            recovered = True
            break

    if recovered:
        log("=== end (exit=0 recovered) ===")
        sys.exit(0)
    else:
        log("=== end (exit=1 timeout) ===")
        sys.exit(1)