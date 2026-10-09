# -*- coding: utf-8 -*-
# R327 - Kill Clash Verge GUI auto-restart chain
# Disables schtasks, disables watchdog, kills clash-verge, fixes reg Run

# Step 1: Disable schtasks
Write-Output "Step 1: disable schtasks (ClashVergeDailyRestart + R314 watchdog)"
schtasks /Change /TN "ClashVergeDailyRestart" /DISABLE | Out-Null
schtasks /Change /TN "ClashVerge-Watchdog-R314" /DISABLE | Out-Null
Start-Sleep -Seconds 1
Write-Output "  disabled"

# Step 2: Kill clash-verge (user already authorized)
Write-Output "Step 2: kill clash-verge.exe"
Get-Process clash-verge,clash-verge-service -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
$alive = Get-Process clash-verge -ErrorAction SilentlyContinue
if ($alive) { Write-Output "  WARN: still alive $($alive.Id -join ',')" }
else { Write-Output "  killed" }

# Step 3: Modify reg Run - only let verge-mihomo auto-start (no clash-verge GUI)
# We replace ClashVergeBoot command to verge-mihomo directly, OR remove Run entry
# Choice: REMOVE - let user start clash GUI manually when needed
Write-Output "Step 3: remove reg ClashVergeBoot"
reg delete "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /v "ClashVergeBoot" /f | Out-Null
Write-Output "  removed"

# Step 4: minimize Codex window again
Write-Output "Step 4: minimize Codex window"
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class W {
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
}
'@
# Codex handle from earlier enum = 19007610
[W]::ShowWindow([IntPtr]19007610, 6) | Out-Null
Write-Output "  minimized"

# Step 5: verify 4-class
Write-Output ""
Write-Output "Step 5: 4-class verification"
Write-Output "--- processes ---"
Get-Process clash-verge,verge-mihomo -ErrorAction SilentlyContinue | Format-Table Name,Id,@{n="WS_MB";e={[Math]::Round($_.WorkingSet/1MB,1)}},MainWindowTitle -AutoSize | Out-String | Write-Output

Write-Output "--- 7897 ---"
netstat -ano | findstr ":7897.*LISTENING"

Write-Output "--- Wintun ---"
Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "Meta|Win" } | Format-Table Name,Status -AutoSize | Out-String | Write-Output

Write-Output "--- chatgpt test ---"
try {
    $r = Invoke-WebRequest -Uri "https://chatgpt.com" -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 5
    Write-Output "chatgpt HTTP=$($r.StatusCode)"
} catch { Write-Output "FAIL: $($_.Exception.Message)" }

Write-Output "=== done ==="