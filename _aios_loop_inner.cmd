@echo off
REM ============================================================================
REM _aios_loop_inner.cmd - AIOS daemon 守护循环 (永久运行)
REM 死循环: 每 10 秒检查 AIOS daemon, 不在就拉起
REM ============================================================================
chcp 65001 >nul 2>&1
setlocal EnableExtensions

set "AIOS_EXE=D:\个人文件\AI\Operator\aios_tools\AIOS_Autonomy_Daemon.exe"
set "LOG=D:\AIOS\_aios_loop_guard.log"
set "INTERVAL=10"

echo [%date% %time%] AIOS loop guard started (interval=%INTERVAL%s) >> "%LOG%"

:loop
REM 检查 AIOS daemon
tasklist /FI "IMAGENAME eq AIOS_Autonomy_Daemon.exe" 2>nul | find /I "AIOS_Autonomy_Daemon.exe" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [%date% %time%] AIOS daemon DOWN, restarting... >> "%LOG%"
    start "" "%AIOS_EXE%"
    timeout /t 5 /nobreak >nul
    tasklist /FI "IMAGENAME eq AIOS_Autonomy_Daemon.exe" 2>nul | find /I "AIOS_Autonomy_Daemon.exe" >nul
    if %ERRORLEVEL% EQU 0 (
        echo [%date% %time%] AIOS daemon restarted OK >> "%LOG%"
    ) else (
        echo [%date% %time%] AIOS daemon restart FAILED >> "%LOG%"
    )
)

REM 等 10s
timeout /t %INTERVAL% /nobreak >nul
goto loop