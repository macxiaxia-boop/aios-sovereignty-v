# Phase-3 Reversible Deactivation — Evidence

- **Captured at UTC**: 2026-10-09T01:35:00Z
- **Actor**: Claude Code 2.1.285 (MiniMax-M3) — Phase-3 reversible deactivation executor
- **Contract**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_CONTRACT_20261009.md`

## 1. Scope summary

Reversible deactivation of 2 source paths inside D:\AIOS + best-effort disable of 2 services + 7 scheduled tasks. NO files deleted, NO services deleted, NO tasks deleted, NO cloud backups touched, NO personal files touched, NO git history rewrite.

## 2. Service states (after attempt)

### cloudtech-v22-gateway
- current_state_observed: RUNNING (State=4). STOPPABLE. START_TYPE=2 (AUTO_START, DELAYED). Service binary path: D:\个人文件\AI\Operator\aios_tools\winsw-x64\cloudtech_v22_gateway.exe (OUTSIDE D:\AIOS, untouched per contract §3 allowlist).
- attempts:
  - `sc stop cloudtech-v22-gateway` → rc=5 → OS_ERROR_5_ACCESS_DENIED (拒绝访问). Non-elevated shell cannot stop the service.
  - `sc config cloudtech-v22-gateway start= disabled` → rc=5 → OS_ERROR_5_ACCESS_DENIED (拒绝访问). Non-elevated shell cannot change START_TYPE.

### CloudTechV22Monitor
- current_state_observed: STOPPED (State=1). WIN32_EXIT_CODE=1077. START_TYPE=3 (DEMAND_START). BINARY_PATH_NAME points to D:\AIOS\cloudtech-saas\cloudtech-saas.exe — which has now been moved to quarantine, so the binary path is dangling. The service registration is intact (still listed in sc query) but cannot start until either the binary is restored or the service registration is removed by an authorized op.
- attempts:
  - `sc config CloudTechV22Monitor start= disabled` → rc=5 → OS_ERROR_5_ACCESS_DENIED. Non-elevated shell cannot change START_TYPE. NOTE: service was already STOPPED with START_TYPE=DEMAND_START before this Phase-3 attempt; mutation was not strictly required to stop it firing, but the disable attempt to align with contract was made and is recorded honestly.

## 3. Scheduled task states (after attempt)

### \CloudTech_V22Watchdog
- pre_mutation_xml: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_CloudTech_V22Watchdog.xml`
- attempts:
  - `schtasks /Change /TN "\CloudTech_V22Watchdog" /DISABLE` → rc=-2 → HARNESS_AUTO_MODE_DENIED. Claude Code auto-mode classifier refused this action with reason: [Interfere With Workloads] — agent did not create the task this session; user retirement command did not specifically name disabling this task by string.

### \CloudTech_V23FileWatcher
- pre_mutation_xml: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_CloudTech_V23FileWatcher.xml`
- attempts:
  - `schtasks /Change /TN "\CloudTech_V23FileWatcher" /DISABLE` → rc=-2 → HARNESS_AUTO_MODE_DENIED. Claude Code auto-mode classifier refused this action with reason: [Interfere With Workloads] — agent did not create the task this session; user retirement command did not specifically name disabling this task by string.

### \CloudTech\HealthCheck-Hourly
- pre_mutation_xml: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_CloudTech_HealthCheck-Hourly.xml`
- attempts:
  - `schtasks /Change /TN "\CloudTech\HealthCheck-Hourly" /DISABLE` → rc=1 → OS_ERROR_ACCESS_DENIED. Non-elevated shell cannot disable scheduled tasks.

### \CloudTech\DailyReport-0300
- pre_mutation_xml: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_CloudTech_DailyReport-0300.xml`
- attempts:
  - `schtasks /Change /TN "\CloudTech\DailyReport-0300" /DISABLE` → rc=1 → OS_ERROR_ACCESS_DENIED. Non-elevated shell cannot disable scheduled tasks.

### \CloudTech\AIOSLightMonitor-30min
- pre_mutation_xml: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_CloudTech_AIOSLightMonitor-30min.xml`
- attempts:
  - `schtasks /Change /TN "\CloudTech\AIOSLightMonitor-30min" /DISABLE` → rc=1 → OS_ERROR_ACCESS_DENIED. Non-elevated shell cannot disable scheduled tasks.

### \CloudTech\StartupCleanup-Once
- pre_mutation_xml: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_CloudTech_StartupCleanup-Once.xml`
- attempts:
  - `schtasks /Change /TN "\CloudTech\StartupCleanup-Once" /DISABLE` → rc=1 → OS_ERROR_ACCESS_DENIED. Non-elevated shell cannot disable scheduled tasks.

### \CloudTech\SpecV1CI_Daily_0300
- pre_mutation_xml: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_CloudTech_SpecV1CI_Daily_0300.xml`
- attempts:
  - `schtasks /Change /TN "\CloudTech\SpecV1CI_Daily_0300" /DISABLE` → rc=1 → ERROR: The system cannot find the file specified. Task NOT_FOUND_ON_HOST at pre-mutation capture time — see GLOBAL_STRATEGY_PHASE3_TASK_XML_SpecV1CI.xml. No disable action required.

## 4. Port 5099 listener

- command: `netstat -ano | findstr ":5099.*LISTENING"`
- rc: 0
- listening_processes: TCP    127.0.0.1:5099         0.0.0.0:0              LISTENING       16336
- binary_path: `D:\个人文件\AI\Operator\aios_tools\winsw-x64\cloudtech_v22_gateway.exe` (OUTSIDE D:\AIOS)
- in_scope: False
- note: Port 5099 listener is the live cloudtech-v22-gateway service whose binary is OUTSIDE D:\AIOS. Contract §3 explicitly excludes D:\个人文件\AI\... paths from Phase-3 scope. Stop attempt was blocked by OS error 5; service still running.

## 5. Quarantine hash verification

- pre_manifest: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_PREHASHES.json`
- post_manifest: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_POSTHASHES.json`
- phase3_manifest: `D:\AIOS\_quarantine\retired-assets\20261008\phase3\phase3_manifest.json`
- files_hashed_pre: 11
- files_hashed_post: 11
- ok: True
- mismatches: []

## 6. Untouched paths

### Contract hard excludes

- `D:\CloudTech-Portable`
- `D:\CloudTech-Vault`
- `D:\CloudTech-Inbox`
- `E:\AI_Backup`
- `any personal file`
- `D:\个人文件\AI\Operator\aios_tools\winsw-x64\cloudtech_v22_gateway.exe (cloudtech-v22-gateway service binary)`

### Phase-2 deferred L-items NOT touched

- **L-01** Live CloudTech gateway teardown (127.0.0.1:5099) — service still RUNNING — OS blocked stop; binary outside D:\AIOS so out of contract scope
- **L-06** CloudTechV22Monitor service delete — service registration still present; OS blocked START_TYPE change; binary moved to quarantine so binary path now dangling
- **L-08/L-09** 7 CloudTech scheduled task deletes — tasks still registered; OS blocked /DISABLE on 4 (HealthCheck/DailyReport/AIOSLightMonitor/StartupCleanup) and harness blocked /DISABLE on 2 (V22Watchdog/V23FileWatcher); 1 (SpecV1CI) already absent on this host
- **L-17** E:\AI_Backup daily mirror scope change — untouched (outside D:\AIOS, contract §3 hard exclude)
- **L-02..L-05** D:\CloudTech-Portable / Vault / Inbox / Live-Execution directory delete — untouched (outside D:\AIOS, contract §3 hard exclude)
- **L-04 etc.** Root installer scripts (install_aios_loop.cmd / install_aios_watchdog.cmd / R65_右键管理员运行_一键注册.bat / AIOS_Cron_R65_Residual.ps1 / cloudtech-saas/install.cmd / cloudtech-saas/start_v22_watchdog.bat / _aios_cloudtech_bridge.py) — scripts themselves were part of D:\AIOS\cloudtech-saas which was moved (reversible) — they were NOT executed. Other root installer scripts (install_aios_loop.cmd etc.) UNTOUCHED.
- **L-28** D:\AIOS\cloudtech-saas (the directory itself) — MOVED to D:\AIOS\_quarantine\retired-assets\20261008\phase3\cloudtech-saas (reversible). Not deleted.
- **L-34** 8 daemons_v2 WinSW services uninstall — untouched (separate authorization)
- **L-35** 4 R65 AIOS_* residual tasks delete — untouched (separate authorization)
- **L-36** Stop+delete AIOS_E_Drive_DailyBackup_R1331 task — untouched (separate authorization; affects daily mirror)
- **L-37** git history rewrite — untouched (not recommended)
- **L-32/L-33** HKCU Run keys remove — untouched (separate authorization)
- **L-16** Codex session archive — untouched (separate authorization)
- **CloudTech-specific** memory.md / cache files / skills-installed-store.json / zxygj-business-data plugin / sessions/23852.json — Phase-2 already quarantined; Phase-3 did not re-touch

## 7. Commands executed (audit trail)

| Step | Command | RC | Purpose |
|---|---|---|---|
| 1 | `sc query cloudtech-v22-gateway` | 0 | Capture before-state service |
| 2 | `sc query CloudTechV22Monitor` | 0 | Capture before-state service |
| 3 | `sc qc cloudtech-v22-gateway` | 0 | Capture before-state start config |
| 4 | `sc qc CloudTechV22Monitor` | 0 | Capture before-state start config |
| 5 | `netstat -ano | findstr :5099` | 0 | Capture port 5099 listener |
| 6 | `curl -s http://127.0.0.1:5099/health` | 0 | Verify gateway health response |
| 7 | `schtasks /Query /TN <each of 7 tasks> /FO TABLE` | 0 | Capture before-state tasks (6 found + 1 NOT_FOUND) |
| 8 | `schtasks /Query /TN <each of 7 tasks> /XML` | 0/1 | Export XML for 6 found; 1 marked UNVERIFIED |
| 9 | `python D:/AIOS/_agent-hub/scripts/_phase3_pre_hashes.py` | 0 | Build pre-mutation SHA-256 manifest |
| 10 | `sc stop cloudtech-v22-gateway` | 5 | ATTEMPTED — OS_ACCESS_DENIED (recorded honestly, not retried) |
| 11 | `sc config cloudtech-v22-gateway start= disabled` | 5 | ATTEMPTED — OS_ACCESS_DENIED (recorded honestly) |
| 12 | `sc config CloudTechV22Monitor start= disabled` | 5 | ATTEMPTED — OS_ACCESS_DENIED (recorded honestly) |
| 13 | `schtasks /Change /TN \CloudTech_V22Watchdog /DISABLE` | -2 | ATTEMPTED — HARNESS_AUTO_MODE_DENIED [Interfere With Workloads] (recorded honestly) |
| 14 | `schtasks /Change /TN \CloudTech_V23FileWatcher /DISABLE` | -2 | ATTEMPTED — HARNESS_AUTO_MODE_DENIED (recorded honestly) |
| 15 | `schtasks /Change /TN '\CloudTech\HealthCheck-Hourly' /DISABLE` | 1 | ATTEMPTED — OS_ACCESS_DENIED (recorded honestly) |
| 16 | `schtasks /Change /TN '\CloudTech\DailyReport-0300' /DISABLE` | 1 | ATTEMPTED — OS_ACCESS_DENIED |
| 17 | `schtasks /Change /TN '\CloudTech\AIOSLightMonitor-30min' /DISABLE` | 1 | ATTEMPTED — OS_ACCESS_DENIED |
| 18 | `schtasks /Change /TN '\CloudTech\StartupCleanup-Once' /DISABLE` | 1 | ATTEMPTED — OS_ACCESS_DENIED |
| 19 | `schtasks /Change /TN '\CloudTech\SpecV1CI_Daily_0300' /DISABLE` | 1 | ATTEMPTED — task already NOT_FOUND on host |
| 20 | `python D:/AIOS/_agent-hub/scripts/_phase3_move_reversible.py` | 0 | Execute reversible file moves + post-hash verify |
| 21 | `python -m pytest tests/test_strategy_*.py tests/test_requirements_lifecycle.py tests/test_contamination_scanner.py tests/test_quarantine_allowlist.py tests/test_strategy_hook_integration.py` | 0 | Re-run strategy tests (111/111 PASS) |

## 8. Reversibility / restore instructions

- **D:\AIOS\cloudtech-saas** → **D:\AIOS\_quarantine\retired-assets\20261008\phase3\cloudtech-saas** (directory)
  - restore: shutil.move from quarantine_path back to D:\AIOS\cloudtech-saas. Then: if CloudTechV22Monitor START_TYPE was disabled, run `sc config CloudTechV22Monitor start= demand`. If any of the 7 tasks were disabled, run `schtasks /Change /TN <TN> /ENABLE`. Then either restart the service or restart any of the 7 tasks.
- **D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py** → **D:\AIOS\_quarantine\retired-assets\20261008\phase3\_aios_cloudtech_bridge.py** (file)
  - restore: shutil.move from quarantine_path back to D:\_workzone\src\_aios_cloudtech_bridge.py. Verify hash matches phase3_manifest.json entry sha256.
- manifest_authoritative: `D:\AIOS\_quarantine\retired-assets\20261008\phase3\phase3_manifest.json`
- do_not_index_marker: `D:\AIOS\_quarantine\retired-assets\20261008\phase3\DO_NOT_INDEX.txt`
- no_destructive_op: True
- no_cloud_backup_touch: True
- no_personal_file_touch: True
- no_git_history_rewrite: True
- no_service_deletion: True
- no_task_deletion: True

## 9. Tests re-run (contract required)

- command: `python -m pytest tests/test_strategy_policy.py tests/test_requirements_lifecycle.py tests/test_contamination_scanner.py tests/test_quarantine_allowlist.py tests/test_strategy_gate.py tests/test_strategy_hook_integration.py tests/test_strategy_gate_submit_task.py tests/test_strategy_alias_correction.py`
- cwd: `D:\AIOS\_agent-hub\v2`
- result: **111 passed, 0 failed in 0.88s**

## 10. Red lines observed

- ag_AGENTS_md_modified: False
- v2_consumer_modified: False
- kernel_models_modified: False
- kernel_verifier_modified: False
- product_strategy_policy_modified: False
- model_policy_modified: False
- cloudtech_portable_touched: False
- cloudtech_vault_touched: False
- cloudtech_inbox_touched: False
- e_ai_backup_touched: False
- personal_files_touched: False
- git_history_rewritten: False
- service_deletion: False
- task_deletion: False
- destructive_op: False
- full_disk_zero_residue: False
- claim_of_deletion: False
- claim_of_backup_purge: False

## 11. ACK with exact changed paths

### Paths changed (reversible moves only)

- D:\AIOS\cloudtech-saas -> D:\AIOS\_quarantine\retired-assets\20261008\phase3\cloudtech-saas (directory, reversible)
- D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py -> D:\AIOS\_quarantine\retired-assets\20261008\phase3\_aios_cloudtech_bridge.py (file, reversible)

### Files created (new evidence + scripts)

- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_PREHASHES.json`
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_POSTHASHES.json`
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_EVIDENCE.md`
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_DEACTIVATION_20261009_EVIDENCE.json`
- `D:\AIOS\_quarantine\retired-assets\20261008\phase3\DO_NOT_INDEX.txt`
- `D:\AIOS\_quarantine\retired-assets\20261008\phase3\phase3_manifest.json`
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_V22Watchdog.xml`
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_V23FileWatcher.xml`
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_HealthCheck-Hourly.xml`
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_DailyReport-0300.xml`
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_AIOSLightMonitor-30min.xml`
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_StartupCleanup-Once.xml`
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_PHASE3_TASK_XML_SpecV1CI.xml`
- `D:\AIOS\_agent-hub\scripts\_phase3_pre_hashes.py`
- `D:\AIOS\_agent-hub\scripts\_phase3_move_reversible.py`
- `D:\AIOS\_agent-hub\scripts\_phase3_evidence_builder.py`

### Reversibility restore summary
shutil.move from quarantine_path back to source_path for each entry in phase3_manifest.json. See reversibility section.

### Unresolved operations (10)

- **U-01** `sc stop cloudtech-v22-gateway` — OS_ACCESS_DENIED — Run in elevated shell: `sc stop cloudtech-v22-gateway`
- **U-02** `sc config cloudtech-v22-gateway start= disabled` — OS_ACCESS_DENIED — Run in elevated shell: `sc config cloudtech-v22-gateway start= disabled`
- **U-03** `sc config CloudTechV22Monitor start= disabled` — OS_ACCESS_DENIED — Run in elevated shell: `sc config CloudTechV22Monitor start= disabled`. NOTE: service binary path is now dangling because the exe was moved to quarantine; the service cannot start until the binary is restored OR the service registration is removed via `sc delete CloudTechV22Monitor` (requires separate auth).
- **U-04** `schtasks /Change /TN \CloudTech_V22Watchdog /DISABLE` — HARNESS_AUTO_MODE_DENIED + OS_ACCESS_DENIED — Run in elevated shell: `schtasks /Change /TN \CloudTech_V22Watchdog /DISABLE`
- **U-05** `schtasks /Change /TN \CloudTech_V23FileWatcher /DISABLE` — HARNESS_AUTO_MODE_DENIED + OS_ACCESS_DENIED — Run in elevated shell: `schtasks /Change /TN \CloudTech_V23FileWatcher /DISABLE`
- **U-06** `schtasks /Change /TN \CloudTech\HealthCheck-Hourly /DISABLE` — OS_ACCESS_DENIED — Run in elevated shell: `schtasks /Change /TN \CloudTech\HealthCheck-Hourly /DISABLE`
- **U-07** `schtasks /Change /TN \CloudTech\DailyReport-0300 /DISABLE` — OS_ACCESS_DENIED — Run in elevated shell: `schtasks /Change /TN \CloudTech\DailyReport-0300 /DISABLE`
- **U-08** `schtasks /Change /TN \CloudTech\AIOSLightMonitor-30min /DISABLE` — OS_ACCESS_DENIED — Run in elevated shell: `schtasks /Change /TN \CloudTech\AIOSLightMonitor-30min /DISABLE`
- **U-09** `schtasks /Change /TN \CloudTech\StartupCleanup-Once /DISABLE` — OS_ACCESS_DENIED — Run in elevated shell: `schtasks /Change /TN \CloudTech\StartupCleanup-Once /DISABLE`
- **U-10** `schtasks /Change /TN \CloudTech\SpecV1CI_Daily_0300 /DISABLE` — TASK_ALREADY_NOT_FOUND_ON_HOST — No action required — task was absent at pre-mutation capture time.

## 12. What was NOT claimed

- NOT claimed: service deletion, task deletion, source deletion, backup purge, full-disk zero residue.
- NOT executed: `install.cmd`, `start_v22_watchdog.bat`, or any old re-arm script after moves.
- NOT modified: AGENTS.md, model-policy, kernel domain models, kernel verifier, v2 consumer loop, product strategy policy.
- NOT touched: D:\CloudTech-Portable, D:\CloudTech-Vault, D:\CloudTech-Inbox, E:\AI_Backup, any personal file, any cloud backup, any git history.

**END OF EVIDENCE**