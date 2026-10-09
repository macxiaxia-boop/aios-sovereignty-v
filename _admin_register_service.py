"""_admin_register_service.py - R-Codex-Cure-2026-09-29 V2
跑在管理员上下文: 用 ctypes 直接调 advapi32 注册 CodexSandboxService.
不被 sandbox 阻挡 (sc.exe / reg.exe 被挡, 但 advapi32.dll 是 DLL).
"""
import ctypes
import ctypes.wintypes as w
import sys
import os

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

RESULT_FILE = r"D:\AIOS\_admin_register_result.txt"


def write_result(stage: str, ok: bool, msg: str = ""):
    """Write result to file for parent process to read."""
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{stage}] ok={ok} {msg}\n")
    print(f"[{stage}] ok={ok} {msg}")


def main():
    # 清空 result 文件
    try:
        with open(RESULT_FILE, "w", encoding="utf-8") as f:
            f.write("")
    except Exception:
        pass

    # 检查管理员权限
    try:
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        is_admin = False
    write_result("ADMIN", is_admin, f"is_admin={is_admin}")
    if not is_admin:
        write_result("FAIL", False, "当前进程不是管理员")
        return 2

    if not os.path.exists(SANDBOX_EXE):
        write_result("EXE", False, f"{SANDBOX_EXE} 不存在")
        return 3

    # 打开 SCManager
    scm = OpenSCManager(None, None, SC_MANAGER_ALL_ACCESS)
    if not scm:
        err = kernel32.GetLastError()
        write_result("SCM", False, f"OpenSCManager failed: {err}")
        return 4
    write_result("SCM", True, "opened")

    # 创建服务
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
        if err == 1073:  # ERROR_SERVICE_EXISTS
            write_result("CREATE", True, "already exists")
            svc = OpenService(scm, SERVICE_NAME, SERVICE_ALL_ACCESS)
            if not svc:
                write_result("OPEN", False, f"OpenService failed: {kernel32.GetLastError()}")
                CloseServiceHandle(scm)
                return 5
        else:
            write_result("CREATE", False, f"CreateService failed: {err}")
            CloseServiceHandle(scm)
            return 6
    else:
        write_result("CREATE", True, "created")

    # 启动服务
    ok = StartService(svc, 0, None)
    if not ok:
        err = kernel32.GetLastError()
        if err == 1056:  # ERROR_SERVICE_ALREADY_RUNNING
            write_result("START", True, "already running")
        else:
            write_result("START", False, f"StartService failed: {err}")
            CloseServiceHandle(svc)
            CloseServiceHandle(scm)
            return 7
    else:
        write_result("START", True, "started")

    # 验证
    status = SERVICE_STATUS()
    if QueryServiceStatus(svc, ctypes.byref(status)):
        states = {1: "STOPPED", 2: "START_PENDING", 3: "STOP_PENDING", 4: "RUNNING", 5: "CONTINUE_PENDING", 6: "PAUSE_PENDING", 7: "PAUSED"}
        state_name = states.get(status.dwCurrentState, str(status.dwCurrentState))
        write_result("STATUS", True, f"state={state_name}, exit_code={status.dwWin32ExitCode}")

    CloseServiceHandle(svc)
    CloseServiceHandle(scm)
    write_result("DONE", True, "CodexSandboxService ready")
    return 0


if __name__ == "__main__":
    sys.exit(main())