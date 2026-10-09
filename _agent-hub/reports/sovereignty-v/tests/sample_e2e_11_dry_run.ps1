# Sample E2E draft · 端到端 11 · Reconciler dry-run
$ErrorActionPreference = "Stop"
Write-Host "=== E2E 11 · Dry-run reconcile ===" -ForegroundColor Cyan

$python = "D:\AIOS\kernel\.venv\Scripts\python.exe"

# A) Backup
$backupDir = "D:\AIOS\_agent-hub\reports\sovereignty-v\tests\e2e_11_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
Copy-Item "$env:USERPROFILE\.cc-switch\cc-switch.db" "$backupDir\cc-switch.db"
Copy-Item "$env:USERPROFILE\.openclaw\state\openclaw.sqlite" "$backupDir\openclaw.sqlite"

# B) Dry-run
& $python -m aios_kernel.governance.model_policy.reconciler --mode scheduled --dry-run 2>&1 |
    Tee-Object "$backupDir\dry-run.log"

# C) Verify NO writes happened
$currentMd5 = (Get-FileHash "$env:USERPROFILE\.cc-switch\cc-switch.db" -Algorithm MD5).Hash
$backupMd5 = (Get-FileHash "$backupDir\cc-switch.db" -Algorithm MD5).Hash
if ($currentMd5 -ne $backupMd5) {
    Write-Host "FAILED — dry-run wrote to cc-switch.db" -ForegroundColor Red
    Copy-Item "$backupDir\cc-switch.db" "$env:USERPROFILE\.cc-switch\cc-switch.db" -Force
    exit 1
}
Write-Host "PASS — dry-run read-only verified" -ForegroundColor Green
exit 0
