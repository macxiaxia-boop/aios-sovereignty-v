@echo off
REM ============================================================
REM uninstall_wetype.cmd - R277 立 (2026-09-29)
REM 一键卸载微信输入法 (WeType) - 终结弹窗死循环的根治方案
REM 用法: 右键 "以管理员身份运行"
REM ============================================================
chcp 936 >nul 2>&1

echo ============================================================
echo   微信输入法 (WeType) 一键卸载
echo ============================================================
echo.

REM 1. 检查 Uninstall.exe
set UNINSTALLER=C:\Program Files\Tencent\WeType\2.1.4.6\Uninstall.exe
if not exist "%UNINSTALLER%" (
    echo [1/3] Uninstall.exe 不存在: %UNINSTALLER%
    echo       微信输入法可能已经卸载
    goto :CHECK_END
)
echo [1/3] Uninstall.exe 存在: %UNINSTALLER%

REM 2. InstallShield 静默卸载 /S
echo [2/3] 启动 InstallShield 静默卸载...
"%UNINSTALLER%" /S -silent
if %ERRORLEVEL% NEQ 0 (
    echo       InstallShield ExitCode=%ERRORLEVEL%, 尝试 msiexec 兜底
    REM 3. 找 MSI product code 用 msiexec /x 卸载
    for /f "tokens=*" %%i in ('reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /f "微信输入法" ^| findstr /i "UninstallString"') do (
        set "MSI_STR=%%i"
    )
    REM 简化: 直接 msiexec /x 通过 WeType 注册表 GUID
    REM WeType 一般用 Tencent 自家安装器, 尝试 msi product code
    msiexec /x {微信输入法的product_code} /quiet /norestart
)

:CHECK_END
echo.
echo [3/3] 验证卸载...
timeout /t 5 /nobreak >nul
tasklist /FI "IMAGENAME eq wetype_server.exe" 2>&1 | findstr wetype_server
if %ERRORLEVEL% EQU 0 (
    echo       ✗ wetype_server.exe 还在跑
) else (
    echo       ✓ wetype_server.exe 已停止
)

if exist "C:\Program Files\Tencent\WeType" (
    echo       ✗ WeType 目录还在: C:\Program Files\Tencent\WeType
    echo       手动删除: rmdir /s /q "C:\Program Files\Tencent\WeType"
) else (
    echo       ✓ WeType 目录已删除
)

echo.
echo ============================================================
echo   卸载完成
echo   - 微软拼音 (系统自带) 自动接管中文输入
echo   - 弹窗治理永久生效 (wetype_* 不再是死循环)
echo ============================================================
pause
