@echo off
REM ============================================================================
REM stop_codex_watchdog_now.cmd - R-Codex-Cure-2026-09-29 V5
REM 立即停 watchdog + 清空所有 Codex 状态 (不杀 WorkBuddy 沙箱!)
REM ============================================================================
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion

echo.
echo ============================================================
echo  立即停 Codex watchdog + 清空状态
echo  (注意: 只杀 Codex 相关, 不动 WorkBuddy 沙箱)
echo ============================================================
echo.

echo [1/7] 杀 Codex watchdog python 进程 (用 ctypes Windows API) ...
python.exe "D:\AIOS\kill_codex_watchdog.py"
echo   OK

echo.
echo [2/7] 杀 ChatGPT.exe + codex.exe + sandbox-cli's 父进程 ...
taskkill /F /IM ChatGPT.exe /T >nul 2>&1
taskkill /F /IM codex.exe /T >nul 2>&1
taskkill /F /IM codex-command-runner.exe /T >nul 2>&1
taskkill /F /IM codex-windows-sandbox-service.exe /T >nul 2>&1
taskkill /F /IM codex-windows-sandbox-ser.exe /T >nul 2>&1
taskkill /F /IM codex-computer-use-swift.exe /T >nul 2>&1
taskkill /F /IM codex-code-mode-host.exe /T >nul 2>&1
timeout /t 3 /nobreak >nul
echo   OK

echo.
echo [3/7] 清残留 lock ...
if exist "%LOCALAPPDATA%\Packages\OpenAI.Codex_2p2nqsd0c76g0\Settings\roaming.lock" (
    del /F /Q "%LOCALAPPDATA%\Packages\OpenAI.Codex_2p2nqsd0c76g0\Settings\roaming.lock" >nul 2>&1
    echo   已删: roaming.lock
)
if exist "%USERPROFILE%\.codex\app-server-daemon" (
    rd /S /Q "%USERPROFILE%\.codex\app-server-daemon" >nul 2>&1
    echo   已清: app-server-daemon
)

echo.
echo [4/7] 校验 hooks hash ...
python.exe "D:\AIOS\sync_codex_hook_hash.py" --check
echo.

echo.
echo [5/7] 验证 Codex 状态 ...
for /F "tokens=*" %%i in ('tasklist /FI "IMAGENAME eq ChatGPT.exe" 2^>nul ^| find /C "ChatGPT.exe"') do set C1=%%i
echo   ChatGPT.exe: !C1! 个
for /F "tokens=*" %%i in ('tasklist /FI "IMAGENAME eq codex.exe" 2^>nul ^| find /C "codex.exe"') do set C2=%%i
echo   codex.exe: !C2! 个

echo.
echo [6/7] 看 CodexSandboxService 是否注册 ...
sc query CodexSandboxService.OpenAI.Codex >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   OK 已注册
) else (
    echo   X 未注册 (下一步右键管理员跑 install_codex_sandbox_service.cmd)
)

echo.
echo [7/7] 看 R313 / R316 schtasks 还在不在 (会每分钟拉起 watchdog) ...
schtasks /Query /TN "OpenAI-Codex-Desktop-Watchdog-R313" 2>&1 | findstr /C:"TaskName" >nul && echo   R313 任务还在! 需要停掉
schtasks /Query /TN "OpenAI-Codex-Beta-Watchdog-R316" 2>&1 | findstr /C:"TaskName" >nul && echo   R316 任务还在! 需要停掉

echo.
echo ============================================================
echo  完成
echo ============================================================
echo.
echo  下一步 (需右键管理员):
echo    1. install_codex_sandbox_service.cmd (注册 CodexSandboxService)
echo    2. disable_old_codex_watchdogs.cmd (停 R313/R316 + 注册 V4 watchdog)
echo    3. start_codex_safe.cmd (启动 Codex)
echo.
pause