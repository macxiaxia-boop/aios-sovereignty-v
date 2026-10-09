"""check_aios_codex.py - 查 AIOS + Codex 实时状态"""
import ctypes
import ctypes.wintypes as w
import sys


def is_running(name: str) -> int:
    PQLI = 0x1000

    class P(ctypes.Structure):
        _fields_ = [
            ("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
            ("th32DefaultHeapID", ctypes.POINTER(w.ULONG)), ("th32ModuleID", w.DWORD),
            ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
            ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
            ("szExeFile", ctypes.c_char * 260),
        ]

    snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(2, 0)
    pe = P()
    pe.dwSize = ctypes.sizeof(P)
    ctypes.windll.kernel32.Process32First(snap, ctypes.byref(pe))

    n = 0
    while True:
        h = ctypes.windll.kernel32.OpenProcess(PQLI, False, pe.th32ProcessID)
        if h:
            sz = ctypes.create_unicode_buffer(260)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, sz, ctypes.byref(w.DWORD(260)))
            if sz.value.lower().endswith(name.lower()):
                n += 1
            ctypes.windll.kernel32.CloseHandle(h)
        if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(pe)):
            break

    ctypes.windll.kernel32.CloseHandle(snap)
    return n


def main():
    aios = is_running("AIOS_Autonomy_Daemon.exe")
    codex = is_running("ChatGPT.exe")
    claude = is_running("claude.exe")

    print(f"AIOS_Autonomy_Daemon.exe: {aios} 个")
    print(f"ChatGPT.exe (Codex): {codex} 个")
    print(f"claude.exe (ClaudeCode): {claude} 个")

    if aios == 0:
        print("\n*** AIOS daemon 死了! 这是 Codex 闪退的根因 ***")
    elif codex == 0:
        print("\n*** Codex 没在跑 ***")
    else:
        print("\nOK 全部在跑")

    return 0


if __name__ == "__main__":
    sys.exit(main())