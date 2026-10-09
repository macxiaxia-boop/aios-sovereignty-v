# -*- coding: utf-8 -*-
# R327 v5 - DEEP SCAN all popup sources

Write-Output "=== 1. ALL WINDOWS (visible + hidden) ==="
Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class W {
    public delegate bool EnumWindowsProc(IntPtr h, IntPtr l);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc p, IntPtr l);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr h);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
}
'@
$wins = @()
[W]::EnumWindows({param($h,$l)
    $len = [W]::GetWindowTextLength($h)
    $vis = [W]::IsWindowVisible($h)
    $r = New-Object W+RECT; [W]::GetWindowRect($h, [ref]$r) | Out-Null
    $w = $r.R - $r.L; $hh = $r.B - $r.T
    $pid2 = 0
    [W]::GetWindowThreadProcessId($h, [ref]$pid2) | Out-Null
    if ($len -gt 0 -and $w -gt 100 -and $hh -gt 50) {
        $sb = New-Object Text.StringBuilder ($len+1)
        [W]::GetWindowText($h, $sb, $len+1) | Out-Null
        $script:wins += [PSCustomObject]@{Title=$($sb.ToString().Substring(0,[Math]::Min(60,$sb.Length))); W=$w; H=$hh; X=$r.L; Y=$r.T; Visible=$vis; PID=$pid2}
    }
    return $true
}, [IntPtr]::Zero) | Out-Null
$wins | Sort-Object W -Descending | Format-Table -AutoSize | Out-String | Write-Output

Write-Output ""
Write-Output "=== 2. ALL STARTUP REG ENTRIES (HKCU Run + RunOnce + HKLM Run + RunOnce + StartupApproved) ==="
$regPaths = @(
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32"
)
foreach ($p in $regPaths) {
    $props = Get-ItemProperty -Path $p -ErrorAction SilentlyContinue
    if ($props) {
        Write-Output "[$p]"
        foreach ($prop in $props.PSObject.Properties) {
            if ($prop.Name -notmatch "^PS" -and $prop.Value -match "\.exe") {
                Write-Output "  $($prop.Name) = $($prop.Value)"
            }
        }
    }
}

Write-Output ""
Write-Output "=== 3. ALL SCHTASKS (Ready + Running tasks can spawn GUI) ==="
Get-ScheduledTask | Where-Object { $_.State -eq "Ready" -or $_.State -eq "Running" } | Where-Object {
    $_.TaskName -match "Clash|Verge|Mihomo|VPN|Claude|WorkBuddy|Codex|Watchdog|Popup" -or
    $_.Actions[0].Execute -match "\.exe"
} | Select-Object TaskName,State,@{n="Exec";e={$_.Actions[0].Execute}} | Format-Table -AutoSize | Out-String | Write-Output

Write-Output ""
Write-Output "=== 4. ALL POPUP-LIKELY PROCESSES (have MainWindow + non-system) ==="
Get-Process | Where-Object { $_.MainWindowTitle.Length -gt 0 -and $_.ProcessName -notmatch "^(svchost|lsass|csrss|wininit|dwm|explorer|System)$" } | Select-Object Name,Id,@{n="Title";e={if($_.MainWindowTitle.Length -gt 40) {$_.MainWindowTitle.Substring(0,40)+"..."} else {$_.MainWindowTitle}}} | Format-Table -AutoSize | Out-String | Write-Output

Write-Output ""
Write-Output "=== 5. STARTUP FOLDER SHORTCUTS ==="
$startupFolders = @(
    "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup",
    "$env:PROGRAMDATA\Microsoft\Windows\Start Menu\Programs\Startup"
)
foreach ($f in $startupFolders) {
    if (Test-Path $f) {
        Write-Output "[$f]"
        Get-ChildItem $f -ErrorAction SilentlyContinue | ForEach-Object { Write-Output "  $($_.Name)" }
    }
}

Write-Output ""
Write-Output "=== 6. WMI EVENT CONSUMERS (rare but powerful auto-spawn) ==="
Get-WmiObject -Namespace root\subscription -Class __EventConsumer -ErrorAction SilentlyContinue | Select-Object Name,CommandLineTemplate | Format-Table -AutoSize | Out-String | Write-Output

Write-Output "=== 7. SCHEDULED TASK CREATORS ==="
$creators = Get-WmiObject -Namespace root\subscription -Class __EventConsumer -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name -ErrorAction SilentlyContinue
foreach ($c in $creators) {
    $b = Get-WmiObject -Namespace root\subscription -Class __FilterToConsumerBinding -ErrorAction SilentlyContinue | Where-Object { $_.Consumer -match $c }
    if ($b) { Write-Output "  Binding: Consumer=$c Filter=$($b.Filter)" }
}

Write-Output "=== END DEEP SCAN ==="