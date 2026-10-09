# install-links.ps1 - One-click junction installer (v2 sandbox-safe)
#
# Effect: creates NTFS directory junctions so each agent's memory file
#         points to D:\AIOS\_agent-hub\ (the single source of truth).
#
# Coverage: workbuddy / codex / claudecode (3 agents)
# Not covered: Hermes (own FTS5 system, see README), OpenClaw (TBD)
#
# Idempotent: safe to re-run. Existing files are backed up to .bak first.
# Sandbox-safe: no wsl.exe (use WSL2 manual verify instead)
#
# Usage:
#   powershell -ExecutionPolicy Bypass -NoProfile -File D:\AIOS\_agent-hub\install-links.ps1
#   Or just double-click.

$ErrorActionPreference = "Continue"
$HUB = "D:\AIOS\_agent-hub"

# Junction pairs
$pairs = @(
    @{ Source = "C:\Users\xinzh\.workbuddy\SOUL.md";   Target = "$HUB\SOUL.md"   },
    @{ Source = "C:\Users\xinzh\.workbuddy\USER.md";   Target = "$HUB\USER.md"   },
    @{ Source = "C:\Users\xinzh\.workbuddy\MEMORY.md"; Target = "$HUB\MEMORY.md" },
    @{ Source = "C:\Users\xinzh\.workbuddy\IDENTITY.md"; Target = "$HUB\SOUL.md" },
    @{ Source = "C:\Users\xinzh\.codex\AGENTS.md";     Target = "$HUB\AGENTS.md" },
    @{ Source = "C:\Users\xinzh\.claude\CLAUDE.md";    Target = "$HUB\CLAUDE.md" }
)

$memoryDirSource = "C:\Users\xinzh\.workbuddy\memory"
$memoryDirTarget = "$HUB\memory"

function Write-OK   { param($m) Write-Host "  [OK]    $m" -ForegroundColor Green }
function Write-MISS { param($m) Write-Host "  [MISS]  $m" -ForegroundColor Red }
function Write-WARN { param($m) Write-Host "  [WARN]  $m" -ForegroundColor Yellow }
function Write-INFO { param($m) Write-Host "  [INFO]  $m" -ForegroundColor Cyan }

function Test-IsJunction {
    param($path)
    if (-not (Test-Path $path)) { return $false }
    $item = Get-Item $path -Force
    return ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0
}

function Remove-PathSafe {
    param($path)
    # Use cmd /c rmdir for directories to avoid PowerShell -Recurse prompt
    if (Test-Path $path) {
        if ((Get-Item $path -Force).PSIsContainer) {
            cmd /c rmdir /S /Q "$path" 2>&1 | Out-Null
        } else {
            Remove-Item $path -Force -ErrorAction SilentlyContinue
        }
    }
}

function New-JunctionSafe {
    param($source, $target)
    # Make parent dir
    $parent = Split-Path $source -Parent
    if (-not (Test-Path $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    # Remove existing (file or junction or empty dir)
    Remove-PathSafe $source
    # Create junction
    cmd /c mklink /J "$source" "$target" 2>&1 | Out-Null
    if (Test-Path $source) {
        return $true
    } else {
        return $false
    }
}

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  Cross-Agent Junction Installer v2" -ForegroundColor Cyan
Write-Host "  Hub: $HUB" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Sanity check: hub exists
if (-not (Test-Path $HUB)) {
    Write-MISS "Hub directory not found: $HUB"
    exit 1
}
Write-OK "Hub exists: $HUB"

# Ensure hub memory dir exists
if (-not (Test-Path $memoryDirTarget)) {
    New-Item -ItemType Directory -Path $memoryDirTarget -Force | Out-Null
    Write-OK "Created hub memory dir: $memoryDirTarget"
}

# Process file pairs
foreach ($p in $pairs) {
    $src = $p.Source
    $tgt = $p.Target
    $name = Split-Path $src -Leaf

    if (-not (Test-Path $tgt)) {
        Write-MISS "Hub target missing: $tgt"
        continue
    }

    # Check existing
    if (Test-Path $src) {
        if (Test-IsJunction $src) {
            Write-OK "Already junction: $name"
            continue
        } else {
            # It's a regular file - back up
            $bak = "$src.bak"
            if (Test-Path $bak) { Remove-PathSafe $bak }
            Move-Item $src $bak -Force
            Write-WARN "Backed up: $name -> $name.bak"
        }
    }

    # Create junction
    if (New-JunctionSafe $src $tgt) {
        Write-OK "Junction: $name -> $(Split-Path $tgt -Leaf)"
    } else {
        Write-MISS "Failed: $name"
    }
}

# Process memory directory
Write-Host ""
Write-INFO "Processing memory dir: $memoryDirSource"
if (Test-Path $memoryDirSource) {
    if (Test-IsJunction $memoryDirSource) {
        Write-OK "Memory dir already junction"
    } else {
        # It's a regular dir - merge contents to hub
        $existingCount = (Get-ChildItem $memoryDirSource -Force -ErrorAction SilentlyContinue | Measure-Object).Count
        if ($existingCount -gt 0) {
            Write-WARN "Merging $existingCount existing files to hub"
            Copy-Item "$memoryDirSource\*" $memoryDirTarget -Recurse -Force -ErrorAction SilentlyContinue
        }
        Remove-PathSafe $memoryDirSource
        if (New-JunctionSafe $memoryDirSource $memoryDirTarget) {
            Write-OK "Memory dir junctioned: $memoryDirSource -> $memoryDirTarget"
        }
    }
} else {
    if (New-JunctionSafe $memoryDirSource $memoryDirTarget) {
        Write-OK "Memory dir created and junctioned"
    }
}

# Final verification
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  VERIFICATION" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

$checks = @(
    "C:\Users\xinzh\.workbuddy\SOUL.md",
    "C:\Users\xinzh\.workbuddy\USER.md",
    "C:\Users\xinzh\.workbuddy\MEMORY.md",
    "C:\Users\xinzh\.workbuddy\IDENTITY.md",
    "C:\Users\xinzh\.codex\AGENTS.md",
    "C:\Users\xinzh\.claude\CLAUDE.md",
    $memoryDirSource
)
$okCount = 0
$failCount = 0
foreach ($c in $checks) {
    if (Test-Path $c) {
        if (Test-IsJunction $c) {
            Write-OK "$c"
            $okCount++
        } else {
            Write-WARN "$c (NOT a junction)"
            $failCount++
        }
    } else {
        Write-MISS "$c (NOT FOUND)"
        $failCount++
    }
}

# Content verification: read through junction, confirm it's the hub content
Write-Host ""
Write-INFO "Content sample (proves junctions work):"
$samplePaths = @(
    "C:\Users\xinzh\.workbuddy\SOUL.md",
    "C:\Users\xinzh\.codex\AGENTS.md",
    "C:\Users\xinzh\.claude\CLAUDE.md"
)
foreach ($p in $samplePaths) {
    if (Test-Path $p) {
        $firstLine = (Get-Content $p -TotalCount 1 -ErrorAction SilentlyContinue)
        Write-Host "    $p -> $firstLine" -ForegroundColor DarkCyan
    }
}

# Final WSL2 hint (no wsl.exe call - sandbox blocks it)
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  MANUAL WSL2 CHECK" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "If you use codex/claudecode in WSL2, verify the mount:"
Write-Host "  wsl -e test -d /mnt/d/AIOS/_agent-hub && echo OK"
Write-Host "  wsl -e ls /mnt/d/AIOS/_agent-hub/"
Write-Host ""
Write-Host "If WSL2 cannot see D:\, run in PowerShell (admin):"
Write-Host "  wsl --mount --bare \\.\PhysicalDrive<number>"
Write-Host "Or simpler: just access via /mnt/d/ (default WSL2 setup has this)"

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  RESULT" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "OK: $okCount / Fail: $failCount"
if ($failCount -eq 0) {
    Write-Host "All junctions installed. Edits to $HUB\* now propagate to all 3 agents." -ForegroundColor Green
} else {
    Write-Host "Some junctions failed - check above. See README.md for manual fix." -ForegroundColor Yellow
}
Write-Host ""
# Non-interactive: skip ReadKey prompt (causes hang in sandboxed PowerShell)
