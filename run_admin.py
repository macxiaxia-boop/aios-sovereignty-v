"""run_admin.py - R-Codex-Cure-2026-09-29
通过 ShellExecuteExW + "runas" 触发 UAC 弹窗, 让用户点确定提权运行指定命令.
"""
import ctypes
import ctypes.wintypes as w
import sys
import os

shell32 = ctypes.windll.shell32
kernel32 = ctypes.windll.kernel32
user32 = ctypes.windll.user32

SEE_MASK_NOCLOSEPROCESS = 0x00000040
SEE_MASK_NOASYNC = 0x00000100
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


def run_as_admin(cmd_path: str, wait: bool = True) -> int:
    """Trigger UAC and run cmd_path as admin. Return exit code (or 0 if wait=False)."""
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = SEE_MASK_NOCLOSEPROCESS | SEE_MASK_NOASYNC
    info.lpVerb = "runas"
    info.lpFile = cmd_path
    info.nShow = SW_SHOWNORMAL

    ok = ShellExecuteExW(ctypes.byref(info))
    if not ok:
        err = ctypes.windll.kernel32.GetLastError()
        print(f"  ERROR: ShellExecuteEx failed: {err}")
        return err

    if wait and info.hProcess:
        kernel32.WaitForSingleObject(info.hProcess, 0xFFFFFFFF)
        exit_code = w.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(exit_code))
        kernel32.CloseHandle(info.hProcess)
        return exit_code.value
    return 0


if __name__ == "__main__":
    # 跑用户传的命令（管理员模式）
    if len(sys.argv) < 2:
        print("usage: run_admin.py <cmd_path> [args...]")
        sys.exit(1)
    cmd = sys.argv[1]
    print(f"=== Trigger UAC for {cmd} ===")
    print(f"  (如果弹 UAC 窗口, 请点 '是' 确认提权)")
    rc = run_as_admin(cmd)
    print(f"\n=== exit code: {rc} ===")
    sys.exit(0 if rc == 0 else rc)