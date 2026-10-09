$content = Get-Content -Raw 'D:\AIOS\_net_test_full.ps1'
[System.IO.File]::WriteAllText('D:\AIOS\_net_test_full.ps1', $content, [System.Text.UTF8Encoding]::new($true))
Write-Output "saved as UTF-8 BOM"