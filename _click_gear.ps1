# -*- coding: utf-8 -*-
Add-Type -AssemblyName System.Windows.Forms
Add-Type @'
using System;
using System.Runtime.InteropServices;
public class M {
    [DllImport("user32.dll")] public static extern void mouse_event(uint f, int x, int y, uint d, int e);
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
}
'@
[M]::SetCursorPos(1825, 100) | Out-Null
Start-Sleep -Milliseconds 200
[M]::mouse_event(0x0002, 0, 0, 0, 0) | Out-Null
Start-Sleep -Milliseconds 50
[M]::mouse_event(0x0004, 0, 0, 0, 0) | Out-Null
Start-Sleep -Milliseconds 800
Write-Output "clicked gear at (1825,100)"