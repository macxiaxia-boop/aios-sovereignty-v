' R268 治本: 用 wscript 包装 cmd, 启动 cmd 时 IntWindowStyle=0 (隐藏)
' 同时调 cmd 自己, cmd 立即启动 _multi_watchdog.py 后退出
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run "D:\AIOS\_multi_watchdog_runner_inner.cmd", 0, True
