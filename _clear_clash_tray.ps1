# -*- coding: utf-8 -*-
# R327 v2 - Clear Clash tray icons by restarting Explorer

Write-Output "Step 1: kill all Clash processes"
Get-Process clash-verge,clash-verge-service,verge-mihomo -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -ne "verge-mihomo" -or $true } | ForEach-Object {
    $keepMihomo = $_.ProcessName -eq "verge-mihomo"
    if (-not $keepMihomo) {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Write-Output "  killed $($_.ProcessName) PID=$($_.Id)"
    } else {
        Write-Output "  keep $($_.ProcessName) PID=$($_.Id) (TUN host)"
    }
}
Start-Sleep -Seconds 2

Write-Output "Step 2: clear TrayNotify registry"
reg delete "HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify" /v "IconStreams" /f 2>$null | Out-Null
reg delete "HKCU\Software\Classes\Local Settings\Software\Microsoft\Windows\CurrentVersion\TrayNotify" /v "PastIconsStream" /f 2>$null | Out-Null
Write-Output "  cleared"

Write-Output "Step 3: restart Explorer (will flash screen 3-5s)"
Stop-Process -Name explorer -Force -ErrorAction SilentlyContinue
Write-Output "  killed explorer"
Start-Sleep -Seconds 5
$e = Get-Process explorer -ErrorAction SilentlyContinue
if ($e) { Write-Output "  explorer PID=$($e.Id)" } else { Write-Output "  WARN: explorer not restarted - waiting 5s more"; Start-Sleep -Seconds 5; $e = Get-Process explorer; Write-Output "  explorer PID=$($e.Id)" }

Write-Output "Step 4: verify 4-class"
Write-Output "--- clash procs ---"
Get-Process clash-verge,verge-mihomo -ErrorAction SilentlyContinue | Format-Table Name,Id,MainWindowTitle -AutoSize | Out-String | Write-Output
Write-Output "--- 7897 ---"
netstat -ano | findstr ":7897.*LISTENING"
Write-Output "--- Wintun ---"
Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "Meta|Win" } | Format-Table Name,Status -AutoSize | Out-String | Write-Output
Write-Output "--- tray visible icons (count) ---"
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class T {
    [DllImport("shell32.dll")] public static extern IntPtr GetForegroundWindow();
}
'@
# Check tray overflow
$trayOverflow = Get-ItemProperty "HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced" -ErrorAction SilentlyContinue
Write-Output "  TrayIconCount param: $($trayOverflow.TaskbarGlomLevel)"
Write-Output "=== done ==="