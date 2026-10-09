# Partial C — Local data / build / runtime source audit (READ-ONLY)

> **Audit ID**: C-AUDIT-2026-10-09
> **Title**: Partial C — Local data/build/runtime source audit
> **Mode**: READ-ONLY
> **Companion JSON**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\C_LOCAL_RUNTIME.json`
> **Contract**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\C_CONTRACT.md`
> **Preconditions read**: `D:\AIOS\_agent-hub\AGENTS.md`, `D:\AIOS\_agent-hub\memory\2026-10-08.md`, `D:\AIOS\_agent-hub\memory\2026-10-09.md`, `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\C_CONTRACT.md`

---

## 1. Overall Verdict

| Field | Value |
|---|---|
| **Headline** | OLD PRODUCT IS CURRENTLY LIVE. CloudTech V22 Unified Gateway is answering `GET http://127.0.0.1:5099/health` right now (status:ok, version:22.0.0, v10_modules_included:135). `D:\AIOS` holds a complete, reinstallable, auto-restoring copy of its monitor layer. |
| **Severity** | **HIGH** |
| **Reactivation possible** | true |
| **Reactivation effort** | **LOW** — one command per mechanism; all payloads already on disk |

### Layer verdicts

| Layer | Verdict |
|---|---|
| `D:\AIOS\cloudtech-saas` | **DORMANT-BUT-REGISTERED** — Windows service `CloudTechV22Monitor` is installed (Stopped/Manual) with `PathName` pointing INTO this directory. `install.cmd` can re-register it; the XML itself carries onfailure/restart policy. |
| `D:\AIOS\_archived_*` / `_backup*` | **ARCHIVE** — no service, task, registry key, or running process references them. Reactivation requires deliberate manual copy. |
| `D:\AIOS` root guidance/config | **ACTIVE-REFERENCE** — `AIOS_SOURCE_OF_TRUTH_FINAL` and `AIOS_RECONSTRUCTION` still declare CloudTech an in-scope project with live roadmap items and registered asset IDs. |
| `E:\AI_Backup` mirror | **ACTIVE** — a robocopy `/MIR` job is running right now mirroring `D:\AIOS` into `E:\AI_Backup`, so every archive under `D:\AIOS` is being re-copied off-box. |

---

## 2. Scope Inspected

- `D:\AIOS` root guidance/scripts/configs (root-level files + `AIOS_SOURCE_OF_TRUTH_FINAL` + `AIOS_RECONSTRUCTION` + `_workzone` + `_capability`; `_relinked` generic caches **EXCLUDED** per contract)
- `D:\AIOS\_out`
- `D:\AIOS\_backups` (incl. `_backups\20261008_rootfix`, `rootcause_fix_20260929`, `task-repair-*`, `chatgpt_bridge_*` snapshots)
- `D:\AIOS\_backups_2026-09-29`
- `D:\AIOS\_backups_relinked_1790674911` (listing only; `_relinked` excluded)
- `D:\AIOS\_archived_2026-09-18`
- `D:\AIOS\_archived_20260925_P0`
- `D:\AIOS\_archived_20260925_R259_popup_cure_rebuild`
- `D:\AIOS\_backup_aios_exe_周二022609_093048`
- `D:\AIOS\_backup_aios_exe_周二022609_093503`
- `D:\AIOS\_schtasks_bak_R344_20260930-*` and `_schtasks_bak_R349_20260930-*`
- `D:\AIOS\_r274_install_backup`
- `D:\AIOS\_r348_model_swap_bak_20260930-092918`
- `D:\AIOS\_dr_v3.0_uncompressed_workspace`
- `D:\AIOS\cloudtech-saas`
- `D:\AIOS\daemons_v2` (WinSW service definitions)
- Windows Scheduled Tasks (266 total enumerated; 70 match AIOS)
- Windows Services (`CIM Win32_Service` filtered on AIOS/CloudTech)
- `HKCU\...\Run` and `HKLM\...\Run`
- Running processes (`Win32_Process`, 574 enumerated)
- Listening ports (`Get-NetTCPConnection`)

### Not Scanned

- `D:\AIOS\_relinked` (generic caches — excluded by contract)
- Personal files outside `D:\AIOS` (read-only listing of the `E:\AI_Backup` mirror used solely to confirm the running robocopy target content)
- Cloud backups were not modified, moved, or deleted

### Forbidden Actions Observed (NONE performed)

- ❌ No file deleted
- ❌ No file moved
- ❌ No git history rewritten
- ❌ No service stopped or restarted
- ❌ No product code or policy modified

---

## 3. Live Runtime Observed

### 3.1 CloudTech V22 Unified Gateway answering on port 5099

- **Port**: 5099
- **Owning PID**: 16336
- **Parent PID**: 9944
- **Process name**: `python.exe`
- **Probe**: `curl -s --max-time 6 http://127.0.0.1:5099/health`
- **Response**:
  ```json
  {"status":"ok","version":"22.0.0","service":"CloudTech V22 Unified Gateway","v10_modules_included":135,"v10_modules_failed":0,"flask_app_loaded":true}
  ```
- **Root cause code in scope**: `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py:51-61` declares `D:\CloudTech-Portable` root, `gateway_v22.py`, port 5099 and the `start_v22.ps1` launcher.
- **Classification**: **ACTIVE — old product live**

### 3.2 CloudTech_V22Watchdog scheduled task RUNNING

- **Task path**: `\CloudTech_V22Watchdog`
- **State**: Running
- **Action**: `"D:\CloudTech-Portable\.venv\Scripts\pythonw.exe" -u D:\CloudTech-Portable\_ct_v22_watchdog.py`
- **Classification**: **ACTIVE — payload outside D:\AIOS**, command line observed per contract

### 3.3 CloudTech_V23FileWatcher scheduled task RUNNING

- **Task path**: `\CloudTech_V23FileWatcher`
- **State**: Running
- **Action**: `"D:\CloudTech-Portable\.venv\Scripts\pythonw.exe" -u D:\CloudTech-Portable\scripts\v23_file_watcher.py`
- **Classification**: **ACTIVE — payload outside D:\AIOS**

### 3.4 cloudtech-v22-gateway Windows service Running/Automatic

- **Service name**: `cloudtech-v22-gateway`
- **State**: Running
- **Start mode**: Auto
- **Path name**: `D:\个人文件\AI\Operator\aios_tools\winsw-x64\cloudtech_v22_gateway.exe`
- **In-scope note**: Reachable in-scope via the `D:\AIOS\aios_tools` junction (`cmd /c dir /AL D:\AIOS` confirms `aios_tools -> D:\个人文件\AI\Operator\aios_tools`). Binary itself lives outside `D:\AIOS` and was not opened.
- **Classification**: **ACTIVE**

### 3.5 Robocopy /MIR of D:\AIOS to E:\AI_Backup currently executing

- **PID**: 31360
- **Command line**:
  ```
  robocopy D:\AIOS E:\AI_Backup\DailyBackup_20261008\AIOS /MIR /FFT /MT:8 /R:1 /W:1 /DCOPY:DA /COPY:DAT /NP /NDL /NFL /XD node_modules venv .venv __pycache__ _pycache__ node_modules_cache .git .next dist build _archived_R_A01_20260922 Desktop_20260926
  ```
- **Launcher task**: `\AIOS_E_Drive_DailyBackup_R1331` (Running) → `wscript.exe "D:\个人文件\AI\Operator\aios_tools\_r1331_e_drive_daily_backup.vbs"`
- **Verified mirror content**:
  - `E:\AI_Backup\DailyBackup_20261008\AIOS\cloudtech-saas\` (`cloudtech-saas.exe`, `cloudtech-saas.xml`, `install.cmd`, `uninstall.cmd`, `start_v22_watchdog.bat`, `winsw.exe` + 3 xml `.bak`)
  - `E:\AI_Backup\DailyBackup_20261008\AIOS\_archived_2026-09-18\`
  - `E:\AI_Backup\DailyBackup_20261008\AIOS\_archived_20260925_P0\`
  - `E:\AI_Backup\DailyBackup_20260925_R259_popup_cure_rebuild` (as sibling path)
- **Classification**: **ACTIVE — automatic re-copy of every archive in scope**

### 3.6 AIOS daemon services Running/Automatic (via D:\AIOS\aios_tools junction)

- `AIOSCentralCollector` (Running/Auto, PID 9008, owns port 18799)
- `AIOSSelfHeal` (Running/Auto)
- `AIOSSupervisor` (Running/Auto)
- `AIOS_Autonomy_Daemon` (Running/Auto, binary = `aios-mcp-gateway-svc.exe`)
- **Classification**: **ACTIVE — infrastructure, product-neutral**

### 3.7 HKCU Run key HideConsoleWindowsV3 boots a D:\AIOS script

- **Registry key**: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`
- **Value name**: `HideConsoleWindowsV3`
- **Value data**: `"C:\Users\xinzh\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\pythonw.exe" -u "D:\AIOS\_hide_console_windows_v3.py"`
- **Running PID**: 14704
- **Code review**: `D:\AIOS\_hide_console_windows_v3.py:36-42` `AI_ROOTS = claude/codex/cursor/code/windsurf`; `:45-51` `USER_ROOTS` explorer/dwm/winlogon/services/taskhostw. Window-hider only — no product code, no launcher.
- **Classification**: **ACTIVE but PRODUCT-NEUTRAL**

### 3.8 HKCU Run keys beyond AIOS

- `WorkBuddy.WorkBuddy -> D:\1\WorkBuddy\WorkBuddy.exe`
- `OneDrive`
- `MicrosoftEdgeAutoLaunch_...`
- **Classification**: **ACTIVE — not AIOS product**

---

## 4. Confirmed Reactivation Mechanisms

| Rank | ID | Name | Type | State Now |
|---|---|---|---|---|
| 1 | REACT-01 | CloudTechV22Monitor Windows service | service | Stopped / Manual |
| 2 | REACT-02 | `cloudtech-saas\install.cmd` / `uninstall.cmd` / `start_v22_watchdog.bat` one-shot scripts | script | present, not invoked by any scheduled task or Run key |
| 3 | REACT-03 | `_workzone\src\_aios_cloudtech_bridge.py` — live bridge implementation (319 lines) | source_code | on disk, not currently imported by any running process |
| 4 | REACT-04 | `E:\AI_Backup` daily mirror — full-fidelity autorestore of `D:\AIOS` | backup_mirror | **ACTIVE** (robocopy PID 31360 in flight) |
| 5 | REACT-05 | `\CloudTech\*` scheduled-task namespace (5 registered tasks, 2 Running, 3 Ready) | scheduled_task | ACTIVE namespace |
| 6 | REACT-06 | Root installer scripts that re-create daemon autoruns (not currently registered) | script | on disk, target tasks absent from Task Scheduler |
| 7 | REACT-07 | `D:\AIOS\daemons_v2` WinSW service definitions (8 wrappers) + `AIOSV2Consumer` | service_definitions | all registered but Stopped/Disabled (`AIOSV2Consumer` Stopped/Automatic) |
| 8 | REACT-08 | Backup snapshots of the CloudTech health-check task definition | backup_xml | on disk only |
| 9 | REACT-09 | `_dr_v3.0_uncompressed_workspace` DR tooling | restore_tooling | on disk; no scheduled task references it (verified against all 266 tasks) |
| 10 | REACT-10 | Executable backups (AIOS daemon binaries) | binary_backup | on disk; NO service `PathName` points into any `_backup*` or `_archived*` directory |

### REACT-01 — CloudTechV22Monitor Windows service (registered, points into D:\AIOS\cloudtech-saas)

- **Type**: service
- **State now**: Stopped / Manual
- **Path name**: `D:\AIOS\cloudtech-saas\cloudtech-saas.exe`
- **Evidence**:
  - `Get-CimInstance Win32_Service` → `CloudTechV22Monitor~Stopped~Manual~"D:\AIOS\cloudtech-saas\cloudtech-saas.exe"`
  - `D:\AIOS\cloudtech-saas\cloudtech-saas.xml:10` `<id>CloudTechV22Monitor</id>`
  - `D:\AIOS\cloudtech-saas\cloudtech-saas.xml:15` executable `D:\AIOS\_relinked\workbuddy\binaries\python\versions\3.13.12\python.exe`
  - `D:\AIOS\cloudtech-saas\cloudtech-saas.xml:16` arguments `-m src._aios_cloudtech_bridge --check`
  - `D:\AIOS\cloudtech-saas\cloudtech-saas.xml:17` workingdirectory `D:\AIOS\_workzone`
  - `D:\AIOS\cloudtech-saas\cloudtech-saas.xml:27` `<startmode>Manual</startmode>`
  - `D:\AIOS\cloudtech-saas\cloudtech-saas.xml:28-29` `<onfailure action="restart" delay="30 sec"/>` / `delay="60 sec"`
  - `D:\AIOS\cloudtech-saas\cloudtech-saas.xml:31` `<resetfailureafter>2 hour</resetfailureafter>`
- **Reactivation command**: `sc start CloudTechV22Monitor` (or `D:\AIOS\cloudtech-saas\install.cmd` line 19: `winsw.exe install cloudtech-saas.xml`)
- **Blast radius**: Re-registers the AIOS→CloudTech V22 bridge monitor against port 5099; writes logs to `D:\AIOS\cloudtech-saas\logs`
- **Blocked by**: Manual start mode only; nothing currently triggers it

### REACT-02 — cloudtech-saas\install.cmd / uninstall.cmd / start_v22_watchdog.bat one-shot scripts

- **Type**: script
- **State now**: present, not invoked by any scheduled task or Run key
- **Evidence**:
  - `D:\AIOS\cloudtech-saas\install.cmd:19` `winsw.exe install cloudtech-saas.xml`
  - `D:\AIOS\cloudtech-saas\install.cmd:26` `curl -s http://127.0.0.1:5099/health`
  - `D:\AIOS\cloudtech-saas\install.cmd:33` echoes AIOS bridge path `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py`
  - `D:\AIOS\cloudtech-saas\install.cmd:9-11` downloads WinSW x64 from GitHub if missing
  - `D:\AIOS\cloudtech-saas\uninstall.cmd:9` `winsw.exe stop cloudtech-saas.xml`
  - `D:\AIOS\cloudtech-saas\uninstall.cmd:12` `winsw.exe uninstall cloudtech-saas.xml`
  - `D:\AIOS\cloudtech-saas\start_v22_watchdog.bat:7` `cd /d D:\AIOS\_workzone`
  - `D:\AIOS\cloudtech-saas\start_v22_watchdog.bat:8` `pythonw.exe -m src._aios_cloudtech_bridge --watch --watch-interval 300`
- **Reactivation command**: double-click `D:\AIOS\cloudtech-saas\install.cmd` OR `D:\AIOS\cloudtech-saas\start_v22_watchdog.bat`
- **Blast radius**: `install.cmd` re-registers the service; `start_v22_watchdog.bat` starts a 300s polling bridge watchdog
- **Blocked by**: manual execution only

### REACT-03 — _workzone\src\_aios_cloudtech_bridge.py — live bridge implementation (319 lines)

- **Type**: source_code
- **State now**: on disk, not currently imported by any running process
- **Evidence**:
  - `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py:51` `CLOUDTECH_V22_ROOT = Path(r"D:\CloudTech-Portable")`
  - `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py:52` `CLOUDTECH_V22_GATEWAY = .../gateway_v22.py`
  - `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py:55` `CLOUDTECH_V22_PORT = 5099`
  - `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py:61` `CLOUDTECH_V22_START_PS = .../tools/start_v22.ps1`
  - `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py:66` `AIOS_ROOT = Path(r"D:\AIOS")`
  - `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py:79-86` endpoint table incl. `/decoration-landing.html` (industry-vertical residue)
  - `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py:89-93` pricing plans free/pro/enterprise
  - `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py:109-121` `check_v22_alive()` queries port 5099 owner PID
- **Reactivation command**: `python -m src._aios_cloudtech_bridge --watch --watch-interval 300` (cwd `D:\AIOS\_workzone`)
- **Blast radius**: Registers old-product endpoints into the AIOS capability registry and monitors port 5099
- **Blocked by**: module invocation only

### REACT-04 — E:\AI_Backup daily mirror — full-fidelity autorestore of D:\AIOS

- **Type**: backup_mirror
- **State now**: **ACTIVE** (robocopy PID 31360 in flight)
- **Evidence**:
  - Running process: `robocopy D:\AIOS E:\AI_Backup\DailyBackup_20261008\AIOS /MIR ...`
  - Scheduled task `\AIOS_E_Drive_DailyBackup_R1331` (Running)
  - Verified on disk: `E:\AI_Backup\DailyBackup_20261008\AIOS\cloudtech-saas\` contains `cloudtech-saas.exe` + `cloudtech-saas.xml` + `install.cmd` + `uninstall.cmd` + `start_v22_watchdog.bat` + `winsw.exe`
  - Verified on disk: `E:\AI_Backup\DailyBackup_20261008\AIOS\_archived_2026-09-18\`, `_archived_20260925_P0\`, `_archived_20260925_R259_popup_cure_rebuild\`
- **Reactivation command**: copy back from `E:\AI_Backup\DailyBackup_20261008\AIOS` (no tooling required)
- **Blast radius**: Restores `cloudtech-saas`, all `_archived_*` and all `_backups` in one operation
- **Blocked by**: **nothing** — the job runs on its own schedule

### REACT-05 — \CloudTech\* scheduled-task namespace (5 registered tasks, 2 Running, 3 Ready)

- **Type**: scheduled_task
- **State now**: ACTIVE namespace
- **Evidence**:
  - `\CloudTech\HealthCheck-Hourly` [Ready] → `powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "C:\Users\xinzh\.workbuddy\scripts\health-check.ps1"`
  - `\CloudTech\DailyReport-0300` [Ready] → same `health-check.ps1`
  - `\CloudTech\AIOSLightMonitor-30min` [Ready] → `C:\Users\xinzh\.workbuddy\scripts\aios-light-monitor.ps1`
  - `\CloudTech\StartupCleanup-Once` [Ready] → `C:\Users\xinzh\.workbuddy\scripts\startup-cleanup.wrapper.ps1`
  - `\CloudTech-V22-Watchdog` [Disabled] → `wscript.exe "D:\UsersTemp\hidden_run.vbs" "D:\CloudTech-Portable\_ct_v22_watchdog_runner.cmd"`
  - `\CloudTech_SpecV1CI_Daily_0300` [Ready] → `wscript.exe "D:\UsersTemp\hidden_run.vbs" "D:\个人文件\AI\CloudTech\V2.0\feedback-lingce-2026-09-09\_tools\RunSpecV1CI.cmd"`
- **Reactivation command**: `Enable-ScheduledTask -TaskPath \CloudTech\ -TaskName HealthCheck-Hourly`
- **Blast radius**: Payloads live outside `D:\AIOS` (workbuddy scripts, `D:\CloudTech-Portable`); observed by command line only, files not opened
- **Blocked by**: payload location outside audited scope

### REACT-06 — Root installer scripts that re-create daemon autoruns (not currently registered)

- **Type**: script
- **State now**: on disk, target tasks absent from Task Scheduler
- **Evidence**:
  - `D:\AIOS\install_aios_loop.cmd:12` `TASK_NAME=AIOS-Daemon-Loop-Guard`; `:33-39` `schtasks /Create /SC ONSTART /RL HIGHEST /RU SYSTEM -> D:\AIOS\_aios_loop_inner.cmd`
  - `D:\AIOS\install_aios_watchdog.cmd:11` `TASK_NAME=AIOS-Daemon-Watchdog`; `:13` `SCRIPT=D:\AIOS\aios_daemon_watchdog.py`; `:32-38` `schtasks /Create /SC ONSTART`
  - `D:\AIOS\R65_右键管理员运行_一键注册.bat:6-19` re-registers `AIOS_WAL_Recovery_Startup` / `AIOS_Quorum_Health_5min` / `AIOS_Quota_Enforcer_Report_10min` / `AIOS_WAL_RecoverAll_Daily`
  - `D:\AIOS\AIOS_Cron_R65_Residual.ps1:14-33` same four tasks via `Register-ScheduledTask`
  - **Verification**: the two `Daemon-*` tasks are NOT present in the 266-task enumeration; the four R65 tasks ARE present and Ready
- **Reactivation command**: run `install_aios_loop.cmd` or `install_aios_watchdog.cmd` elevated
- **Blast radius**: SYSTEM-priority ONSTART tasks rooted in `D:\AIOS`
- **Blocked by**: requires elevation + deliberate execution

### REACT-07 — D:\AIOS\daemons_v2 WinSW service definitions (8 wrappers) + AIOSV2Consumer

- **Type**: service_definitions
- **State now**: all registered but Stopped/Disabled (`AIOSV2Consumer` Stopped/Automatic)
- **Evidence**:
  - `D:\AIOS\daemons_v2\winsw\supervisor\winsw.xml` → service `aios-supervisor` Stopped/Disabled
  - `D:\AIOS\daemons_v2\winsw\cron-orchestrator\winsw.xml` → `aios-cron-orchestrator` Stopped/Disabled
  - `D:\AIOS\daemons_v2\winsw\observability-hub\winsw.xml` → `aios-observability-hub` Stopped/Disabled
  - `D:\AIOS\daemons_v2\winsw\role-channels\winsw.xml` → `aios-role-channels` Stopped/Disabled
  - `D:\AIOS\daemons_v2\winsw\bridge-cc-codex-cli\winsw.xml`, `bridge-cc-doubao`, `bridge-cc-openclaw`, `bridge-codex-desktop-cli` → all Stopped/Disabled
  - `D:\AIOS\daemons_v2\winsw\v2-consumer\AIOSV2Consumer.xml` → service `AIOSV2Consumer` Stopped/Automatic (installed 2026-10-09, P1 commit `4d5b905`)
- **Reactivation command**: `sc start <service>`
- **Blast radius**: agent bridges / envelope consumer — infrastructure, product-neutral
- **Blocked by**: all disabled except `AIOSV2Consumer` (non-elevated shell cannot `Start-Service`: OS error 5, per memory 2026-10-09)

### REACT-08 — Backup snapshots of the CloudTech health-check task definition

- **Type**: backup_xml
- **State now**: on disk only
- **Evidence**:
  - `D:\AIOS\_backups\task-repair-20260930-active\CloudTech_HealthCheck-Hourly.pre-fix.xml:4-5` Description "CloudTech WorkBuddy 健康巡检 (每小时)" URI `\CloudTech\HealthCheck-Hourly`
  - `D:\AIOS\_backups\task-repair-20260930-active\CloudTech_HealthCheck-Hourly.pre-fix.xml:30-36` hourly trigger PT1H / P365D
  - `D:\AIOS\_backups\task-repair-20260930-active\CloudTech_HealthCheck-Hourly.pre-fix.xml:40` `<Command>powershell.exe</Command>`
  - `D:\AIOS\_backups\task-repair-20260930-active\AIOS_Sync_Watchdog.pre-fix.xml`, `OpenClaw-HealthMonitor.pre-fix.xml`
- **Reactivation command**: `schtasks /create /tn "\CloudTech\HealthCheck-Hourly" /xml <file>`
- **Blast radius**: restores the old task namespace entry point
- **Blocked by**: manual

### REACT-09 — _dr_v3.0_uncompressed_workspace DR tooling

- **Type**: restore_tooling
- **State now**: on disk; no scheduled task references it (verified against all 266 tasks)
- **Evidence**:
  - `D:\AIOS\_dr_v3.0_uncompressed_workspace\dr_restore_now.py:20` `DEST_BASE = E:\移动硬盘\Dr2026-09-18_DR_v3.0\01b_full_backup_uncompressed`
  - `D:\AIOS\_dr_v3.0_uncompressed_workspace\dr_restore_now.py:21` `MANIFEST = E:\移动硬盘\Dr2026-09-18_DR_v3.0\MANIFEST.json`
  - `D:\AIOS\_dr_v3.0_uncompressed_workspace\dr_nightly_drift_check.py`, `dr_manifest_generator.py`, `dr_uncomp_copy.py`, `99_verify_full_drill.py`
  - `D:\AIOS\_dr_v3.0_uncompressed_workspace\_r155_autobackup_start.cmd`, `_r155_autobackup_startup.vbs`, `_r155_backup_runner.py`
- **Reactivation command**: `python dr_restore_now.py` (with external drive attached)
- **Blast radius**: restores 11 core modules from the DR manifest
- **Blocked by**: requires external `E:\移动硬盘` media

### REACT-10 — Executable backups (AIOS daemon binaries)

- **Type**: binary_backup
- **State now**: on disk; NO service `PathName` points into any `_backup*` or `_archived*` directory (verified by filtering all `Win32_Service` `PathName`)
- **Evidence**:
  - `D:\AIOS\_backup_aios_exe_周二022609_093048\AIOSCentralCollector.exe` (10,075,602 B)
  - `D:\AIOS\_backup_aios_exe_周二022609_093048\AIOSSelfHeal.exe` (9,073,580 B)
  - `D:\AIOS\_backup_aios_exe_周二022609_093048\AIOSSupervisor.exe` (9,074,690 B)
  - `D:\AIOS\_backup_aios_exe_周二022609_093048\AIOS_Autonomy_Daemon.exe` (8,927,192 B)
  - `D:\AIOS\_backup_aios_exe_周二022609_093503\` (empty)
  - `D:\AIOS\_archived_2026-09-18\` (17 entries: `AIOSCentralCollector` `.old/.old2./v2/v3`, `AIOSSelfHeal.exe.old`, `AIOSSupervisor.exe.old`, `AIOS_Autonomy_Daemon` `.old/v2/v3`, `aios-incident-controller.exe.old`, `_health_reports\R91_v2_final_health.json`, `_r91_v1_superseded\*.bat`)
- **Reactivation command**: manual copy over the live binary + re-point the service `PathName`
- **Blast radius**: AIOS infrastructure binaries only — no product code
- **Blocked by**: manual, and superseded binaries

---

## 5. Active vs Archive Classification

### Definitions

| Class | Meaning |
|---|---|
| **ACTIVE** | Referenced by a currently-running process, listening socket, registered-but-armed service/task, registry Run key, or an actively-executing backup job. |
| **DORMANT_REGISTERED** | A Windows service or scheduled task exists and points at the path, but is Stopped/Disabled/Manual and nothing triggers it. |
| **ARCHIVE** | No service, task, Run key, or running process references the path. Reachable only by deliberate manual action. |
| **REFERENCE_ONLY** | Documentation/registry JSON that names the asset but executes nothing. |

### Classification Table

| Path | Classification | Reason |
|---|---|---|
| `D:\AIOS\cloudtech-saas` | **DORMANT_REGISTERED** | `CloudTechV22Monitor` service installed (Stopped/Manual), `PathName` `D:\AIOS\cloudtech-saas\cloudtech-saas.exe`; XML onfailure restart policy armed; `install.cmd` present |
| `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py` | **DORMANT_REGISTERED** | Referenced by `cloudtech-saas.xml:16` and `start_v22_watchdog.bat:8`; the port it targets (5099) is live |
| `127.0.0.1:5099` (`D:\CloudTech-Portable\gateway_v22.py`) | **ACTIVE** | GET `/health` returns `status:ok` `version:22.0.0` |
| `\CloudTech_V22Watchdog`, `\CloudTech_V23FileWatcher` | **ACTIVE** | Task state Running |
| `\CloudTech\HealthCheck-Hourly`, `DailyReport-0300`, `AIOSLightMonitor-30min`, `StartupCleanup-Once`, `CloudTech_SpecV1CI_Daily_0300` | **ACTIVE** | Task state Ready with triggers |
| `\CloudTech-V22-Watchdog` | **ARCHIVE** | Task state Disabled |
| `cloudtech-v22-gateway` (service) | **ACTIVE** | Running/Automatic; binary under `D:\个人文件\AI\Operator\aios_tools` (reachable via `D:\AIOS\aios_tools` junction) |
| `skill-http-server` (service, Stopped/Manual) | **DORMANT_REGISTERED** | `PathName` `D:\个人文件\AI\CloudTech\V2.0\feedback-lingce-2026-09-09\_tools\skill_http_server.exe` |
| `D:\AIOS\_archived_2026-09-18` | **ARCHIVE** | 17 retired `.exe/.old/.bat` artifacts; no service/task/Run/process reference |
| `D:\AIOS\_archived_20260925_P0` | **ARCHIVE** | `_aios_tools_state` bridges + `_NEW_ARCHITECTURE_SSOT_V1.0_2026-09-25.md` + `_pid_files`; nothing references them |
| `D:\AIOS\_archived_20260925_R259_popup_cure_rebuild` | **ARCHIVE** | 4 popup-cure `.bak` files; no reference |
| `D:\AIOS\_backup_aios_exe_周二022609_093048` / `_093503` | **ARCHIVE** | binary backups; no service `PathName` points here |
| `D:\AIOS\_backups` (3543 files) | **ARCHIVE (contents) / ACTIVE (as restore source)** | No live reference, but `REACT-04` mirrors it into `E:\AI_Backup` every run |
| `D:\AIOS\_backups_2026-09-29` | **ARCHIVE** | `Merge.yaml.bak-R327-pinning`, `Run-reg-bak.reg`, `_clash_verge_watchdog.py.bak-R327-disabled` |
| `D:\AIOS\_backups_relinked_1790674911` | **ARCHIVE** | `openclaw/` + `workbuddy/` snapshots; `_relinked` excluded from this audit |
| `D:\AIOS\_schtasks_bak_R344_*` / `_R349_*` | **ARCHIVE** | `AIOS-DashboardSupervisor.xml`, `AIOS-HealthMonitor.xml`, `AIOS-SessionCleanup.xml`, `AIOS-SyncClaudeMemory.xml`, `AIOS_V13_Protocol_Audit.xml` |
| `D:\AIOS\_r274_install_backup` | **ARCHIVE** | 6 `.bak` files from the 2026-09-29 untracked-file install |
| `D:\AIOS\_r348_model_swap_bak_20260930-092918` | **ARCHIVE** | `model_resources.json` + `_aios_model_resource_state.json` |
| `D:\AIOS\_out` | **REFERENCE_ONLY** | 3 PNG screenshots: `R222_sc001_screenshot.png`, `R222_sc003_handwritten.png`, `R222_xh01_decor_pitfalls.png` (decoration-industry evidence, not executable) |
| `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL` | **REFERENCE_ONLY** | Declares `project-cloudtech` with 4 live risk items and a `P3-01` roadmap line; executes nothing |
| `D:\AIOS\AIOS_RECONSTRUCTION` | **REFERENCE_ONLY** | Registries name CloudTech as a system asset; executes nothing |
| `D:\AIOS\daemons_v2` | **DORMANT_REGISTERED** | 8 WinSW definitions; 7 services Stopped/Disabled, `AIOSV2Consumer` Stopped/Automatic |
| `D:\AIOS\_dr_v3.0_uncompressed_workspace` | **ARCHIVE** | DR tooling; no scheduled task references it (verified across all 266 tasks) |
| `E:\AI_Backup\DailyBackup_20261008\AIOS` | **ACTIVE** | robocopy PID 31360 mirroring into it right now |

---

## 6. Local Sources Detail

### 6.1 `D:\AIOS\_out` (file_count: 3)

- **Classification**: REFERENCE_ONLY
- **Items**:
  - `D:\AIOS\_out\R222_sc001_screenshot.png` — screenshot evidence
  - `D:\AIOS\_out\R222_sc003_handwritten.png` — screenshot evidence
  - `D:\AIOS\_out\R222_xh01_decor_pitfalls.png` — decoration-industry pitfalls — old-product industry residue

### 6.2 `D:\AIOS\_backups` (file_count: 3543)

- **Classification**: ARCHIVE + restore source
- **Key subtrees**:
  - `D:\AIOS\_backups\20261008_rootfix`:
    - `AIOS_Autonomy_Daemon-svc.xml.orig` (802 B)
    - `aios_interop_launcher.py.orig` (7377 B)
  - `D:\AIOS\_backups\rootcause_fix_20260929`:
    - `_aios_cloudtech_bridge.py.bak`
    - `winsw_xml\{AIOSCentralCollector,AIOSSelfHeal,AIOSSupervisor,AIOS_Autonomy_Daemon}-svc.xml`
    - `dirs_archived\{_venv312,aios_tools}`
    - `winsw_logs_archive\`
  - `D:\AIOS\_backups\task-repair-20260930-active`:
    - `CloudTech_HealthCheck-Hourly.pre-fix.xml`
    - `AIOS_Sync_Watchdog.pre-fix.xml`
    - `OpenClaw-HealthMonitor.pre-fix.xml`
  - `D:\AIOS\_backups\task-repair-20260929-p0 / -p1 / -p2 / -p3`:
    - 13 AIOS_* task XML + `.err` + `status-all.txt`
  - `D:\AIOS\_backups\chatgpt_bridge_pre_rollback_to_V4P9-FINAL_20260927_*`:
    - count: 16
    - bridge rollback snapshots with `_task_store.db` and `_project_registry.py`
  - `D:\AIOS\_backups\HKCU_Run_20261008.reg` / `HKCU_Run_20261008_afterfix.reg`:
    - Run-key snapshots
  - `D:\AIOS\_backups\task-t0001-claude-settings-20261008-105353.json` / `task-t0007-registry-20261008-105437.json`:
    - agent-config snapshots
  - `D:\AIOS\_backups\aios_mcp_gateway_autostart.cmd.20261008`:
    - gateway autostart script snapshot

### 6.3 `D:\AIOS\_archived` (classification: ARCHIVE)

- **Trees**:
  - `D:\AIOS\_archived_2026-09-18`:
    - entry_count: 17
    - notable: `AIOSCentralCollector.exe.old/.old2/.old3/.old4/.old5/.20260919.old/.20260919.v2.old/.20260919.v3.old`, `AIOSSelfHeal.exe.old`, `AIOSSupervisor.exe.old`, `AIOS_Autonomy_Daemon.exe.old/.v2.old/.v3.old/.20260919.old/.v2/.v3`, `aios-incident-controller.exe.old`, `_health_reports\R91_v2_final_health.json`, `_r91_v1_superseded\_fix_*.bat + _run_*.bat`
  - `D:\AIOS\_archived_20260925_P0`:
    - notable: `_aios_tools_state\` (25 bridge/daemon/watcher `.py` + `.bak`), `_pid_files\` (12 `.pid`), `_NEW_ARCHITECTURE_SSOT_V1.0_2026-09-25.md`, `_AIOSWatchdogAliveCheck.cmd`, `_AIOSWatchdogAliveCheck_v2.cmd`, `_cleanup_restart.ps1`
  - `D:\AIOS\_archived_20260925_R259_popup_cure_rebuild`:
    - notable: `AIOSPopupCure.cmd.bak`, `_popup_cure_watchdog.py.bak`, `_popup_state.json.bak`, `_R82_AIOSPopupCure_install.cmd.bak`

### 6.4 `D:\AIOS\cloudtech-saas` (file_count: 13)

- **Classification**: DORMANT_REGISTERED
- **Files**:
  - `cloudtech-saas.exe`
  - `cloudtech-saas.xml`
  - `cloudtech-saas.xml.bak_C_1790215941`
  - `cloudtech-saas.xml.pre_descriptor_R284_20260929T200200.bak`
  - `cloudtech-saas.xml.pre_repair_R283_20260929T195700.bak`
  - `install.cmd`
  - `uninstall.cmd`
  - `start_v22_watchdog.bat`
  - `start_v22_watchdog.bat.pre_R284_20260929T200200.bak`
  - `winsw.exe`
  - `logs\cloudtech-saas.err.log`
  - `logs\cloudtech-saas.out.log`
  - `logs\cloudtech-saas.wrapper.log`
- **Last install event**: `logs\cloudtech-saas.wrapper.log`: 2026-09-29 20:00:49 INFO - Installing service 'CloudTech V22 Health Monitor (AIOS Bridge R156g)'... installed successfully; 20:00:59 started process 23932

### 6.5 Root Guidance References

| File | Lines | Content |
|---|---|---|
| `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` | 28-40, 334, 352-354, 378, 381 | `project-cloudtech` id/name/scope spans `D:/CloudTech-Portable` + Vault + Inbox + Live-Execution + `D:/AIOS/cloudtech-saas`; 4 open risk items (Vault sync stale, 3 untracked incl. cloudtech.db PII risk, Inbox 5 industries empty, AR-0086 not deployed) |
| `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\assets\AIOS_ASSET_REGISTRY.csv` | 62, 63, 73-88, 216 | AR-0061 `.env` + AR-0062 `.jwt_secret` of CloudTech-Portable registered as sensitive assets; AR-0072 CloudTech-Inbox BROKEN; AR-0073 rc2 Live Direct Execution VERIFIED/LIVE_UNAUDITED; AR-0074..0081 CloudTech-Portable main repo; AR-0082..0085 CloudTech-Vault; AR-0086/0087 `D:/AIOS/cloudtech-saas` install skeleton |
| `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` | 305, 308-309 | P3-01 CloudTech 业务推进 — Owner: CloudTech 团队 + Codex 协调 — 范围 `D:/CloudTech-*` 5 根 |
| `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\context\AIOS_REALITY_BASELINE_FINAL.md` | 136, 157-158, 163 | CloudTech rc2 candidate Tested 129/129; Vault syncer STALE; Inbox 5 industries MISSING; CloudTech-Portable 3 untracked DIRTY |
| `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SYSTEM_REGISTRY.json` | 48-55 | `sys-cloudtech` entry, path `D:\个人文件\AI\cloudtech`, description 用户个人独立项目 cloudtech |
| `D:\AIOS\AIOS_RECONSTRUCTION\00_REALITY\AIOS_REALITY_MAP.json` | 71, 147-148, 163 | `cloudtech-saas` node; CloudTech path `D:\个人文件\AI\cloudtech`; CloudTech.lnk desktop shortcut |
| `D:\AIOS\AIOS_RECONSTRUCTION\11_REPORTS\AIOS_ORPHAN_REPORT.json` | 197-210 | 3 orphaned CloudTech design docs under `Operator\00_CORE` (BLUEPRINT, DECISION-MATRIX, PhaseBC_EXEC_PLAN) |
| `D:\AIOS\AIOS_RECONSTRUCTION\09_LAB\_step8_reports.py` | 110 | scans `D:\个人文件\AI\cloudtech` as a project root |
| `D:\AIOS\_audit_reports\全量查漏补缺报告_2026-10-08.md` | 95, 121 | references the cloudtech watchdog PID-lock scheme; CloudTech V23 port-conflict note (V23 moved to 18800 colliding with the AIOS dashboard) |

---

## 7. Scheduled Task Inventory

- **Total enumerated**: 266
- **State counts**: Running=9, Ready=207, Disabled=50
- **Tasks matching AIOS**: 70
- **Tasks pointing into D:\AIOS root**:

| Task | State | Action |
|---|---|---|
| `\AIOS_Explorer_Watchdog` | Ready | `D:\AIOS\aios_tools\_aios_run_explorer_watchdog.cmd` |
| `\AIOS_V13_Protocol_Audit` | Ready | `"D:\AIOS\aios_venv\Scripts\python.exe" "D:\AIOS\aios_tasks\_aios_v13_protocol_audit.py"` |
| `\AIOS_Sync_Watchdog` | Ready | `wscript.exe "D:\UsersTemp\hidden_run.vbs" "D:\AIOS\aios_tools\R163\R163_Sync_Watchdog.cmd"` |
| `\OpenClaw Lease Guard` | Ready | `D:\AIOS\aios_venv\Scripts\pythonw.exe D:\AIOS\aios_tools\_aios_openclaw_lease_guard.py` |
| `\AIOS_R193_Popup_Rootcure_3min` | Ready | `D:\AIOS\aios_venv\Scripts\pythonw.exe -u C:\Users\xinzh\.claude\_aios_popup_rootcure_v1.py` |
| `\AIOS_R176_R152_Incremental_60min` | Disabled | `pythonw.exe -u "D:\AIOS\aios_tools\_aios_r152_incremental.py" run --source-timeout 600` |
| `\Codex-Portable-Watchdog-R319` | Ready | `wscript.exe "D:\UsersTemp\hidden_run.vbs" "D:\AIOS\_codex_portable_watchdog_runner.cmd"` |
| `\OpenClaw-18792-Watchdog-R312` | Ready | `wscript.exe "D:\UsersTemp\hidden_run.vbs" "D:\AIOS\_openclaw_18792_watchdog_runner.cmd"` |
| `\ClashVerge-Watchdog-R314` | Disabled | `pythonw.exe -u D:\AIOS\_clash_verge_watchdog.py 60` |
| `\_multi_watchdog` | Disabled | `"D:\AIOS\_multi_watchdog_runner.cmd"` |

### R65 Tasks Still Registered

- `AIOS_WAL_Recovery_Startup` (Ready)
- `AIOS_Quorum_Health_5min` (Ready)
- `AIOS_Quota_Enforcer_Report_10min` (Ready)
- `AIOS_WAL_RecoverAll_Daily` (Ready)

### Not Registered but Scripts Present

- `AIOS-Daemon-Loop-Guard` (`install_aios_loop.cmd`)
- `AIOS-Daemon-Watchdog` (`install_aios_watchdog.cmd`)

---

## 8. Service Inventory

- **Total matched**: 22

### Running

| Name | State | Notes |
|---|---|---|
| `AIOSCentralCollector` | Running/Auto | PID 9008, owns port 18799 |
| `AIOSSelfHeal` | Running/Auto | — |
| `AIOSSupervisor` | Running/Auto | — |
| `AIOS_Autonomy_Daemon` | Running/Auto | binary `aios-mcp-gateway-svc.exe` |
| `cloudtech-v22-gateway` | Running/Auto | path `D:\个人文件\AI\Operator\aios_tools\winsw-x64\cloudtech_v22_gateway.exe` |
| `skill-http-server` | Manual/Stopped | not running |

### Stopped Pointing into D:\AIOS

| Name | State | Start mode | Path |
|---|---|---|---|
| `CloudTechV22Monitor` | Stopped | Manual | `D:\AIOS\cloudtech-saas\cloudtech-saas.exe` |
| `AIOSWatchdogAliveCheck` | Stopped | Disabled | `D:\AIOS\_AIOSWatchdogAliveCheck.cmd` |
| `AIOSV2Consumer` | Stopped | Auto | `D:\AIOS\daemons_v2\winsw\v2-consumer\AIOSV2Consumer.exe` |

### Stopped Pointing into D:\AIOS\daemons_v2

- `aios-supervisor`
- `aios-cron-orchestrator`
- `aios-observability-hub`
- `aios-role-channels`
- `aios-bridge-cc-codex-cli`
- `aios-bridge-cc-doubao`
- `aios-bridge-cc-openclaw`
- `aios-bridge-codex-desktop-cli`

### External CloudTech Services

| Name | State | Start mode | Path |
|---|---|---|---|
| `skill-http-server` | Stopped | Manual | `D:\个人文件\AI\CloudTech\V2.0\feedback-lingce-2026-09-09\_tools\skill_http_server.exe` |

---

## 9. Listening Ports

| Port | PID | Identity | Classification |
|---|---|---|---|
| 5099 | 16336 | CloudTech V22 Unified Gateway (`python.exe`) | **ACTIVE old product** |
| 18799 | 9008 | `AIOSCentralCollector.exe` alerts endpoint | ACTIVE infrastructure |
| 18801 | 16184 | OpenClaw MCP bridge (R307) | ACTIVE infrastructure |
| 18803 | null | SaaS HTTP demo (R1297) — not listening in this snapshot | not running |
| 18804 | null | A2A protocol (R1298) — not listening in this snapshot | not running |

---

## 10. Out-of-Scope Observed (NOT read)

| Path | Note |
|---|---|
| `D:\CloudTech-Portable` | 10826 files / 934 dirs / 200 MB per `AIOS_ASSET_REGISTRY.csv:75`; `gateway_v22.py` 786 lines; `.env` and `.jwt_secret` registered as sensitive assets (AR-0061/AR-0062). NOT read — outside `D:\AIOS`. Observed only via scheduled-task command lines and the live 5099 listener. |
| `D:\CloudTech-Vault` | 22 files; sync stale since 2026-09-24 per `AIOS_REALITY_BASELINE_FINAL.md:157`. NOT read. |
| `D:\CloudTech-Inbox` | 5 industry subdirs (catering/decoration/medical/retail) all empty per AR-0072. NOT read. |
| `D:\CloudTech-Live-Execution\CloudTech_rc2_Live_Direct_Execution_20260925` | 129/129 pytest PASS candidate, marked `LIVE_UNAUDITED` per AR-0073. NOT read. |
| `D:\个人文件\AI\CloudTech\V2.0\feedback-lingce-2026-09-09` | Targets the `CloudTech_SpecV1CI_Daily_0300` task and the `skill-http-server` service. NOT read. |
| `E:\AI_Backup\` | Directory listing only, to confirm the running robocopy target content. Nothing written or modified. |
| `E:\移动硬盘\Dr2026-09-18_DR_v3.0\` | DR restore target referenced by `dr_restore_now.py:20-21`. Not accessed (external media). |

---

## 11. Verification

- **Files written**:
  - `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\C_LOCAL_RUNTIME.md`
  - `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\C_LOCAL_RUNTIME.json`
- **Protocol preconditions read**:
  - `D:\AIOS\_agent-hub\AGENTS.md`
  - `D:\AIOS\_agent-hub\memory\2026-10-08.md`
  - `D:\AIOS\_agent-hub\memory\2026-10-09.md`
  - `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\C_CONTRACT.md`
- **Method**: Read-only filesystem enumeration, grep with line numbers, `Get-ScheduledTask` / `Get-CimInstance Win32_Service` / `Win32_Process` / `Get-ItemProperty Run` / `Get-NetTCPConnection`, and one read-only HTTP GET to `127.0.0.1:5099/health`.
- **Mutations performed**: 0
- **Terminates with**: ACK