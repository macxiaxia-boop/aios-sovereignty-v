@echo off
chcp 65001 >nul
echo === Kill Code.exe (keep main 31952) ===
taskkill /F /IM Code.exe /FI "PID ne 31952"
echo === Kill ChatGPT.exe ===
taskkill /F /IM ChatGPT.exe
echo === DONE ===