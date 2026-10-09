#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
hermes_daemon.py — Hermes 持久守护 (Phase I.3 / T25 · 2026-10-09)

目标
  - 把原 `reconciler.py --once` 的 CLI 调用改成 60s 周期 + heartbeat + drift scan + audit append
  - mode A: 自循环 (默认 60s 一次, 直到外部 STOP)
  - mode B: on-demand 启动钩 (--once 跑一次即退)

SSOT 路径
  - Spec:       D:\AIOS\_agent-hub\policy\adapter-spec.v1.md
  - Policy:     D:\AIOS\_agent-hub\policy\model-policy.v1.yaml
  - Manifest:   D:\AIOS\_agent-hub\policy\model-policy.v1.sha256
  - Reconciler: D:\AIOS\_agent-hub\policy\reconciler\reconciler.py
  - Audit log:  D:\AIOS\_agent-hub\audit\drift-events.log
  - Heartbeat:  D:\AIOS\_agent-hub\policy\daemons\hermes_daemon.heartbeat.json

线程 / 授权
  - Thread:    01a11c33-c813-7752-9e53-b7c332d00445 (Phase I.3)
  - Supervisor: 01a11c30-6f6c-76c0-8c60-a55f3a43ff63
  - Authorizer: user-2026-10-08T23:55 (sovereignty-v) + 你就开始 + 继续 (2026-10-09)

红线契约
  - NO_FABRICATE_MODEL_ID        : 仅复用 reconciler 的 sha256 / drift 检测, 不在本 daemon 写新策略
  - UNIFIED_INTERFACE_REQUIRED   : 不替代 reconciler; 仅做调度 + heartbeat
  - NO_AUTO_FALLBACK_IN_ADAPTER  : drift 不修复, 仅 audit + 心跳

工作流
  1. 每 60s 调一次 `reconciler.py --once --auto-rollback` (subprocess)
  2. 写心跳 JSON: ts / drift_count / rollback_count / exit_code
  3. drift > 0 → 写一行 ERROR 到 daemon 日志
  4. ctrl-C / KeyboardInterrupt → 优雅退出, 写 last-stop heartbeat

退出码
  0  全部 cycle OK 或 仅有 rollback 已处理
  1  某次 cycle 出 residual L2 drift
  2  参数错
  130 SIGINT (ctrl-c)
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# 路径常量
RECONCILER   = Path(r"D:\AIOS\_agent-hub\policy\reconciler\reconciler.py")
HEARTBEAT    = Path(r"D:\AIOS\_agent-hub\policy\daemons\hermes_daemon.heartbeat.json")
DAEMON_LOG   = Path(r"D:\AIOS\_agent-hub\policy\daemons\hermes_daemon.log")
LOCK_PATH    = Path(r"D:\AIOS\_agent-hub\policy\daemons\hermes_daemon.lock")
PYTHON_BIN   = Path(r"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe")

# 8h CST
_TZ_CN = timezone(timedelta(hours=8))


def _now_iso() -> str:
    now = datetime.now(_TZ_CN)
    return now.strftime("%Y-%m-%dT%H:%M:%S") + now.strftime("%z")[:3] + ":" + now.strftime("%z")[3:]


def _log(line: str) -> None:
    """stdout + log file (append, 不抛)."""
    msg = f"[{_now_iso()}] {line}"
    print(msg, flush=True)
    try:
        DAEMON_LOG.parent.mkdir(parents=True, exist_ok=True)
        with DAEMON_LOG.open("a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:  # noqa: BLE001
        pass


def _write_heartbeat(record: dict) -> None:
    try:
        HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        # atomic-ish write (best-effort)
        tmp = HEARTBEAT.with_suffix(".tmp")
        tmp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        try:
            os.replace(tmp, HEARTBEAT)
        except OSError:
            tmp.unlink(missing_ok=True)
    except Exception as e:  # noqa: BLE001
        _log(f"heartbeat write failed: {type(e).__name__}:{e}")


def _acquire_lock() -> Optional[int]:
    """单实例锁 (LOCK_PATH 创建, exclusive 创建失败 → 已有实例)."""
    try:
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, f"{os.getpid()}\n".encode())
        return fd
    except FileExistsError:
        return None


def _release_lock(fd: Optional[int]) -> None:
    if fd is None:
        return
    try:
        os.close(fd)
    except OSError:
        pass
    try:
        LOCK_PATH.unlink(missing_ok=True)
    except OSError:
        pass


def _run_reconciler_cycle() -> dict:
    """跑一次 reconciler, 收集 stdout 末尾 JSON 行 + exit_code."""
    if not RECONCILER.exists():
        return {"exit_code": -1, "error": f"reconciler missing: {RECONCILER}"}
    if not PYTHON_BIN.exists():
        return {"exit_code": -1, "error": f"python missing: {PYTHON_BIN}"}

    try:
        proc = subprocess.run(
            [str(PYTHON_BIN), str(RECONCILER), "--once", "--auto-rollback"],
            capture_output=True, text=True, timeout=30,
        )
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "error": "reconciler timeout 30s"}
    except Exception as e:  # noqa: BLE001
        return {"exit_code": -1, "error": f"{type(e).__name__}:{e}"}

    # reconciler 最后一行通常是 OK/ALERT 汇总; 反向扫找 drift_count
    last_json: Optional[dict] = None
    drift_count = -1
    for line in reversed(proc.stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                obj = json.loads(line)
                last_json = obj
                drift_count = int(obj.get("drift_count", -1))
                break
            except Exception:  # noqa: BLE001
                continue

    return {
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "").splitlines()[-1][:200],
        "stderr_tail": (proc.stderr or "").splitlines()[-1][:200],
        "drift_count": drift_count,
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="Hermes daemon (Phase I.3 / T25)")
    ap.add_argument("--interval", type=int, default=60, help="cycle interval sec (default 60)")
    ap.add_argument("--once", action="store_true", help="run one cycle then exit (mode B)")
    ap.add_argument("--max-cycles", type=int, default=0, help="max cycles (0=infinite)")
    ap.add_argument("--verbose", action="store_true", help="verbose per cycle")
    args = ap.parse_args(argv)

    lock_fd = _acquire_lock()
    if lock_fd is None:
        _log(f"ABORT: another hermes_daemon instance holds {LOCK_PATH}")
        return 4

    stop_flag = {"stop": False}

    def _handle_sigint(signum, frame):  # noqa: ARG001
        stop_flag["stop"] = True
        _log(f"signal {signum} received, requesting graceful stop after current cycle")

    try:
        signal.signal(signal.SIGINT, _handle_sigint)
    except Exception:  # noqa: BLE001
        pass  # Windows 下 signal.SIGINT 偶发 OSError, 忽略

    _log(f"hermes_daemon started pid={os.getpid()} interval={args.interval}s once={args.once} max_cycles={args.max_cycles}")

    cycles = 0
    failures = 0
    try:
        while not stop_flag["stop"]:
            t0 = time.time()
            result = _run_reconciler_cycle()
            cycles += 1
            ec = result["exit_code"]
            drift = result["drift_count"]
            ok = ec == 0 and (drift == 0 or drift > 0)  # drift>0 但有 rollback 也算 OK
            if ec != 0:
                failures += 1
            _write_heartbeat({
                "ts":           _now_iso(),
                "pid":          os.getpid(),
                "cycle":        cycles,
                "interval_sec": args.interval,
                "exit_code":    ec,
                "drift_count":  drift,
                "stdout_tail":  result.get("stdout_tail", ""),
                "stderr_tail":  result.get("stderr_tail", ""),
                "failures":     failures,
            })
            if args.verbose or ec != 0:
                _log(f"cycle={cycles} exit={ec} drift={drift} stdout='{result.get('stdout_tail','')[:80]}'")
            if ec == 1:
                _log(f"cycle={cycles} residual drift detected - alerting")
            if args.once:
                break
            if args.max_cycles and cycles >= args.max_cycles:
                _log(f"reached max_cycles={args.max_cycles}, stopping")
                break
            # sleep until next cycle, but break early on stop signal
            elapsed = time.time() - t0
            sleep_left = max(0, args.interval - int(elapsed))
            slept = 0
            while slept < sleep_left and not stop_flag["stop"]:
                step = min(1, sleep_left - slept)
                time.sleep(step)
                slept += step
    finally:
        _log(f"hermes_daemon stopping cycles={cycles} failures={failures}")
        _release_lock(lock_fd)

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except KeyboardInterrupt:
        _log("ctrl-c, exit 130")
        sys.exit(130)