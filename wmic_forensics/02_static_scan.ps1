# WMIC Forensics - 6-channel static scan
# Sections 10-17: scheduled tasks, services, autoruns, WMI subscriptions, PS logs, code refs

$outDir = "D:\AIOS\wmic_forensics"
$evidenceDir = "$outDir/evidence"

Write-Host "=== STATIC SCAN (no modifications) ===" -ForegroundColor Cyan

# 1. Scheduled Tasks (Section 10)
Write-Host "`n--- Scheduled Tasks ---" -ForegroundColor Yellow
$tasks = Get-ScheduledTask | ForEach-Object {
    $task = $_
    foreach ($action in $task.Actions) {
        [PSCustomObject]@{
            TaskPath = $task.TaskPath
            TaskName = $task.TaskName
            State = $task.State
            Execute = $action.Execute
            Arguments = $action.Arguments
            WorkingDirectory = $action.WorkingDirectory
        }
    }
}
$tasks | Export-Csv "$evidenceDir/06_scheduled_tasks_all.csv" -NoTypeInformation -Encoding UTF8
$wmicTasks = $tasks | Where-Object {
    $_.Execute -match 'wmic|powershell|pwsh|cmd|python|node|\.ps1|\.bat|\.cmd|\.vbs|\.js' -or
    $_.Arguments -match 'wmic|powershell|pwsh|cmd|python|node|\.ps1|\.bat|\.cmd|\.vbs|\.js'
}
$wmicTasks | Export-Csv "$evidenceDir/06b_scheduled_tasks_wmic_suspect.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Total tasks: $($tasks.Count) | Suspect (wm|ps|cmd|py|node): $($wmicTasks.Count)"
$wmicTasks | Select-Object TaskPath, TaskName, State, Execute | Format-Table -AutoSize | Out-String | Write-Host

# 2. Services (Section 11)
Write-Host "`n--- Services ---" -ForegroundColor Yellow
$svc = Get-CimInstance Win32_Service |
    Select-Object Name, DisplayName, State, StartMode, PathName, ProcessId
$svc | Export-Csv "$evidenceDir/07_services_all.csv" -NoTypeInformation -Encoding UTF8
$susSvc = $svc | Where-Object {
    $_.PathName -match 'cmd|powershell|python|node|AIOS|OpenClaw|watchdog|monitor|health|hermes|workbuddy|codex'
}
$susSvc | Export-Csv "$evidenceDir/07b_services_wmic_suspect.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Total services: $($svc.Count) | Suspect: $($susSvc.Count)"
$susSvc | Format-Table Name, State, StartMode, PathName -AutoSize | Out-String | Write-Host

# 3. WMI Permanent Subscriptions (Section 13)
Write-Host "`n--- WMI Subscriptions ---" -ForegroundColor Yellow
$filters = Get-CimInstance -Namespace root\subscription -ClassName __EventFilter -ErrorAction SilentlyContinue
$consumers = Get-CimInstance -Namespace root\subscription -ClassName CommandLineEventConsumer -ErrorAction SilentlyContinue
$scriptCons = Get-CimInstance -Namespace root\subscription -ClassName ActiveScriptEventConsumer -ErrorAction SilentlyContinue
$bindings = Get-CimInstance -Namespace root\subscription -ClassName __FilterToConsumerBinding -ErrorAction SilentlyContinue

$filters | Export-Csv "$evidenceDir/08_wmi_eventfilters.csv" -NoTypeInformation -Encoding UTF8
$consumers | Export-Csv "$evidenceDir/08b_wmi_cmdlineconsumers.csv" -NoTypeInformation -Encoding UTF8
$scriptCons | Export-Csv "$evidenceDir/08c_wmi_scriptconsumers.csv" -NoTypeInformation -Encoding UTF8
$bindings | Export-Csv "$evidenceDir/08d_wmi_bindings.csv" -NoTypeInformation -Encoding UTF8

Write-Host "  EventFilters: $(if($filters){$filters.Count}else{0})"
Write-Host "  CommandLineConsumers: $(if($consumers){$consumers.Count}else{0})"
Write-Host "  ActiveScriptConsumers: $(if($scriptCons){$scriptCons.Count}else{0})"
Write-Host "  FilterToConsumerBindings: $(if($bindings){$bindings.Count}else{0})"

# 4. Autoruns (Section 12)
Write-Host "`n--- Autoruns (HKCU/HKLM Run + Startup) ---" -ForegroundColor Yellow
$autoruns = @()
$paths = @(
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\Run',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\Run',
    'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run',
    'HKCU:\Software\Microsoft\Windows\CurrentVersion\RunOnce',
    'HKLM:\Software\Microsoft\Windows\CurrentVersion\RunOnce'
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        $items = Get-ItemProperty -Path $p -ErrorAction SilentlyContinue
        foreach ($name in $items.PSObject.Properties.Name) {
            if ($name -in @('PSPath','PSParentPath','PSChildName','PSDrive','PSProvider')) { continue }
            $autoruns += [PSCustomObject]@{
                Registry = $p
                ValueName = $name
                ValueData = $items.$name
            }
        }
    }
}
$autoruns | Export-Csv "$evidenceDir/09_autoruns_registry.csv" -NoTypeInformation -Encoding UTF8
$susAutoruns = $autoruns | Where-Object { $_.ValueData -match 'wmic|powershell|pwsh|cmd|python|node|\.ps1|\.bat|\.cmd' }
$susAutoruns | Export-Csv "$evidenceDir/09b_autoruns_wmic_suspect.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Total autoruns: $($autoruns.Count) | Suspect: $($susAutoruns.Count)"

# 5. PowerShell 4104 Script Block (Section 14)
Write-Host "`n--- PowerShell 4104 (last 24h script blocks mentioning wmic) ---" -ForegroundColor Yellow
$ps4104 = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational'; Id=4104} `
    -MaxEvents 5000 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'wmic' }
if ($ps4104) {
    $ps4104 | Select-Object -First 50 TimeCreated, @{n='Snippet';e={$_.Message.Substring(0, [Math]::Min(800, $_.Message.Length))}} |
        Export-Csv "$evidenceDir/10_ps4104_wmic.csv" -NoTypeInformation -Encoding UTF8
    Write-Host "  Found $($ps4104.Count) script blocks with wmic reference"
} else {
    Write-Host "  No 4104 with wmic reference (script block logging may be disabled)" -ForegroundColor DarkYellow
    "No 4104 with wmic reference" | Out-File "$evidenceDir/10_ps4104_wmic.txt" -Encoding utf8
}

# 6. Local code references (Sections 15-16)
Write-Host "`n--- Local code search for wmic ---" -ForegroundColor Yellow
$searchDirs = @(
    'D:\AIOS',
    'D:\个人文件\AI\Operator',
    'D:\OpenAI.Codex',
    'C:\Users\xinzh\.workbuddy',
    'C:\Users\xinzh\.codex',
    'D:\Tools'
)
$codeRefs = @()
foreach ($dir in $searchDirs) {
    if (Test-Path $dir) {
        Write-Host "  scanning $dir ..."
        try {
            # Use Select-String - utf8 default, fast
            $hits = Select-String -Path (Get-ChildItem -Path $dir -Recurse -File -Include '*.ps1','*.psm1','*.cmd','*.bat','*.py','*.js','*.ts','*.json','*.yaml','*.yml' -ErrorAction SilentlyContinue).FullName `
                -Pattern 'wmic\.exe|Win32_Process|Win32_Processor|Win32_OperatingSystem|Win32_PhysicalMemory|Win32_VideoController|Win32_LogicalDisk' `
                -CaseSensitive:$false -ErrorAction SilentlyContinue
            foreach ($h in $hits) {
                $codeRefs += [PSCustomObject]@{
                    Directory = $dir
                    File = $h.Path
                    Line = $h.LineNumber
                    Match = $h.Line.Trim()
                }
            }
        } catch {
            Write-Host "  error scanning $dir : $_" -ForegroundColor DarkYellow
        }
    }
}
$codeRefs | Export-Csv "$evidenceDir/11_wmic_code_references.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Total code refs: $($codeRefs.Count)"

# 7. Health-check / watchdog / telemetry scripts (Section 16)
Write-Host "`n--- Health-check / Watchdog / Telemetry scripts ---" -ForegroundColor Yellow
$hcKeywords = 'health|heartbeat|watchdog|telemetry|monitor|metrics|hardware|diagnostic|runtime_check|supervisor|daemon|collect'
$hcRefs = @()
foreach ($dir in $searchDirs) {
    if (Test-Path $dir) {
        try {
            $hits = Select-String -Path (Get-ChildItem -Path $dir -Recurse -File -Include '*.ps1','*.py' -ErrorAction SilentlyContinue).FullName `
                -Pattern $hcKeywords -ErrorAction SilentlyContinue
            foreach ($h in $hits) {
                if ($h.Line -match 'wmic|CimInstance|Get-CimInstance') {
                    $hcRefs += [PSCustomObject]@{
                        Directory = $dir
                        File = $h.Path
                        Line = $h.LineNumber
                        Match = $h.Line.Trim()
                    }
                }
            }
        } catch {}
    }
}
$hcRefs | Export-Csv "$evidenceDir/12_healthcheck_wmic_refs.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  HC scripts with wmic/CIM refs: $($hcRefs.Count)"

Write-Host "`n=== STATIC SCAN COMPLETE ===" -ForegroundColor Cyan
Write-Host "All evidence in: $evidenceDir"