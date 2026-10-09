"""trigger_install_aios_loop.py - 触发 UAC 跑 install_aios_loop.cmd"""
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
    cmd = r"D:\AIOS\install_aios_loop.cmd"
    info = SHELLEXECUTEINFOW()
    info.cbSize = ctypes.sizeof(info)
    info.fMask = 0x140
    info.lpVerb = "runas"
    info.lpFile = cmd
    info.nShow = 1

    ShellExecuteExW(ctypes.byref(info))
    if info.hProcess:
        kernel32.WaitForSingleObject(info.hProcess, 60000)
        ec = w.DWORD()
        kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(ec))
        kernel32.CloseHandle(info.hProcess)
        print(f"exit code: {ec.value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())