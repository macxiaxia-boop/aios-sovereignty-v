# Phase 2 analysis - find root cause of wmic.exe popup
# 1. Check WMI Activity log
# 2. Check Task Scheduler Operational for wmic
# 3. Search registry for wmic references
# 4. Deep-scan code refs in major dirs
# 5. Check 4103 (pipeline execution) for wmic
# 6. Check recent PowerShell commands history beyond what we have

$outDir = "D:\AIOS\wmic_forensics"
$evidenceDir = "$outDir/evidence"

Write-Host "=== PHASE 2 ROOT CAUSE ANALYSIS ===" -ForegroundColor Cyan

# 1. Task Scheduler Operational - filter for wmic
Write-Host "`n--- 1. TaskScheduler Operational (wmic) ---" -ForegroundColor Yellow
$ts = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-TaskScheduler/Operational'} -MaxEvents 5000 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'wmic' }
if ($ts) {
    $ts | Select-Object -First 50 TimeCreated, Id, @{n='Snippet';e={$_.Message.Substring(0, [Math]::Min(300, $_.Message.Length))}} |
        Export-Csv "$evidenceDir/13_tasksched_wmic.csv" -NoTypeInformation -Encoding UTF8
    Write-Host "  Found $($ts.Count) entries"
} else {
    Write-Host "  No TaskScheduler wmic events"
}

# 2. WMI Activity log
Write-Host "`n--- 2. WMI Activity log ---" -ForegroundColor Yellow
$wmiAct = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-WMI-Activity/Operational'} -MaxEvents 1000 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'wmic' -or $_.Message -match 'Win32_Process' }
if ($wmiAct) {
    $wmiAct | Select-Object -First 30 TimeCreated, Id, @{n='Snippet';e={$_.Message.Substring(0, [Math]::Min(300, $_.Message.Length))}} |
        Export-Csv "$evidenceDir/14_wmi_activity_wmic.csv" -NoTypeInformation -Encoding UTF8
    Write-Host "  Found $($wmiAct.Count) entries"
} else {
    Write-Host "  No WMI Activity matches"
}

# 3. Registry - search for "wmic" in all Run keys
Write-Host "`n--- 3. Registry search for wmic in HKLM/HKCU ---" -ForegroundColor Yellow
$regPaths = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunServices',
    'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run',
    'HKLM:\SYSTEM\CurrentControlSet\Services',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
    'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
)
$wmicReg = @()
foreach ($p in $regPaths) {
    if (Test-Path $p) {
        $hits = Get-ChildItem -Path $p -Recurse -ErrorAction SilentlyContinue |
            Get-ItemProperty -ErrorAction SilentlyContinue |
            Where-Object { $_.PSObject.Properties.Value -match 'wmic' }
        foreach ($h in $hits) {
            $wmicReg += [PSCustomObject]@{
                Path = $h.PSPath
                Name = $h.PSChildName
                Value = ($h.PSObject.Properties | Where-Object { $_.Value -match 'wmic' }).Value
            }
        }
    }
}
$wmicReg | Export-Csv "$evidenceDir/15_registry_wmic.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Registry wmic matches: $($wmicReg.Count)"

# 4. Deep code search in major dirs (incremental - top suspects only)
Write-Host "`n--- 4. Deep code search (ps1, bat, cmd, py) for wmic ---" -ForegroundColor Yellow
$searchDirs = @('D:\AIOS', 'D:\Tools', 'D:\1', 'D:\demo', 'C:\Users\xinzh\.openclaw', 'C:\Users\xinzh\.codebuddy', 'C:\Users\xinzh\.claude')
$codeRefs = @()
foreach ($dir in $searchDirs) {
    if (Test-Path $dir) {
        $files = Get-ChildItem -Path $dir -Recurse -File -Include '*.ps1','*.bat','*.cmd','*.py' -ErrorAction SilentlyContinue
        foreach ($f in $files) {
            $content = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
            if ($content -match 'wmic\.exe|wmic\s+os|wmic\s+process|wmic\s+cpu|wmic\s+service') {
                $matches = [regex]::Matches($content, '.*wmic\.\w+|.*wmic\s+\w+.*')
                $firstMatch = $matches[0].Value.Trim()
                $codeRefs += [PSCustomObject]@{
                    Directory = $dir
                    File = $f.FullName
                    LastModified = $f.LastWriteTime
                    Match = $firstMatch.Substring(0, [Math]::Min(200, $firstMatch.Length))
                }
            }
        }
    }
}
$codeRefs | Export-Csv "$evidenceDir/16_deep_wmic_code_refs.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Deep code refs: $($codeRefs.Count)"
foreach ($r in $codeRefs | Select-Object -First 30) {
    Write-Host "    $($r.File)"
    Write-Host "      [$($r.LastModified)] $($r.Match)"
}

# 5. PowerShell 4103 (pipeline execution) for wmic
Write-Host "`n--- 5. PowerShell 4103 (wmic) ---" -ForegroundColor Yellow
$p4103 = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational'; Id=4103} -MaxEvents 1000 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'wmic' }
if ($p4103) {
    $p4103 | Select-Object -First 30 TimeCreated, @{n='Snippet';e={$_.Message.Substring(0, [Math]::Min(400, $_.Message.Length))}} |
        Export-Csv "$evidenceDir/17_ps4103_wmic.csv" -NoTypeInformation -Encoding UTF8
    Write-Host "  Found $($p4103.Count) entries"
} else {
    Write-Host "  No 4103 wmic entries"
}

# 6. Search Windows-MCP / CodeBuddy related scripts
Write-Host "`n--- 6. CodeBuddy & related tooling scripts ---" -ForegroundColor Yellow
$cbPaths = @('C:\Users\xinzh\.codebuddy', 'C:\Users\xinzh\.trae', 'C:\Users\xinzh\.qoder')
foreach ($p in $cbPaths) {
    if (Test-Path $p) {
        Write-Host "  found $p - scanning"
        $hits = Get-ChildItem -Path $p -Recurse -File -Include '*.ps1','*.psm1' -ErrorAction SilentlyContinue |
            Select-String -Pattern 'wmic|SAFE_DELETE_FAIL_CLOSED|wmic_min' -ErrorAction SilentlyContinue
        foreach ($h in $hits) {
            Write-Host "    HIT: $($h.Path):$($h.LineNumber)"
        }
    } else {
        Write-Host "  $p [not exists]"
    }
}

Write-Host "`n=== PHASE 2 COMPLETE ===" -ForegroundColor Cyan