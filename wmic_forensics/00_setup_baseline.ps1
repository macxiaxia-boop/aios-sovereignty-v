# WMIC Forensics - Phase 1 Baseline Capture
# Section 3 of forensic spec - establish current state BEFORE any analysis
# R260-Wmic follow-up - finding ROOT CAUSE of wmic.exe spawns

$outDir = "D:\AIOS\wmic_forensics"
$evidenceDir = "$outDir/evidence"

Write-Host "=== WMIC FORENSICS BASELINE ===" -ForegroundColor Cyan
Write-Host "Timestamp: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff')"
Write-Host "Computer: $env:COMPUTERNAME"
Write-Host "User: $env:USERNAME"
Write-Host "OS: $((Get-CimInstance Win32_OperatingSystem).Caption)"

# 1. Current wmic processes (may be empty - that's fine)
Write-Host "`n--- 1. Current wmic.exe processes ---" -ForegroundColor Yellow
$wmicProcs = Get-Process wmic -ErrorAction SilentlyContinue
if ($wmicProcs) {
    $wmicProcs | Select-Object Id, ProcessName, StartTime, Path | Format-Table -AutoSize
} else {
    Write-Host "  [none currently running - this is expected if popup is brief]"
}
$wmicProcs | Select-Object Id, ProcessName, StartTime, Path |
    Export-Csv "$outDir/01_PROCESS_BASELINE.csv" -NoTypeInformation -Encoding UTF8

# 2. All related processes (cmd/powershell/pwsh/conhost/wmic)
Write-Host "`n--- 2. Related processes (cmd/powershell/pwsh/conhost/wmic) ---" -ForegroundColor Yellow
$related = Get-CimInstance Win32_Process |
    Where-Object { $_.Name -match '^(wmic|cmd|powershell|pwsh|conhost|python|node)\.exe$' } |
    Select-Object Name, ProcessId, ParentProcessId, ExecutablePath, CommandLine
$related | Format-Table -Wrap -AutoSize
$related | Export-Csv "$evidenceDir/02_related_processes.csv" -NoTypeInformation -Encoding UTF8

# 3. audit policy for Process Creation (4688)
Write-Host "`n--- 3. Audit policy: Process Creation ---" -ForegroundColor Yellow
$auditProc = auditpol /get /subcategory:"Process Creation" 2>&1
$auditProc | Out-File "$evidenceDir/03_audit_policy_proc_creation.txt" -Encoding utf8
Write-Host $auditProc

# 4. Sysmon check
Write-Host "`n--- 4. Sysmon check ---" -ForegroundColor Yellow
$sysmon = sc query Sysmon64 2>&1
$sysmon2 = sc query Sysmon 2>&1
$sysmon | Out-File "$evidenceDir/04_sysmon_check.txt" -Encoding utf8
$sysmon2 | Out-File "$evidenceDir/04_sysmon_check.txt" -Append -Encoding utf8
Write-Host "Sysmon64: $(if ($sysmon -match 'RUNNING') {'INSTALLED+RUNNING'} else {'NOT INSTALLED'})"
Write-Host "Sysmon: $(if ($sysmon2 -match 'RUNNING') {'INSTALLED+RUNNING'} else {'NOT INSTALLED'})"

# 5. Windows version + uptime
Write-Host "`n--- 5. System info ---" -ForegroundColor Yellow
$os = Get-CimInstance Win32_OperatingSystem
[PSCustomObject]@{
    Caption = $os.Caption
    Version = $os.Version
    LastBootUpTime = $os.LastBootUpTime
    UptimeDays = [math]::Round(((Get-Date) - $os.LastBootUpTime).TotalDays, 2)
} | Format-List

# 6. Sample 4688 events for wmic (last 24h if available)
Write-Host "`n--- 6. Sample Event 4688 (wmic) - last 100 ---" -ForegroundColor Yellow
$evt4688 = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4688} -ErrorAction SilentlyContinue -MaxEvents 5000 |
    Where-Object { $_.Message -match 'wmic.exe' } |
    Select-Object -First 100 TimeCreated, Id, @{n='Message';e={$_.Message.Substring(0, [Math]::Min(500, $_.Message.Length))}}
if ($evt4688) {
    Write-Host "  Found $($evt4688.Count) wmic.exe 4688 events"
    $evt4688 | Export-Csv "$evidenceDir/05_4688_wmic_sample.csv" -NoTypeInformation -Encoding UTF8
} else {
    Write-Host "  No 4688 wmic.exe events in last 5000 Security entries" -ForegroundColor Red
    "4688 events unavailable or auditing disabled" | Out-File "$evidenceDir/05_4688_wmic_sample.txt"
}

Write-Host "`n=== BASELINE COMPLETE ===" -ForegroundColor Cyan
Write-Host "Files: $evidenceDir"