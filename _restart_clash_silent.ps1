# -*- coding: utf-8 -*-
# R327 Phase 1 Step 3 - Restart Clash with --silent-start

# Kill all clash-verge + verge-mihomo
Write-Output "Step 1: killing clash processes..."
Get-Process clash-verge,verge-mihomo,clash-verge-service -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 3

# Verify killed
$alive = Get-Process clash-verge,verge-mihomo -ErrorAction SilentlyContinue
if ($alive) {
    Write-Output "FAIL: still alive $($alive.Id -join ',')"
    exit 1
}
Write-Output "killed"

# Start clash-verge with --silent-start
Write-Output "Step 2: starting clash-verge with --silent-start..."
$proc = Start-Process -FilePath "D:\1\Clash Verge\clash-verge.exe" -ArgumentList "--silent-start" -PassThru
Write-Output "started PID=$($proc.Id)"
Start-Sleep -Seconds 5

# Step 3: 4-class verification
Write-Output ""
Write-Output "Step 3: 4-class verification"
Write-Output "--- processes ---"
Get-Process clash-verge,verge-mihomo -ErrorAction SilentlyContinue | Format-Table Name,Id,@{n="WS_MB";e={[Math]::Round($_.WorkingSet/1MB,1)}},StartTime -AutoSize | Out-String | Write-Output

Write-Output "--- main window check (should be empty/hidden) ---"
$main = Get-Process clash-verge -ErrorAction SilentlyContinue
foreach ($p in $main) {
    $hasWindow = $p.MainWindowTitle
    $handle = $p.MainWindowHandle
    Write-Output "PID=$($p.Id) Title='$hasWindow' Handle=$handle"
}

Write-Output "--- 7897 LISTENING ---"
netstat -ano | findstr ":7897.*LISTENING"

Write-Output "--- verge.yaml tun.enable ---"
$line = Select-String -Path "C:\Users\xinzh\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\clash-verge.yaml" -Pattern "tun:"
Write-Output $line
$line2 = Select-String -Path "C:\Users\xinzh\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\clash-verge.yaml" -Pattern "  enable: true" | Select-Object -First 1
Write-Output $line2

Write-Output "--- Wintun adapter ---"
Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "Wintun|Meta|Tap" } | Format-Table Name,Status,InterfaceDescription -AutoSize | Out-String | Write-Output

Write-Output "--- chatgpt.com test ---"
try {
    $r = Invoke-WebRequest -Uri "https://chatgpt.com" -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 5
    Write-Output "chatgpt.com HTTP=$($r.StatusCode)"
} catch {
    Write-Output "chatgpt.com FAIL: $($_.Exception.Message)"
}

Write-Output "=== restart complete ==="