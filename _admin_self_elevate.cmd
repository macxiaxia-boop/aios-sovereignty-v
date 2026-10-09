@echo off
REM Self-elevate wrapper for CodexSandboxService registration
REM 1. Re-trigger UAC for this same .cmd (already in admin context)
REM 2. Run Python with ctypes to register + start service
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    REM Not admin yet, re-trigger UAC
    powershell.exe -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)

REM Now we're admin - run Python with ctypes to register the service
python.exe "D:\AIOS\_admin_register_service.py"
