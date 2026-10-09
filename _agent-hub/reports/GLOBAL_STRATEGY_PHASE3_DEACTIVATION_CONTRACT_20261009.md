# Phase-3 reversible deactivation contract — authorized by the user's 2026-10-08/09 retirement command

Claude Code is the executor; Codex independently verifies. Read D:\AIOS\_agent-hub\AGENTS.md and memory 2026-10-08/09. This phase performs only the precise reversible deactivation needed to stop the retired product from running/rearming. Do not delete files, services, tasks, backups, cloud data, personal files, or git history.

## Exact allowlist
1. Stop (do not delete) Windows service `cloudtech-v22-gateway`; set startup to Disabled if permitted. Stop (do not delete) `CloudTechV22Monitor`; set startup Disabled if permitted.
2. Disable (do not unregister/delete) exactly these seven scheduled tasks: `CloudTech_V22Watchdog`, `CloudTech_V23FileWatcher`, `CloudTech\HealthCheck-Hourly`, `CloudTech\DailyReport-0300`, `CloudTech\AIOSLightMonitor-30min`, `CloudTech\StartupCleanup-Once`, `CloudTech\SpecV1CI_Daily_0300`. Do not touch any other task.
3. After verifying resolved absolute paths are inside D:\AIOS, reversibly move `D:\AIOS\cloudtech-saas` and `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py` into `D:\AIOS\_quarantine\retired-assets\20261008\phase3\`, preserving SHA-256 manifest and DO_NOT_INDEX marker. Do not touch D:\CloudTech-Portable, D:\CloudTech-Vault, D:\CloudTech-Inbox, E:\AI_Backup, or any personal file in this phase.

## Safety/preconditions
- Export/record service state, task XML/state, paths, hashes, timestamps, and exact command outcomes before mutation.
- Verify target paths are within D:\AIOS and source paths are not symlinks/junctions to outside targets. If any path is outside the allowlist or hash cannot be recorded, do not move it; record UNVERIFIED.
- Do not run old install/start scripts after moving them.
- Do not modify AGENTS.md, model-policy, kernel models, verifier, v2 consumer loop, or product strategy policy.

## Required evidence
- Write `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_EVIDENCE.md/.json` including before/after service/task states, port 5099 listener result, quarantine manifest/hash verification, untouched deferred paths, and commands/results.
- Re-run the strategy tests: policy/lifecycle/scanner/quarantine/gate/submit-task/alias correction. Record any environment permission failure honestly.
- Do not claim service/task deletion, source deletion, backup purge, or full-disk zero residue. Return ACK with exact changed paths, reversibility/restore instructions, and unresolved operations.
