# sync-from-hub.ps1 - Sync hub content to all agents
#
# Effect: copies files from D:\AIOS\_agent-hub\ to each agent's config dir.
#         This is the FALLBACK for when file symlinks can't be created
#         (PowerShell 5.1 / sandbox / non-admin / non-dev-mode).
#
# Coverage: workbuddy / codex / claudecode (3 agents)
# Not covered: Hermes (own FTS5), OpenClaw (TBD)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -NoProfile -File D:\AIOS\_agent-hub\sync-from-hub.ps1
#   Or double-click.
#
# Workflow:
#   1. Edit a file in D:\AIOS\_agent-hub\ (e.g. AGENTS.md)
#   2. Run this script
#   3. All 3 agents' config dirs get the new content
#
# Compare with: install-links.ps1 (one-time junction setup, ideal but blocked by sandbox)

$HUB = "D:\AIOS\_agent-hub"

# Map: source file in hub -> list of destinations
$syncMap = @(
    @{ Source = "$HUB\SOUL.md";   Dests = @("C:\Users\xinzh\.workbuddy\SOUL.md", "C:\Users\xinzh\.workbuddy\IDENTITY.md") },
    @{ Source = "$HUB\USER.md";   Dests = @("C:\Users\xinzh\.workbuddy\USER.md") },
    @{ Source = "$HUB\MEMORY.md"; Dests = @("C:\Users\xinzh\.workbuddy\MEMORY.md") },
    @{ Source = "$HUB\AGENTS.md"; Dests = @("C:\Users\xinzh\.codex\AGENTS.md") },
    @{ Source = "$HUB\CLAUDE.md"; Dests = @("C:\Users\xinzh\.claude\CLAUDE.md") }
)

# Memory directory: mirror (file-by-file copy of *.md)
$hubMemDir = "$HUB\memory"
$destMemDir = "C:\Users\xinzh\.workbuddy\memory"

function Write-OK   { param($m) Write-Host "  [OK]    $m" -ForegroundColor Green }
function Write-MISS { param($m) Write-Host "  [MISS]  $m" -ForegroundColor Red }
function Write-WARN { param($m) Write-Host "  [WARN]  $m" -ForegroundColor Yellow }
function Write-INFO { param($m) Write-Host "  [INFO]  $m" -ForegroundColor Cyan }

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Hub -> Agents Sync (fallback mode)" -ForegroundColor Cyan
Write-Host "  Hub: $HUB" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path $HUB)) {
    Write-MISS "Hub not found: $HUB"
    exit 1
}
Write-OK "Hub exists: $HUB"

# File-level sync
foreach ($entry in $syncMap) {
    $src = $entry.Source
    if (-not (Test-Path $src)) {
        Write-MISS "Hub source missing: $src"
        continue
    }
    foreach ($dst in $entry.Dests) {
        $parent = Split-Path $dst -Parent
        if (-not (Test-Path $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        # Backup existing
        if (Test-Path $dst) {
            $bak = "$dst.bak"
            if (Test-Path $bak) { Remove-Item $bak -Force -ErrorAction SilentlyContinue }
            # Don't backup if it's already a .bak itself or junction
            try {
                Copy-Item $dst $bak -Force -ErrorAction SilentlyContinue
            } catch {}
        }
        # Copy
        try {
            Copy-Item $src $dst -Force
            $size = (Get-Item $dst -Force).Length
            Write-OK ("Copied: " + (Split-Path $dst -Leaf) + " (" + $size + " bytes)")
        } catch {
            Write-MISS ("Copy failed: " + $dst + " - " + $_)
        }
    }
}

# Memory directory mirror
Write-Host ""
Write-INFO "Syncing memory/ directory..."
if (-not (Test-Path $hubMemDir)) {
    New-Item -ItemType Directory -Path $hubMemDir -Force | Out-Null
    Write-OK "Created hub memory dir"
}
if (-not (Test-Path $destMemDir)) {
    New-Item -ItemType Directory -Path $destMemDir -Force | Out-Null
    Write-OK "Created workbuddy memory dir"
}

# Mirror: copy all .md files from hub to dest, do not delete extra files in dest
Get-ChildItem $hubMemDir -Filter "*.md" -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $dst = Join-Path $destMemDir $_.Name
    Copy-Item $_.FullName $dst -Force
    Write-OK ("Memory: " + $_.Name)
}

# Also include the system-generated GUID file if it exists in dest
$sysFile = Get-ChildItem $destMemDir -Filter "*_memory.md" -Force -ErrorAction SilentlyContinue
if ($sysFile) {
    foreach ($sf in $sysFile) {
        $hubCopy = Join-Path $hubMemDir $sf.Name
        if (-not (Test-Path $hubCopy)) {
            Copy-Item $sf.FullName $hubCopy -Force
            Write-OK ("Memory -> hub: " + $sf.Name + " (system file preserved)")
        }
    }
}

# Final verification
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  VERIFICATION (post-sync)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$verifyPaths = @(
    "C:\Users\xinzh\.workbuddy\SOUL.md",
    "C:\Users\xinzh\.workbuddy\USER.md",
    "C:\Users\xinzh\.workbuddy\MEMORY.md",
    "C:\Users\xinzh\.workbuddy\IDENTITY.md",
    "C:\Users\xinzh\.codex\AGENTS.md",
    "C:\Users\xinzh\.claude\CLAUDE.md"
)
foreach ($p in $verifyPaths) {
    if (Test-Path $p) {
        $i = Get-Item $p -Force
        $firstLine = (Get-Content $p -TotalCount 1 -ErrorAction SilentlyContinue)
        Write-OK ("  " + $p + " [" + $i.Length + " bytes]  first: " + $firstLine)
    } else {
        Write-MISS ("  " + $p)
    }
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  DONE" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "All agents now have latest hub content."
Write-Host ""
Write-Host "Workflow reminder:"
Write-Host "  1. Edit any file in $HUB"
Write-Host "  2. Run this script"
Write-Host "  3. All 3 agents see the change on next session"
Write-Host ""
