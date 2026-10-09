Add-Type @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public class W {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr hWnd, StringBuilder s, int n);
    [DllImport("user32.dll")] public static extern int GetWindowTextLength(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT r);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hWnd);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L,T,R,B; }
}
'@
$results = @()
[W]::EnumWindows({param($h,$l)
    $vis = [W]::IsWindowVisible($h)
    $ico = [W]::IsIconic($h)
    $len = [W]::GetWindowTextLength($h)
    if ($len -gt 0) {
        $sb = New-Object System.Text.StringBuilder ($len + 1)
        [W]::GetWindowText($h, $sb, $len + 1) | Out-Null
        $title = $sb.ToString()
        $r = New-Object W+RECT
        [W]::GetWindowRect($h, [ref]$r) | Out-Null
        $w = $r.R - $r.L
        $hh = $r.B - $r.T
        if ($vis -and -not $ico -and $title.Length -gt 0 -and $w -gt 200 -and $hh -gt 200) {
            $script:results += [PSCustomObject]@{Title=$title; W=$w; H=$hh; X=$r.L; Y=$r.T; Handle=$h}
        }
    }
    return $true
}, [IntPtr]::Zero) | Out-Null
$results | Sort-Object -Property W -Descending | Format-Table -AutoSize | Out-String | Write-Output