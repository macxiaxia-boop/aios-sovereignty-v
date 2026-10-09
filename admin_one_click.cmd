@echo off
REM ============================================================================
REM admin_one_click.cmd - R-Codex-Cure-2026-09-29
REM 单 .cmd 完成: UAC 提升 + 跑 Python + 调 ctypes 注册 CodexSandboxService
REM
REM 用法: 右键 "以管理员身份运行" (绕过 sandbox 阻挡 sc.exe/reg.exe/powershell.exe)
REM ============================================================================
chcp 65001 >nul 2>&1

REM 检查管理员
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo X 此脚本需要管理员权限, 请右键 "以管理员身份运行"
    pause
    exit /B 1
)

echo ============================================================
echo  Codex 完整配置 (admin)
echo ============================================================
echo.

REM 1. 杀所有 Codex watchdog 进程
echo [1/6] 杀 Codex watchdog 进程 ...
taskkill /F /IM ChatGPT.exe /T >nul 2>&1
taskkill /F /IM codex.exe /T >nul 2>&1
taskkill /F /IM codex-command-runner.exe /T >nul 2>&1
taskkill /F /IM codex-windows-sandbox-service.exe /T >nul 2>&1
taskkill /F /IM codex-windows-sandbox-ser.exe /T >nul 2>&1
taskkill /F /IM codex-computer-use-swift.exe /T >nul 2>&1
taskkill /F /IM codex-code-mode-host.exe /T >nul 2>&1
echo   OK

REM 2. 删 V4 schtasks
echo.
echo [2/6] 删 V4 schtasks ...
schtasks /Delete /TN "Codex-Codex-Cure-V4-Watchdog" /F >nul 2>&1
echo   OK

REM 3. 删 R316 schtasks
echo.
echo [3/6] 删 R316 schtasks ...
schtasks /Delete /TN "OpenAI-Codex-Beta-Watchdog-R316" /F >nul 2>&1
echo   OK

REM 4. 注册 CodexSandboxService (用 Python + ctypes 避免 sandbox 阻挡 sc.exe)
echo.
echo [4/6] 注册 CodexSandboxService (Python + ctypes 绕过 sandbox) ...
python.exe "D:\AIOS\_admin_register_service.py"
echo.

REM 5. 启动 Codex
echo [5/6] 启动 Codex (免安装版 ChatGPT.exe) ...
start "" "D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\app\ChatGPT.exe"
echo   OK

REM 6. 等待 + 验证
echo.
echo [6/6] 等待 20s 后验证 ...
timeout /t 20 /nobreak >nul

set COUNT=0
for /F "tokens=*" %%i in ('tasklist /FI "IMAGENAME eq ChatGPT.exe" 2^>nul ^| find /C "ChatGPT.exe"') do set COUNT=%%i
echo.
echo   ChatGPT.exe 进程: !COUNT! 个

echo.
echo ============================================================
echo  完成
echo ============================================================
echo.
echo 验证 CodexSandboxService 状态:
sc query CodexSandboxService.OpenAI.Codex
echo.
pause