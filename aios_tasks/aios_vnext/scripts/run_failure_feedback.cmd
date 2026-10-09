@echo off
REM run_failure_feedback.cmd - Scheduled Task entry for Phase G G001.
REM
REM Schedules (建议):
REM   schtasks /create /tn "AIOS\PhaseG\FailureFeedback" /tr "D:\AIOS\aios_tasks\aios_vnext\scripts\run_failure_feedback.cmd" /sc MINUTE /mo 15 /ru SYSTEM
REM
REM 用法 (手动):
REM   run_failure_feedback.cmd [extra args passed to runner]
REM
REM 设计: 每 15 分钟跑一次 failure_feedback_runner.main(), 默认 min_occurrence=3.
REM 失败: 单次失败不应阻止下次执行; runner 内部 try/except 已经处理.
REM log: 默认输出到 stdout; Scheduled Task 会自动捕获到 Task Scheduler log.

setlocal

set "KERNEL_DIR=D:\AIOS\kernel"
set "PYTHON_EXE=%KERNEL_DIR%\.venv\Scripts\python.exe"
set "RUNNER_MODULE=aios_kernel.learning.failure_feedback_runner"

if not exist "%PYTHON_EXE%" (
    echo [run_failure_feedback.cmd] ERROR: python not found at %PYTHON_EXE%
    exit /b 2
)

cd /d "%KERNEL_DIR%"

REM 默认参数: min-occurrence=3, dry-run=False
REM 用户可加 --dry-run 测试, 或 --min-occurrence N 调整阈值
"%PYTHON_EXE%" -m "%RUNNER_MODULE%" --min-occurrence 3 %*
set "RC=%ERRORLEVEL%"

if not "%RC%"=="0" (
    echo [run_failure_feedback.cmd] runner exited with code %RC%
)

endlocal & exit /b %RC%
