# -*- coding: utf-8 -*-
$aios = @(9916, 21356)
Write-Output "PROTECT AIOS MCP: $($aios -join ',')"
Write-Output "=== kill non-AIOS mcp-remote + chrome about:blank ==="
Get-CimInstance Win32_Process | Where-Object {
    $_.ProcessId -notin $aios -and (
        $_.CommandLine -match "puppeteer-real-browser|firecrawl|reddit-mcp|socialcrawl" -or
        ($_.Name -eq "chrome.exe" -and $_.CommandLine -match "about:blank")
    )
} | ForEach-Object {
    $cmd = $_.CommandLine.Substring(0,[Math]::Min(70,$_.CommandLine.Length))
    Write-Output "  kill PID=$($_.ProcessId) $($_.Name) $cmd"
    Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Seconds 3
Write-Output ""
Write-Output "=== verify ==="
Get-Process | Where-Object { $_.ProcessName -match "chrome|mihomo|verge|clash" -or $_.ProcessName -in @("python","pythonw") } | Select-Object Name,Id,MainWindowTitle | Format-Table -AutoSize | Out-String | Write-Output
Write-Output "--- 7897 + Wintun ---"
netstat -ano | findstr ":7897.*LISTENING"
Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "Meta" } | Format-Table Name,Status -AutoSize | Out-String | Write-Output