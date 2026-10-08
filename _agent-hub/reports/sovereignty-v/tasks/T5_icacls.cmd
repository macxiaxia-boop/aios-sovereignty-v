@echo off
REM T5 icacls close-out (avoid bash parsing of (R))
icacls "D:\AIOS\_agent-hub\policy\model-policy.v1.yaml" /inheritance:r /grant:r %USERNAME%:(R)
echo --- READBACK ---
icacls "D:\AIOS\_agent-hub\policy\model-policy.v1.yaml"
