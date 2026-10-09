# -*- coding: utf-8 -*-
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms
$screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
$bmp = New-Object System.Drawing.Bitmap $screen.Width, $screen.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
$bmp.Save("D:\AIOS\_clash_verge_settings.png", [System.Drawing.Imaging.ImageFormat]::Png)
Write-Output "saved $($screen.Width)x$($screen.Height)"