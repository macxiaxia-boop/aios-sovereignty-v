# -*- coding: utf-8 -*-
#!/usr/bin/env python3
# _clash_verge_watchdog.py - R314 Clash Verge alive + auto restart (2026-09-29)
import subprocess
import time
import sys
import os

CLASH_EXE = r"D:\1\Clash Verge\clash-verge.exe"
CLASH_PORT = 7897
LOG = r"D:\AIOS\_clash_verge_watchdog.log"

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

def is_port_open():
    try:
        with socket.create_connection(("127.0.0.1", CLASH_PORT), timeout=3) as s:
            return True
    except Exception:
        return False

def is_clash_process_running():
    try:
        r = subprocess.run(["tasklist"], capture_output=True, text=True, timeout=5)
        return "clash-verge.exe" in r.stdout or "verge-mihomo.exe" in r.stdout
    except Exception:
        return False

def restart_clash():
    log("Clash DOWN - restarting clash-verge.exe...")
    try:
        subprocess.Popen(
            [CLASH_EXE],
            cwd=r"D:\1\Clash Verge",
            creationflags=0x08000008  # CREATE_NO_WINDOW | DETACHED_PROCESS
        )
        log("Clash restart issued")
    except Exception as e:
        log(f"Clash restart FAILED: {e}")

if __name__ == "__main__":
    interval = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    log(f"Watchdog started (interval={interval}s, port={CLASH_PORT}) [R314]")
    while True:
        port_ok = is_port_open()
        proc_ok = is_clash_process_running()
        if not port_ok or not proc_ok:
            log(f"Clash DOWN (port_open={port_ok}, proc_ok={proc_ok})")
            restart_clash()
            time.sleep(90)
        else:
            log("Clash OK (port + process)")
        time.sleep(interval)
