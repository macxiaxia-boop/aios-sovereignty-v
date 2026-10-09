@echo off
REM ============================================================================
REM install_aios_loop.cmd - R-Codex-Cure-2026-09-29 V5
REM 注册 AIOS daemon 守护循环: 死循环跑 watchdog
REM
REM 解决 Codex + ClaudeCode + Hermes + OpenClaw 闪退根因:
REM   AIOS_Autonomy_Daemon.exe 是共享依赖. 它死了 = 整个 AI 栈闪退.
REM ============================================================================
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion

set "TASK_NAME=AIOS-Daemon-Loop-Guard"
set "AIOS_EXE=D:\个人文件\AI\Operator\aios_tools\AIOS_Autonomy_Daemon.exe"
set "GUARD_LOG=D:\AIOS\_aios_loop_guard.log"

echo.
echo ============================================================
echo  注册 AIOS daemon 守护循环 (开机启动 + 持续运行)
echo ============================================================
echo.

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  X 请右键 "以管理员身份运行"
    pause
    exit /B 1
)

REM 先删旧任务
schtasks /Delete /TN "%TASK_NAME%" /F >nul 2>&1

REM 创建开机启动 + 最高权限 + SYSTEM 用户
schtasks /Create /TN "%TASK_NAME%" ^
    /TR "cmd.exe /c \"D:\AIOS\_aios_loop_inner.cmd\"" ^
    /SC ONSTART ^
    /DELAY 0000:30 ^
    /RL HIGHEST ^
    /RU SYSTEM ^
    /F

if %ERRORLEVEL% EQU 0 (
    echo  OK 已注册 %TASK_NAME% 开机启动
) else (
    echo  X 注册失败
    pause
    exit /B 1
)

REM 立即启动一次 (后台)
start /b "" cmd.exe /c "D:\AIOS\_aios_loop_inner.cmd"

echo.
echo ============================================================
echo  完成. AIOS daemon 死了会自动拉起.
echo  日志: %GUARD_LOG%
echo ============================================================
echo.
pause