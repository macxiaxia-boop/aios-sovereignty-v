@echo off
REM R268 治本: 派发 detached pythonw, cmd 立即 exit (START /B + CREATE_NEW_PROCESS_GROUP + DETACHED_PROCESS)
chcp 65001 >nul 2>&1
REM 0x00000008 = DETACHED_PROCESS (脱离父进程 console)
REM 0x00000200 = CREATE_NEW_PROCESS_GROUP
REM 0x08000000 = CREATE_NO_WINDOW
start "wrapper" /b "C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\pythonw.exe" -u "D:\AIOS\_multi_watchdog.py" 60
exit /B 0