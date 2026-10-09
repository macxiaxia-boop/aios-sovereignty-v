@echo off
REM ============================================================================
REM disable_old_codex_watchdogs.cmd - R-Codex-Cure-2026-09-29 V4
REM 停用失效的 R313 / R316 Codex watchdog 任务 (用错 AUMID)
REM
REM V4 重大变更:
REM   - 之前的 R313 监控旧版 OpenAI.Codex v2738 (已下架) → 失效
REM   - 之前的 R316 监控 OpenAI.CodexBeta (用户已卸载) → 失效
REM   - 现在的 V4 watchdog 监控免安装版 ChatGPT.exe (R-Codex-Cure-2026-09-29)
REM   - 必须停掉旧 R313 + R316 任务, 否则会持续产生 zombie AUMID 调用
REM
REM 用法: 右键 "以管理员身份运行"
REM ============================================================================
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion

echo.
echo ============================================================
echo  停用失效的 R313 / R316 Codex watchdog 任务
echo  (R-Codex-Cure 2026-09-29 V4)
echo ============================================================
echo.

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  请右键本脚本, 选择 "以管理员身份运行"
    pause
    exit /B 1
)

REM 列出所有 Codex 相关任务
echo [1/4] 查 Codex 相关任务 ...
schtasks /Query /FO CSV 2>&1 | findstr /I "Codex" | findstr /I "Watchdog"
echo.

REM 停 R313
echo [2/4] 删 R313 任务 ...
schtasks /Query /TN "OpenAI-Codex-Desktop-Watchdog-R313" 2>&1 | findstr /C:"TaskName" >nul
if %ERRORLEVEL% EQU 0 (
    schtasks /Delete /TN "OpenAI-Codex-Desktop-Watchdog-R313" /F 2>&1
    if !ERRORLEVEL! EQU 0 (echo   OK R313 已删) else (echo   X R313 删失败)
) else (
    echo   R313 不存在, 跳过
)

REM 停 R316
echo [3/4] 删 R316 任务 ...
schtasks /Query /TN "OpenAI-Codex-Beta-Watchdog-R316" 2>&1 | findstr /C:"TaskName" >nul
if %ERRORLEVEL% EQU 0 (
    schtasks /Delete /TN "OpenAI-Codex-Beta-Watchdog-R316" /F 2>&1
    if !ERRORLEVEL! EQU 0 (echo   OK R316 已删) else (echo   X R316 删失败)
) else (
    echo   R316 不存在, 跳过
)

REM 注册新的 V4 watchdog
echo [4/4] 注册 V4 watchdog (免安装版) ...
set "PYTHON=C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe"
schtasks /Query /TN "Codex-Codex-Cure-V4-Watchdog" 2>&1 | findstr /C:"TaskName" >nul
if %ERRORLEVEL% EQU 0 (
    echo   V4 watchdog 已存在, 跳过
) else (
    schtasks /Create /TN "Codex-Codex-Cure-V4-Watchdog" ^
        /TR "\"%PYTHON%\" -u \"D:\AIOS\_openai_codex_beta_watchdog.py\" 60" ^
        /SC ONSTART ^
        /RU DelayMinutes:1 /RI 1 /DU 3650 /F 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo   OK V4 watchdog 已注册 (开机启动 + 每分钟跑)
    ) else (
        echo   X V4 watchdog 注册失败
    )
)

echo.
echo ============================================================
echo  完成. 重启电脑后 V4 watchdog 自动接管.
echo ============================================================
echo.
pause