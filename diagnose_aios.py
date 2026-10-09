"""diagnose_aios.py - 启动 AIOS daemon 并捕获 stderr/stdout 找闪退原因"""
import subprocess
import sys
import time

AIOS = r"D:\个人文件\AI\Operator\aios_tools\AIOS_Autonomy_Daemon.exe"

print(f"Starting {AIOS} with stderr capture...")
try:
    r = subprocess.run(
        [AIOS],
        capture_output=True,
        text=True,
        encoding="gbk",
        errors="replace",
        timeout=10,
        creationflags=0x08000008,  # CREATE_NO_WINDOW
    )
    print(f"exit code: {r.returncode}")
    print(f"stdout ({len(r.stdout)} chars):")
    print(r.stdout[:2000] if r.stdout else "  (empty)")
    print(f"stderr ({len(r.stderr)} chars):")
    print(r.stderr[:2000] if r.stderr else "  (empty)")
except subprocess.TimeoutExpired:
    print("AIOS still running after 10s (good - not crashing)")
    # Check process state
    import ctypes, ctypes.wintypes as w
    PQLI = 0x1000
    class P(ctypes.Structure):
        _fields_ = [("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
                    ("th32DefaultHeapID", ctypes.POINTER(w.ULONG)), ("th32ModuleID", w.DWORD),
                    ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
                    ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
                    ("szExeFile", ctypes.c_char * 260)]
    snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(2, 0)
    pe = P()
    pe.dwSize = ctypes.sizeof(P)
    ctypes.windll.kernel32.Process32First(snap, ctypes.byref(pe))
    while True:
        h = ctypes.windll.kernel32.OpenProcess(PQLI, False, pe.th32ProcessID)
        if h:
            sz = ctypes.create_unicode_buffer(260)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, sz, ctypes.byref(w.DWORD(260)))
            if sz.value.lower().endswith("aios_autonomy_daemon.exe"):
                print(f"  AIOS daemon still alive: PID {pe.th32ProcessID}")
            ctypes.windll.kernel32.CloseHandle(h)
        if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(pe)):
            break
except Exception as e:
    print(f"ERROR: {e}")