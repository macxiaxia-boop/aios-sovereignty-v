@echo off
REM _openai_codex_beta_watchdog_runner.cmd - R316 ChatGPT Beta watchdog
REM R268 治本: start /b 让 cmd 自身不阻塞控制台窗
chcp 65001 >nul 2>&1
cd /d D:\AIOS
start /b "" "C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\python.exe" -u "D:\AIOS\_openai_codex_beta_watchdog.py" 60
exit /B 0