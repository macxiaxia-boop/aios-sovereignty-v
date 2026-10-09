"""_admin_start_svc.py - 跑在 admin 上下文: 用 ctypes 启动 CodexSandboxService."""
import ctypes
import ctypes.wintypes as w
import sys
import time

advapi32 = ctypes.windll.advapi32
kernel32 = ctypes.windll.kernel32
NL = chr(10)

SC_MANAGER_ALL_ACCESS = 0xF003F
SERVICE_ALL_ACCESS = 0xF01FF
SERVICE_QUERY_STATUS = 0x0004
SERVICE_START = 0x0010

OpenSCManager = advapi32.OpenSCManagerW
OpenSCManager.restype = w.LPCVOID
OpenSCManager.argtypes = [w.LPCWSTR, w.LPCWSTR, w.DWORD]

OpenService = advapi32.OpenServiceW
OpenService.restype = w.LPCVOID
OpenService.argtypes = [w.LPCVOID, w.LPCWSTR, w.DWORD]

StartService = advapi32.StartServiceW
StartService.restype = w.BOOL
StartService.argtypes = [w.LPCVOID, w.DWORD, ctypes.c_void_p]

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
RESULT_FILE = r"D:\AIOS\_admin_start_svc_result.txt"

with open(RESULT_FILE, "w", encoding="utf-8") as f:
    f.write("")

if not ctypes.windll.shell32.IsUserAnAdmin():
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"NOT ADMIN{NL}")
    sys.exit(2)

scm = OpenSCManager(None, None, SC_MANAGER_ALL_ACCESS)
if not scm:
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"OpenSCManager failed: {kernel32.GetLastError()}{NL}")
    sys.exit(3)

svc = OpenService(scm, SERVICE_NAME, SERVICE_ALL_ACCESS)
if not svc:
    err = kernel32.GetLastError()
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"OpenService failed: {err}{NL}")
    CloseServiceHandle(scm)
    sys.exit(4)

# 启动
ok = StartService(svc, 0, None)
err = kernel32.GetLastError()
with open(RESULT_FILE, "a", encoding="utf-8") as f:
    if ok:
        f.write(f"StartService OK, err=0{NL}")
    elif err == 1056:  # already running
        f.write(f"StartService: already running (err=1056){NL}")
    else:
        f.write(f"StartService failed: err={err}{NL}")

# 等 5s 看状态
time.sleep(5)

status = SERVICE_STATUS()
if QueryServiceStatus(svc, ctypes.byref(status)):
    states = {
        1: "STOPPED", 2: "START_PENDING", 3: "STOP_PENDING",
        4: "RUNNING", 5: "CONTINUE_PENDING", 6: "PAUSE_PENDING", 7: "PAUSED",
    }
    state = states.get(status.dwCurrentState, str(status.dwCurrentState))
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"state={state}, win32_exit={status.dwWin32ExitCode}, specific_exit={status.dwServiceSpecificExitCode}{NL}")

CloseServiceHandle(svc)
CloseServiceHandle(scm)
sys.exit(0)