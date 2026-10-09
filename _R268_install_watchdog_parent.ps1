# R268 install watchdog_parent as schtasks onstart task
# 用 schtasks /sc onstart /ru SYSTEM 注册, 开机自启 + SYSTEM 权限
# watchdog_parent 死了, schtasks /sc minute /mo 1 兜底

# 1. 创建开机自启任务 (SYSTEM 权限, HIGHEST 优先级)
schtasks /create /tn "PopupCureWatchdogParent" `
    /tr "\"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\pythonw.exe\" -u \"D:\AIOS\_popup_watchdog_parent.py\" --interval 5" `
    /sc onstart `
    /ru SYSTEM `
    /rl HIGHEST `
    /f

# 2. 创建兜底任务 (1 分钟级检查, 死了立即拉起)
schtasks /create /tn "PopupCureWatchdogParent_Failsafe" `
    /tr "\"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\pythonw.exe\" -u \"D:\AIOS\_popup_watchdog_parent.py\" --interval 5" `
    /sc minute /mo 1 `
    /ru SYSTEM `
    /rl HIGHEST `
    /f

# 3. 立即拉起 watchdog_parent
schtasks /run /tn "PopupCureWatchdogParent"

Write-Host "R268 install complete"
Write-Host "Verify: schtasks /query /tn PopupCureWatchdogParent"
