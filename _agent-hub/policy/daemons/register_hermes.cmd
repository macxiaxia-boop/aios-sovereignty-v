@echo off
REM ====================================================================
REM register_hermes.cmd · Phase I.3 / T25 · 注册 Hermes Daemon (2026-10-09)
REM ====================================================================
REM mode B: on-demand 启动钩. 不注册到 schtasks (避免 30 min time limit
REM 与 daemon 长期语义冲突). 仅:
REM   1) 创建 daemon log/heartbeat 目录
REM   2) 跑一次 --once --verbose 让用户看到 daemon 真启动了
REM   3) 输出 schtasks 一键启停命令 (用户自行决定是否注册)
REM
REM 线程:    01a11c33-c813-7752-9e53-b7c332d00445
REM 授权:    user-2026-10-08T23:55 + 你就开始 + 继续 (2026-10-09)
REM ====================================================================

setlocal ENABLEEXTENSIONS ENABLEDELAYEDEXPANSION

set "PYTHON_BIN=C:\Users\xinzh\.workbuddy\binaries\python\versions\3.13.12\python.exe"
set "DAEMON=D:\AIOS\_agent-hub\policy\daemons\hermes_daemon.py"
set "HEARTBEAT_DIR=D:\AIOS\_agent-hub\policy\daemons"
set "LOG=%HEARTBEAT_DIR%\hermes_daemon.log"

echo ============================================================
echo "[register_hermes] Phase I.3 / T25 · mode B on-demand"
echo "[register_hermes] python=%PYTHON_BIN%"
echo "[register_hermes] daemon=%DAEMON%"
echo "[register_hermes] heartbeat_dir=%HEARTBEAT_DIR%"
echo ============================================================

REM 1) 准备目录
if not exist "%HEARTBEAT_DIR%" (
    mkdir "%HEARTBEAT_DIR%"
    echo "[register_hermes] created %HEARTBEAT_DIR%"
) else (
    echo "[register_hermes] %HEARTBEAT_DIR% exists"
)

REM 2) 跑一次 --once --verbose 真启动验证
echo.
echo [register_hermes] running --once --verbose ...
"%PYTHON_BIN%" "%DAEMON%" --once --verbose
set "RC=%ERRORLEVEL%"
echo [register_hermes] --once exit=%RC%
echo.

REM 3) 输出 schtasks 一键启停提示 (用户可选)
echo ============================================================
echo "[register_hermes] 一键启停 (用户可选, mode A 自循环):"
echo.
echo   启动 daemon (前台自循环, ctrl-c 停):
echo     "%PYTHON_BIN%" "%DAEMON%"
echo.
echo   注册 schtasks (每 5 分钟心跳, 需用户授权):
echo     schtasks /Create /SC MINUTE /MO 5 /TR "\"%PYTHON_BIN%\" \"%DAEMON%\" --once --verbose" /TN AIOS_Hermes_Daemon /F
echo     schtasks /Run    /TN AIOS_Hermes_Daemon
echo     schtasks /Query  /TN AIOS_Hermes_Daemon
echo     schtasks /Delete /TN AIOS_Hermes_Daemon /F
echo.
echo   验证 daemon 真跑:
echo     "%PYTHON_BIN%" "%DAEMON%" --once --verbose
echo     type "%HEARTBEAT_DIR%\hermes_daemon.heartbeat.json"
echo     type "%LOG%"
echo ============================================================

endlocal & exit /b %RC%