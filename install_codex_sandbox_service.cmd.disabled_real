@echo off
REM ============================================================================
REM install_codex_sandbox_service.cmd - R-Codex-Cure-2026-09-29 V4
REM 安装/启动 CodexSandboxService Windows 服务 (免安装版必需)
REM
REM 原理: 免安装版 ChatGPT Desktop 是解压的 AppX 包, 没有 MS Store 安装器
REM       自动注册 <desktop6:Extension windows.service> 服务
REM       必须手动用 sc.exe 注册 CodexSandboxService.OpenAI.Codex
REM
REM 用法: 右键 "以管理员身份运行"
REM ============================================================================
chcp 65001 >nul 2>&1
setlocal EnableExtensions EnableDelayedExpansion

echo.
echo ============================================================
echo  安装 CodexSandboxService (R-Codex-Cure V4)
echo ============================================================
echo.

net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  X 错误: 请右键本脚本, 选择 "以管理员身份运行"
    pause
    exit /B 1
)

set "SANDBOX_EXE=D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\app\resources\codex-windows-sandbox-service.exe"
set "SANDBOX_SETUP=D:\OpenAI.Codex_26.924.2738.0_x64【免安装版】【适合大多数电脑】\app\resources\codex-windows-sandbox-setup.exe"
set "SVC=CodexSandboxService.OpenAI.Codex"

REM ---- 1. 检查 exe 存在 ----
echo [1/4] 检查服务 exe ...
if not exist "%SANDBOX_EXE%" (
    echo   X 错误: %SANDBOX_EXE% 不存在
    pause
    exit /B 1
)
echo   OK 服务 exe 存在

REM ---- 2. 检查服务是否已注册 ----
echo.
echo [2/4] 检查服务是否已注册 ...
sc query %SVC% >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   服务 %SVC% 已注册, 跳到第 3 步
    goto SERVICE_START
)

REM ---- 3. 注册服务 ----
echo.
echo [3/4] 注册 CodexSandboxService (使用 sc create) ...
sc create %SVC% binPath= "\"%SANDBOX_EXE%\"" start= auto displayname= "Codex Sandbox Service" >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   OK 服务注册成功
) else (
    echo   X 服务注册失败, 尝试 setup 命令 ...
    if exist "%SANDBOX_SETUP%" (
        "%SANDBOX_SETUP%" /install
        if !ERRORLEVEL! EQU 0 (
            echo   OK setup 命令完成
        ) else (
            echo   X setup 也失败, 请查看 Windows 事件查看器
            pause
            exit /B 1
        )
    )
)

:SERVICE_START
echo.
echo [4/4] 启动 CodexSandboxService ...
sc start %SVC% >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo   OK 服务已启动
) else (
    echo   X 服务启动失败, 尝试延迟启动 ...
    sc config %SVC% start= delayed-auto >nul 2>&1
    sc start %SVC% >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo   OK 服务以延迟启动模式启动成功
    ) else (
        echo   X 服务启动失败, 请查看 %SystemRoot%\System32\LogFiles\...
        pause
        exit /B 1
    )
)

echo.
echo ============================================================
echo  完成! CodexSandboxService 已注册并启动.
echo  现在可以双击 D:\AIOS\start_codex_safe.cmd 启动 Codex
echo ============================================================
echo.
pause