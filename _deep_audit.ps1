# -*- coding: utf-8 -*-
# R327 v8 - DEEP audit with Process Creation audit policy enabled

Write-Output "Step 1: Enable Process Creation audit"
auditpol /set /category:"Detailed Tracking" /subcategory:"Process Creation" /success:enable /failure:enable 2>&1 | Out-Null
Write-Output "  enabled (security log will record future spawns)"

Write-Output ""
Write-Output "Step 2: ALL schtasks with .exe that spawn UI (not just .py)"
Get-ScheduledTask | Where-Object { $_.State -in @("Ready","Running") } | ForEach-Object {
    $act = $_.Actions[0].Execute
    $arg = $_.Actions[0].Arguments
    $full = if ($arg) { "$act $arg" } else { "$act" }
    if ($full -match "\.exe") {
        Write-Output "  $($_.TaskName) [$($_.State)] => $full"
    }
}

Write-Output ""
Write-Output "Step 3: ANY script that references clash-verge.exe (search all .ps1 .cmd .py on D: AIOS drive)"
$grepResults = Get-ChildItem "D:\AIOS" -Recurse -Include *.ps1,*.cmd,*.py -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "_archived|_backups" } | ForEach-Object {
    $content = Get-Content $_.FullName -ErrorAction SilentlyContinue
    if ($content -match "clash-verge\.exe") {
        Write-Output "  $($_.FullName)"
    }
}

Write-Output ""
Write-Output "Step 4: ANY WMI subscription / event consumer (legacy auto-spawn)"
Get-WmiObject -Namespace root\subscription -Class __EventConsumer -ErrorAction SilentlyContinue | Format-Table -AutoSize | Out-String | Write-Output
Get-WmiObject -Namespace root\subscription -Class __EventFilter -ErrorAction SilentlyContinue | Format-Table -AutoSize | Out-String | Write-Output

Write-Output ""
Write-Output "Step 5: ALL scheduled tasks Action XML for clash mentions"
Get-ScheduledTask | ForEach-Object {
    $xml = ($_.Actions[0].OuterXml -replace "`n", " ")
    if ($xml -match "clash" -or $xml -match "ClashVerge" -or $xml -match "7897") {
        Write-Output "  $($_.TaskName): $($_.State) PS:($($_.Actions[0].Execute))"
    }
}

Write-Output ""
Write-Output "Step 6: Registry RunOnce + StartupApproved (overrides for disabled items)"
foreach ($p in @(
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce",
    "HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run",
    "HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32"
)) {
    $props = Get-ItemProperty -Path $p -ErrorAction SilentlyContinue
    if ($props) {
        Write-Output "[$p]"
        foreach ($prop in $props.PSObject.Properties) {
            if ($prop.Name -notmatch "^PS") { Write-Output "  $($prop.Name) = $($prop.Value)" }
        }
    }
}

Write-Output "=== END ==="