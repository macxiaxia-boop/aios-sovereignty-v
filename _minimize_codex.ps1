Add-Type @'
using System;
using System.Runtime.InteropServices;
public class W {
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
}
'@
$handle = [IntPtr]19007610
$r = New-Object W+RECT
[W]::GetWindowRect($handle, [ref]$r) | Out-Null
Write-Output "Before: WxH=$($r.R - $r.L)x$($r.B - $r.T) at ($($r.L),$($r.T))"
# SW_MINIMIZE = 6
[W]::ShowWindow($handle, 6) | Out-Null
Start-Sleep -Milliseconds 500
$r2 = New-Object W+RECT
[W]::GetWindowRect($handle, [ref]$r2) | Out-Null
Write-Output "After:  WxH=$($r2.R - $r2.L)x$($r2.B - $r2.T) at ($($r2.L),$($r2.T))"
Write-Output "Codex codex GUI minimized; process still running"