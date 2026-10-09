# Self-elevate to admin and stop CloudTech V22 Gateway
# Triggered by Codex 01a11c23 via UAC
$ErrorActionPreference = 'Stop'

Write-Host "[1/4] Verifying admin..." -ForegroundColor Cyan
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "FATAL: not admin, UAC denied" -ForegroundColor Red
    exit 1
}
Write-Host "  admin OK" -ForegroundColor Green

Write-Host "[2/4] Stopping Windows service cloudtech-v22-gateway..." -ForegroundColor Cyan
Stop-Service -Name 'cloudtech-v22-gateway' -Force -ErrorAction Continue
Set-Service -Name 'cloudtech-v22-gateway' -StartupType Disabled
Write-Host "  service stop+disable attempted" -ForegroundColor Green

Write-Host "[3/4] Killing cloudtech processes..." -ForegroundColor Cyan
Get-Process -Name 'cloudtech_v22_gateway' -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process -Name 'python' -ErrorAction SilentlyContinue | Where-Object {
    $parent = (Get-CimInstance Win32_Process -Filter "ProcessId=$($_.Id)" -ErrorAction SilentlyContinue).ParentProcessId
    $parentProc = Get-CimInstance Win32_Process -Filter "ProcessId=$parent" -ErrorAction SilentlyContinue
    $parentProc.Name -match 'cloudtech' -or $parentProc.CommandLine -match 'cloud'
} | Stop-Process -Force -ErrorAction SilentlyContinue
taskkill /F /IM cloudtech_v22_gateway.exe 2>&1 | Out-Null
Write-Host "  processes kill attempted" -ForegroundColor Green

Write-Host "[4/4] Verifying port 5099 closed..." -ForegroundColor Cyan
Start-Sleep -Seconds 3
$port5099 = Get-NetTCPConnection -LocalPort 5099 -State Listen -ErrorAction SilentlyContinue
if ($port5099) {
    Write-Host "  port 5099 STILL LISTENING (PID $($port5099.OwningProcess))" -ForegroundColor Red
    Write-Host "  Reboot may be required" -ForegroundColor Yellow
    exit 2
} else {
    Write-Host "  port 5099 CLOSED ✓" -ForegroundColor Green
    exit 0
}
