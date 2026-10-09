# uninstall_wetype.ps1 - R277 立 (2026-09-29)
# 一键卸载微信输入法 (WeType) - PowerShell 版本
# 用法: 右键 "以 PowerShell 管理员身份运行"
$ErrorActionPreference = 'Stop'

Write-Host '============================================================'
Write-Host '  微信输入法 (WeType) 一键卸载 (R277)'
Write-Host '============================================================'
Write-Host ''

# 1. 检查 Uninstall.exe
$uninstaller = 'C:\Program Files\Tencent\WeType\2.1.4.6\Uninstall.exe'
if (-not (Test-Path $uninstaller)) {
    Write-Host "[1/4] Uninstall.exe 不存在: $uninstaller" -ForegroundColor Yellow
    Write-Host '      微信输入法可能已经卸载, 跳过' -ForegroundColor Yellow
} else {
    Write-Host "[1/4] Uninstall.exe 存在: $uninstaller" -ForegroundColor Green

    # 2. InstallShield 静默卸载 /S
    Write-Host '[2/4] 启动 InstallShield 静默卸载...'
    $p = Start-Process -FilePath $uninstaller -ArgumentList '/S','-silent' -PassThru -Wait -NoNewWindow -ErrorAction SilentlyContinue
    if ($p.ExitCode -eq 0) {
        Write-Host '      ✓ InstallShield /S 卸载成功' -ForegroundColor Green
    } else {
        Write-Host "      ⚠ InstallShield ExitCode=$($p.ExitCode), 尝试其他方法" -ForegroundColor Yellow

        # 3. 查 MSI product code + msiexec /x
        $uninst = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\*' -EA SilentlyContinue |
                  Where-Object { $_.DisplayName -eq '微信输入法' } |
                  Select-Object -First 1 -ExpandProperty UninstallString
        if ($uninst -match '\{([A-F0-9-]+)\}') {
            $msiGuid = $matches[1]
            Write-Host "[3/4] msiexec /x 卸载 MSI GUID: {$msiGuid}"
            $p2 = Start-Process -FilePath 'msiexec.exe' -ArgumentList '/x',"{$msiGuid}",'/quiet','/norestart' -PassThru -Wait -NoNewWindow -ErrorAction SilentlyContinue
            if ($p2.ExitCode -eq 0) {
                Write-Host '      ✓ msiexec 卸载成功' -ForegroundColor Green
            } else {
                Write-Host "      ⚠ msiexec ExitCode=$($p2.ExitCode)" -ForegroundColor Yellow
            }
        }
    }
}

# 4. 兜底: 杀所有 wetype 进程 + 删目录
Write-Host '[4/4] 兜底清理 (杀进程 + 删目录)...'
Get-Process -Name 'wetype_*' -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2
$still = Get-Process -Name 'wetype_*' -ErrorAction SilentlyContinue
if ($still.Count -eq 0) {
    Write-Host '      ✓ 所有 wetype_* 进程已停止' -ForegroundColor Green
} else {
    Write-Host "      ⚠ 还有 $($still.Count) 个 wetype_* 进程" -ForegroundColor Yellow
}

$dir = 'C:\Program Files\Tencent\WeType'
if (Test-Path $dir) {
    Write-Host "      手动删目录: $dir"
    Write-Host "      命令: rmdir /s /q `"$dir`"" -ForegroundColor Cyan
} else {
    Write-Host '      ✓ WeType 目录已删除' -ForegroundColor Green
}

# 5. 注册表残留清理
$paths = @(
    'HKLM:\SOFTWARE\Tencent\WeType',
    'HKLM:\SOFTWARE\WOW6432Node\Tencent\WeType'
)
foreach ($p in $paths) {
    if (Test-Path $p) {
        Write-Host "      注册表残留: $p (手动删除: Remove-Item '$p' -Recurse)"
    }
}

Write-Host ''
Write-Host '============================================================'
Write-Host '  卸载完成 (或手动执行上述剩余步骤)' -ForegroundColor Green
Write-Host '  - 微软拼音 (系统自带) 自动接管中文输入'
Write-Host '  - 弹窗治理永久生效 (wetype_* 不再是死循环)'
Write-Host '============================================================'
Read-Host '按 Enter 退出'
