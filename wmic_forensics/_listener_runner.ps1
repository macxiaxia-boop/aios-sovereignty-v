# Launches listener as a detached, no-window background process
# Per red line #78 (no black window), uses -WindowStyle Hidden + CREATE_NO_WINDOW equivalent

$listenerScript = "D:\AIOS\wmic_forensics\01_wmic_listener.ps1"

# Start a persistent PowerShell with -NoExit so the Register-CimIndicationEvent subscription stays alive
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "powershell.exe"
$psi.Arguments = "-NoProfile -NoExit -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$listenerScript`""
$psi.UseShellExecute = $false
$psi.WindowStyle = 'Hidden'
$psi.CreateNoWindow = $true

$p = [System.Diagnostics.Process]::Start($psi)
Write-Host "Listener launched PID=$($p.Id)"
$p.Id | Out-File "D:\AIOS\wmic_forensics\evidence\listener.pid" -Encoding utf8