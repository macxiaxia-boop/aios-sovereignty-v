import winreg
import os
PYTHONW = r"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\pythonw.exe"
SCRIPT = r"D:\AIOS\_popup_ultimate_shield_v2.py"
# 用 cmd /c 包装 (cmd /c 不会弹控制台窗口因为 pythonw 已经隐藏)
# 但 cmd /c 会显示控制台窗口 — 用双引号包裹 pythonw + args
value = f'"{PYTHONW}" -u "{SCRIPT}"'

with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_SET_VALUE) as k:
    winreg.SetValueEx(k, "PopupUltimateShieldV2", 0, winreg.REG_SZ, value)
print("✓ 注册 PopupUltimateShieldV2")
print(f"  值: {value}")

# 验证
with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run",
                    0, winreg.KEY_READ) as k:
    i = 0
    print("\n=== HKCU Run popup 全部项 ===")
    while True:
        try:
            name, val, _ = winreg.EnumValue(k, i)
            i += 1
            if "popup" in name.lower() or "cure" in name.lower() or "shield" in name.lower():
                print(f"  ✓ {name}")
                print(f"    {val[:130]}")
        except OSError:
            break
