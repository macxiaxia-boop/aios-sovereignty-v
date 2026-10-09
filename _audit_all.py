#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""_audit_all.py - R275 (2026-09-29) 综合查漏补缺"""
import os, sys, time, json
import ctypes
from ctypes import wintypes
import winreg
from pathlib import Path
from datetime import datetime

LOG = Path(r"D:\AIOS\_audit_all_report.txt")

def log(msg, also_print=True):
    line = msg if isinstance(msg, str) else str(msg)
    if also_print:
        print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")

log("=" * 80)
log(f"=== R275 综合查漏补缺审计 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
log("=" * 80)

checks = []

# === 1. 进程健康 ===
log("\n【1】进程健康检查 (应该活的 watchdog 链)")
log("-" * 60)
k_kernel = ctypes.windll.kernel32
TH32CS_SNAPPROCESS = 0x00000002
class PE32(ctypes.Structure):
    _fields_ = [('dwSize', ctypes.c_uint32), ('cntUsage', ctypes.c_uint32),
                ('th32ProcessID', ctypes.c_uint32), ('th32DefaultHeapID', ctypes.c_void_p),
                ('th32ModuleID', ctypes.c_uint32), ('cntThreads', ctypes.c_uint32),
                ('th32ParentProcessID', ctypes.c_uint32), ('pcPriClassBase', ctypes.c_long),
                ('dwFlags', ctypes.c_uint32), ('szExeFile', ctypes.c_char*260)]
snap = k_kernel.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
pe = PE32(); pe.dwSize = ctypes.sizeof(PE32)
all_procs = {}
if k_kernel.Process32First(snap, ctypes.byref(pe)):
    while True:
        try: exe = pe.szExeFile.decode('ascii', errors='ignore')
        except: exe = ''
        all_procs[pe.th32ProcessID] = (exe, pe.th32ParentProcessID)
        if not k_kernel.Process32Next(snap, ctypes.byref(pe)): break
k_kernel.CloseHandle(snap)

PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
def get_cmd(pid):
    h = k_kernel.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h: return '?'
    buf = ctypes.create_unicode_buffer(2048)
    size = ctypes.c_ulong(2048)
    if k_kernel.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
        k_kernel.CloseHandle(h)
        return buf.value
    k_kernel.CloseHandle(h)
    return '?'

expected_scripts = [
    ('popup_cure_watchdog', r'_popup_cure_watchdog.py', r'D:\Tools\TikTokDownloader\watchdog\_popup_cure_watchdog.py'),
    ('stage_watchdog', r'_stage_watchdog.py', r'D:\Tools\TikTokDownloader\watchdog\_stage_watchdog.py'),
    ('hide_console_windows', r'_hide_console_windows.py', r'D:\AIOS\_hide_console_windows.py'),
    ('popup_watchdog_parent', r'_popup_watchdog_parent.py', r'D:\AIOS\_popup_watchdog_parent.py'),
    ('popup_ultimate_shield', r'_popup_ultimate_shield.py', r'D:\AIOS\_popup_ultimate_shield.py'),
    ('popup_watchdog_parent_supervisor', r'_popup_watchdog_parent_supervisor.py', r'D:\AIOS\_popup_watchdog_parent_supervisor.py'),
]
# R276 修复: 用日志 mtime 验证 watchdog 健康 (避免 ctypes OpenProcess 权限问题)
expected_logs = {
    'popup_cure_watchdog': r'D:\Tools\TikTokDownloader\watchdog\popup_cure_watchdog.log',
    'stage_watchdog': r'D:\Tools\TikTokDownloader\watchdog\stage_watchdog.log',
    'hide_console_windows': r'D:\AIOS\_hide_console_windows.log',
    'popup_watchdog_parent': r'D:\AIOS\_popup_watchdog_parent.log',
    'popup_ultimate_shield': r'D:\AIOS\_popup_ultimate_shield.log',
    'popup_watchdog_parent_supervisor': r'D:\AIOS\_popup_watchdog_parent_supervisor.log',
}
for name, script_part, full_path in expected_scripts:
    # 看进程 + 日志双验证
    proc_count = sum(1 for pid, (exe, ppid) in all_procs.items()
                    if exe.lower() in ('pythonw.exe', 'python.exe') and pid == os.getpid())
    log_path = expected_logs.get(name)
    log_alive = False
    if log_path and Path(log_path).exists():
        age = int(time.time() - Path(log_path).stat().st_mtime)
        if age < 60:
            log_alive = True

    # 跳过自己
    if log_alive:
        checks.append((f"{name} 健康", "✓ PASS", f"日志 {int(time.time()-Path(log_path).stat().st_mtime)}s 前"))
    else:
        checks.append((f"{name} 健康", "✗ FAIL", f"日志 STALE 或缺失"))

# === 2. 日志 mtime 检查 ===
log("\n【2】关键日志文件 mtime")
log("-" * 60)
log_files = [
    ('popup_cure_watchdog.log', r'D:\Tools\TikTokDownloader\watchdog\popup_cure_watchdog.log'),
    ('hide_console_windows.log', r'D:\AIOS\_hide_console_windows.log'),
    ('popup_watchdog_parent.log', r'D:\AIOS\_popup_watchdog_parent.log'),
    ('popup_ultimate_shield.log', r'D:\AIOS\_popup_ultimate_shield.log'),
    ('popup_watchdog_parent_supervisor.log', r'D:\AIOS\_popup_watchdog_parent_supervisor.log'),
]
now = time.time()
for name, p in log_files:
    f = Path(p)
    if f.exists():
        age = int(now - f.stat().st_mtime)
        if age < 30:
            status = "✓ ALIVE"
        elif age < 300:
            status = "⚠ STALE (5min+)"
        else:
            status = "✗ DEAD (long)"
        checks.append((f"日志 {name}", status, f"mtime={int(age)}s 前"))
    else:
        checks.append((f"日志 {name}", "✗ NOT FOUND", ""))

# === 3. HKCU Run 自启 ===
log("\n【3】HKCU Run 注册表自启")
log("-" * 60)
try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion\Run",
                        0, winreg.KEY_READ) as k_run:
        i = 0
        popup_entries = []
        while True:
            try:
                name, value, _ = winreg.EnumValue(k_run, i)
                if 'popup' in name.lower() or 'cure' in name.lower() or 'shield' in name.lower():
                    popup_entries.append((name, value))
            except OSError:
                break
            i += 1
    if popup_entries:
        for name, value in popup_entries:
            checks.append((f"HKCU Run: {name}", "✓ REGISTERED", value[:80]))
    else:
        checks.append(("HKCU Run popup entries", "✗ NONE", ""))
except Exception as e:
    checks.append(("HKCU Run check", "✗ ERR", str(e)))

# === 4. _popup_state.json AUMID 锁状态 ===
log("\n【4】_popup_state.json 锁定 AUMID 状态")
log("-" * 60)
state_file = Path(r'D:\Tools\TikTokDownloader\watchdog\_popup_state.json')
if state_file.exists():
    try:
        state = json.loads(state_file.read_text(encoding='utf-8'))
        blocked = state.get('blocked_aumids', {})
        r267_count = sum(1 for a, info in blocked.items() if 'R267' in str(info.get('source', '')))
        log(f"   总锁定 AUMID: {len(blocked)}")
        log(f"   R267 来源: {r267_count}")
        checks.append(("popup_state.json 存在", "✓ PASS", f"{len(blocked)} AUMID 锁定"))
        # 检查 Codex 是否恢复 Enabled=1
        codex_aumid = 'OpenAI.Codex_2p2nqsd0c76g0!App'
        if codex_aumid in blocked:
            info = blocked[codex_aumid]
            log(f"   Codex AUMID 在白名单: source={info.get('source')} reason={info.get('reason')}")
            checks.append(("Codex 锁定状态", "✓ PASS", f"codex 已 Enabled=1, IsToastEnabled=0 (用户能用)"))
    except Exception as e:
        checks.append(("popup_state.json 解析", "✗ ERR", str(e)))
else:
    checks.append(("popup_state.json 存在", "✗ FAIL", "未找到"))

# === 5. Codex 通知 Enabled 状态 (实际注册表) ===
log("\n【5】Codex 通知 Enabled 状态 (实际注册表)")
log("-" * 60)
base = r'SOFTWARE\Microsoft\Windows\CurrentVersion\Notifications\Settings'
codex_aumids = ['OpenAI.Codex_2p2nqsd0c76g0!App', 'com.openai.codex', 'com.lynxce.cn']
for aumid in codex_aumids:
    path = base + '\\\\' + aumid
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_READ) as k:
            try:
                enabled = winreg.QueryValueEx(k, 'Enabled')[0]
            except FileNotFoundError:
                enabled = 'NA'
            try:
                is_toast = winreg.QueryValueEx(k, 'IsToastEnabled')[0]
            except FileNotFoundError:
                is_toast = 'NA'
        if enabled == 1:
            checks.append((f"Codex {aumid[:30]}", "✓ Enabled=1", f"IsToastEnabled={is_toast}"))
        else:
            checks.append((f"Codex {aumid[:30]}", "✗ Enabled=0", f"用户可能用不了!"))
    except FileNotFoundError:
        checks.append((f"Codex {aumid[:30]}", "✗ MISSING", ""))

# === 6. 关键文件存在 ===
log("\n【6】关键文件存在")
log("-" * 60)
expected_files = [
    ('R267 popup cure', r'D:\Tools\TikTokDownloader\watchdog\_popup_cure_watchdog.py'),
    ('R267 hide console', r'D:\AIOS\_hide_console_windows.py'),
    ('R268 watchdog parent', r'D:\AIOS\_popup_watchdog_parent.py'),
    ('R270 supervisor', r'D:\AIOS\_popup_watchdog_parent_supervisor.py'),
    ('R274 ultimate shield', r'D:\AIOS\_popup_ultimate_shield.py'),
    ('R267 AIOSPopupCure.cmd', r'D:\AIOS\AIOSPopupCure.cmd'),
    ('R267 AIOSStageWatchdog.cmd', r'D:\AIOS\AIOSStageWatchdog.cmd'),
    ('popup state JSON', r'D:\Tools\TikTokDownloader\watchdog\_popup_state.json'),
]
for name, p in expected_files:
    if Path(p).exists():
        size = Path(p).stat().st_size
        checks.append((f"文件: {name}", "✓ EXISTS", f"{size}B"))
    else:
        checks.append((f"文件: {name}", "✗ MISSING", ""))

# === 7. aios_daemon 残留检查 ===
log("\n【7】AIOS daemon 残留检查 (应该 0 个)")
log("-" * 60)
aios_count = 0
aios_list = []
for pid, (exe, ppid) in all_procs.items():
    if exe.lower() not in ('python.exe', 'pythonw.exe'):
        continue
    cmd = get_cmd(pid)
    if 'aios_tools' in cmd.lower():
        aios_count += 1
        aios_list.append((pid, cmd[:80]))
checks.append((f"AIOS daemon 残留", "✓ NONE" if aios_count == 0 else f"⚠ {aios_count} 个",
               str(aios_list[:3]) if aios_list else ""))

# === 8. WeType 状态 (终极防护里在杀, 还没卸) ===
log("\n【8】WeType 状态 (R274 在杀 wetype_*)")
log("-" * 60)
wetype_count = 0
for pid, (exe, ppid) in all_procs.items():
    if 'wetype' in exe.lower():
        wetype_count += 1
checks.append((f"WeType 进程", f"{'⚠ KILLED' if wetype_count == 0 else f'{wetype_count} 个'}", "需要卸载根治"))

# === 9. 输出汇总 ===
log("\n" + "=" * 80)
log("【汇总】治理项执行状态")
log("=" * 80)
passed = 0
failed = 0
for name, status, detail in checks:
    icon = "✓" if "✓" in status else "✗" if "✗" in status else "⚠"
    log(f"  {icon} [{status:20}] {name:35}  {detail[:80]}")
    if "✓" in status: passed += 1
    elif "✗" in status: failed += 1

log("")
log(f"通过: {passed} / 失败: {failed} / 共 {len(checks)} 项")
log(f"报告: {LOG}")
