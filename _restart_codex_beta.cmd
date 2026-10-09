@echo off
chcp 65001 >nul
echo === Killing any stale codex/ChatGPT procs ===
taskkill /F /IM codex.exe 2>nul
taskkill /F /IM ChatGPT.exe 2>nul
echo === Clearing stale Codex locks ===
del /q /f "C:\Users\xinzh\AppData\Local\Packages\OpenAI.CodexBeta_2p2nqsd0c76g0\Settings\roaming.lock" 2>nul
del /q /f "C:\Users\xinzh\AppData\Local\Packages\OpenAI.CodexBeta_2p2nqsd0c76g0\AC\INetCache\*" 2>nul
echo === Launching Codex Beta via AUMID ===
start "" "shell:AppsFolder\OpenAI.CodexBeta_2p2nqsd0c76g0!OpenAI.CodexBeta"
echo === Launch issued, waiting 10s ===
ping -n 11 127.0.0.1 >nul
echo === Post state ===
tasklist /NH /FI "IMAGENAME eq ChatGPT.exe" 2>nul | find /c "ChatGPT.exe"
tasklist /NH /FI "IMAGENAME eq codex.exe" 2>nul | find /c "codex.exe"