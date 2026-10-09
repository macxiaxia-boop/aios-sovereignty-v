#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
_hide_console_windows_v3.py - surgical console hider (2026-10-08)

Why v3 exists:
  VSCode Claude Code / Codex / npx MCP servers spawn console windows that flash
  and linger. v2 hid EVERY ConsoleWindowClass window, which also hid the user's
  own cmd.exe opened from Win+R -> "cmd unusable".

v3 rule (surgical, conservative):
  HIDE  a console window ONLY when one of its process ancestors is an AI
        toolchain process (claude.exe / codex.exe / code.exe / cursor.exe).
  NEVER hide when the ancestor chain reaches explorer.exe / dwm.exe / winlogon.exe
        (that means the user launched it themselves).
  NEVER hide when we cannot positively identify an AI ancestor.

Parent PID lookup uses the Toolhelp32 process snapshot (rebuilt every 2s), so
no per-window OpenProcess/NtQueryInformationProcess calls in the hot loop.
"""
import ctypes
import json
import time
from ctypes import wintypes
from datetime import datetime
from pathlib import Path

LOG = Path(r"D:\AIOS\_hide_console_windows_v3.log")
PID_FILE = Path(r"D:\AIOS\_hide_console_windows_v3.pid")

TICK_SEC = 0.1
SNAPSHOT_REFRESH_SEC = 2.0
MAX_ANCESTOR_WALK = 12

# A console window under any of these is safe to hide.
AI_ROOTS = {
    "claude.exe",
    "codex.exe",
    "cursor.exe",
    "code.exe",
    "windsurf.exe",
}

# If any of these appear in the ancestor chain, the user started it - never hide.
USER_ROOTS = {
    "explorer.exe",
    "dwm.exe",
    "winlogon.exe",
    "services.exe",
    "taskhostw.exe",
}

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

TH32CS_SNAPPROCESS = 0x00000002

# --- Toolhelp32 structures -----------------------------------------------------
class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wintypes.DWORD),
        ("cntUsage", wintypes.DWORD),
        ("th32ProcessID", wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", wintypes.DWORD),
        ("cntThreads", wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wintypes.DWORD),
        ("szExeFile", wintypes.WCHAR * 260),
    ]


kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32NextW.restype = wintypes.BOOL

# pid -> (parent_pid, exe_name_lower)
_proc_map = {}
_snap_at = 0.0


def build_snapshot():
    """Rebuild the pid -> (ppid, name) map."""
    global _proc_map, _snap_at
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1 or snap == 0xFFFFFFFFFFFFFFFF:
        return
    m = {}
    try:
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if kernel32.Process32FirstW(snap, ctypes.byref(pe)):
            while True:
                name = pe.szExeFile.rsplit("\\", 1)[-1].lower()
                m[int(pe.th32ProcessID)] = (int(pe.th32ParentProcessID), name)
                pe = PROCESSENTRY32W()
                pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)
                if not kernel32.Process32NextW(snap, ctypes.byref(pe)):
                    break
    finally:
        kernel32.CloseHandle(snap)
    _proc_map = m
    _snap_at = time.time()


def lookup(pid):
    """(ppid, name) or (None, None)."""
    if time.time() - _snap_at > SNAPSHOT_REFRESH_SEC:
        build_snapshot()
    return _proc_map.get(pid, (None, None))


def should_hide(hwnd):
    """True only when an AI toolchain ancestor is positively identified."""
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    cur = pid.value
    if not cur:
        return False

    seen = set()
    for _ in range(MAX_ANCESTOR_WALK):
        if not cur or cur in seen:
            return False
        seen.add(cur)
        ppid, name = lookup(cur)
        if name is None:
            return False  # unknown -> conservative: do not hide
        if name in USER_ROOTS:
            return False  # user-launched -> never hide
        if name in AI_ROOTS:
            return True   # proven AI toolchain -> hide
        cur = ppid
    return False


WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
_cls_buf = ctypes.create_unicode_buffer(256)


def _cb(hwnd, lparam):
    try:
        if not user32.IsWindowVisible(hwnd):
            return True
        user32.GetClassNameW(hwnd, _cls_buf, 256)
        if _cls_buf.value != "ConsoleWindowClass":
            return True
        if should_hide(hwnd):
            user32.ShowWindow(hwnd, 0)  # SW_HIDE
            lparam[0] += 1
    except Exception:
        pass
    return True


def log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write("[%s] %s\n" % (datetime.now().isoformat(timespec="seconds"), msg))
    except Exception:
        pass


def main():
    my_pid = int(kernel32.GetCurrentProcessId())
    try:
        PID_FILE.write_text(json.dumps({"pid": my_pid, "ts": datetime.now().isoformat()}),
                            encoding="utf-8")
    except Exception:
        pass
    log("=== v3 START pid=%d surgical mode ===" % my_pid)
    log("    AI_ROOTS(hide):   %s" % ",".join(sorted(AI_ROOTS)))
    log("    USER_ROOTS(keep): %s" % ",".join(sorted(USER_ROOTS)))

    total = 0
    last = 0.0
    while True:
        counter = [0]
        try:
            user32.EnumWindows(WNDENUMPROC(_cb), ctypes.byref(counter))
        except Exception:
            pass
        total += counter[0]
        if counter[0] and time.time() - last > 5:
            log("hidden +%d (total=%d)" % (counter[0], total))
            last = time.time()
        time.sleep(TICK_SEC)


if __name__ == "__main__":
    main()
