# Phase 4 - Final caller scan: search ALL code/config/scripts for direct wmic.exe calls
# Goal: find any remaining wmic caller that survived R260-Wmic replacement

$outDir = "D:\AIOS\wmic_forensics"
$evidenceDir = "$outDir\evidence"

Write-Host "=== PHASE 4: FULL WMIC CALLER SCAN ===" -ForegroundColor Cyan

# 1. Definite wmic.exe invocation search across drives
Write-Host "`n--- 1. Definite wmic.exe callsite search ---" -ForegroundColor Yellow
$searchRoots = @(
    'D:\AIOS',
    'D:\Tools',
    'D:\1',
    'D:\demo',
    'C:\Users\xinzh\.openclaw',
    'C:\Users\xinzh\.codebuddy',
    'C:\Users\xinzh\.claude',
    'C:\Users\xinzh\.codex',
    'D:\个人文件\AI\Operator',
    'C:\Windows\System32\Tasks',
    'C:\Windows\System32\wbem' # skip wmic itself
)

$definiteWmic = @()
foreach ($root in $searchRoots) {
    if (-not (Test-Path $root)) { continue }
    Write-Host "  scanning $root ..."
    try {
        $files = Get-ChildItem -Path $root -Recurse -File -Include '*.ps1','*.psm1','*.bat','*.cmd','*.py','*.js','*.ts','*.vbs','*.json','*.yaml','*.yml','*.xml','*.ini' -ErrorAction SilentlyContinue
        foreach ($f in $files) {
            try {
                $content = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
                # Match direct wmic.exe or wmic with arguments (not just the word "wmic")
                if ($content -match 'wmic\.exe' -or $content -match 'wmic\s+(os|cpu|process|service|disk|memory|nic|bios|baseboard|computersystem)') {
                    $definiteWmic += [PSCustomObject]@{
                        File = $f.FullName
                        LastModified = $f.LastWriteTime
                        Size = $f.Length
                    }
                }
            } catch {}
        }
    } catch {}
}
$definiteWmic | Export-Csv "$evidenceDir\19_definite_wmic_callers.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Definite wmic.exe callers: $($definiteWmic.Count)"
foreach ($d in $definiteWmic) {
    Write-Host "    $($d.File) [$($d.LastModified)]"
}

# 2. Search winsw XML files
Write-Host "`n--- 2. WinSW XML configs for wmic ---" -ForegroundColor Yellow
$winswXmls = @()
$winswRoots = @('D:\AIOS\daemons_v2\winsw', 'D:\个人文件\AI\Operator\aios_tools\winsw-handoff-watchdog', 'C:\Users\xinzh\.workbuddy')
foreach ($r in $winswRoots) {
    if (Test-Path $r) {
        Get-ChildItem -Path $r -Recurse -File -Filter '*.xml' -ErrorAction SilentlyContinue | ForEach-Object {
            $c = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
            if ($c -match 'wmic') {
                $winswXmls += [PSCustomObject]@{ File = $_.FullName }
            }
        }
    }
}
$winswXmls | Export-Csv "$evidenceDir\20_winsw_wmic.xml.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  WinSW XML with wmic: $($winswXmls.Count)"

# 3. Scheduled Tasks - deep search arguments for wmic.exe or wmic <verb>
Write-Host "`n--- 3. Scheduled Tasks deep search ---" -ForegroundColor Yellow
$tasksDeep = Get-ScheduledTask | ForEach-Object {
    $t = $_
    foreach ($a in $t.Actions) {
        [PSCustomObject]@{
            TaskPath = $t.TaskPath
            TaskName = $t.TaskName
            State = $t.State
            Execute = $a.Execute
            Arguments = $a.Arguments
        }
    }
} | Where-Object {
    $_.Arguments -match 'wmic' -or $_.Execute -match 'wmic'
}
$tasksDeep | Export-Csv "$evidenceDir\21_tasks_with_wmic_args.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Tasks with wmic in arguments: $($tasksDeep.Count)"
foreach ($t in $tasksDeep) {
    Write-Host "    [$($t.TaskName)] $($t.Execute) $($t.Arguments)"
}

# 4. Check user PATH for wmic wrappers
Write-Host "`n--- 4. PATH check for wmic shadowing ---" -ForegroundColor Yellow
$pathDirs = $env:Path -split ';'
foreach ($p in $pathDirs) {
    if ($p -and (Test-Path $p)) {
        $wmic = Get-ChildItem -Path $p -Filter 'wmic*' -ErrorAction SilentlyContinue
        if ($wmic) {
            Write-Host "    PATH[$p] has: $($wmic.Name -join ', ')"
        }
    }
}

# 5. Check user PATH + AIOS for wmic.cmd / wmic.ps1 shadowing
Write-Host "`n--- 5. wmic.cmd / wmic.ps1 shadowing check ---" -ForegroundColor Yellow
$shadowFiles = @()
foreach ($p in $pathDirs) {
    if ($p -and (Test-Path $p)) {
        Get-ChildItem -Path $p -File -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^wmic(\.exe|\.cmd|\.ps1|\.bat)?$' } | ForEach-Object {
            $shadowFiles += [PSCustomObject]@{
                Path = $_.FullName
                Size = $_.Length
                LastModified = $_.LastWriteTime
            }
        }
    }
}
$shadowFiles | Export-Csv "$evidenceDir\22_wmic_shadow_files.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Shadow wmic files in PATH: $($shadowFiles.Count)"

# 6. Service PathName deep search
Write-Host "`n--- 6. Service PathName deep search ---" -ForegroundColor Yellow
$svcWmic = Get-CimInstance Win32_Service | Where-Object { $_.PathName -match 'wmic' }
$svcWmic | Export-Csv "$evidenceDir\23_services_with_wmic.csv" -NoTypeInformation -Encoding UTF8
Write-Host "  Services with wmic in PathName: $($svcWmic.Count)"
foreach ($s in $svcWmic) {
    Write-Host "    $($s.Name): $($s.PathName)"
}

Write-Host "`n=== PHASE 4 COMPLETE ===" -ForegroundColor Cyan
Write-Host "All evidence: $evidenceDir"