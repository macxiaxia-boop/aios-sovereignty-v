# T-final cron daily regression - 2026-10-10

## Status: DONE - schtasks created SUCCESS, next run 2026/10/11 03:00

## Files created
- D:\AIOS\_agent-hub\policy\regression-tests\run_daily.cmd  (size ~600 B, sha=**A973A81162C1A5A3A2F4B8D61E17F5636256A6FC9FA1234A6150A59F2FC233FD**)

## schtasks query result
```
$ schtasks /Query /TN "AIOS-RegressionDaily"
Folder: \
TaskName: AIOS-RegressionDaily
Next Run Time: 2026/10/11 3:00:00
Status: Ready
```

## Schedule spec
- Frequency: DAILY
- Time: 03:00 (low-traffic window)
- Task path: `D:\AIOS\_agent-hub\policy\regression-tests\run_daily.cmd`
- Output log: `D:\AIOS\_agent-hub\audit\regression-daily-YYYY-MM-DD.log`

## What it does
- cd D:\AIOS
- set PYTHONPATH=D:\AIOS\kernel
- pytest regression-tests/ -v --tb=short
- capture output to dated log file
- preserve pytest exit code in cmd return

## Red lines respected
- 没 push 远端
- 没动 EX-001~011
- 没动 AIOSCentralCollector / aios_kernel

--- Codex supervisor - T-final cron DONE - 2026-10-10
