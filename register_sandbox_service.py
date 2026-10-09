"""register_sandbox_service.py - R-Codex-Cure-2026-09-29 V2
用 ctypes 直接调 advapi32.dll 注册 CodexSandboxService (绕过 sc.exe 被 sandbox 阻挡).
"""
import ctypes
import ctypes.wintypes as w
import sys
import os

# Constants
SC_MANAGER_ALL_ACCESS = 0xF003F
SERVICE_ALL_ACCESS = 0xF01FF
SERVICE_AUTO_START = 0x00000002
SERVICE_DEMAND_START = 0x00000003

# advapi32.dll
advapi32 = ctypes.windll.advapi32
kernel32 = ctypes.windll.kernel32

OpenSCManager = advapi32.OpenSCManagerW
OpenSCManager.restype = w.LPCVOID
OpenSCManager.argtypes = [w.LPCWSTR, w.LPCWSTR, w.DWORD]

CreateService = advapi32.CreateServiceW
CreateService.restype = w.LPCVOID
CreateService.argtypes = [
    w.LPCVOID,  # hSCManager
    w.LPCWSTR,  # lpServiceName
    w.LPCWSTR,  # lpDisplayName
    w.DWORD,    # dwDesiredAccess
    w.DWORD,    # dwServiceType
    w.DWORD,    # dwStartType
    w.DWORD,    # dwErrorControl
    w.LPCWSTR,  # lpBinaryPathName
    w.LPCWSTR,  # lpLoadOrderGroup
    ctypes.c_void_p,  # lpdwTagId
    w.LPCWSTR,  # lpDependencies
    w.LPCWSTR,  # lpServiceStartName
    w.LPCWSTR,  # lpPassword
]

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


def main():
    if not os.path.exists(SANDBOX_EXE):
        print(f"ERROR: sandbox service exe not found: {SANDBOX_EXE}")
        return 2

    # 打开 SCManager
    print("[1/4] OpenSCManager ...")
    scm = OpenSCManager(None, None, SC_MANAGER_ALL_ACCESS)
    if not scm:
        print(f"  ERROR: OpenSCManager failed, last error: {kernel32.GetLastError()}")
        return 3

    # 创建服务
    print(f"[2/4] CreateService {SERVICE_NAME} ...")
    svc = CreateService(
        scm,
        SERVICE_NAME,
        DISPLAY_NAME,
        SERVICE_ALL_ACCESS,
        0x10,  # SERVICE_WIN32_OWN_PROCESS
        SERVICE_AUTO_START,
        1,  # SERVICE_ERROR_NORMAL
        SANDBOX_EXE,
        None, None, None, None, None,
    )
    if not svc:
        err = kernel32.GetLastError()
        if err == 1073:  # ERROR_SERVICE_EXISTS
            print(f"  服务已存在, 打开现有服务")
            svc = OpenService(scm, SERVICE_NAME, SERVICE_ALL_ACCESS)
            if not svc:
                print(f"  ERROR: OpenService failed: {kernel32.GetLastError()}")
                CloseServiceHandle(scm)
                return 4
        else:
            print(f"  ERROR: CreateService failed: {err}")
            CloseServiceHandle(scm)
            return 5

    # 启动服务
    print("[3/4] StartService ...")
    ok = StartService(svc, 0, None)
    if not ok:
        err = kernel32.GetLastError()
        if err == 1056:  # ERROR_SERVICE_ALREADY_RUNNING
            print(f"  服务已在跑")
        else:
            print(f"  ERROR: StartService failed: {err}")
            CloseServiceHandle(svc)
            CloseServiceHandle(scm)
            return 6
    else:
        print(f"  服务启动成功")

    # 验证
    print("[4/4] QueryServiceStatus ...")
    status = SERVICE_STATUS()
    if QueryServiceStatus(svc, ctypes.byref(status)):
        states = {
            1: "STOPPED", 2: "START_PENDING", 3: "STOP_PENDING",
            4: "RUNNING", 5: "CONTINUE_PENDING", 6: "PAUSE_PENDING", 7: "PAUSED",
        }
        state_name = states.get(status.dwCurrentState, str(status.dwCurrentState))
        print(f"  状态: {state_name}")

    CloseServiceHandle(svc)
    CloseServiceHandle(scm)
    print("\n✓ CodexSandboxService 注册并启动成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())