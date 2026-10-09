@echo off
REM _restart_cloudtech_v22_apply_minimax.cmd
REM A+B 重启 V22 让 .env + model_aggregator.py 改动生效
REM 需要 admin 启动 winsw service
chcp 65001 >nul 2>&1
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

echo [ADMIN 1/3] Restarting cloudtech-v22-gateway...
sc stop cloudtech-v22-gateway
timeout /t 5 /nobreak >nul
sc start cloudtech-v22-gateway

echo [ADMIN 2/3] Waiting for V22 to come up...
timeout /t 15 /nobreak >nul

echo [ADMIN 3/3] Verifying port 5099 health...
powershell -Command "\$h = try { (Invoke-WebRequest -Uri 'http://127.0.0.1:5099/health' -TimeoutSec 5 -UseBasicParsing).Content } catch { 'NOT_RESPONDING: ' + \$_.Exception.Message }; Write-Host \"  health endpoint: \$h\""

pause
