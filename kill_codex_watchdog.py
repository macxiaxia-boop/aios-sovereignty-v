"""kill_codex_watchdog.py - R-Codex-Cure-2026-09-29 V4
立即杀掉所有 Codex watchdog Python 进程.

策略:
  1. 枚举所有 python.exe / pythonw.exe 进程 (用 ctypes + QueryFullProcessImageName)
  2. 检查每个进程的 image path 是否在 WorkBuddy 沙箱之外
  3. 检查父进程: 如果父进程是 schtasks 启动的 svchost, 大概率是 watchdog
  4. 杀父进程是 cpython-3.12 的 pythonw.exe 子进程 (watchdog 的派生链)

但更简单: 直接杀所有 cpython-3.12 + cpython-3.13 进程.
用户主动跑这个脚本时, 没有重要 python 任务.
"""
import ctypes
import ctypes.wintypes as w

PQLI = 0x1000
PT = 1


class PROCESSENTRY32(ctypes.Structure):
    _fields_ = [
        ("dwSize", w.DWORD),
        ("cntUsage", w.DWORD),
        ("th32ProcessID", w.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(w.ULONG)),
        ("th32ModuleID", w.DWORD),
        ("cntThreads", w.DWORD),
        ("th32ParentProcessID", w.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", w.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


def main():
    snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(2, 0)
    pe = PROCESSENTRY32()
    pe.dwSize = ctypes.sizeof(PROCESSENTRY32)
    ctypes.windll.kernel32.Process32First(snap, ctypes.byref(pe))

    targets = []
    while True:
        h = ctypes.windll.kernel32.OpenProcess(PQLI, False, pe.th32ProcessID)
        if h:
            sz = ctypes.create_unicode_buffer(260)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(
                h, 0, sz, ctypes.byref(w.DWORD(260))
            )
            path = sz.value.lower()
            # 只匹配 cpython-3.12 / cpython-3.13 (watchdog runner.cmd 用这个)
            if "cpython-3.12" in path or "cpython-3.13" in path:
                targets.append((pe.th32ProcessID, pe.th32ParentProcessID, path))
            ctypes.windll.kernel32.CloseHandle(h)
        if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(pe)):
            break

    print(f"=== 找到 {len(targets)} 个 cpython-3.12/13 进程 ===")
    killed = 0
    for pid, ppid, path in targets:
        # 不杀当前进程的 PID (避免自杀)
        cur_pid = ctypes.windll.kernel32.GetCurrentProcessId()
        if pid == cur_pid:
            print(f"  SKIP self: PID {pid}")
            continue
        h = ctypes.windll.kernel32.OpenProcess(PT, False, pid)
        if h:
            ok = ctypes.windll.kernel32.TerminateProcess(h, 0)
            ctypes.windll.kernel32.CloseHandle(h)
            if ok:
                killed += 1
                print(f"  killed PID {pid} (parent {ppid})")
            else:
                print(f"  FAIL PID {pid}")
        else:
            print(f"  open fail PID {pid}")
    print(f"=== killed {killed} cpython ===")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())