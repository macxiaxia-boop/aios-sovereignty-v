# _proc_terminator_snoop.ps1 - R268 诊断
# 用 WMI 订阅 __InstanceDeletionEvent (进程终止) + __InstanceCreationEvent (进程创建)
# 写到 _proc_terminator.log 供分析
$ErrorActionPreference = 'Continue'
$logPath = 'D:\AIOS\_proc_terminator.log'
$procKillLog = 'D:\AIOS\_proc_kill.log'

"=== _proc_terminator_snoop START $(Get-Date) ===" | Out-File -FilePath $logPath -Append -Encoding utf8

# 1. 订阅进程终止事件 (__InstanceDeletionEvent)
$query = @"
SELECT * FROM __InstanceDeletionEvent WITHIN 1
WHERE TargetInstance ISA 'Win32_Process'
"@

try {
    Register-CimIndicationEvent -Query $query -SourceIdentifier "ProcTerm" -Action {
        $proc = $Event.SourceEventArgs.NewEvent.TargetInstance
        $pid = $proc.ProcessId
        $name = $proc.Name
        $cmd = $proc.CommandLine
        $ppid = $proc.ParentProcessId
        $ts = Get-Date -Format 'HH:mm:ss.fff'
        "[$ts] TERM PID=$pid Name=$name PPID=$ppid Cmd=$cmd" | Out-File -FilePath $using:procKillLog -Append -Encoding utf8
    } | Out-Null
    "✓ WMI 进程终止事件订阅成功" | Out-File -FilePath $logPath -Append -Encoding utf8
} catch {
    "✗ WMI 进程终止订阅失败: $_" | Out-File -FilePath $logPath -Append -Encoding utf8
}

# 2. 订阅进程创建事件
$queryCreate = @"
SELECT * FROM __InstanceCreationEvent WITHIN 1
WHERE TargetInstance ISA 'Win32_Process'
"@

try {
    Register-CimIndicationEvent -Query $queryCreate -SourceIdentifier "ProcCreate" -Action {
        $proc = $Event.SourceEventArgs.NewEvent.TargetInstance
        $pid = $proc.ProcessId
        $name = $proc.Name
        $ts = Get-Date -Format 'HH:mm:ss.fff'
        "[$ts] CREATE PID=$pid Name=$name" | Out-File -FilePath $using:procKillLog -Append -Encoding utf8
    } | Out-Null
    "✓ WMI 进程创建事件订阅成功" | Out-File -FilePath $logPath -Append -Encoding utf8
} catch {
    "✗ WMI 进程创建订阅失败: $_" | Out-File -FilePath $logPath -Append -Encoding utf8
}

"=== 持续监控中 (PID=$PID), 按 Ctrl+C 停止 ===" | Out-File -FilePath $logPath -Append -Encoding utf8

# 持续运行 5 分钟
$endTime = (Get-Date).AddMinutes(5)
while ((Get-Date) -lt $endTime) {
    Start-Sleep -Seconds 10
    $alive = "$((Get-Date).ToString('HH:mm:ss')) still alive, watchdog_count=$((Get-Process pythonw -ErrorAction SilentlyContinue).Count)"
    $alive | Out-File -FilePath $logPath -Append -Encoding utf8
}

"=== _proc_terminator_snoop END $(Get-Date) ===" | Out-File -FilePath $logPath -Append -Encoding utf8
