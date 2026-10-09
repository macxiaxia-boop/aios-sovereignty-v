# Launch the wmic listener detached + verify alive
$listenerScript = "D:\AIOS\wmic_forensics\01_wmic_listener.ps1"

# Cleanup any old listener first
Get-Process powershell -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -eq '' -and $_.CommandLine -match 'wmic_listener' -and $_.Id -ne $PID
} | Stop-Process -Force -ErrorAction SilentlyContinue

# Start detached hidden PowerShell with the listener
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "powershell.exe"
$psi.Arguments = "-NoProfile -NoExit -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$listenerScript`""
$psi.UseShellExecute = $false
$psi.WindowStyle = 'Hidden'
$psi.CreateNoWindow = $true

$p = [System.Diagnostics.Process]::Start($psi)
Write-Host "Listener launched PID=$($p.Id)"
$p.Id | Out-File "D:\AIOS\wmic_forensics\evidence\listener.pid" -Encoding utf8

Start-Sleep -Seconds 3

# Verify alive and check log file
$logFile = "D:\AIOS\wmic_forensics\evidence\wmic_process_chain.log"
$alive = Get-Process -Id $p.Id -ErrorAction SilentlyContinue
Write-Host "Listener alive: $($null -ne $alive)"
if (Test-Path $logFile) {
    $size = (Get-Item $logFile).Length
    Write-Host "Log file: $logFile size=$size bytes"
    Get-Content "$logFile" | Select-Object -Last 3 | ForEach-Object { Write-Host "  $_" }
} else {
    Write-Host "Log file not yet created"
}