# AIOS Sovereignty Reconciler · 启动钩 (T7 设计)
# 每次 PowerShell 启动时, 自动跑一次 reconcile
# 注入方式 (user 手动执行一次): Add-Content -Path $PROFILE -Value '. D:\AIOS\kernel\etc\sovereignty\powershell_profile_aios.ps1'

if (-not $Global:AiosSovereigntyReconcilerLoaded) {
    $Global:AiosSovereigntyReconcilerLoaded = $true
    $python = 'D:\AIOS\kernel\.venv\Scripts\python.exe'
    $env:PYTHONPATH = 'D:\AIOS\kernel\src'
    try {
        & $python -m aios_kernel.governance.model_policy.reconciler --mode onstart 2>$null
    } catch {
        # Silent fail in startup hook (don't block user shell)
    }
}
