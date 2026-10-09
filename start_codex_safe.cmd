@echo off
REM ============================================================================
REM start_codex_safe.cmd - R-Codex-Cure-2026-09-29 V4
REM Codex (免安装版 ChatGPT Desktop v26.924.2738.0) 安全启动 wrapper
REM
REM 用法:
REM   双击此 .cmd (推荐)
REM   或: cmd /c "D:\AIOS\start_codex_safe.cmd"
REM
REM 步骤:
REM   1. 清残留 lock (roaming.lock + app-server 锁)
REM   2. 杀多实例 ChatGPT.exe (极端情况)
REM   3. 检查 CodexSandboxService (没注册则尝试自动注册, 需右键管理员)
REM   4. 校验 hooks hash 一致性
REM   5. 启动 ChatGPT.exe (免安装版)
REM   6. 验证启动 (15s 后)
REM ============================================================================
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion

echo.
echo ============================================================
echo  Codex 启动 (免安装版 ChatGPT Desktop v26.924.2738.0)
echo  R-Codex-Cure 2026-09-29 V4
echo ============================================================
echo.

set "CODEX_PORTABLE=D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】"
set "CHATGPT_EXE=%CODEX_PORTABLE%\app\ChatGPT.exe"
set "SANDBOX_SETUP=%CODEX_PORTABLE%\app\resources\codex-windows-sandbox-setup.exe"
set "SANDBOX_SERVICE=%CODEX_PORTABLE%\app\resources\codex-windows-sandbox-service.exe"
set "CODEX_HOME=%USERPROFILE%\.codex"
set "OLD_PKG=%LOCALAPPDATA%\Packages\OpenAI.Codex_2p2nqsd0c76g0"
set "LOG=%USERPROFILE%\.codex\log\start_codex_safe.log"

REM ---- 0. 检查免安装版是否存在 ----
echo [0/6] 检查免安装版 ...
if not exist "%CHATGPT_EXE%" (
    echo   X 错误: 免安装版不存在于 %CODEX_PORTABLE%
    echo   请先解压免安装版到该路径
    pause
    exit /B 1
)
echo   OK 免安装版已就位

REM ---- 1. 清残留 ----
echo.
echo [1/6] 清理残留 lock + cache ...
if exist "%OLD_PKG%\Settings\roaming.lock" (
    del /F /Q "%OLD_PKG%\Settings\roaming.lock" >nul 2>&1
    echo   已删: 旧版 roaming.lock
)
if exist "%CODEX_HOME%\app-server-daemon\daemon.pid.lock" (
    del /F /Q "%CODEX_HOME%\app-server-daemon\daemon.pid.lock" >nul 2>&1
    echo   已删: daemon.pid.lock
)
if exist "%CODEX_HOME%\app-server-daemon\app-server.pid.lock" (
    del /F /Q "%CODEX_HOME%\app-server-daemon\app-server.pid.lock" >nul 2>&1
    echo   已删: app-server.pid.lock
)
if exist "%CODEX_HOME%\app-server-daemon\daemon.lock" (
    del /F /Q "%CODEX_HOME%\app-server-daemon\daemon.lock" >nul 2>&1
    echo   已删: daemon.lock
)

REM ---- 2. 杀多实例 ----
echo.
echo [2/6] 检查多实例 ChatGPT.exe ...
set COUNT=0
for /F "tokens=*" %%i in ('tasklist /FI "IMAGENAME eq ChatGPT.exe" 2^>nul ^| find /C "ChatGPT.exe"') do set COUNT=%%i
if !COUNT! GTR 0 (
    echo   检测到 !COUNT! 个 ChatGPT.exe 实例, 全部杀掉
    taskkill /F /IM ChatGPT.exe /T >nul 2>&1
    timeout /t 2 /nobreak >nul
) else (
    echo   没有遗留实例
)

REM ---- 3. 检查 CodexSandboxService ----
echo.
echo [3/6] 检查 CodexSandboxService ...
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   注意: 当前不是管理员, 无法自动注册服务
    echo   请右键 "以管理员身份运行" 此脚本完成服务注册
    goto SKIP_SERVICE_SETUP
)
sc query CodexSandboxService.OpenAI.Codex >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   OK CodexSandboxService 已注册
) else (
    echo   X CodexSandboxService 未注册, 尝试注册 ...
    if exist "%SANDBOX_SETUP%" (
        "%SANDBOX_SETUP%" /install
        if !ERRORLEVEL! EQU 0 (
            echo   OK setup 完成
        ) else (
            echo   警告: setup 退出码 !ERRORLEVEL!, 尝试手动注册 ...
            sc create CodexSandboxService.OpenAI.Codex binPath= "\"%SANDBOX_SERVICE%\"" start= auto displayname= "Codex Sandbox Service" >nul 2>&1
            sc start CodexSandboxService.OpenAI.Codex >nul 2>&1
        )
    ) else (
        echo   警告: setup 不存在, 尝试 sc 命令 ...
        sc create CodexSandboxService.OpenAI.Codex binPath= "\"%SANDBOX_SERVICE%\"" start= auto displayname= "Codex Sandbox Service" >nul 2>&1
        sc start CodexSandboxService.OpenAI.Codex >nul 2>&1
    )
)

:SKIP_SERVICE_SETUP

REM ---- 4. 验证 hooks hash 一致性 ----
echo.
echo [4/6] 验证 Codex hooks hash 一致性 ...
if exist "D:\AIOS\sync_codex_hook_hash.py" (
    python.exe "D:\AIOS\sync_codex_hook_hash.py" --check >nul 2>&1
    if !ERRORLEVEL! NEQ 0 (
        echo   hooks hash 不一致, 正在自动同步 ...
        python.exe "D:\AIOS\sync_codex_hook_hash.py" --sync 2>&1
    ) else (
        echo   OK hooks hash 一致
    )
) else (
    echo   跳过 (sync 工具不存在)
)

REM ---- 5. 启动 ChatGPT.exe ----
echo.
echo [5/6] 启动 ChatGPT.exe ...
start "" "%CHATGPT_EXE%"
echo   路径: %CHATGPT_EXE%

REM ---- 6. 验证启动 ----
echo.
echo [6/6] 等待 15s 后验证 ...
timeout /t 15 /nobreak >nul

set OK=0
for /F "tokens=*" %%i in ('tasklist /FI "IMAGENAME eq ChatGPT.exe" 2^>nul ^| find /C "ChatGPT.exe"') do set COUNT=%%i
if !COUNT! GEQ 1 (
    set OK=1
    echo   OK ChatGPT.exe 在跑 (!COUNT! 个进程)
) else (
    echo   X ChatGPT.exe 未启动, 可能是 sandbox 服务问题
)

echo.
echo ============================================================
if !OK! EQU 1 (
    echo  OK 完成. 如 UI 不显示, 按 Win+Tab 切换窗口.
) else (
    echo  WARN 启动可能失败. 检查:
    echo    1. CodexSandboxService 是否已注册 (sc query CodexSandboxService.OpenAI.Codex)
    echo    2. %LOG%
)
echo ============================================================

echo [%date% %time%] OK=!OK! COUNT=!COUNT! >> "%LOG%" 2>nul
endlocal
exit /B 0