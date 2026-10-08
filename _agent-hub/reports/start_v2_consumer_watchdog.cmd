@echo off
REM AIOS V2 Consumer 24/7 Watchdog launcher (elevated safe)
REM 设置环境 + 启动 consumer + 重启自愈
set AIOS_V2_CHANNEL_ENABLED=1
set AIOS_V2_ROOT=D:\AIOS\_agent-hub\v2
set PYTHONPATH=D:\AIOS\_agent-hub\v2
cd /d D:\AIOS\_agent-hub\v2

REM 如果已有 consumer 在跑则跳过 (PID file lock)
if exist "D:\AIOS\_agent-hub\v2\state\.aios_v2_consumer.lock" goto ALREADY_RUNNING

REM 主循环：start consumer, 如果 exit 则 restart (15s 后)
:START
echo [%date% %time%] Starting v2 consumer...
python -u -m src.start_consumer_real --interval 3 >> "D:\AIOS\_agent-hub\reports\v2_consumer_real.out.log" 2>&1
echo [%date% %time%] Consumer exited with code %ERRORLEVEL%, restarting in 15s...
timeout /t 15 /nobreak >nul
goto START

:ALREADY_RUNNING
echo [%date% %time%] Consumer already running, exiting watchdog.
exit /b 0