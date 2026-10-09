@echo off
REM ============================================================================
REM daily_codex_health_check.cmd - R-Codex-Cure-2026-09-29
REM Codex 每日健康检查 (添加到 schtasks, 每日 9:00 跑)
REM
REM 用法:
REM   1. 双击本脚本, 会自动注册计划任务 "Codex-Daily-HealthCheck"
REM   2. 每日 9:00 自动跑 codex_health_check.py
REM   3. 报告写到 D:\AIOS\codex_health_check.log
REM ============================================================================
chcp 65001 >nul 2>&1
setlocal EnableExtensions

set "TASK_NAME=Codex-Daily-HealthCheck"
set "PYTHON=C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe"
set "SCRIPT=D:\AIOS\codex_health_check.py"

echo.
echo ============================================================
echo  Codex 每日健康检查任务注册
echo ============================================================
echo.

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  请右键本脚本, 选择 "以管理员身份运行"
    pause
    exit /B 1
)

echo [1/3] 注册每日 9:00 健康检查 ...
schtasks /Create /TN "%TASK_NAME%" /TR "\"%PYTHON%\" -u \"%SCRIPT%\" --json >> D:\AIOS\codex_health_check.log 2>&1" /SC DAILY /ST 09:00 /F 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   ✓ 已注册 %TASK_NAME%
) else (
    echo   ✗ 注册失败
)

echo.
echo [2/3] 注册开机启动健康检查 ...
schtasks /Create /TN "Codex-Bootstrap-HealthCheck" /TR "\"%PYTHON%\" -u \"%SCRIPT%\" --fix" /SC ONSTART /F 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   ✓ 已注册 Codex-Bootstrap-HealthCheck
) else (
    echo   ✗ 注册失败
)

echo.
echo [3/3] 立刻跑一次, 验证 ...
"%PYTHON%" -u "%SCRIPT%" 2>&1
echo.
echo ============================================================
echo  完成. 每日 9:00 自动跑, 开机也跑.
echo ============================================================
echo.
pause