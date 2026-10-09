#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_heartbeat_test.py - R268 诊断

每 1s 写一次心跳到 _heartbeat_test.log, 持续 120s
看是否被杀 (mtime 是否停在 < 120s)
"""
import time
import sys
from pathlib import Path
from datetime import datetime

LOG = Path(r"D:\AIOS\_heartbeat_test.log")
PID = Path(r"D:\AIOS\_heartbeat_test.pid")

def log(msg):
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception as e:
        sys.stderr.write(f"log err: {e}\n")

try:
    PID.write_text(str(__import__('os').getpid()), encoding="utf-8")
except Exception:
    pass

log(f"_heartbeat_test START PID={__import__('os').getpid()}")
start = time.time()
tick = 0
while time.time() - start < 120:
    tick += 1
    log(f"tick={tick} uptime={int(time.time()-start)}s")
    try:
        PID.write_text(f"{__import__('os').getpid()} tick={tick} uptime={int(time.time()-start)}", encoding="utf-8")
    except Exception:
        pass
    time.sleep(1)

log("_heartbeat_test DONE")
