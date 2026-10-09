"""start_codex.py - 直接启动 Codex 免安装版 ChatGPT.exe"""
import subprocess
import sys
import ctypes
import ctypes.wintypes as w
import time

CHATGPT_EXE = r"D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\app\ChatGPT.exe"

print(f"Starting: {CHATGPT_EXE}")

try:
    p = subprocess.Popen(
        [CHATGPT_EXE],
        creationflags=0x08000008,  # CREATE_NO_WINDOW
    )
    print(f"Started PID={p.pid}")
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)

# 等 20s
time.sleep(20)

# 统计进程
PQLI = 0xF003F


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

n_chatgpt = 0
total_mem = 0
chatgpt_pids = []
while True:
    h = ctypes.windll.kernel32.OpenProcess(PQLI, False, pe.th32ProcessID)
    if h:
        sz = ctypes.create_unicode_buffer(260)
        ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, sz, ctypes.byref(w.DWORD(260)))
        path = sz.value
        if path.lower().endswith("chatgpt.exe"):
            n_chatgpt += 1
            chatgpt_pids.append(pe.th32ProcessID)

            class PMC(ctypes.Structure):
                _fields_ = [
                    ("cb", w.DWORD), ("PageFaultCount", w.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]
            pmc = PMC()
            ctypes.windll.psapi.GetProcessMemoryInfo(h, ctypes.byref(pmc), ctypes.sizeof(pmc))
            total_mem += pmc.WorkingSetSize
        ctypes.windll.kernel32.CloseHandle(h)
    if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(pe)):
        break

print(f"\n=== 启动结果 ===")
print(f"ChatGPT.exe 进程: {n_chatgpt} 个")
print(f"PID: {chatgpt_pids}")
print(f"总内存: {total_mem / 1024 / 1024:.1f} MB")

if n_chatgpt == 0:
    print("\n*** Codex 未启动，可能原因: ***")
    print("1. CodexSandboxService 未注册或未运行")
    print("2. hooks hash 不一致导致 Codex 拒绝启动 hooks")
    print("3. 免安装版 path 配置问题")