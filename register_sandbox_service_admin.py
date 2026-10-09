"""register_sandbox_service_admin.py - R-Codex-Cure-2026-09-29
触发 UAC 提权本 Python 进程, 然后调 advapi32 注册 CodexSandboxService.

策略:
  1. 用 ShellExecuteExW "runas" 触发 UAC 弹窗, 跑一个 self-elevate.cmd
  2. self-elevate.cmd 用 PowerShell Start-Process -Verb RunAs 触发 UAC
  3. 提升的子进程跑一个 ctypes_callback.py 调 Windows API
  4. ctypes_callback.py 注册服务 + 启动服务 + 写状态文件
  5. 主进程读状态文件确认结果

但 sandbox 阻挡 PowerShell ... 简化: self-elevate.cmd 直接再触发 UAC 跑 ctypes_callback
"""
import os
import sys
import ctypes
import ctypes.wintypes as w

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


# Write a self-elevating wrapper that runs ctypes_callback.py as admin
WRAPPER_CMD = r"""@echo off
REM Self-elevate wrapper for CodexSandboxService registration
REM 1. Re-trigger UAC for this same .cmd (already in admin context)
REM 2. Run Python with ctypes to register + start service
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    REM Not admin yet, re-trigger UAC
    powershell.exe -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

REM Now we're admin - run Python with ctypes to register the service
python.exe "D:\AIOS\_admin_register_service.py"
"""


def main():
    # 1. 写 wrapper 到临时文件
    wrapper_path = r"D:\AIOS\_admin_self_elevate.cmd"
    with open(wrapper_path, "w", encoding="utf-8") as f:
        f.write(WRAPPER_CMD)
    # 强制 CRLF
    with open(wrapper_path, "rb") as f:
        data = f.read()
    data = data.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
    with open(wrapper_path, "wb") as f:
        f.write(data)
    print(f"wrote: {wrapper_path}")

    # 2. 触发 UAC
    print(f"\n=== Trigger UAC for {wrapper_path} ===")
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC
    info.lpVerb = "runas"
    info.lpFile = wrapper_path
    info.nShow = SW_SHOWNORMAL

    ok = ShellExecuteExW(ctypes.byref(info))
    if not ok:
        err = kernel32.GetLastError()
        print(f"  ERROR: ShellExecuteEx failed: {err}")
        return err

    if info.hProcess:
        print(f"  Process handle: {info.hProcess}")
        # 等 30 秒让 UAC + Python 完成
        WAIT_TIMEOUT = 30000
        rc = kernel32.WaitForSingleObject(info.hProcess, WAIT_TIMEOUT)
        if rc == 0:
            exit_code = w.DWORD()
            kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code))
            print(f"  exit code: {exit_code.value}")
            kernel32.CloseHandle(info.hProcess)
        else:
            print(f"  timeout (rc={rc}), UAC 可能还在等")
            kernel32.CloseHandle(info.hProcess)
    return 0


if __name__ == "__main__":
    sys.exit(main())