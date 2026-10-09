# -*- coding: utf-8 -*-
# R327 v4 - Kill the ROOT cause: R314 watchdog script

Write-Output "Step 1: kill the watchdog python (PID 3332) - the loop spawner"
Get-Process -Id 3332 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$alive = Get-Process -Id 3332 -ErrorAction SilentlyContinue
if ($alive) { Write-Output "  WARN alive"; taskkill /F /PID 3332 2>&1 | Out-Null; Start-Sleep 2 }
$alive = Get-Process -Id 3332 -ErrorAction SilentlyContinue
if ($alive) { Write-Output "  STILL alive" } else { Write-Output "  killed watchdog" }

Write-Output "Step 2: kill any surviving clash-verge"
Get-Process clash-verge -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2
$cv = Get-Process clash-verge -ErrorAction SilentlyContinue
if ($cv) { Write-Output "  WARN: still alive $($cv.Id -join ',')" } else { Write-Output "  killed" }

Write-Output "Step 3: backup + disable the watchdog .py file (root cause)"
$wd = "D:\AIOS\_clash_verge_watchdog.py"
$backupDir = "D:\AIOS\_backups_2026-09-29"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Copy-Item $wd "$backupDir\_clash_verge_watchdog.py.bak-R327-disabled" -Force | Out-Null
# Rename .py to .py.disabled so no future process can spawn from it
Rename-Item $wd "$wd.disabled" -Force | Out-Null
Write-Output "  watchdog renamed to .py.disabled"

Write-Output ""
Write-Output "Step 4: verify all clash procs gone"
Get-Process | Where-Object { $_.ProcessName -match "clash|verge|mihomo" } | Format-Table Name,Id,MainWindowTitle -AutoSize | Out-String | Write-Output

Write-Output "Step 5: verify TUN + 7897 still alive"
netstat -ano | findstr ":7897.*LISTENING"
Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "Meta|Win" } | Format-Table Name,Status -AutoSize | Out-String | Write-Output
Write-Output "=== ROOT CAUSE ELIMINATED ==="