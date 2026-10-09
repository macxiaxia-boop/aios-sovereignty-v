@echo off
REM ============================================================================
REM install_aios_watchdog.cmd - R-Codex-Cure-2026-09-29 V4
REM 注册 AIOS daemon watchdog (开机启动 + 每分钟检查)
REM
REM 解决 Codex + ClaudeCode 闪退根因: AIOS daemon 死了没自动重启
REM ============================================================================
chcp 65001 >nul 2>&1
setlocal EnableExtensions

set "TASK_NAME=AIOS-Daemon-Watchdog"
set "PYTHON=C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe"
set "SCRIPT=D:\AIOS\aios_daemon_watchdog.py"

echo.
echo ============================================================
echo  注册 AIOS daemon watchdog (开机启动 + 每分钟跑)
echo ============================================================
echo.

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  X 请右键 "以管理员身份运行"
    pause
    exit /B 1
)

REM 先删旧任务 (如果有)
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

REM 创建新任务: 开机启动 + 每分钟重复 + 高优先级
schtasks /Create /TN "%TASK_NAME%" ^
    /TR "\"%PYTHON%\" -u \"%SCRIPT%\" 30" ^
    /SC ONSTART ^
    /DELAY 0000:30 ^
    /RL HIGHEST ^
    /RU SYSTEM ^
    /F

if %ERRORLEVEL% EQU 0 (
    echo  OK 已注册 %TASK_NAME% 开机启动 + 每30s检查
) else (
    echo  X 注册失败
    pause
    exit /B 1
)

REM 立即启动一次 (后台)
start /b "" "%PYTHON%" -u "%SCRIPT%" 30

echo.
echo ============================================================
echo  完成. AIOS daemon 死了会自动拉起.
echo  日志: %SCRIPT% 的 _aios_daemon_watchdog.log
echo ============================================================
echo.
pause