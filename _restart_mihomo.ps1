# -*- coding: utf-8 -*-
# Restart mihomo to load new Merge.yaml rules

Write-Output "Kill old mihomo PID 25868"
$result = taskkill /F /PID 25868 2>&1
Write-Output "taskkill: $result"
Start-Sleep -Seconds 3

Write-Output ""
Write-Output "Check still listening?"
$listen = netstat -ano | findstr ":7897.*LISTENING"
Write-Output "7897: $listen"

if ($listen) {
    Write-Output "still alive - try taskkill /F /IM"
    taskkill /F /IM verge-mihomo.exe 2>&1 | Out-Null
    Start-Sleep -Seconds 3
}

Write-Output ""
Write-Output "Start new mihomo"
$proc = Start-Process -FilePath "D:\1\Clash Verge\verge-mihomo.exe" `
    -ArgumentList "-d","C:\Users\xinzh\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev","-f","C:\Users\xinzh\AppData\Roaming\io.github.clash-verge-rev.clash-verge-rev\clash-verge.yaml" `
    -PassThru
Write-Output "new mihomo PID=$($proc.Id)"
Start-Sleep -Seconds 5

Write-Output ""
Write-Output "=== verify ==="
Get-Process verge-mihomo -ErrorAction SilentlyContinue | Format-Table Name,Id,StartTime -AutoSize | Out-String | Write-Output
netstat -ano | findstr ":7897.*LISTENING"
Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "Meta" } | Format-Table Name,Status -AutoSize | Out-String | Write-Output

Write-Output ""
Write-Output "=== chatgpt test ==="
try { $r = Invoke-WebRequest -Uri "https://chatgpt.com" -UseBasicParsing -TimeoutSec 12 -MaximumRedirection 5; Write-Output "chatgpt HTTP=$($r.StatusCode)" } catch { Write-Output "chatgpt FAIL: $($_.Exception.Message)" }
try { $r = Invoke-WebRequest -Uri "https://www.google.com" -UseBasicParsing -TimeoutSec 8; Write-Output "google HTTP=$($r.StatusCode)" } catch { Write-Output "google FAIL" }

Write-Output "=== done ==="