$path = 'D:\AIOS\aios_tasks\aios_vnext\INDEX.md'
$lines = Get-Content -LiteralPath $path -Encoding UTF8
$out = @()
$changed = $false
foreach ($line in $lines) {
    if ($line -match 'T0003.*InProgress.*dev #5') {
        $newLine = $line -replace '\*\*InProgress\*\* \(dev #5\)', 'Submitted (evidence: evidence/T0003_20261008-110409.md)'
        $out += $newLine
        $changed = $true
        Write-Output "MODIFIED:"
        Write-Output "  before: $line"
        Write-Output "  after:  $newLine"
    } else {
        $out += $line
    }
}
if ($changed) {
    $out -join "`n" | Set-Content -LiteralPath $path -Encoding UTF8
    Write-Output "INDEX.md updated successfully"
} else {
    Write-Output "ERROR: T0003 row not matched"
    exit 1
}