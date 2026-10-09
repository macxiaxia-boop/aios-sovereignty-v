@echo off
REM CloudTech V22 Watchdog 启动器 · R-C (2026-09-24 · 用户拍板 C)
REM 红线 #29 .cmd → GBK 无 BOM
REM 红线 #78 CREATE_NO_WINDOW (pythonw.exe 无窗口)
REM 红线 #82 不弹窗 (Task Scheduler 后台启动, 无 console)
chcp 65001 >nul
cd /d D:\AIOS\_workzone
D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\pythonw.exe -m src._aios_cloudtech_bridge --watch --watch-interval 300 >> D:\AIOS\cloudtech-saas\logs\watchdog_stdout.log 2>&1