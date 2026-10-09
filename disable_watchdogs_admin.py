"""disable_watchdogs_admin.py - R-Codex-Cure-2026-09-29
触发 UAC, 用管理员上下文跑 _admin_disable_watchdogs.py.
"""
import ctypes
import ctypes.wintypes as w
import sys
import os

shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32

SEE_MASK_NOCLOSEPROCESS = 0x40
SEE_MASK_NOASYNC = 0x100
SW_SHOWNORMAL = 1


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


WRAPPER_CMD = r"""@echo off
chcp 65001 >nul 2>&1
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    powershell.exe -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)
python.exe "D:\AIOS\_admin_disable_watchdogs.py"
"""


def main():
    wrapper_path = r"D:\AIOS\_admin_disable_self_elevate.cmd"
    with open(wrapper_path, "w", encoding="utf-8") as f:
        f.write(WRAPPER_CMD)
    # CRLF
    with open(wrapper_path, "rb") as f:
        data = f.read()
    data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    with open(wrapper_path, "wb") as f:
        f.write(data)

    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC
    info.lpVerb = "runas"
    info.lpFile = wrapper_path
    info.nShow = SW_SHOWNORMAL

    ok = ShellExecuteExW(ctypes.byref(info))
    if not ok:
        err = kernel32.GetLastError()
        print(f"ERROR: {err}")
        return err

    if info.hProcess:
        kernel32.WaitForSingleObject(info.hProcess, 30000)
        exit_code = w.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code))
        kernel32.CloseHandle(info.hProcess)
        print(f"exit code: {exit_code.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())