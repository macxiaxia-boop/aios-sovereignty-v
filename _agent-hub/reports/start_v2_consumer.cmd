@echo off
REM AIOS V2 Consumer Watchdog launcher
set AIOS_V2_CHANNEL_ENABLED=1
set AIOS_V2_ROOT=D:\AIOS\_agent-hub\v2
set PYTHONPATH=D:\AIOS\_agent-hub\v2
cd /d D:\AIOS\_agent-hub\v2
python -u -m src.start_consumer_real --interval 3 >> "D:\AIOS\_agent-hub\reports\v2_consumer_real.out.log" 2>> "D:\AIOS\_agent-hub\reports\v2_consumer_real.err.log"