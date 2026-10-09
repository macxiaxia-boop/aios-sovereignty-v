# Phase-3 helper cleanup correction

Claude Code, read D:\AIOS\_agent-hub\AGENTS.md and memory 2026-10-08/09. Independent inspection found Phase 3 created three ad-hoc helper scripts, which violates the SSOT red line against new ad-hoc patch/debug scripts:
- D:\AIOS\_agent-hub\scripts\_phase3_pre_hashes.py
- D:\AIOS\_agent-hub\scripts\_phase3_move_reversible.py
- D:\AIOS\_agent-hub\scripts\_phase3_evidence_builder.py

Verify each path exists, is within D:\AIOS, and is not referenced by any active loader/runtime before removing only those three newly-created helper files. Do not remove or alter any other script, product code, policy, service, task, backup, or user data. Append the cleanup record to the Phase-3 evidence JSON/Markdown (or write a small correction evidence file), run the 119 strategy tests, and return ACK with exact before/after paths. Do not delete the quarantine manifests/evidence.
