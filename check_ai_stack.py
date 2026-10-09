"""check_ai_stack.py - 查所有 AI 栈进程状态"""
import ctypes
import ctypes.wintypes as w

PQLI = 0xF003F


class P(ctypes.Structure):
    _fields_ = [
        ("dwSize", w.DWORD), ("cntUsage", w.DWORD), ("th32ProcessID", w.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(w.ULONG)), ("th32ModuleID", w.DWORD),
        ("cntThreads", w.DWORD), ("th32ParentProcessID", w.DWORD),
        ("pcPriClassBase", ctypes.c_long), ("dwFlags", w.DWORD),
        ("szExeFile", ctypes.c_char * 260),
    ]


def main():
    snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(2, 0)
    pe = P()
    pe.dwSize = ctypes.sizeof(P)
    ctypes.windll.kernel32.Process32First(snap, ctypes.byref(pe))

    categories = {}
    details = {}

    while True:
        h = ctypes.windll.kernel32.OpenProcess(PQLI, False, pe.th32ProcessID)
        if h:
            sz = ctypes.create_unicode_buffer(260)
            ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, sz, ctypes.byref(w.DWORD(260)))
            path = sz.value
            name = path.split("\\")[-1].lower()

            if "codex" in name or "chatgpt" in name:
                cat = "Codex"
            elif "claude" in name:
                cat = "ClaudeCode"
            elif "hermes" in name:
                cat = "Hermes"
            elif "aios" in name:
                cat = "AIOS"
            elif "openclaw" in name:
                cat = "OpenClaw"
            elif "workbuddy" in name:
                cat = "WorkBuddy"
            elif "sandbox" in name and "WorkBuddy" not in path and "workbuddy" not in path:
                cat = "Sandbox(Codex)"
            else:
                cat = "Other"

            categories[cat] = categories.get(cat, 0) + 1
            details.setdefault(cat, []).append((pe.th32ProcessID, path))
            ctypes.windll.kernel32.CloseHandle(h)
        if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(pe)):
            break

    print("=== AI 栈进程 ===")
    total = 0
    for cat in ["Codex", "ClaudeCode", "Hermes", "AIOS", "OpenClaw", "WorkBuddy", "Sandbox(Codex)", "Other"]:
        if cat in categories:
            n = categories[cat]
            total += n
            print(f"  {cat}: {n} 个")
            for pid, path in details[cat][:3]:
                print(f"    PID {pid}: ...{path[-60:]}")
            if len(details[cat]) > 3:
                print(f"    ... +{len(details[cat])-3} more")
    print(f"  TOTAL: {total}")


if __name__ == "__main__":
    main()