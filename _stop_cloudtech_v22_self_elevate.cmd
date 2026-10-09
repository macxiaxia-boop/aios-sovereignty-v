@echo off
REM _stop_cloudtech_v22_self_elevate.cmd
REM Auto-elevate to admin and stop cloudtech-v22-gateway
REM 双击或右键以管理员身份运行

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting admin elevation...
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

echo [ADMIN] Stopping cloudtech-v22-gateway service...
sc stop cloudtech-v22-gateway
sc config cloudtech-v22-gateway start= disabled

echo [ADMIN] Killing processes...
taskkill /F /IM cloudtech_v22_gateway.exe
taskkill /F /FI "WINDOWTITLE eq *cloud*"

echo [ADMIN] Verifying port 5099 closed...
powershell -Command "Start-Sleep -Seconds 3; \$c = Get-NetTCPConnection -LocalPort 5099 -State Listen -ErrorAction SilentlyContinue; if (\$c) { Write-Host 'port 5099 STILL LISTENING (reboot required)' -ForegroundColor Red; exit 1 } else { Write-Host 'port 5099 CLOSED' -ForegroundColor Green }"

pause
