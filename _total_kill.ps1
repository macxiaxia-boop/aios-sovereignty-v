# -*- coding: utf-8 -*-
# R327 v3 - Total kill clash-verge service chain

Write-Output "Step 1: trace parent PID 3332"
$p3332 = Get-CimInstance Win32_Process -Filter "ProcessId=3332" -ErrorAction SilentlyContinue
if ($p3332) { Write-Output "  PID 3332 = $($p3332.Name) CMD=$($p3332.CommandLine)" } else { Write-Output "  PID 3332 already dead" }

Write-Output "Step 2: kill clash-verge PID 1968"
Stop-Process -Id 1968 -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
$alive = Get-Process -Id 1968 -ErrorAction SilentlyContinue
if ($alive) { Write-Output "  WARN alive"; Stop-Process -Id 1968 -Force }
else { Write-Output "  killed" }

Write-Output "Step 3: try kill clash-verge-service PID 15480"
try {
    Stop-Process -Id 15480 -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    $svc = Get-Process -Id 15480 -ErrorAction SilentlyContinue
    if ($svc) {
        Write-Output "  normal Stop-Process failed - trying taskkill /F"
        taskkill /F /PID 15480 2>&1 | Out-Null
        Start-Sleep -Seconds 2
        $svc = Get-Process -Id 15480 -ErrorAction SilentlyContinue
        if ($svc) { Write-Output "  STILL alive (admin needed)" }
        else { Write-Output "  killed via taskkill" }
    } else {
        Write-Output "  killed"
    }
} catch {
    Write-Output "  error: $_"
}

Write-Output "Step 4: check if mihomo died (was child of 15480)"
$mihomo = Get-Process verge-mihomo -ErrorAction SilentlyContinue
if ($mihomo) { Write-Output "  mihomo PID=$($mihomo.Id) still alive - keep as standalone" }
else { Write-Output "  mihomo dead - will need restart" }

Write-Output "Step 5: clear ALL registry Run entries that mention Clash"
$runKeys = @(
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run"
)
foreach ($key in $runKeys) {
    $props = Get-ItemProperty -Path $key -ErrorAction SilentlyContinue
    if ($props) {
        foreach ($p in $props.PSObject.Properties) {
            if ($p.Name -notmatch "^PS" -and $p.Value -match "[Cc]lash") {
                Write-Output "  removing $($key):: $($p.Name)"
                Remove-ItemProperty -Path $key -Name $p.Name -ErrorAction SilentlyContinue
            }
        }
    }
}

Write-Output ""
Write-Output "Step 6: 4-class verify"
Get-Process | Where-Object { $_.ProcessName -match "clash|verge|mihomo" } | Format-Table Name,Id,MainWindowTitle -AutoSize | Out-String | Write-Output
Write-Output "--- 7897 ---"
netstat -ano | findstr ":7897.*LISTENING"
Write-Output "--- Wintun ---"
Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "Meta|Win" } | Format-Table Name,Status -AutoSize | Out-String | Write-Output
Write-Output "=== done ==="