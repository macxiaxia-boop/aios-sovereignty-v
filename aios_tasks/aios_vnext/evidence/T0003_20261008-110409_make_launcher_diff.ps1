$bakPath = 'D:\AIOS\_backups\start-cc-current.ps1.pre-t0003-20261008-110409.bak'
$curPath = 'D:\demo\start-cc-current.ps1'
$bak = Get-Content -LiteralPath $bakPath -Encoding UTF8
$cur = Get-Content -LiteralPath $curPath -Encoding UTF8

# Strip trailing blank lines (artifact of multiple Set-Content operations)
while ($bak.Count -gt 0 -and [string]::IsNullOrEmpty($bak[$bak.Count - 1])) { $bak = $bak[0..($bak.Count - 2)] }
while ($cur.Count -gt 0 -and [string]::IsNullOrEmpty($cur[$cur.Count - 1])) { $cur = $cur[0..($cur.Count - 2)] }

$out = @()
$out += "# T0003 launcher diff (D:\demo\start-cc-current.ps1)"
$out += "# Backup SHA1: $((Get-FileHash -LiteralPath $bakPath -Algorithm SHA1).Hash)"
$out += "# Current SHA1: $((Get-FileHash -LiteralPath $curPath -Algorithm SHA1).Hash)"
$out += "# Backup lines (trimmed): $($bak.Count); Current lines (trimmed): $($cur.Count)"
$out += "# Stale branch grew from 3 lines to 5 lines (delta=+2)."
$out += ""
$out += '## Hunk: stale branch (file line 32-37)'
$out += ""
$out += 'Backup (lines 32-35):'
$out += '```powershell'
for ($i = 31; $i -lt 35; $i++) {
    $line = if ($i -lt $bak.Count) { $bak[$i] } else { '<MISSING>' }
    $out += "$($i+1): $line"
}
$out += '```'
$out += ""
$out += 'Current (lines 32-37):'
$out += '```powershell'
for ($i = 31; $i -lt 37; $i++) {
    $line = if ($i -lt $cur.Count) { $cur[$i] } else { '<MISSING>' }
    $out += "$($i+1): $line"
}
$out += '```'
$out += ""
$out += '## Verification: lines 1-31 byte-identical'
$out += '```'
$mismatch = $false
for ($i = 0; $i -lt 31; $i++) {
    if ($bak[$i] -ne $cur[$i]) {
        $mismatch = $true
        $out += "MISMATCH at line $($i+1): bak=$($bak[$i]) cur=$($cur[$i])"
    }
}
if (-not $mismatch) {
    $out += 'OK: lines 1-31 are byte-identical'
}
$out += '```'
$out += ""
$out += '## Verification: business-launch block byte-identical (offset +2 for stale branch growth)'
$out += '```'
$endMismatch = $false
for ($i = 35; $i -lt $bak.Count; $i++) {
    $bakLine = $bak[$i]
    $curLine = if (($i + 2) -lt $cur.Count) { $cur[$i + 2] } else { '<MISSING>' }
    if ($bakLine -ne $curLine) {
        $endMismatch = $true
        $out += "MISMATCH at bak-line $($i+1) vs cur-line $($i+3): bak=$bakLine cur=$curLine"
    }
}
if (-not $endMismatch) {
    $out += 'OK: lines 36-end of backup match lines 38-end of current (delta=+2 lines from stale branch growth)'
}
$out += '```'
$out += ""
$out += '## Summary of modification'
$out += ''
$out += '- Original 3 lines (backup lines 32-35):'
$out += '    if (...) {'
$out += '        Write-Error "STALE_HANDOFF: ..."'
$out += '        exit 42'
$out += '    }'
$out += '- New 6 lines (current lines 32-37):'
$out += '    if (...) {'
$out += '        $staleMsg = "STALE_HANDOFF: ..."'
$out += '        Write-Output $staleMsg'
$out += '        Write-Error -Message $staleMsg -ErrorAction SilentlyContinue'
$out += '        exit 42'
$out += '    }'
$out += ''
$out += "Why `-ErrorAction SilentlyContinue` is needed: the file sets ``$ErrorActionPreference = 'Stop'`` at the top,"
$out += 'which converts `Write-Error` into a terminating error and overrides the explicit `exit 42` (the script'
$out += 'would exit with code 1 instead). `-ErrorAction SilentlyContinue` on the Write-Error call keeps the'
$out += 'stderr message visible while letting control flow reach `exit 42`.'

$out -join "`n" | Out-File -FilePath 'D:\AIOS\aios_tasks\aios_vnext\evidence\T0003_launcher_diff.txt' -Encoding UTF8
Write-Output 'Diff file written.'
Get-Content 'D:\AIOS\aios_tasks\aios_vnext\evidence\T0003_launcher_diff.txt'