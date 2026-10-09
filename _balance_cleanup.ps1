# -*- coding: utf-8 -*-
# R327 v6 - Balance cleanup: kill non-AIOS python, disable TikTokDownloader tasks

$aiosPids = @(9916, 21356)  # PROTECTED: AIOS MCP core
$keepPids = Get-Process | Where-Object { $_.ProcessName -match "verge-mihomo|clash-verge-service" } | Select-Object -ExpandProperty Id
Write-Output "PROTECTED PIDs: $($aiosPids -join ',' + ' (AIOS MCP) | ')$($keepPids -join ',' + ' (TUN host)')"

Write-Output ""
Write-Output "Step 1: kill NON-AIOS python processes (TikTokDownloader + others)"
Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq "python.exe" -and
    $_.ProcessId -notin $aiosPids -and
    $_.ProcessId -notin $keepPids -and
    ($_.CommandLine -match "TikTokDownloader|_cover_relay|_run_pipeline|_transcribe_all|_cover_one|_mermaid_to_svg" -or
     -not ($_.CommandLine -match "Operator"))
} | ForEach-Object {
    Write-Output "  kill PID=$($_.ProcessId) $($_.CommandLine.Substring(0,[Math]::Min(60,$_.CommandLine.Length)))"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}

Write-Output ""
Write-Output "Step 2: disable TikTokDownloader schtasks"
$tiktasks = @("PatternValidationQueue-Sat", "TimeModelRouter", "DecomposeSupervisor")
foreach ($t in $tiktasks) {
    $state = (Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue).State
    if ($state -eq "Running" -or $state -eq "Ready") {
        Stop-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue | Out-Null
        Write-Output "  stopped $t (was $state)"
    }
    Disable-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue | Out-Null
    Write-Output "  disabled $t"
}

Write-Output ""
Write-Output "Step 3: kill any leftover cmd.exe windows that have visible title"
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class W {
    public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc p, IntPtr l);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
}
'@
[W]::EnumWindows({param($h,$l)
    $len = [W]::GetWindowTextLength($h)
    $vis = [W]::IsWindowVisible($h)
    if ($len -gt 0 -and $vis) {
        $pid2 = 0; [W]::GetWindowThreadProcessId($h, [ref]$pid2) | Out-Null
        $proc = Get-Process -Id $pid2 -ErrorAction SilentlyContinue
        if ($proc -and $proc.ProcessName -eq "cmd") {
            $sb = New-Object Text.StringBuilder ($len+1)
            [W]::GetWindowText($h, $sb, $len+1) | Out-Null
            $t = $sb.ToString()
            Write-Output "  visible cmd PID=$pid2 title=`"$t`""
            [W]::ShowWindow($h, 6) | Out-Null
        }
    }
    return $true
}, [IntPtr]::Zero) | Out-Null

Write-Output ""
Write-Output "Step 4: verify 4-class"
Get-Process | Where-Object { $_.ProcessName -match "clash|verge|mihomo|python|pythonw" } | Group-Object ProcessName | Select-Object Name,Count | Format-Table -AutoSize | Out-String | Write-Output
Write-Output "--- 7897 ---"; netstat -ano | findstr ":7897.*LISTENING"
Write-Output "--- Wintun ---"; Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "Meta" } | Format-Table Name,Status -AutoSize | Out-String | Write-Output
Write-Output "--- chatgpt ---"
try { $r = Invoke-WebRequest -Uri "https://chatgpt.com" -UseBasicParsing -TimeoutSec 10 -MaximumRedirection 5; Write-Output "chatgpt HTTP=$($r.StatusCode)" } catch { Write-Output "FAIL: $($_.Exception.Message)" }
Write-Output "=== done ==="