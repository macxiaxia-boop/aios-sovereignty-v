"""_admin_full_setup.py - 跑在管理员上下文, 完整配置 CodexSandboxService.
"""
import ctypes
import ctypes.wintypes as w
import sys
import os
import subprocess
import time

advapi32 = ctypes.windll.advapi32
kernel32 = ctypes.windll.kernel32

SC_MANAGER_ALL_ACCESS = 0xF003F
SERVICE_ALL_ACCESS = 0xF01FF
SERVICE_QUERY_CONFIG = 0x0001
SERVICE_AUTO_START = 0x00000002
SERVICE_WIN32_OWN_PROCESS = 0x00000010
SERVICE_ERROR_NORMAL = 0x00000001

OpenSCManager = advapi32.OpenSCManagerW
OpenSCManager.restype = w.LPCVOID
OpenSCManager.argtypes = [w.LPCWSTR, w.LPCWSTR, w.DWORD]

CreateService = advapi32.CreateServiceW
CreateService.restype = w.LPCVOID
CreateService.argtypes = [w.LPCVOID, w.LPCWSTR, w.LPCWSTR, w.DWORD, w.DWORD, w.DWORD, w.DWORD, w.LPCWSTR, w.LPCWSTR, ctypes.c_void_p, w.LPCWSTR, w.LPCWSTR, w.LPCWSTR]

OpenService = advapi32.OpenServiceW
OpenService.restype = w.LPCVOID
OpenService.argtypes = [w.LPCVOID, w.LPCWSTR, w.DWORD]

StartService = advapi32.StartServiceW
StartService.restype = w.BOOL
StartService.argtypes = [w.LPCVOID, w.DWORD, ctypes.c_void_p]

CloseServiceHandle = advapi32.CloseServiceHandle

QueryServiceStatus = advapi32.QueryServiceStatus
QueryServiceStatus.restype = w.BOOL
QueryServiceStatus.argtypes = [w.LPCVOID, ctypes.c_void_p]

DeleteService = advapi32.DeleteService
DeleteService.restype = w.BOOL
DeleteService.argtypes = [w.LPCVOID]


class SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ("dwServiceType", w.DWORD),
        ("dwCurrentState", w.DWORD),
        ("dwControlsAccepted", w.DWORD),
        ("dwWin32ExitCode", w.DWORD),
        ("dwServiceSpecificExitCode", w.DWORD),
        ("dwCheckPoint", w.DWORD),
        ("dwWaitHint", w.DWORD),
    ]


SANDBOX_EXE = r"D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\app\resources\codex-windows-sandbox-service.exe"
SERVICE_NAME = "CodexSandboxService.OpenAI.Codex"
DISPLAY_NAME = "Codex Sandbox Service"
RESULT_FILE = r"D:\AIOS\_admin_full_setup_result.txt"


def write(msg: str):
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(msg + "\n")
    print(msg)


def main():
    with open(RESULT_FILE, "w", encoding="utf-8") as f:
        f.write("")

    is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    write(f"[1/5] is_admin={is_admin}")
    if not is_admin:
        return 2

    # 1. 停 V4 watchdog + 删 schtasks (避免它反复创建 service)
    write("[2/5] 停 V4 watchdog + 删 schtasks")
    subprocess.run(["schtasks.exe", "/Delete", "/TN", "Codex-Codex-Cure-V4-Watchdog", "/F"],
                   capture_output=True, text=True, encoding="gbk", errors="ignore", timeout=10)
    write("  V4 watchdog schtasks 删了")

    # 2. 杀所有正在跑的 watchdog Python 进程 (用 taskkill)
    # 找 cpython-3.x 进程
    import ctypes
    PQLI = 0xF003F
    PT = 1

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
    killed_watchdog = 0
    while True:
        try:
            h = ctypes.windll.kernel32.OpenProcess(PQLI, False, pe.th32ProcessID)
            if h:
                sz = ctypes.create_unicode_buffer(260)
                ctypes.windll.kernel32.QueryFullProcessImageNameW(h, 0, sz, ctypes.byref(w.DWORD(260)))
                path = sz.value.lower()
                if ("cpython-3.12" in path or "cpython-3.13" in path) and "_openai_codex_beta_watchdog" in path:
                    h2 = ctypes.windll.kernel32.OpenProcess(PT, False, pe.th32ProcessID)
                    if h2:
                        ctypes.windll.kernel32.TerminateProcess(h2, 0)
                        ctypes.windll.kernel32.CloseHandle(h2)
                        killed_watchdog += 1
                ctypes.windll.kernel32.CloseHandle(h)
        except Exception:
            pass
        if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(pe)):
            break
    write(f"  killed {killed_watchdog} watchdog python 进程")

    # 3. 注册 CodexSandboxService
    write(f"[3/5] 注册 CodexSandboxService")
    scm = OpenSCManager(None, None, SC_MANAGER_ALL_ACCESS)
    if not scm:
        write(f"  ERROR OpenSCManager: {kernel32.GetLastError()}")
        return 3

    svc = CreateService(
        scm,
        SERVICE_NAME,
        DISPLAY_NAME,
        SERVICE_ALL_ACCESS,
        SERVICE_WIN32_OWN_PROCESS,
        SERVICE_AUTO_START,
        SERVICE_ERROR_NORMAL,
        SANDBOX_EXE,
        None, None, None, None, None,
    )
    if not svc:
        err = kernel32.GetLastError()
        if err == 1073:  # already exists
            write("  服务已存在")
            svc = OpenService(scm, SERVICE_NAME, SERVICE_ALL_ACCESS)
            if not svc:
                write(f"  OpenSCManager Open failed: {kernel32.GetLastError()}")
                CloseServiceHandle(scm)
                return 4
        else:
            write(f"  CreateService failed: {err}")
            CloseServiceHandle(scm)
            return 5
    else:
        write("  服务已创建")

    # 4. 启动服务
    write(f"[4/5] 启动 CodexSandboxService")
    ok = StartService(svc, 0, None)
    if not ok:
        err = kernel32.GetLastError()
        if err == 1056:
            write("  服务已在跑")
        else:
            write(f"  StartService failed: {err}")
            CloseServiceHandle(svc)
            CloseServiceHandle(scm)
            return 6
    else:
        write("  服务启动命令发出, 等 3s")

    # 等服务完全启动
    time.sleep(3)

    # 5. 验证状态
    write(f"[5/5] 验证状态")
    status = SERVICE_STATUS()
    if QueryServiceStatus(svc, ctypes.byref(status)):
        states = {1: "STOPPED", 2: "START_PENDING", 3: "STOP_PENDING", 4: "RUNNING", 5: "CONTINUE_PENDING", 6: "PAUSE_PENDING", 7: "PAUSED"}
        write(f"  state: {states.get(status.dwCurrentState, status.dwCurrentState)}")
        write(f"  exit_code: {status.dwWin32ExitCode}")

    CloseServiceHandle(svc)
    CloseServiceHandle(scm)
    write("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())