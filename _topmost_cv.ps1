# -*- coding: utf-8 -*-
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class W {
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr h2, int x, int y, int w, int hh, uint f);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
}
'@
$h = [IntPtr]4982636
# HWND_TOPMOST = -1, flag = SWP_NOMOVE | SWP_NOSIZE
[W]::SetWindowPos($h, [IntPtr](-1), 0, 0, 0, 0, 0x0003) | Out-Null
Start-Sleep -Milliseconds 500
[W]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 800
Write-Output "topmost done"