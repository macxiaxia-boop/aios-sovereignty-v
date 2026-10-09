"""trigger_admin_one_click.py - 触发 UAC 跑 admin_one_click.cmd (完整 setup)."""
import ctypes
import ctypes.wintypes as w
import sys

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


def main():
    cmd_path = r"D:\AIOS\admin_one_click.cmd"
    print(f"=== Triggering UAC for {cmd_path} ===")
    print("  (如果弹 UAC 窗口, 请点 '是' 确认提权)")
    print("  然后 cmd 会自动跑完整配置")

    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x140  # NOCLOSEPROCESS | NOASYNC
    info.lpVerb = "runas"
    info.lpFile = cmd_path
    info.nShow = 1

    ok = ShellExecuteExW(ctypes.byref(info))
    if not ok:
        err = kernel32.GetLastError()
        print(f"ERROR: {err}")
        return err

    print(f"  process started, handle={info.hProcess}")
    print(f"  waiting up to 90 seconds for full setup...")

    if info.hProcess:
        # 等 90 秒 (杀 + 删 + 注册 + 启动 + 等 + 验证)
        rc = kernel32.WaitForSingleObject(info.hProcess, 90000)
        ec = w.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(ec))
        kernel32.CloseHandle(info.hProcess)
        print(f"  wait rc={rc}, exit code={ec.value}")
        return ec.value if rc == 0 else -1

    return 0


if __name__ == "__main__":
    sys.exit(main())