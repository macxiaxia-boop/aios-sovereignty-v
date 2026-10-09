# Phase 3 - Identify PID 8480 + audit 14:36-15:03 window + verify wmic hasn't fired

$outDir = "D:\AIOS\wmic_forensics"
$evidenceDir = "$outDir\evidence"

Write-Host "=== PHASE 3: PID 8480 INVESTIGATION ===" -ForegroundColor Cyan

# 1. PID 8480 process info (current + from Win32_Process)
Write-Host "`n--- 1. PID 8480 process details ---" -ForegroundColor Yellow
$proc8480 = Get-CimInstance Win32_Process -Filter "ProcessId=8480" -ErrorAction SilentlyContinue
if ($proc8480) {
    $proc8480 | Select-Object Name, ProcessId, ParentProcessId, CreationDate, ExecutablePath, CommandLine | Format-List
    $ppid = $proc8480.ParentProcessId
    Write-Host "Parent PID: $ppid"
    $parent = Get-CimInstance Win32_Process -Filter "ProcessId=$ppid" -ErrorAction SilentlyContinue
    if ($parent) {
        $parent | Select-Object Name, ProcessId, ParentProcessId, ExecutablePath, CommandLine | Format-List
    }
    # Grandparent
    if ($parent) {
        $gpid = $parent.ParentProcessId
        $gp = Get-CimInstance Win32_Process -Filter "ProcessId=$gpid" -ErrorAction SilentlyContinue
        if ($gp) {
            $gp | Select-Object Name, ProcessId, ExecutablePath, CommandLine | Format-List
        }
    }
} else {
    Write-Host "PID 8480 not running currently"
}

# 2. Full Win32_ProcessStartTrace history for wmic - any from today?
Write-Host "`n--- 2. Win32_ProcessStopTrace/StartTrace for wmic (today) ---" -ForegroundColor Yellow
$wmiTrace = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-WMI-Activity/Operational'} -MaxEvents 5000 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match "wmic.exe" -and $_.TimeCreated -ge (Get-Date).Date.AddDays(-1) }
$wmiTrace | Select-Object -First 20 TimeCreated, Id, @{n='Snippet';e={$_.Message.Substring(0, [Math]::Min(400, $_.Message.Length))}} |
    Format-Table -Wrap

# 3. Listener log check
Write-Host "`n--- 3. wmic process chain log status ---" -ForegroundColor Yellow
$logFile = "$evidenceDir\wmic_process_chain.log"
if (Test-Path $logFile) {
    $size = (Get-Item $logFile).Length
    $lines = (Get-Content $logFile).Count
    Write-Host "  Log file size: $size bytes, $lines lines"
    if ($size -gt 0) {
        Get-Content $logFile | ForEach-Object { Write-Host "  $_" }
    }
} else {
    Write-Host "  Log file doesn't exist"
}

# 4. Check listener process still alive
$listenerPidFile = "$evidenceDir\listener.pid"
if (Test-Path $listenerPidFile) {
    $listenerPid = Get-Content $listenerPidFile
    $listenerAlive = Get-Process -Id $listenerPid -ErrorAction SilentlyContinue
    Write-Host "`n  Listener PID=$listenerPid alive: $($null -ne $listenerAlive)"
}

# 5. Check 4103 (PowerShell pipeline execution) for wmic in last 24h
Write-Host "`n--- 5. PowerShell 4103 pipeline execution (last 24h) ---" -ForegroundColor Yellow
$p4103 = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational'; Id=4103} -MaxEvents 5000 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'wmic' -and $_.TimeCreated -ge (Get-Date).AddHours(-24) }
if ($p4103) {
    Write-Host "  Found $($p4103.Count) entries"
    $p4103 | Select-Object -First 10 TimeCreated, @{n='Snippet';e={$_.Message.Substring(0, [Math]::Min(300, $_.Message.Length))}} |
        Format-Table -Wrap
} else {
    Write-Host "  No 4103 wmic entries in last 24h"
}

# 6. All PID 8480-related events - to see WHEN it started
Write-Host "`n--- 6. PID 8480 WMI Activity timeline ---" -ForegroundColor Yellow
$p8480events = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-WMI-Activity/Operational'} -MaxEvents 5000 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'ClientProcessId = 8480' -or $_.Message -match 'ClientProcessId = 8480' } |
    Select-Object -First 5 TimeCreated, Id
$p8480events | Format-Table -AutoSize

# 7. Snapshot ALL Win32_Process to disk for offline analysis
Write-Host "`n--- 7. Snapshot of all Win32_Process (anonymized) ---" -ForegroundColor Yellow
Get-CimInstance Win32_Process |
    Select-Object Name, ProcessId, ParentProcessId, CreationDate, ExecutablePath |
    Where-Object { $_.ProcessId -lt 65536 } |
    Export-Csv "$evidenceDir\18_process_snapshot.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Saved $($(Get-CimInstance Win32_Process).Count) processes"

Write-Host "`n=== PHASE 3 COMPLETE ===" -ForegroundColor Cyan