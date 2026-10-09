@echo off
chcp 65001 >nul 2>&1
cd /d D:\AIOS
"D:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe" -u "D:\AIOS\_multi_watchdog.py" 60
exit /B 0