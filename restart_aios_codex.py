"""restart_aios_codex.py - 启动 AIOS + Codex (不死循环检查 + 自动重启)"""
import subprocess
import time
import ctypes
import ctypes.wintypes as w
import sys

AIOS = r"D:\个人文件\AI\Operator\aios_tools\AIOS_Autonomy_Daemon.exe"
CODEX = r"D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\app\ChatGPT.exe"


def is_running(name: str) -> int:
    """返回匹配 name 的进程数"""
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


def start_aios():
    if is_running("AIOS_Autonomy_Daemon.exe") > 0:
        print("AIOS daemon 已在跑")
        return True
    p = subprocess.Popen([AIOS], creationflags=0x08000008)
    print(f"启动 AIOS daemon PID={p.pid}")
    time.sleep(8)
    return is_running("AIOS_Autonomy_Daemon.exe") > 0


def start_codex():
    if is_running("ChatGPT.exe") > 0:
        print("Codex 已在跑")
        return True
    p = subprocess.Popen([CODEX], creationflags=0x08000008)
    print(f"启动 Codex PID={p.pid}")
    time.sleep(15)
    return is_running("ChatGPT.exe") > 0


def main():
    print("=== 启动 AIOS + Codex ===\n")

    # 先杀残留
    print("[0] 杀残留 Codex + AIOS daemon ...")
    subprocess.run(["taskkill", "/F", "/IM", "ChatGPT.exe", "/T"],
                   capture_output=True, creationflags=0x08000008, timeout=10)
    subprocess.run(["taskkill", "/F", "/IM", "codex.exe", "/T"],
                   capture_output=True, creationflags=0x08000008, timeout=10)
    subprocess.run(["taskkill", "/F", "/IM", "AIOS_Autonomy_Daemon.exe", "/T"],
                   capture_output=True, creationflags=0x08000008, timeout=10)
    time.sleep(3)

    # 启动 AIOS
    print("[1] 启动 AIOS daemon ...")
    if not start_aios():
        print("AIOS 启动失败, 退出")
        return 1

    # 启动 Codex
    print("\n[2] 启动 Codex ...")
    if not start_codex():
        print("Codex 启动失败")
        return 1

    # 验证
    print("\n[3] 验证状态 ...")
    n_aios = is_running("AIOS_Autonomy_Daemon.exe")
    n_codex = is_running("ChatGPT.exe")
    print(f"AIOS daemon: {n_aios} 个")
    print(f"Codex (ChatGPT.exe): {n_codex} 个")

    if n_aios > 0 and n_codex > 0:
        print("\n✓ AIOS + Codex 都跑起来了")
        print("\n注意:")
        print("- AIOS daemon 闪退是 Codex 闪退的根因")
        print("- 必须右键管理员跑 D:\\AIOS\\install_aios_loop.cmd 注册永久守护")
        print("- 守护没注册前, AIOS daemon 死掉 Codex 也会跟着闪退")
    return 0


if __name__ == "__main__":
    sys.exit(main())