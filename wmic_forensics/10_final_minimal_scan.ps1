# Phase 6 - minimal final scan
$roots = @(
    'D:\1', 'D:\demo', 'D:\Tools',
    'C:\Users\xinzh\.openclaw', 'C:\Users\xinzh\.codebuddy',
    'C:\Users\xinzh\.workbuddy', 'C:\Users\xinzh\.claude',
    'D:\个人文件\AI\Operator'
)
$out = @()
foreach ($r in $roots) {
    if (-not (Test-Path $r)) { continue }
    $files = Get-ChildItem -Path $r -Recurse -File -Include '*.ps1','*.bat','*.cmd','*.py','*.vbs' -ErrorAction SilentlyContinue
    foreach ($f in $files) {
        try {
            $c = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
            if ($c -match 'wmic\.exe|\bwmic\s+(os|cpu|process|service|disk|memory|nic|bios)') {
                $out += [pscustomobject]@{
                    File = $f.FullName
                    Modified = $f.LastWriteTime
                    Match = ([regex]::Match($c, '.{0,60}wmic.{0,60}').Value).Trim()
                }
            }
        } catch {}
    }
}
$out | Export-Csv "D:\AIOS\wmic_forensics\evidence\26_final_wmic_callers.csv" -NoTypeInformation -Encoding UTF8
Write-Host "FOUND: $($out.Count) post-cure wmic callers"
foreach ($x in $out) { Write-Host "  $($x.File) [$($x.Modified)]  $($x.Match)" }

# Also dump current date/time
Get-Date -Format 'yyyy-MM-dd HH:mm:ss' | Write-Host