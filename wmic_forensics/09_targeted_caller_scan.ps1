# Phase 5 - Targeted wmic caller scan (post R260-Wmic cure)
# Skip D:\AIOS (already replaced per R260-Wmic)
# Focus on: openclaw, codebuddy, workbuddy, demo, user dirs

$outDir = "D:\AIOS\wmic_forensics"
$evidenceDir = "$outDir\evidence"

Write-Host "=== PHASE 5: TARGETED WMIC CALLER SCAN (POST R260-CURE) ===" -ForegroundColor Cyan

$targets = @(
    @{ Root='D:\1'; Note='User root scripts' },
    @{ Root='D:\demo'; Note='Demo scripts' },
    @{ Root='D:\Tools'; Note='Tools' },
    @{ Root='C:\Users\xinzh\.openclaw'; Note='OpenClaw' },
    @{ Root='C:\Users\xinzh\.codebuddy'; Note='CodeBuddy' },
    @{ Root='C:\Users\xinzh\.workbuddy'; Note='WorkBuddy' },
    @{ Root='C:\Users\xinzh\.claude'; Note='Claude Code' },
    @{ Root='C:\Users\xinzh\.codex'; Note='Codex CLI' },
    @{ Root='D:\个人文件\AI\Operator'; Note='Operator' },
    @{ Root='D:\个人文件\AI\CloudTech'; Note='CloudTech' }
)

$findings = @()
foreach ($t in $targets) {
    $root = $t.Root
    if (-not (Test-Path $root)) { Write-Host "  skip $($t.Note) ($root - not exists)"; continue }
    Write-Host "  scanning $($t.Note) ($root) ..."
    try {
        Get-ChildItem -Path $root -Recurse -File -Include '*.ps1','*.psm1','*.bat','*.cmd','*.py','*.js','*.ts','*.vbs' -ErrorAction SilentlyContinue | ForEach-Object {
            try {
                $content = Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue
                if ($content -match 'wmic\.exe|\bwmic\s+(os|cpu|process|service|disk|memory|nic|bios|baseboard|computersystem|product)') {
                    $findings += [pscustomobject]@{
                        Repository = $t.Note
                        File = $_.FullName
                        Modified = $_.LastWriteTime
                        Size = $_.Length
                        Match = ([regex]::Match($content, '.{0,80}wmic.{0,80}').Value).Trim()
                    }
                }
            } catch {}
        }
    } catch {}
}
$findings | Export-Csv "$evidenceDir\24_post_curse_wmic_callers.csv" -NoTypeInformation -Encoding UTF8
Write-Host "`n  *** POST-CURE REMAINING WMIC CALLERS: $($findings.Count) ***" -ForegroundColor Magenta
foreach ($f in $findings) {
    Write-Host "    [$($f.Repository)] $($f.File)"
    Write-Host "      [$($f.Modified)] $($f.Match)"
}

# 7. Check Scheduled Tasks arguments (deep)
Write-Host "`n--- Scheduled Tasks arg search ---" -ForegroundColor Yellow
Get-ScheduledTask | ForEach-Object {
    $t = $_
    foreach ($a in $t.Actions) {
        if ($a.Arguments -match 'wmic' -or $a.Execute -match 'wmic') {
            [pscustomobject]@{
                TaskName = $t.TaskName
                TaskPath = $t.TaskPath
                State = $t.State
                Execute = $a.Execute
                Arguments = $a.Arguments
            }
        }
    }
} | Export-Csv "$evidenceDir\25_tasks_wmic_arg.csv" -NoTypeInformation -Encoding UTF8

Write-Host "`n=== PHASE 5 COMPLETE ===" -ForegroundColor Cyan