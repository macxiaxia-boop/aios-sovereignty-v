# -*- coding: utf-8 -*-
# R327 v7 - DEEP scan: all auto-launch sources

Write-Output "=== 1. RECENTLY STARTED processes (last 30 min) ==="
$cutoff = (Get-Date).AddMinutes(-30)
Get-CimInstance Win32_Process | Where-Object { $_.CreationDate -gt $cutoff } | Sort-Object CreationDate -Descending | Select-Object ProcessId,Name,@{n="Start";e={$_.CreationDate.ToString("HH:mm:ss")}},@{n="PPID";e={$_.ParentProcessId}},@{n="Cmd";e={$_.CommandLine.Substring(0,[Math]::Min(60,$_.CommandLine.Length))}} | Format-Table -AutoSize | Out-String | Write-Output

Write-Output ""
Write-Output "=== 2. ALL UI/HAS-WINDOW processes (excluding core AIOS MCP + WorkBuddy + explorer) ==="
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class W {
    public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc p, IntPtr l);
    [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
'@
$script:ui = @()
[W]::EnumWindows({param($h,$l)
    $len = [W]::GetWindowTextLength($h)
    if ($len -gt 0) {
        $pid2 = 0; [W]::GetWindowThreadProcessId($h, [ref]$pid2) | Out-Null
        $proc = Get-Process -Id $pid2 -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -notin @("explorer","dwm","svchost","lsass","wininit","csrss","System","Code","chrome","msedge","python","pythonw","claude","Cursor","WorkBuddy","Telegram")) {
            $script:ui += [PSCustomObject]@{Name=$proc.ProcessName; PID=$pid2; Title=$proc.MainWindowTitle}
        }
    }
    return $true
}, [IntPtr]::Zero) | Out-Null
$ui | Group-Object Name | Select-Object Name,Count | Format-Table -AutoSize | Out-String | Write-Output

Write-Output ""
Write-Output "=== 3. ALL AIOS popup watchdog (active) ==="
Get-CimInstance Win32_Process | Where-Object {
    $_.Name -in @("python.exe","pythonw.exe","cmd.exe","powershell.exe") -and
    ($_.CommandLine -match "popup|hide_console|supervisor|aios_tools|r304|r193|k2c|aios_light|r274|r65|winsw|runall|monitor|continuity|silent_run|discovery|hermes|hub_health|evolution|protect_allowlist|safe_path|force_kill|pid_truth|aios_cron|pid_check")
} | Select-Object ProcessId,Name,@{n="Cmd";e={$_.CommandLine.Substring(0,[Math]::Min(70,$_.CommandLine.Length))}} | Format-Table -AutoSize | Out-String | Write-Output

Write-Output ""
Write-Output "=== 4. ALL browser windows (Chrome/Edge/Firefox) ==="
Get-Process | Where-Object { $_.ProcessName -match "chrome|msedge|firefox" } | Where-Object { $_.MainWindowTitle.Length -gt 0 } | Select-Object Name,Id,@{n="Title";e={$_.MainWindowTitle.Substring(0,[Math]::Min(70,$_.MainWindowTitle.Length))}} | Format-Table -AutoSize | Out-String | Write-Output

Write-Output ""
Write-Output "=== 5. Startup folder + Run entries (ALREADY SHOWN but recapping for context) ==="
Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -ErrorAction SilentlyContinue | Get-Member -NoteProperty -MemberType Properties | Where-Object { $_.Definition -match "exe" } | ForEach-Object { $v = (Get-ItemProperty "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" -Name $_.Name -ErrorAction SilentlyContinue).$($_.Name); Write-Output "  $($_.Name) = $v" }

Write-Output "=== END ==="