@echo off
REM AIOS V2 Consumer watchdog — independent cmd.exe
REM Restarts consumer if it dies; survives parent exits
set AIOS_V2_CHANNEL_ENABLED=1
set AIOS_V2_ROOT=D:\AIOS\_agent-hub\v2
set PYTHONPATH=D:\AIOS\_agent-hub\v2
cd /d D:\AIOS\_agent-hub\v2

:START
echo [%date% %time%] watchdog starting consumer...
python -u -m src.start_consumer_real --interval 3
echo [%date% %time%] consumer exited code=%ERRORLEVEL%, restart in 10s
timeout /t 10 /nobreak >nul
goto START