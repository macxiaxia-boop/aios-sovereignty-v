@echo off
REM _restore_cloudtech_v22_self_elevate.cmd
REM Auto-elevate to admin and restore cloudtech-v22-gateway service + scheduled tasks
REM A+B 恢复 + 应用 ModelPolicy
chcp 65001 >nul 2>&1
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -Command "Start-Process cmd -ArgumentList '/c \"%~f0\"' -Verb RunAs"
    exit /b
)

echo [ADMIN 1/4] Re-enabling cloudtech-v22-gateway Windows service...
sc config cloudtech-v22-gateway start= auto
sc start cloudtech-v22-gateway

echo [ADMIN 2/4] Re-enabling CloudTech scheduled tasks...
schtasks /Change /TN "CloudTech-V22-Watchdog" /Enable
schtasks /Change /TN "CloudTech_V22Watchdog" /Enable
schtasks /Change /TN "CloudTech_V23FileWatcher" /Enable
schtasks /Change /TN "CloudTech_SpecV1CI_Daily_0300" /Enable
schtasks /Change /TN "\CloudTech\AIOSLightMonitor-30min" /Enable
schtasks /Change /TN "\CloudTech\DailyReport-0300" /Enable

echo [ADMIN 3/4] Verifying port 5099 listening...
powershell -Command "Start-Sleep -Seconds 5; \$c = Get-NetTCPConnection -LocalPort 5099 -State Listen -ErrorAction SilentlyContinue; if (\$c) { Write-Host '  port 5099 LISTENING (PID='\$c.OwningProcess')' -ForegroundColor Green } else { Write-Host '  port 5099 NOT LISTENING (will retry)' -ForegroundColor Yellow; Start-Sleep -Seconds 10; \$c2 = Get-NetTCPConnection -LocalPort 5099 -State Listen -ErrorAction SilentlyContinue; if (\$c2) { Write-Host '  port 5099 LISTENING (PID='\$c2.OwningProcess')' -ForegroundColor Green } else { Write-Host '  port 5099 STILL NOT LISTENING' -ForegroundColor Red } }"

echo [ADMIN 4/4] DONE
pause
