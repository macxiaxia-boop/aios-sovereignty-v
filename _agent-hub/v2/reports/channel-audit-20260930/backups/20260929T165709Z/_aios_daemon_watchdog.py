#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_aios_daemon_watchdog.py - R201 daemon watchdog (2026-09-24)

用户原话 "可以按照推荐走" → 选 A 治本 (L1) + "测试一下" → R201 测试发现 2 daemon 死

按 #11.5 SOP-A 决策 (5 步):
  ① sc query: 已有 AIOSSupervisor / AIOSSelfHeal / AIOS_Autonomy_Daemon
  ② XML: 无 Operator winsw 目录
  ③ PID: bridge v2.3=22432 alive, polling 12112 dead, watcher 15916 dead
  ④ 拓扑: WinSW 服务 4 个 + background pythonw 12 个
  ⑤ 决策: 不加 WinSW watchdog (Round 28 实证 supervisor 冗余 spawn 冲突),
          用 background pythonw + 手动管理 + 写 PID file 给 supervisor 监控

功能:
  1. 监控 _codex_polling_daemon.py (Codex 视角持续 polling)
  2. 监控 _codex_to_cc_inbox_watcher.py (CC 视角持续扫 Codex 输出)
  3. 死了 → 自动重启 + 写告警日志
  4. watchdog 自身 PID → PID file 让 supervisor 可查
  5. 不监控 bridge v2.3 (已有 WinSW/自己 WinSW 守护)

调用:
  pythonw _aios_daemon_watchdog.py  # 持续跑
  pythonw _aios_daemon_watchdog.py --interval 30  # 检查间隔

触达红线: #101 · #103 · #108 · #22 · #60 · #78 · #82 · #29 · #11.5
"""
import subprocess
import json
import time
import os
import sys
import argparse
import ctypes
import pathlib
import msvcrt
import re
from ctypes import wintypes
from datetime import datetime, timedelta

# R203 治本 (红线 #78+#82+#103): ctypes 直接调 Win32 API 零子进程调用
# 替换原 alive_pid + find_pid_by_script (subprocess.run(tasklist) → 黑色 cmd 窗口)
# 真根因: watchdog 主循环每 30s 调 22 次 tasklist, watchdog 是 pythonw 启的无 console,
#   Windows 每次必须为 tasklist 强建 cmd 黑色窗口 → 用户看到弹窗
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
STILL_ACTIVE = 259
CREATE_NO_WINDOW = 0x08000000
DETACHED_PROCESS = 0x00000008
_psapi = ctypes.windll.psapi
_kernel32 = ctypes.windll.kernel32
_EnumProcesses = _psapi.EnumProcesses
_EnumProcesses.argtypes = [ctypes.POINTER(wintypes.DWORD), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
_EnumProcesses.restype = wintypes.BOOL
_OpenProcess = _kernel32.OpenProcess
_OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
_OpenProcess.restype = wintypes.HANDLE
_QueryFullProcessImageNameW = _kernel32.QueryFullProcessImageNameW
_QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.c_wchar_p, ctypes.POINTER(wintypes.DWORD)]
_QueryFullProcessImageNameW.restype = wintypes.BOOL
_GetExitCodeProcess = _kernel32.GetExitCodeProcess
_GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
_GetExitCodeProcess.restype = wintypes.BOOL
_CloseHandle = _kernel32.CloseHandle
_CloseHandle.argtypes = [wintypes.HANDLE]
_CloseHandle.restype = wintypes.BOOL

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PYTHONW = r"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\pythonw.exe"
TOOLS = "D:/个人文件/AI/Operator/aios_tools"

DAEMONS = [
    # R201 daemon (CC ↔ Codex Desktop) - V14.5 已验稳活
    {
        "name": "_codex_polling_daemon",
        "script": TOOLS + "/_codex_polling_daemon.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    {
        "name": "_codex_to_cc_inbox_watcher",
        "script": TOOLS + "/_codex_to_cc_inbox_watcher.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    # V14.5 (R201) EXTEND: Codex Desktop 双向 bridge (CC ↔ Codex Desktop)
    {
        "name": "_codex_to_cc_bridge_v2",
        "script": TOOLS + "/_codex_to_cc_bridge_v2.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    # V15.0 L5 EXTEND: Codex CLI 通道 (CC ↔ Codex CLI) - 3 daemon
    {
        "name": "_cc_to_codex_cli_bridge",
        "script": TOOLS + "/_cc_to_codex_cli_bridge.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    {
        "name": "_cc_to_codex_cli_polling_daemon",
        "script": TOOLS + "/_cc_to_codex_cli_polling_daemon.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    {
        "name": "_codex_cli_to_cc_inbox_watcher",
        "script": TOOLS + "/_codex_cli_to_cc_inbox_watcher.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    # V15.0 L5 EXTEND: 豆包 ARK API 通道 (CC ↔ Doubao) - 3 daemon
    {
        "name": "_cc_to_doubao_bridge",
        "script": TOOLS + "/_cc_to_doubao_bridge.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    {
        "name": "_cc_to_doubao_polling_daemon",
        "script": TOOLS + "/_cc_to_doubao_polling_daemon.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    {
        "name": "_doubao_to_cc_inbox_watcher",
        "script": TOOLS + "/_doubao_to_cc_inbox_watcher.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    # V15.0 L5 EXTEND: OpenClaw MCP 通道 (CC ↔ OpenClaw) - 3 daemon
    {
        "name": "_cc_to_openclaw_bridge",
        "script": TOOLS + "/_cc_to_openclaw_bridge.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    {
        "name": "_cc_to_openclaw_polling_daemon",
        "script": TOOLS + "/_cc_to_openclaw_polling_daemon.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    {
        "name": "_openclaw_to_cc_inbox_watcher",
        "script": TOOLS + "/_openclaw_to_cc_inbox_watcher.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    # V16.0 EXTEND (用户拍板 D · 2026-09-24): Codex Desktop ↔ Codex CLI 双向路由桥
    {
        "name": "_codex_desktop_to_cli_bridge",
        "script": TOOLS + "/_codex_desktop_to_cli_bridge.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
    {
        "name": "_codex_cli_to_desktop_bridge",
        "script": TOOLS + "/_codex_cli_to_desktop_bridge.py",
        "args": ["--interval", "15"],
        "expected_pid_file": None,
        "min_uptime_seconds": 10,
    },
]

PID_DIR = "D:/个人文件/AI/Operator/handoff/watchdog"
ALERT_LOG = TOOLS + "/_aios_daemon_watchdog_alert.log"
STATE_FILE = TOOLS + "/_aios_daemon_watchdog_state.json"
# R202 (红线 #81 节流): 同 daemon 1h 内 restart 上限 3 次, 防 restart 风暴
RESTART_HISTORY_FILE = TOOLS + "/_aios_daemon_watchdog_restart_history.json"
MAX_RESTART_PER_HOUR = 3
# R206 治本 (按 #103 + #60 + R70): 节流 = 5 分钟间隔 (不是单纯累计)
# 真根因: daemon 死 → watchdog 重启 → 立即死 → 节流累计 → 1h 后才清 → 期间 daemon 一直死
# 治本: 每次 restart 之间至少间隔 5 分钟 (给 daemon 充分时间启动 + 稳定)
MIN_RESTART_INTERVAL_SECONDS = 300  # 5 分钟


def ensure_dirs():
    for d in [PID_DIR, os.path.dirname(ALERT_LOG)]:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception:
            pass


def alive_pid(pid):
    """R203 ctypes OpenProcess + GetExitCodeProcess 检查 PID 是否还活着 (零子进程调用)"""
    try:
        h = _OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid))
        if not h:
            return False
        try:
            code = wintypes.DWORD(0)
            if _GetExitCodeProcess(h, ctypes.byref(code)):
                return code.value == STILL_ACTIVE
            return False
        finally:
            _CloseHandle(h)
    except Exception:
        return False


def find_pid_by_script(script_basename):
    """R203 ctypes EnumProcesses + QueryFullProcessImageNameW 找跑某 script 的 PID

    返回所有 (pid) where image_path basename == script_basename + ".py" (脚本名匹配)
    注意: 因为脚本名一般唯一 (e.g. _codex_polling_daemon.py), image_path 含绝对路径
    """
    try:
        size = 4096
        pids = (wintypes.DWORD * size)()
        needed = wintypes.DWORD(0)
        if not _EnumProcesses(pids, ctypes.sizeof(pids), ctypes.byref(needed)):
            return []
        count = needed.value // 4
        target = script_basename + ".py"
        matched = []
        for i in range(min(count, size)):
            pid = pids[i]
            if pid == 0:
                continue
            h = _OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not h:
                continue
            try:
                bufsize = wintypes.DWORD(1024)
                buf = ctypes.create_unicode_buffer(1024)
                if _QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(bufsize)):
                    name = os.path.basename(buf.value).lower()
                    # image_path 是 pythonw.exe / python.exe, 不是 script
                    # 用 image_path 的父目录 + 进程环境 (命令行) 太复杂
                    # 改: 只返回所有 pythonw PIDs, 让调用者自己 match PID file
                    # 但这里返回名字含 python 的即可, 由 alive_pid 二次过滤
                    if "python" in name and pid not in matched:
                        matched.append(pid)
            finally:
                _CloseHandle(h)
        return matched
    except Exception:
        return []


def start_daemon(d):
    """启动 daemon (R203 治本 · Popen + CREATE_NO_WINDOW + DETACHED_PROCESS)

    R203 治本 (红线 #78+#82+#103 · 用户 L4 拍板 A 方案):
      - watchdog 直接 Popen 启 daemon (不用 schtasks, 不用 cmd wrapper)
      - creationflags=CREATE_NO_WINDOW(0x08000000)|DETACHED_PROCESS(0x00000008)
        → 0 console window (红线 #78 治本)
      - stdout/stderr/stdin = DEVNULL → 不弹窗 (daemon 死了也不会触发 console 创建)
      - close_fds=True → 不继承 watchdog fd
      - Popen.pid → PID file (PID_DIR/_daemon_name.pid)
      - watchdog 主循环用 PID file + ctypes alive_pid 检查 (零子进程调用)

    之前 V1/V2/V3/R202 都治不掉弹窗 → 真根因是 watchdog 22次/分钟 tasklist 调用
    """
    # 红线 #81 节流: 同 daemon 1h 内 ≤3 次 restart (R202 保留)
    # R206 治本: 加 5 分钟最小间隔检查 (R70 + #103 + #60 真根因: daemon 立即死 → restart 风暴)
    try:
        one_hour_ago = (datetime.now() - timedelta(hours=1)).isoformat()
        history = []
        if os.path.exists(RESTART_HISTORY_FILE):
            try:
                with open(RESTART_HISTORY_FILE, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except Exception:
                history = []
        recent = [h for h in history if h.get("name") == d["name"] and h.get("ts", "") >= one_hour_ago]
        if len(recent) >= MAX_RESTART_PER_HOUR:
            log_alert("THROTTLE " + d["name"] + " skipped (1h 内已 restart " + str(len(recent)) + " 次, 上限 " + str(MAX_RESTART_PER_HOUR) + ")")
            return False
        # R206 治本: 5 分钟最小间隔 (避免 daemon 立即死 → restart 风暴)
        if recent:
            last_ts = recent[-1].get("ts", "")
            try:
                last_dt = datetime.fromisoformat(last_ts)
                elapsed = (datetime.now() - last_dt).total_seconds()
                if elapsed < MIN_RESTART_INTERVAL_SECONDS:
                    log_alert("THROTTLE " + d["name"] + " skipped (距上次 restart 仅 " + str(int(elapsed)) + "s, 最小间隔 " + str(MIN_RESTART_INTERVAL_SECONDS) + "s)")
                    return False
            except Exception:
                pass
    except Exception:
        pass

    try:
        cmd = [PYTHONW, "-u", d["script"]] + d["args"]
        # R203 治本 (红线 #78+#82): Popen + CREATE_NO_WINDOW + DETACHED_PROCESS
        proc = subprocess.Popen(
            cmd,
            creationflags=CREATE_NO_WINDOW | DETACHED_PROCESS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            close_fds=True,
        )
        write_pid_file(d["name"], proc.pid)
        log_alert("RESTART (R203 Popen CREATE_NO_WINDOW) " + d["name"] + " PID=" + str(proc.pid))
        # R207 V2 治本 (按 #103 + #60 + R70): 启动后 3s 验证 (快速版, 不在 start_daemon 里 sleep 累积)
        # 真根因: BOOT-CHECK 启 14 daemon × 3s = 42s → cycle 30s 撞 → 卡死
        # V2 治本: 仅 3s 验证, BOOT-CHECK 不阻塞 cycle
        # 注意: V1 sleep(3) 让 BOOT-CHECK 太慢 → 撤回到 1s + 不 sleep 在 start_daemon
        # R207 V2 在 main_loop cycle 中检测到 dead 时用 3s 验证, start_daemon 只做基本启
        time.sleep(1)
        if not alive_pid(proc.pid):
            log_alert("R207 V2 VERIFY_FAIL T+1s " + d["name"] + " PID=" + str(proc.pid) + " (daemon 启后 1s 内死)")
            clean_pid_file(d["name"])
            return False
        # 红线 #81 节流: 记录 restart 时间戳 (保留 24h)
        try:
            history2 = []
            if os.path.exists(RESTART_HISTORY_FILE):
                try:
                    with open(RESTART_HISTORY_FILE, "r", encoding="utf-8") as f:
                        history2 = json.load(f)
                except Exception:
                    history2 = []
            history2.append({"name": d["name"], "ts": datetime.now().isoformat()})
            cutoff24 = (datetime.now() - timedelta(hours=24)).isoformat()
            history2 = [h for h in history2 if h.get("ts", "") >= cutoff24]
            with open(RESTART_HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history2, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
        return True
    except Exception as e:
        log_alert("ERR restart " + d["name"] + ": " + repr(e))
        return False


def log_alert(msg):
    line = "[" + datetime.now().isoformat() + "] " + msg
    try:
        with open(ALERT_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    try:
        sys.stdout.buffer.write((line + "\n").encode("utf-8"))
        sys.stdout.buffer.flush()
    except Exception:
        pass


def write_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def write_pid_file(name, pid):
    try:
        pf = PID_DIR + "/" + name + ".pid"
        with open(pf, "w", encoding="utf-8") as f:
            f.write(str(pid))
    except Exception:
        pass


def main_loop(interval):
    log_alert("=" * 60)
    log_alert("AIOS Daemon Watchdog v2 (R203 治本 · 2026-09-24)")
    log_alert("监控 daemon 数: " + str(len(DAEMONS)))
    log_alert("检查间隔: " + str(interval) + "s")
    log_alert("Watchdog PID: " + str(os.getpid()))
    log_alert("=" * 60)

    ensure_dirs()

    # R206 治本 (#103 + #60): watchdog 启动时写自己的 PID file → 让 self_check 可查
    try:
        own_pid_file = PID_DIR + "/_aios_daemon_watchdog.pid"
        with open(own_pid_file, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    def read_pid_file(name):
        """读 PID file → 返回 PID int or None"""
        pf = PID_DIR + "/" + name + ".pid"
        if not os.path.exists(pf):
            return None
        try:
            with open(pf, "r", encoding="utf-8") as f:
                return int(f.read().strip())
        except Exception:
            return None

    def clean_pid_file(name):
        """R206 治本 (#103 + #60): 删 stale PID file (daemon 已死但 PID file 还在指向死 PID)"""
        pf = PID_DIR + "/" + name + ".pid"
        try:
            if os.path.exists(pf):
                os.remove(pf)
        except Exception:
            pass

    # 启动时如果 daemon 死了 → 自动重启 (R203: 只用 PID file, 不用 find_pid_by_script)
    # R210 EXTEND (按 #95 + #103 + #60 + R70 + R77 + R186 V3 + #11.5):
    #   BOOT-CHECK 段串行 start_daemon → 13 daemon 全死时 13 × sleep(1+5) = 65s+ 主循环阻塞 → watchdog 1s 内死
    #   V2: 并行 ThreadPoolExecutor (max_workers=13) → 13 daemon 同时 start_daemon → 1-5s 完成 → watchdog 不阻塞
    from concurrent.futures import ThreadPoolExecutor, as_completed
    boot_dead = []  # 收集 dead daemon
    for d in DAEMONS:
        saved_pid = read_pid_file(d["name"])
        alive_now = saved_pid is not None and alive_pid(saved_pid)
        if not alive_now:
            if saved_pid is not None:
                clean_pid_file(d["name"])  # R206 治本: 删 stale PID file
            log_alert("BOOT-CHECK " + d["name"] + " dead (PID file=" + str(saved_pid) + ") → 并行启动")
            boot_dead.append(d)
        else:
            log_alert("BOOT-CHECK " + d["name"] + " alive PID=" + str(saved_pid))
    # R210 并行启动 dead daemon (ThreadPoolExecutor → 13 daemon 同时启)
    if boot_dead:
        with ThreadPoolExecutor(max_workers=min(len(boot_dead), 13)) as executor:
            futures = {executor.submit(start_daemon, d): d["name"] for d in boot_dead}
            for fut in as_completed(futures):
                name = futures[fut]
                try:
                    fut.result()
                except Exception as e:
                    log_alert("BOOT-CHECK " + name + " start ERR: " + repr(e))
        log_alert("R210 BOOT-CHECK 并行启动完成 (" + str(len(boot_dead)) + " daemon)")

    cycle = 0
    while True:
        cycle += 1
        state = {"cycle": cycle, "ts": datetime.now().isoformat(), "daemons": []}
        cycle_dead = []  # R210: 收集死 daemon, 并行启
        try:
            for d in DAEMONS:
                saved_pid = read_pid_file(d["name"])
                live_now = saved_pid is not None and alive_pid(saved_pid)
                status = "alive" if live_now else "dead"
                daemon_state = {
                    "name": d["name"],
                    "status": status,
                    "pid": saved_pid if live_now else None,
                }
                state["daemons"].append(daemon_state)

                if not live_now:
                    if saved_pid is not None:
                        clean_pid_file(d["name"])  # R206 治本: 删 stale PID file
                    log_alert("DETECTED DEAD " + d["name"] + " (PID file=" + str(saved_pid) + ") → restart")
                    cycle_dead.append(d)  # R210: 收集到列表, 并行启

            write_state(state)

            # R210 EXTEND (按 #95 + #103 + #60 + R70 + R77 + R186 V3 + #11.5):
            #   main_loop 重启段串行 start_daemon + sleep(5) → 13 daemon 全死时 65s+ 主循环阻塞 → watchdog 1s 内死
            #   V2: 并行 ThreadPoolExecutor (max_workers=13) → 13 daemon 同时 start_daemon → 1-5s 完成 → watchdog 不阻塞
            if cycle_dead:
                log_alert("R210 main_loop 并行启动 " + str(len(cycle_dead)) + " dead daemon")
                with ThreadPoolExecutor(max_workers=min(len(cycle_dead), 13)) as executor:
                    futures = {executor.submit(start_daemon, d): d["name"] for d in cycle_dead}
                    for fut in as_completed(futures):
                        name = futures[fut]
                        try:
                            fut.result()
                        except Exception as e:
                            log_alert("R210 " + name + " start ERR: " + repr(e))
                # R207 V2 验证: 并行启动后批量检查 alive (替代原 sleep(5))
                for d in cycle_dead:
                    new_pid = read_pid_file(d["name"])
                    if new_pid and alive_pid(new_pid):
                        log_alert("RESTARTED " + d["name"] + " new PID=" + str(new_pid))
                    else:
                        log_alert("RESTART FAILED " + d["name"])

            if cycle % 10 == 0:
                summary = " | ".join(s["name"] + "=" + s["status"] for s in state["daemons"])
                log_alert("[CYCLE " + str(cycle) + "] " + summary)
        except Exception as e:
            log_alert("[CYCLE " + str(cycle) + "] ERR: " + repr(e))

        time.sleep(interval)


if __name__ == "__main__":
    # R270 治本 (红线 #11.5+#103+#60+#82+#78+#29+#22+#65+#81+#95+#108):
    #   AIOS daemon watchdog 单实例化 (治 watchdog 多实例化 → 反复重启 daemon → codex/CC/VS 闪退)
    # 真根因: watchdog 启动入口没 filelock, 多个 cron/schtasks/手动同时启 → 14 daemon 反复并行重启
    # 治本: msvcrt LK_NBLCK 单实例锁 (Windows 原生, 进程死自动释放)
    _WD_LOCK = pathlib.Path('D:/个人文件/AI/Operator/aios_tools/state/.aios_daemon_watchdog.lock')
    _WD_LOCK.parent.mkdir(parents=True, exist_ok=True)
    _WD_LOCK.touch(exist_ok=True)
    _wd_fd = open(_WD_LOCK, 'r+b')
    try:
        msvcrt.locking(_wd_fd.fileno(), msvcrt.LK_NBLCK, 1)
        # 抢到锁: 写自己的 PID
        _wd_fd.seek(0)
        _wd_fd.write(('PID=' + str(os.getpid()) + ' TIME=' + str(time.time()) + chr(10)).encode('utf-8'))
        _wd_fd.flush()
    except (OSError, IOError):
        # 锁被占: 检查 holder 是否真活着 (lock fd 残魂 vs 真活 watchdog)
        _wd_fd.seek(0)
        _content = _wd_fd.read(200).decode('utf-8', errors='replace').strip()
        _m = re.search(r'PID=(\d+)', _content)
        _holder_alive = False
        _other_pid = None
        if _m:
            try:
                _other_pid = int(_m.group(1))
                if _other_pid != os.getpid():
                    _holder_alive = alive_pid(_other_pid)
            except Exception:
                pass
        _wd_fd.close()
        if _holder_alive:
            # 另一个 watchdog 真活着 → 当前进程立即退出
            sys.stderr.write('[watchdog] singleton lock held by PID=' + str(_other_pid) + ', exiting' + chr(10))
            sys.stderr.flush()
            sys.exit(0)
        # lock holder 已死 (msvcrt lock 在进程死时自动释放, 残魂 1s 内清) → 二次抢锁
        try:
            time.sleep(1.0)
        except Exception:
            pass
        _wd_fd = open(_WD_LOCK, 'r+b')
        try:
            msvcrt.locking(_wd_fd.fileno(), msvcrt.LK_NBLCK, 1)
            _wd_fd.seek(0)
            _wd_fd.write(('PID=' + str(os.getpid()) + ' TIME=' + str(time.time()) + chr(10)).encode('utf-8'))
            _wd_fd.flush()
        except Exception:
            _wd_fd.close()
            sys.stderr.write('[watchdog] failed to acquire singleton lock after stale holder, exiting' + chr(10))
            sys.stderr.flush()
            sys.exit(1)

    # _wd_fd 在 main 作用域持有, 进程退出时自动关闭 → msvcrt 锁自动释放
    parser = argparse.ArgumentParser(description="AIOS Daemon Watchdog")
    parser.add_argument("--interval", type=int, default=30, help="检查间隔秒数")
    args = parser.parse_args()
    main_loop(args.interval)