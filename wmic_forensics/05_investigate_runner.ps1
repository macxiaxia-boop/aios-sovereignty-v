# Find who is running the wmic_min.txt scanner
# Check PowerShell profiles + check file mtime + check startup scripts content

Write-Host "=== 1. PowerShell profile locations ===" -ForegroundColor Cyan
Write-Host "AllUsersAllHosts: $PROFILE.AllUsersAllHosts"
Write-Host "AllUsersCurrentHost: $PROFILE.AllUsersCurrentHost"
Write-Host "CurrentUserAllHosts: $PROFILE.CurrentUserAllHosts"
Write-Host "CurrentUserCurrentHost: $PROFILE.CurrentUserCurrentHost"

Write-Host "`n=== 2. wmic_min.txt details ===" -ForegroundColor Cyan
$minFile = "$env:USERPROFILE\wmic_min.txt"
if (Test-Path $minFile) {
    $info = Get-Item $minFile
    Write-Host "Path: $($info.FullName)"
    Write-Host "LastWriteTime: $($info.LastWriteTime)"
    Write-Host "Size: $($info.Length)"
} else {
    Write-Host "Not found"
}

Write-Host "`n=== 3. All profiles content ===" -ForegroundColor Cyan
foreach ($p in @($PROFILE.AllUsersAllHosts, $PROFILE.AllUsersCurrentHost, $PROFILE.CurrentUserAllHosts, $PROFILE.CurrentUserCurrentHost)) {
    Write-Host "`n--- $p ---"
    if (Test-Path $p) {
        Write-Host "[EXISTS]"
        Get-Content $p | Select-Object -First 50 | ForEach-Object { Write-Host "  $_" }
    } else {
        Write-Host "[not exists]"
    }
}

Write-Host "`n=== 4. Content scan of all Startup files for wmic ===" -ForegroundColor Cyan
$startup = [Environment]::GetFolderPath('Startup')
$startupFiles = Get-ChildItem -Path $startup -File -ErrorAction SilentlyContinue
foreach ($f in $startupFiles) {
    Write-Host "`n--- $($f.Name) ---"
    $content = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
    if ($content -match 'wmic') {
        Write-Host "*** WMIC REFERENCE FOUND ***" -ForegroundColor Red
        $content | Select-String -Pattern 'wmic' -AllMatches | Select-Object -First 5 | ForEach-Object { Write-Host "  $($_.Line.Trim())" }
    } else {
        Write-Host "  [no wmic reference]"
    }
}

Write-Host "`n=== 5. Search for wmic_min.txt reference in all Startup + auto-import ===" -ForegroundColor Cyan
$searchDirs = @($startup, "$env:USERPROFILE\Documents\PowerShell", "$env:USERPROFILE\Documents\WindowsPowerShell", "C:\Windows\System32\WindowsPowerShell\v1.0")
foreach ($d in $searchDirs) {
    if (Test-Path $d) {
        Write-Host "  scanning $d ..."
        $hits = Get-ChildItem -Path $d -Recurse -File -ErrorAction SilentlyContinue |
            Select-String -Pattern 'wmic_min\.txt|SAFE_DELETE_FAIL_CLOSED|CODEBUDDY_SAFE_DELETE_PS_READY' -ErrorAction SilentlyContinue
        foreach ($h in $hits) {
            Write-Host "    HIT: $($h.Path):$($h.LineNumber) - $($h.Line.Trim().Substring(0, [Math]::Min(150, $h.Line.Trim().Length)))"
        }
    }
}

Write-Host "`n=== 6. PSReadLine / ConsoleHost startup ===" -ForegroundColor Cyan
Get-ChildItem -Path "$env:USERPROFILE\AppData\Roaming\Microsoft\Windows\PowerShell\PSReadLine" -ErrorAction SilentlyContinue | Select-Object Name, LastWriteTime | Format-Table -AutoSize

Write-Host "`n=== 7. PSModulePath modules with safe-delete wmic ===" -ForegroundColor Cyan
$psm = $env:PSModulePath -split ';'
foreach ($p in $psm) {
    if (Test-Path $p) {
        $hits = Get-ChildItem -Path $p -Recurse -File -Include '*.ps1','*.psm1' -ErrorAction SilentlyContinue |
            Select-String -Pattern 'wmic_min\.txt|SAFE_DELETE_FAIL_CLOSED' -ErrorAction SilentlyContinue
        foreach ($h in $hits) {
            Write-Host "  HIT: $($h.Path):$($h.LineNumber)"
        }
    }
}