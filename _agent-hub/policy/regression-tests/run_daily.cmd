@echo off
REM run_daily.cmd - D:\AIOS\_agent-hub\policy\regression-tests\ daily CI sweep
REM Added 2026-10-10 by Codex supervisor (T-final cron batch).
REM Schedule: AIOS-RegressionDaily at 03:00 every day (created via schtasks).
REM Why 03:00: low-traffic window, lets nightly drift settle before scan.

cd /d D:\AIOS
set PYTHONPATH=D:\AIOS\kernel
set REGRESSION_LOG_DIR=D:\AIOS\_agent-hub\audit

REM Generate dated log filename: regression-daily-YYYY-MM-DD.log
for /f "tokens=2 delims==" %%i in ('wmic os get localdatetime /value 2^>nul') do set dt=%%i
set dt=%dt:~0,4%-%dt:~4,2%-%dt:~6,2%

REM Run the regression suite and capture full output
pytest D:\AIOS\_agent-hub\policy\regression-tests\ -v --tb=short > "%REGRESSION_LOG_DIR%\regression-daily-%dt%.log" 2>&1

REM Exit with pytest's exit code (preserve in this cmd's return code)
exit /b %ERRORLEVEL%
