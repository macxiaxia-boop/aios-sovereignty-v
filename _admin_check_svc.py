"""_admin_check_svc.py - 跑在管理员上下文: 查 CodexSandboxService 状态.
修正: 用 chr(10) 代替 \\n 避免字符串转义问题.
"""
import ctypes
import ctypes.wintypes as w
import sys

advapi32 = ctypes.windll.advapi32
kernel32 = ctypes.windll.kernel32
NL = chr(10)

SC_MANAGER_ALL_ACCESS = 0xF003F
SERVICE_QUERY_CONFIG = 0x0001
SERVICE_QUERY_STATUS = 0x0004
SERVICE_INTERROGATE = 0x0080

OpenSCManager = advapi32.OpenSCManagerW
OpenSCManager.restype = w.LPCVOID
OpenSCManager.argtypes = [w.LPCWSTR, w.LPCWSTR, w.DWORD]

OpenService = advapi32.OpenServiceW
OpenService.restype = w.LPCVOID
OpenService.argtypes = [w.LPCVOID, w.LPCWSTR, w.DWORD]

QueryServiceStatus = advapi32.QueryServiceStatus
QueryServiceStatus.restype = w.BOOL
QueryServiceStatus.argtypes = [w.LPCVOID, ctypes.c_void_p]

CloseServiceHandle = advapi32.CloseServiceHandle


class SERVICE_STATUS(ctypes.Structure):
    _fields_ = [
        ("dwServiceType", w.DWORD), ("dwCurrentState", w.DWORD),
        ("dwControlsAccepted", w.DWORD), ("dwWin32ExitCode", w.DWORD),
        ("dwServiceSpecificExitCode", w.DWORD), ("dwCheckPoint", w.DWORD),
        ("dwWaitHint", w.DWORD),
    ]


SERVICE_NAME = "CodexSandboxService.OpenAI.Codex"
RESULT_FILE = r"D:\AIOS\_admin_check_svc_result.txt"

with open(RESULT_FILE, "w", encoding="utf-8") as f:
    f.write("")

is_admin = ctypes.windll.shell32.IsUserAnAdmin()
with open(RESULT_FILE, "a", encoding="utf-8") as f:
    f.write(f"is_admin={is_admin}{NL}")

if not is_admin:
    sys.exit(2)

scm = OpenSCManager(None, None, SC_MANAGER_ALL_ACCESS)
if not scm:
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"OpenSCManager failed: {kernel32.GetLastError()}{NL}")
    sys.exit(3)
with open(RESULT_FILE, "a", encoding="utf-8") as f:
    f.write(f"OpenSCManager ok{NL}")

svc = OpenService(scm, SERVICE_NAME, SERVICE_QUERY_STATUS | SERVICE_INTERROGATE | SERVICE_QUERY_CONFIG)
if not svc:
    err = kernel32.GetLastError()
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"OpenService failed: {err}, service not registered{NL}")
    CloseServiceHandle(scm)
    sys.exit(4)
with open(RESULT_FILE, "a", encoding="utf-8") as f:
    f.write(f"OpenService ok{NL}")

status = SERVICE_STATUS()
ok = QueryServiceStatus(svc, ctypes.byref(status))
if ok:
    states = {
        1: "STOPPED", 2: "START_PENDING", 3: "STOP_PENDING",
        4: "RUNNING", 5: "CONTINUE_PENDING", 6: "PAUSE_PENDING", 7: "PAUSED",
    }
    state = states.get(status.dwCurrentState, str(status.dwCurrentState))
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"state={state}, exit_code={status.dwWin32ExitCode}, checkpoint={status.dwCheckPoint}, wait_hint={status.dwWaitHint}{NL}")
else:
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"QueryServiceStatus failed: {kernel32.GetLastError()}{NL}")

CloseServiceHandle(svc)
CloseServiceHandle(scm)
sys.exit(0)