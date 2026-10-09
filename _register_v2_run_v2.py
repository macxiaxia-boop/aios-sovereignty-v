import winreg

PYTHONW = r"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\pythonw.exe"
SCRIPT = r"D:\AIOS\_hide_console_windows_v2.py"
value = f'"{PYTHONW}" -u "{SCRIPT}"'

with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_SET_VALUE) as k:
    winreg.SetValueEx(k, "HideConsoleWindowsV2", 0, winreg.REG_SZ, value)
print(f"✓ 注册 HideConsoleWindowsV2")
print(f"  值: {value}")

# 验证
with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_READ) as k:
    i = 0
    print("\n=== HKCU Run 全部 popup 相关项 ===")
    while True:
        try:
            name, val, _ = winreg.EnumValue(k, i)
            i += 1
            if "popup" in name.lower() or "cure" in name.lower() or "shield" in name.lower() or "hide" in name.lower() or "console" in name.lower() or "watchdog" in name.lower() or "supervisor" in name.lower():
                print(f"  ✓ {name}")
                print(f"    {val[:140]}")
        except OSError:
            break
