"""check_service_v2.py - 用 UAC 跑 admin context 查 CodexSandboxService 真实状态."""
import ctypes
import ctypes.wintypes as w
import sys
import os
import subprocess

shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32


class SHELLEXECUTEINFOW(ctypes.Structure):
    _fields_ = [
        ("cbSize", w.DWORD),
        ("fMask", ctypes.c_ulong),
        ("hwnd", w.HWND),
        ("lpVerb", w.LPCWSTR),
        ("lpFile", w.LPCWSTR),
        ("lpParameters", w.LPCWSTR),
        ("lpDirectory", w.LPCWSTR),
        ("nShow", ctypes.c_int),
        ("hInstApp", w.HINSTANCE),
        ("lpIDList", ctypes.c_void_p),
        ("lpClass", w.LPCWSTR),
        ("hkeyClass", w.HKEY),
        ("dwHotKey", w.DWORD),
        ("hUnionOrIcon", w.HANDLE),
        ("hProcess", w.HANDLE),
    ]


ShellExecuteExW = shell32.ShellExecuteExW
ShellExecuteExW.restype = w.BOOL
ShellExecuteExW.argtypes = [ctypes.POINTER(SHELLEXECUTEINFOW)]


ADMIN_PY = r"""import ctypes, ctypes.wintypes as w, sys, os
advapi32 = ctypes.windll.advapi32
kernel32 = ctypes.windll.kernel32

SC_MANAGER_ALL_ACCESS = 0xF003F
SERVICE_QUERY_CONFIG = 0x0001

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
        ('dwServiceType', w.DWORD), ('dwCurrentState', w.DWORD),
        ('dwControlsAccepted', w.DWORD), ('dwWin32ExitCode', w.DWORD),
        ('dwServiceSpecificExitCode', w.DWORD), ('dwCheckPoint', w.DWORD),
        ('dwWaitHint', w.DWORD),
    ]

SERVICE_NAME = 'CodexSandboxService.OpenAI.Codex'
RESULT_FILE = r'D:\\AIOS\\_admin_check_svc_v2_result.txt'

with open(RESULT_FILE, 'w', encoding='utf-8') as f:
    f.write('')

is_admin = ctypes.windll.shell32.IsUserAnAdmin()
with open(RESULT_FILE, 'a', encoding='utf-8') as f:
    f.write(f'is_admin={is_admin}\\n')

if not is_admin:
    print('not admin')
    sys.exit(2)

scm = OpenSCManager(None, None, SC_MANAGER_ALL_ACCESS)
if not scm:
    print(f'OpenSCManager failed: {kernel32.GetLastError()}')
    sys.exit(3)
with open(RESULT_FILE, 'a', encoding='utf-8') as f:
    f.write('OpenSCManager ok\\n')

svc = OpenService(scm, SERVICE_NAME, SERVICE_QUERY_CONFIG)
if not svc:
    err = kernel32.GetLastError()
    with open(RESULT_FILE, 'a', encoding='utf-8') as f:
        f.write(f'OpenService failed: {err}, service not registered\\n')
    print(f'OpenService failed: {err}')
    CloseServiceHandle(scm)
    sys.exit(4)
with open(RESULT_FILE, 'a', encoding='utf-8') as f:
    f.write('OpenService ok\\n')

status = SERVICE_STATUS()
if QueryServiceStatus(svc, ctypes.byref(status)):
    states = {1:'STOPPED',2:'START_PENDING',3:'STOP_PENDING',4:'RUNNING',5:'CONTINUE_PENDING',6:'PAUSE_PENDING',7:'PAUSED'}
    state_name = states.get(status.dwCurrentState, str(status.dwCurrentState))
    msg = f'state={state_name}, exit_code={status.dwWin32ExitCode}, checkpoint={status.dwCheckPoint}, wait_hint={status.dwWaitHint}\\n'
    with open(RESULT_FILE, 'a', encoding='utf-8') as f:
        f.write(msg)
    print(msg.strip())

CloseServiceHandle(svc)
CloseServiceHandle(scm)
print('done')
"""


def main():
    # 1. 写 admin python 到文件
    admin_py_path = r"D:\AIOS\_admin_check_svc_v2.py"
    with open(admin_py_path, "w", encoding="utf-8") as f:
        f.write(ADMIN_PY)
    with open(admin_py_path, "rb") as f:
        data = f.read()
    data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    with open(admin_py_path, "wb") as f:
        f.write(data)

    # 2. 写 wrapper cmd
    wrapper = r"""@echo off
chcp 65001 >nul 2>&1
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    powershell.exe -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)
python.exe "D:\AIOS\_admin_check_svc_v2.py"
"""
    wrapper_path = r"D:\AIOS\_admin_check_svc_v2_self_elevate.cmd"
    with open(wrapper_path, "w", encoding="utf-8") as f:
        f.write(wrapper)
    with open(wrapper_path, "rb") as f:
        data = f.read()
    data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    with open(wrapper_path, "wb") as f:
        f.write(data)

    # 3. 触发 UAC
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x140  # NOCLOSEPROCESS | NOASYNC
    info.lpVerb = "runas"
    info.lpFile = wrapper_path
    info.nShow = 1

    ok = ShellExecuteExW(ctypes.byref(info))
    if not ok:
        err = kernel32.GetLastError()
        print(f"ERROR: {err}")
        return err

    if info.hProcess:
        kernel32.WaitForSingleObject(info.hProcess, 30000)
        ec = w.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(ec))
        kernel32.CloseHandle(info.hProcess)
        print(f"exit code: {ec.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())