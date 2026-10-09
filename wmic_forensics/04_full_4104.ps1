# Get full 4104 PowerShell script blocks with wmic - UNTRUNCATED
$results = Get-WinEvent -FilterHashtable @{LogName='Microsoft-Windows-PowerShell/Operational'; Id=4104} `
    -MaxEvents 500 -ErrorAction SilentlyContinue |
    Where-Object { $_.Message -match 'wmic' } |
    Select-Object -First 30 TimeCreated, Id, Message

$results | ForEach-Object {
    Write-Host "=== Event $($_.Id) at $($_.TimeCreated) ==="
    Write-Host $_.Message
    Write-Host ""
}

# Save full to evidence
$results | ForEach-Object {
    [PSCustomObject]@{
        Time = $_.TimeCreated
        EventId = $_.Id
        FullMessage = $_.Message
    }
} | Export-Csv "D:\AIOS\wmic_forensics\evidence\10b_ps4104_full.csv" -NoTypeInformation -Encoding UTF8

Write-Host "Total 4104 with wmic: $($results.Count)"
Write-Host "Saved full to evidence/10b_ps4104_full.csv"