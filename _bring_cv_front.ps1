# -*- coding: utf-8 -*-
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class W {
    [DllImport("user32.dll")] public static extern bool SetWindowPos(IntPtr h, IntPtr h2, int x, int y, int w, int hh, uint f);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr h, int n);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
}
'@
$h = [IntPtr]4982636
[W]::SetWindowPos($h, [IntPtr](-1), 100, 100, 1400, 800, 0x0000) | Out-Null
[W]::ShowWindow($h, 1) | Out-Null
[W]::SetForegroundWindow($h) | Out-Null
Start-Sleep -Milliseconds 800
Write-Output "fronted again"