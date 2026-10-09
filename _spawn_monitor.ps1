# _spawn_monitor.ps1 - R272 (2026-09-29)
# 5 分钟实时监控所有 cmd.exe / powershell.exe spawn 源
# 写到 D:\AIOS\_spawn_log.txt
$ErrorActionPreference = 'Continue'
$logFile = 'D:\AIOS\_spawn_log.txt'

"=== _spawn_monitor START $(Get-Date) ===" | Out-File -FilePath $logFile -Append -Encoding utf8

# 轮询 Win32_Process, 每 2s 比较上次结果, 找出新出现的 cmd/powershell/conhost
$targetExes = @('cmd.exe','powershell.exe','pwsh.exe','conhost.exe','wmic.exe','taskkill.exe','tasklist.exe','python.exe','pythonw.exe')

$prev = @{}
$endTime = (Get-Date).AddMinutes(5)
while ((Get-Date) -lt $endTime) {
    $curr = @{}
    try {
        $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue
        foreach ($p in $procs) {
            $curr[$p.ProcessId] = @{Name=$p.Name; PPID=$p.ParentProcessId; Cmd=$p.CommandLine}
        }
    } catch {}

    $newPids = $curr.Keys | Where-Object { -not $prev.ContainsKey($_) }
    foreach ($pid in $newPids) {
        $p = $curr[$pid]
        if ($targetExes -contains $p.Name) {
            $ppid = $p.PPID
            $parentCmd = if ($curr.ContainsKey($ppid)) { $curr[$ppid].Cmd } else { '' }
            $parentName = if ($curr.ContainsKey($ppid)) { $curr[$ppid].Name } else { '' }
            $ts = Get-Date -Format 'HH:mm:ss.fff'
            "[$ts] NEW SPAWN PID=$pid Name=$p.Name" | Out-File -FilePath $logFile -Append -Encoding utf8
            "  Cmd: $($p.Cmd.Substring(0,[Math]::Min(200,$p.Cmd.Length)))" | Out-File -FilePath $logFile -Append -Encoding utf8
            "  Parent PID=$ppid Name=$parentName Cmd: $($parentCmd.Substring(0,[Math]::Min(200,$parentCmd.Length)))" | Out-File -FilePath $logFile -Append -Encoding utf8
        }
    }
    $prev = $curr
    Start-Sleep -Seconds 2
}

"=== _spawn_monitor END $(Get-Date) ===" | Out-File -FilePath $logFile -Append -Encoding utf8
