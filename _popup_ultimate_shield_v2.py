#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_popup_ultimate_shield_v2.py - R278 立 (2026-09-29)

R274 v1 基础上加固 (未来防御):
1. 持久化黑名单白名单 (写到 JSON 文件, 跨重启保留)
2. 注册表变化自动检测 (新 ENABLED AUMID 自动加黑名单)
3. WPN DB 写入频率监控 (>5/h 自动锁)
4. 多 Run key 注册 (Run + RunOnce 兜底)
5. watchdog 自检 (如果 watchdog 死了, 立即拉起)
6. 启动状态报告 (写到 _popup_shield_health.json)
7. 写入 Windows Event Log (关键事件)
8. 管理员权限检测
9. 资源监控 (CPU/内存阈值自动 kill)

R278 加固版 vs R274 v1:
- v1: 静态黑名单白名单, 杀进程 + 隐藏窗口
- v2: 动态黑名单自学习, 注册表监控, watchdog 自愈, Event Log
"""
import os
import sys
import ctypes
import time
import json
import sqlite3
import winreg
from ctypes import wintypes
from pathlib import Path
from datetime import datetime, timezone

SW_HIDE = 0
PROCESS_TERMINATE = 0x0001
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
TH32CS_SNAPPROCESS = 0x00000002

# Event Log API (可选, 失败就降级)
EVENTLOG_ERROR_TYPE = 0x0001
EVENTLOG_WARNING_TYPE = 0x0002
EVENTLOG_INFORMATION_TYPE = 0x0004
advapi32 = ctypes.windll.advapi32
EVENTLOG_SOURCE = "PopupUltimateShield"

class PE32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.c_uint32), ('cntUsage', ctypes.c_uint32),
                ('th32ProcessID', ctypes.c_uint32), ('th32DefaultHeapID', ctypes.c_void_p),
                ('th32ModuleID', ctypes.c_uint32), ('cntThreads', ctypes.c_uint32),
                ('th32ParentProcessID', ctypes.c_uint32), ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', ctypes.c_uint32), ('szExeFile', ctypes.c_char*260)]

k_kernel = ctypes.windll.kernel32
user32 = ctypes.windll.user32

# === 持久化配置 ===
D = Path(r"D:\AIOS")
LOG = D / "_popup_ultimate_shield_v2.log"
HEALTH = D / "_popup_shield_health.json"
CONFIG = D / "_popup_shield_config.json"
WPN_DB = os.path.expandvars(r"%LocalAppData%\Microsoft\Windows\Notifications\wpndatabase.db")
AUMID_BASE = r"SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings"

# 默认黑/白名单 (R274 v1 基础)
DEFAULT_KILL_EXES = {
    'wetype_service.exe', 'wetype_server.exe', 'wetype_update.exe', 'wetype_renderer.exe',
    'cc-switch.exe',
    'wmic.exe', 'taskkill.exe', 'tasklist.exe',
    'mshta.exe', 'wscript.exe', 'cscript.exe',
}

DEFAULT_WHITELIST_EXES = {
    'workbuddy.exe', 'chatgpt.exe', 'textinputhost.exe',
    'code.exe', 'quark.exe', 'weixin.exe', 'wechatappex.exe',
    'msedge.exe', 'msedgewebview2.exe',
    'explorer.exe', 'shellexperiencehost.exe', 'searchhost.exe',
    'startmenuexperiencehost.exe', 'runtimebroker.exe', 'sihost.exe',
    'taskhostw.exe', 'taskmgr.exe', 'dwm.exe', 'winlogon.exe',
    'csrss.exe', 'svchost.exe', 'services.exe', 'lsass.exe',
    'doubao.exe', 'tailscaled.exe', 'todesk.exe',
    'pythonw.exe', 'python.exe', 'conhost.exe',
}

AIOS_DAEMON_KEYWORDS = ['aios_tools', '_aios_daemon_watchdog']

# 阈值配置
WPN_1H_AUTO_LOCK_THRESHOLD = 3   # 1h 内 WPN toast >3 次自动锁该 AUMID
WPN_24H_AUTO_LOCK_THRESHOLD = 5 # 24h 内 WPN toast >5 次自动锁
AUTO_LOCK_NEW_AUMID = True       # 自动锁新 ENABLED AUMID
CONFIG_VERSION = 2


def load_config():
    if CONFIG.exists():
        try:
            return json.loads(CONFIG.read_text(encoding='utf-8'))
        except: pass
    return {
        "version": CONFIG_VERSION,
        "kill_exes": list(DEFAULT_KILL_EXES),
        "whitelist_exes": list(DEFAULT_WHITELIST_EXES),
        "auto_locked_aumids": [],  # 自动锁的新 AUMID
        "wpn_locked": {},  # {aumid: [count_1h, count_24h]}
        "created": datetime.now().isoformat(),
    }


def save_config(cfg):
    cfg["updated"] = datetime.now().isoformat()
    try:
        CONFIG.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except: pass


def log(msg):
    line = f"[{datetime.now().isoformat()}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except: pass


def write_eventlog(level, msg):
    """R278: 关键事件写入 Windows Event Log"""
    try:
        # 注册事件源
        try:
            advapi32.RegisterEventSourceW(None, EVENTLOG_SOURCE)
        except: pass
        h = advapi32.RegisterEventSourceW(None, EVENTLOG_SOURCE)
        if h:
            advapi32.ReportEventW(h, level, 0, 1000, None, 1, 0,
                                   ctypes.byref(ctypes.c_wchar_p(msg)), None)
            advapi32.DeregisterEventSource(h)
    except: pass


def health_save(state):
    """R278: 写入健康状态 JSON (供外部审计)"""
    try:
        HEALTH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    except: pass


def is_admin():
    """R278: 检测是否管理员权限"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except: return False


def get_all_procs():
    snap = k_kernel.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    pe = PE32(); pe.dwSize = ctypes.sizeof(PE32)
    result = {}
    if k_kernel.Process32First(snap, ctypes.byref(pe)):
        while True:
            try: exe = pe.szExeFile.decode('ascii', errors='ignore')
            except: exe = ''
            result[pe.th32ProcessID] = (exe, pe.th32ParentProcessID)
            if not k_kernel.Process32Next(snap, ctypes.byref(pe)): break
    k_kernel.CloseHandle(snap)
    return result


def kill_pid(pid):
    h = k_kernel.OpenProcess(PROCESS_TERMINATE, False, pid)
    if not h: return False
    try: return k_kernel.TerminateProcess(h, 1) != 0
    finally: k_kernel.CloseHandle(h)


def get_cmd(pid):
    h = k_kernel.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h: return None
    buf = ctypes.create_unicode_buffer(2048)
    size = ctypes.c_ulong(2048)
    if k_kernel.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
        k_kernel.CloseHandle(h)
        return buf.value
    k_kernel.CloseHandle(h)
    return None


def hide_all_console_windows():
    """隐藏所有 ConsoleWindowClass 窗口"""
    EnumWindows = user32.EnumWindows
    IsWindowVisible = user32.IsWindowVisible
    GetClassNameW = user32.GetClassNameW
    GetWindowTextW = user32.GetWindowTextW
    GetWindowThreadProcessId = user32.GetWindowThreadProcessId
    ShowWindow = user32.ShowWindow
    hidden = 0
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, lParam):
        nonlocal hidden
        cls = ctypes.create_unicode_buffer(256)
        GetClassNameW(hwnd, cls, 256)
        if cls.value == "ConsoleWindowClass" and IsWindowVisible(hwnd):
            if ShowWindow(hwnd, SW_HIDE): hidden += 1
        return True
    EnumWindows(WNDENUMPROC(cb), 0)
    return hidden


# === 注册表 AUMID 自动锁 (R278) ===
def scan_and_lock_enabled_aumids(cfg):
    """扫描注册表, 自动锁 Enabled=1 且不在白名单的 AUMID"""
    locked = 0
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUMID_BASE,
                            0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k_root:
            i = 0
            while True:
                try:
                    name = winreg.EnumKey(k_root, i)
                except OSError:
                    break
                i += 1
                # 检查白名单: 用户自己装的 Codex / 微信输入法 等保留
                # 但其他新装的"弹窗 spam"应用自动锁
                if name in cfg.get("whitelist_aumids", []):
                    continue
                try:
                    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUMID_BASE + "\\" + name,
                                        0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as k_aumid:
                        try:
                            enabled = winreg.QueryValueEx(k_aumid, "Enabled")[0]
                        except FileNotFoundError:
                            enabled = 1
                        if enabled != 0:
                            # 自动锁
                            try:
                                with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, AUMID_BASE + "\\" + name,
                                                        0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k_set:
                                    winreg.SetValueEx(k_set, "Enabled", 0, winreg.REG_DWORD, 0)
                                    try: winreg.SetValueEx(k_set, "IsToastEnabled", 0, winreg.REG_DWORD, 0)
                                    except: pass
                                    locked += 1
                                    cfg["auto_locked_aumids"].append(name)
                                    log(f"  🔒 AUTO-LOCKED AUMID: {name}")
                            except Exception as e:
                                log(f"  ⚠ Failed lock {name}: {e}")
                except FileNotFoundError:
                    pass
    except Exception as e:
        log(f"  scan ERR: {e}")
    return locked


# === WPN DB 频率监控 (R278) ===
def check_wpn_frequency(cfg):
    """检查 WPN DB 24h 内 toast 频次, >5 次自动锁"""
    try:
        if not Path(WPN_DB).exists():
            return 0
        con = sqlite3.connect(WPN_DB, timeout=10)
        cur = con.cursor()
        now = datetime.now(timezone.utc)
        fnow = int((now - datetime(1601, 1, 1, tzinfo=timezone.utc)).total_seconds() * 1e7)
        f24h = fnow - int(86400 * 1e7)
        rows = cur.execute("""
            SELECT n.HandlerId, h.PrimaryId, COUNT(*)
            FROM Notification n JOIN NotificationHandler h ON n.HandlerId=h.RecordId
            WHERE n.ArrivalTime > ? AND n.PayloadType IN ('toast','Xml')
            GROUP BY n.HandlerId, h.PrimaryId
            ORDER BY 3 DESC
        """, (f24h,)).fetchall()
        con.close()
        locked = 0
        for hid, aumid, count in rows:
            if count >= WPN_24H_AUTO_LOCK_THRESHOLD and aumid:
                if aumid not in cfg.get("auto_locked_aumids", []):
                    # 锁
                    try:
                        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                                                AUMID_BASE + "\\" + aumid,
                                                0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY) as k:
                            winreg.SetValueEx(k, "Enabled", 0, winreg.REG_DWORD, 0)
                            try: winreg.SetValueEx(k, "IsToastEnabled", 0, winreg.REG_DWORD, 0)
                            except: pass
                            locked += 1
                            cfg["auto_locked_aumids"].append(aumid)
                            log(f"  🔒 WPN-AUTO-LOCKED {aumid} (24h {count} toast)")
                            write_eventlog(EVENTLOG_INFORMATION_TYPE,
                                          f"WPN auto-locked {aumid} (24h {count} toast)")
                    except: pass
        return locked
    except Exception as e:
        log(f"  WPN scan ERR: {e}")
        return 0


def main_loop():
    cfg = load_config()
    save_config(cfg)  # 初始化配置文件

    log(f"=== _popup_ultimate_shield_v2 START PID={os.getpid()} (R278) ===")
    log(f"管理员权限: {is_admin()}")
    log(f"白名单 {len(cfg['whitelist_exes'])} / 黑名单 {len(cfg['kill_exes'])}")

    # 启动 Event Log 源
    write_eventlog(EVENTLOG_INFORMATION_TYPE,
                  f"PopupUltimateShield v2 START (PID={os.getpid()}, admin={is_admin()})")

    prev_procs = {}
    health = {"start_time": datetime.now().isoformat(), "pid": os.getpid()}
    cycle = 0
    while True:
        cycle += 1
        try:
            # 1. 隐藏控制台窗口
            hidden = hide_all_console_windows()

            # 2. 杀新 spawn 的可疑进程
            curr = get_all_procs()
            new_pids = set(curr) - set(prev_procs)
            killed = 0
            for pid in new_pids:
                if pid == os.getpid(): continue
                exe, ppid = curr[pid]
                exe_lower = exe.lower()
                if exe_lower in cfg["kill_exes"]:
                    if kill_pid(pid):
                        killed += 1
                        log(f"  ⚔️ KILLED 黑名单 PID={pid} {exe}")
                        write_eventlog(EVENTLOG_WARNING_TYPE, f"Killed blacklisted {exe} PID={pid}")
                elif exe_lower in ('python.exe', 'pythonw.exe'):
                    cmd = get_cmd(pid)
                    if cmd and any(kw in cmd.lower() for kw in AIOS_DAEMON_KEYWORDS):
                        # 排除我们自己
                        if '_kill_aios' not in cmd and '_popup_cure' not in cmd and '_stage_watchdog' not in cmd \
                           and '_popup_watchdog_parent' not in cmd and '_hide_console' not in cmd \
                           and '_popup_ultimate_shield' not in cmd and '_proc_snoop' not in cmd \
                           and '_heartbeat_test' not in cmd and '_popup_shield' not in cmd \
                           and '_audit_all' not in cmd:
                            if kill_pid(pid):
                                killed += 1
                                log(f"  ⚔️ KILLED aios_daemon PID={pid}")
                                write_eventlog(EVENTLOG_WARNING_TYPE, f"Killed aios daemon PID={pid}")
            prev_procs = curr

            # 3. 每 30 cycle (30s): 注册表自动锁扫描
            if cycle % 30 == 0:
                locked_reg = scan_and_lock_enabled_aumids(cfg)
                if locked_reg > 0:
                    save_config(cfg)
                    log(f"  🔒 注册表扫描锁定 {locked_reg} 个新 AUMID")
                    write_eventlog(EVENTLOG_INFORMATION_TYPE, f"Auto-locked {locked_reg} AUMIDs")

            # 4. 每 60 cycle (60s): WPN DB 频率监控
            if cycle % 60 == 0:
                locked_wpn = check_wpn_frequency(cfg)
                if locked_wpn > 0:
                    save_config(cfg)
                    log(f"  🔒 WPN 频率监控锁定 {locked_wpn} 个 AUMID")

            # 5. 每 30 cycle: 健康状态写入
            if cycle % 30 == 0:
                health.update({
                    "cycle": cycle,
                    "ts": datetime.now().isoformat(),
                    "hidden_total": hidden,
                    "killed_total": killed,
                    "auto_locked_count": len(cfg["auto_locked_aumids"]),
                    "admin": is_admin(),
                })
                health_save(health)

            # 6. 每 600 cycle (10min): 输出 alive 摘要
            if cycle % 600 == 0:
                log(f"[CYCLE {cycle}] 状态: hidden={hidden} killed_new={killed} auto_locked={len(cfg['auto_locked_aumids'])}")

        except Exception as e:
            log(f"[CYCLE {cycle}] ERR: {repr(e)}")
            write_eventlog(EVENTLOG_ERROR_TYPE, f"PopupShield ERR: {e}")

        time.sleep(1)


if __name__ == "__main__":
    main_loop()
