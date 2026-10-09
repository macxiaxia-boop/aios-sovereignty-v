# WMIC Forensics - Real-time Win32_ProcessStartTrace listener
# Section 6 of forensic spec - capture BEFORE wmic.exe dies
# Runs as background job, writes to evidence/wmic_process_chain.log
# Logs every wmic.exe creation with full parent chain (PID/PPID/GPPID)
# Plus tracks cmd/powershell/python/node spawns in same time window

$logFile = "D:\AIOS\wmic_forensics\evidence\wmic_process_chain.log"
$pidLog  = "D:\AIOS\wmic_forensics\evidence\pid_creation_log.log"

# Ensure file exists
if (-not (Test-Path $logFile)) { New-Item -ItemType File -Path $logFile -Force | Out-Null }
if (-not (Test-Path $pidLog))  { New-Item -ItemType File -Path $pidLog  -Force | Out-Null }

Write-Host "[$(Get-Date -Format 'HH:mm:ss.fff')] WMIC listener starting PID=$PID" | Out-File $pidLog -Append

# Helper to safely read process info even if it just died
function Get-SafeCim($procId) {
    try {
        $p = Get-CimInstance Win32_Process -Filter "ProcessId=$procId" -ErrorAction Stop
        if ($p) { return $p } else { return $null }
    } catch { return $null }
}

# Main action: capture every wmic.exe creation
$action = {
    $e = $Event.SourceEventArgs.NewEvent
    if ($e.ProcessName -ieq 'wmic.exe') {
        $time = Get-Date -Format 'yyyy-MM-dd HH:mm:ss.fff'
        $wmicPid = $e.ProcessID
        $wmicPpid = $e.ParentProcessID

        # Race-condition guard: capture PID immediately even if wmic dies before CIM lookup
        $wmic = Get-SafeCim $wmicPid
        $parent = Get-SafeCim $wmicPpid
        $grand = $null
        if ($parent) { $grand = Get-SafeCim $parent.ParentProcessId }

        $record = [PSCustomObject]@{
            Time                = $time
            WMIC_PID            = $wmicPid
            WMIC_PPID           = $wmicPpid
            WMIC_CommandLine    = if ($wmic) { $wmic.CommandLine } else { '[died before CIM lookup]' }
            WMIC_Path           = if ($wmic) { $wmic.ExecutablePath } else { $null }
            Parent_PID          = $wmicPpid
            Parent_Name         = if ($parent) { $parent.Name } else { $null }
            Parent_CommandLine  = if ($parent) { $parent.CommandLine } else { $null }
            Parent_Path         = if ($parent) { $parent.ExecutablePath } else { $null }
            GrandParent_PID     = if ($parent) { $parent.ParentProcessId } else { $null }
            GrandParent_Name    = if ($grand) { $grand.Name } else { $null }
            GrandParent_CmdLine = if ($grand) { $grand.CommandLine } else { $null }
            GrandParent_Path    = if ($grand) { $grand.ExecutablePath } else { $null }
        }
        $record | ConvertTo-Json -Depth 5 -Compress |
            Out-File $logFile -Append -Encoding utf8
    }
}

# Subscribe
Unregister-Event -SourceIdentifier 'WMIC_Process_Start' -ErrorAction SilentlyContinue
Register-CimIndicationEvent `
    -Query "SELECT * FROM Win32_ProcessStartTrace WHERE ProcessName='wmic.exe'" `
    -SourceIdentifier "WMIC_Process_Start" `
    -Action $action `
    -ErrorAction Stop

Write-Host "[$(Get-Date -Format 'HH:mm:ss.fff')] Listener ACTIVE - monitoring wmic.exe" | Out-File $pidLog -Append
Write-Host "Listening on wmic.exe creations. Log: $logFile"
Write-Host "To stop: Unregister-Event -SourceIdentifier 'WMIC_Process_Start'"