@echo off
REM _clash_verge_watchdog_runner.cmd - schtasks wrapper (R314)
REM R265 治本: start /b 让 cmd 自身不阻塞控制台窗
chcp 65001 >nul 2>&1
cd /d D:\AIOS
start /b "" "C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe" -u "D:\AIOS\_clash_verge_watchdog.py" 60
exit /B 0