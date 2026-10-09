# -*- coding: utf-8 -*-
#!/usr/bin/env python3
"""One-shot OpenClaw gateway watchdog for scheduled execution."""

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request


OPENCLAW_PORT = 18792
HEALTH_URL = f"http://127.0.0.1:{OPENCLAW_PORT}/healthz"
GATEWAY_CMD = [
    r"C:\Windows\System32\wscript.exe",
    r"C:\Users\xinzh\.openclaw\gateway.vbs",
]
GATEWAY_CWD = r"C:\Users\xinzh"
LOG = r"D:\AIOS\_openclaw_18792_watchdog.log"
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008


def log(message):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as handle:
        handle.write(f"[{timestamp}] {message}\n")


def is_port_open():
    try:
        with socket.create_connection(("127.0.0.1", OPENCLAW_PORT), timeout=3):
            return True
    except OSError:
        return False


def is_healthy():
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=5) as response:
            return response.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
        return False


def launch_gateway_once():
    subprocess.Popen(
        GATEWAY_CMD,
        cwd=GATEWAY_CWD,
        creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )


def main():
    if is_port_open():
        if is_healthy():
            log(f"HEALTHY port={OPENCLAW_PORT} healthz=200")
            return 0
        log(f"UNHEALTHY port={OPENCLAW_PORT} open healthz=failed; no restart attempted")
        return 1

    log(f"DOWN port={OPENCLAW_PORT}; launching standard gateway entry once")
    try:
        launch_gateway_once()
    except Exception as error:
        log(f"LAUNCH_FAILED {type(error).__name__}: {error}")
        return 1

    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        time.sleep(5)
        if is_healthy():
            log(f"RECOVERED port={OPENCLAW_PORT} healthz=200")
            return 0

    log(f"RECOVERY_TIMEOUT port={OPENCLAW_PORT} healthz=failed after 90s")
    return 1


if __name__ == "__main__":
    sys.exit(main())
