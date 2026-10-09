@echo off
chcp 65001 >nul 2>&1
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    powershell.exe -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
    exit /b 0
)
python.exe "D:\AIOS\_admin_check_svc_v2.py"
