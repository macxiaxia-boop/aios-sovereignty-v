@echo off
REM ============================================================================
REM fix_codex_cli_shim.cmd - R-Codex-Cure-2026-09-29
REM 合并 Codex CLI 双 npm shim: 删 Roaming\npm\codex.cmd (指向错路径)
REM
REM 原理: Codex CLI 有 2 套 npm shim:
REM   C:\Users\xinzh\AppData\Roaming\npm\codex.cmd  -> 调用 D:\npm-global\codex.ps1 (9月28日)
REM   D:\npm-global\codex.cmd                       -> 调用 node + @openai/codex/bin/codex.js (9月19日)
REM 双 shim 互相干扰, where codex 显示 4 个结果. 保留 D:\npm-global\codex.cmd
REM
REM 用法: 双击运行 (不需要管理员)
REM ============================================================================
chcp 65001 >nul 2>&1
setlocal EnableExtensions

set "OLD_SHIM=%APPDATA%\npm\codex.cmd"
set "OLD_PS1=%APPDATA%\npm\codex.ps1"
set "NEW_SHIM=D:\npm-global\codex.cmd"

echo.
echo ============================================================
echo  合并 Codex CLI 双 npm shim
echo ============================================================
echo.

echo [1/3] 当前 PATH 里有几个 codex:
where codex 2>&1

echo.
echo [2/3] 保留 %NEW_SHIM% (D:\npm-global), 删 Roaming 旧 shim ...
if exist "%OLD_SHIM%" (
    move /Y "%OLD_SHIM%" "%OLD_SHIM%.bak-rcodex-cure" >nul
    echo   备份 %OLD_SHIM% -> %OLD_SHIM%.bak-rcodex-cure
)
if exist "%OLD_PS1%" (
    move /Y "%OLD_PS1%" "%OLD_PS1%.bak-rcodex-cure" >nul
    echo   备份 %OLD_PS1% -> %OLD_PS1%.bak-rcodex-cure
)

echo.
echo [3/3] 现在 PATH 里 codex 简化到 ...
where codex 2>&1

echo.
echo ============================================================
echo  完成. Codex CLI 调用统一走 %NEW_SHIM%
echo ============================================================
echo.
pause