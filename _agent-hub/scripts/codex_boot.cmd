@echo off
REM Codex Session Bootstrap — Codex session 启动时第一件事
REM 不等用户说话，自动跑 self-audit，让 Codex 立刻知道系统状态
REM 用法: codex_boot.cmd （启动 Codex 前手动跑 / 或 Scheduled Task）

echo ============================================
echo Codex Session Bootstrap @ %date% %time%
echo ============================================

cd /d D:\AIOS

REM 1. 读 AGENTS.md (echo 提醒，不阻塞)
echo.
echo [1/4] Reading AGENTS.md central SSOT...
echo      (D:\AIOS\_agent-hub\AGENTS.md)

REM 2. 跑 self-audit（核心）
echo.
echo [2/4] Running codex self-audit...
"D:\AIOS\kernel\.venv\Scripts\python.exe" "D:\AIOS\_agent-hub\scripts\codex_self_audit.py"
set AUDIT_EXIT=%errorlevel%
echo self-audit exit=%AUDIT_EXIT%

REM 3. 扫当日 memory
echo.
echo [3/4] Reading today's memory log...
if exist "D:\AIOS\_agent-hub\memory\%date:~0,4%-%date:~5,2%-%date:~8,2%.md" (
    powershell -Command "Get-Content 'D:\AIOS\_agent-hub\memory\%date:~0,4%-%date:~5,2%-%date:~8,2%.md' | Select-Object -Last 30"
) else (
    echo No memory log for today yet.
)

REM 4. 报告结论
echo.
echo [4/4] Result...
if %AUDIT_EXIT% == 0 (
    echo SYSTEM CLEAN. Codex may proceed autonomously per AGENTS.md + autonomous_scope.
) else (
    echo SYSTEM DEGRADED. Codex must read Findings from today's memory log and self-heal.
    echo     No user input required if fix is in autonomous_scope.
    echo     Otherwise, list blockers and wait.
)

echo ============================================
echo Bootstrap complete.
echo ============================================
exit /b %AUDIT_EXIT%