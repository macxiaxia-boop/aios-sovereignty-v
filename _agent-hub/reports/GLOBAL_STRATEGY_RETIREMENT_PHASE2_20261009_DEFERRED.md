# GLOBAL STRATEGY RETIREMENT — Phase-2 Deferred High-Impact Manifest

> **Captured at**: 2026-10-09 +08:00
> **Author**: Claude Code 2.1.285 (MiniMax-M3) — executor
> **Phase-2 Contract**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PHASE2_CONTRACT_20261009.md`
> **Audit reference**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008.md/.json`
> **Companion evidence**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PHASE2_20261009_EVIDENCE.md/.json`

## 1. Scope

This manifest enumerates every high-impact Phase-2 operation that the contract **explicitly defers** to a future authorization round. Per AGENTS.md `requires_authorization`, every item below requires fresh user approval before execution. Phase-2 SAFE_REVERSIBLE implementation did **not** touch any of these paths.

Each item has:
- the exact path or live process / task / service evidence
- the authorization needed (and which AGENTS.md rule)
- the reversible alternative (if any) used by Phase-2 instead

## 2. Live CloudTech gateway (L-01 in audit)

| Field | Value |
|---|---|
| Live URL | `http://127.0.0.1:5099/health` |
| Last health response | `{"status":"ok","version":"22.0.0","service":"CloudTech V22 Unified Gateway","v10_modules_included":135,"v10_modules_failed":0,"flask_app_loaded":true}` |
| Windows service | `cloudtech-v22-gateway` (State=RUNNING, Type=WIN32_OWN_PROCESS) |
| Code | `D:\CloudTech-Portable\gateway_v22.py` (786 lines) |
| Audit ID | A-01 |
| Phase-2 disposition | `SEPARATELY_AUTHORIZED` |
| Authorization needed | `sc stop cloudtech-v22-gateway` + `sc delete cloudtech-v22-gateway` + backup of `cloudtech.db` |
| AGENTS.md rule | `OS service restart` (requires_authorization) |
| Reversible alternative used | None — process still live as observed; no mutation performed |

## 3. CloudTech V22 Monitor service (L-06)

| Field | Value |
|---|---|
| Service name | `CloudTechV22Monitor` |
| State | STOPPED (manual trigger) |
| Restart policy | `cloudtech-saas.xml:28-31` armed (`<onfailure action="restart" delay="30 sec"/>`) |
| Code | `D:\AIOS\cloudtech-saas\cloudtech-saas.exe` |
| Audit ID | A-05 |
| Phase-2 disposition | `SEPARATELY_AUTHORIZED` |
| Authorization needed | `sc stop CloudTechV22Monitor` + `sc delete CloudTechV22Monitor` + disarm XML restart policy |
| AGENTS.md rule | `OS service restart` |
| Reversible alternative used | None |

## 4. CloudTech scheduled tasks (5 tasks namespace + 2 sibling Running tasks)

Tasks enumerated from audit C §3.5 + C §7:

| Task path | Trigger | Status (per audit) | Audit ID | Phase-2 disposition |
|---|---|---|---|---|
| `\CloudTech_V22Watchdog` | watchdog polling port 5099 | Running | A-02 | SEPARATELY_AUTHORIZED |
| `\CloudTech_V23FileWatcher` | file watcher on `D:\CloudTech-Portable\` | Running | A-03 | SEPARATELY_AUTHORIZED |
| `\CloudTech\HealthCheck-Hourly` | workbuddy script health-check | Ready | A-04 | SEPARATELY_AUTHORIZED |
| `\CloudTech\DailyReport-0300` | workbuddy script daily report | Ready | A-04 | SEPARATELY_AUTHORIZED |
| `\CloudTech\AIOSLightMonitor-30min` | workbuddy light monitor | Ready | A-04 | SEPARATELY_AUTHORIZED |
| `\CloudTech\StartupCleanup-Once` | workbuddy startup cleanup | Ready | A-04 | SEPARATELY_AUTHORIZED |
| `\CloudTech\SpecV1CI_Daily_0300` | `RunSpecV1CI.cmd` | Ready | A-04 | SEPARATELY_AUTHORIZED |

Total: 7 scheduled tasks (2 Running + 5 Ready).

| Field | Value |
|---|---|
| Authorization needed | `schtasks /Delete /TN <task> /F` for each |
| AGENTS.md rule | `OS service restart` |
| Reversible alternative used | None — all tasks still registered, no mutation performed |

## 5. Root installer scripts (re-arm path)

| Script | Purpose | Audit ID | Phase-2 disposition |
|---|---|---|---|
| `D:\AIOS\install_aios_loop.cmd` (line 12: TASK_NAME=AIOS-Daemon-Loop-Guard) | Re-create SYSTEM-priority ONSTART task → `_aios_loop_inner.cmd` | C-04 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\install_aios_watchdog.cmd` (line 11: TASK_NAME=AIOS-Daemon-Watchdog) | Re-create SYSTEM-priority ONSTART task → `aios_daemon_watchdog.py` | C-05 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\R65_右键管理员运行_一键注册.bat` (lines 6-19) | Re-register 4 R65 tasks | C-06 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\AIOS_Cron_R65_Residual.ps1` (lines 14-33) | PowerShell equivalent of R65 batch | C-06 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\cloudtech-saas\install.cmd` (lines 9-33) | `winsw.exe install cloudtech-saas.xml` + health probe | A-06 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\cloudtech-saas\start_v22_watchdog.bat` (lines 7-8) | `_aios_cloudtech_bridge --watch --watch-interval 300` | A-07 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py` (319 lines) | Python module importing into AIOS capability registry on `--watch` | A-08 | SEPARATELY_AUTHORIZED |

| Field | Value |
|---|---|
| Authorization needed | Execute each script (or delete) — see audit |
| AGENTS.md rule | `OS service restart` + `派 dev sub-agent 写代码` |
| Reversible alternative used | None — scripts on disk but not invoked |

## 6. E:\AI_Backup daily mirror

| Field | Value |
|---|---|
| Task | `\AIOS_E_Drive_DailyBackup_R1331` (per audit: currently Running, PID 31360) |
| Destination | `E:\AI_Backup\DailyBackup_20261008\AIOS\` |
| Mirror mode | robocopy `/MIR` |
| Scope | Includes `cloudtech-saas\`, `_archived_2026-09-18\`, `_archived_20260925_P0\`, `_archived_20260925_R259_popup_cure_rebuild\`, `_backup*` |
| Audit ID | A-09 |
| Phase-2 disposition | `SEPARATELY_AUTHORIZED` |
| Authorization needed | Reconfigure robocopy job to exclude `_archived_*` / `_backup*` / `cloudtech-saas\`. Mirror history retained; future scope changed. |
| AGENTS.md rule | `OS service restart` (the robocopy job) + `delete any file` (the exclusion policy) |
| Reversible alternative used | None — mirror job still scheduled and running |

## 7. Out-of-scope CloudTech directories (L-02..L-05)

| Path | Size / contents | Audit ID | Phase-2 disposition |
|---|---|---|---|
| `D:\CloudTech-Portable` | 200 MB; 10826 files / 934 dirs per AR-0075 | H-06 | SEPARATELY_AUTHORIZED |
| `D:\CloudTech-Vault` | 22 files | H-06 | SEPARATELY_AUTHORIZED |
| `D:\CloudTech-Inbox` | 5 industry subdirs, all empty | H-06 | SEPARATELY_AUTHORIZED |
| `D:\CloudTech-Live-Execution\CloudTech_rc2_Live_Direct_Execution_20260925` | 129/129 pytest PASS | H-13 | SEPARATELY_AUTHORIZED |

| Field | Value |
|---|---|
| Authorization needed | Recursive directory deletion |
| AGENTS.md rule | `delete any file` |
| Reversible alternative used | None — directories on disk, no mutation |

## 8. Personal / session files (L-11..L-16, L-32..L-33)

| Path | Reason quarantined by Phase-2 | Audit ID | Phase-2 disposition |
|---|---|---|---|
| `C:\Users\xinzh\.workbuddy\memory\45e357fa-…_memory.md` | **MOVED** to `D:\AIOS\_quarantine\retired-assets\20261008\memory\` (reversible) | B-01 | DONE in Phase-2 quarantine |
| `C:\Users\xinzh\.workbuddy\storage\…\home-first-screen-cache.json` | **MOVED** to quarantine | B-02 | DONE in Phase-2 quarantine |
| `C:\Users\xinzh\.workbuddy\storage\…\skills-installed-store.json` | **MOVED** to quarantine | B-03 | DONE in Phase-2 quarantine |
| `C:\Users\xinzh\.workbuddy\plugins\…\zxygj-business-data\` | **MOVED** to quarantine | B-04 | DONE in Phase-2 quarantine |
| `C:\Users\xinzh\.workbuddy\sessions\23852.json` | **MOVED** to quarantine (confirmed pre-retirement session, cwd `D:\1\WorkBuddy`) | B-06 | DONE in Phase-2 quarantine |
| `C:\Users\xinzh\.codex\sessions\2026\09\` + `10\` | Archive of pre-retirement Codex sessions | B-05 | SEPARATELY_AUTHORIZED — file move (reversible only if backup retained) |
| HKCU Run key `HideConsoleWindowsV3` | `D:\AIOS\_hide_console_windows_v3.py` is the registry-keyed startup script | L-32 | SEPARATELY_AUTHORIZED — registry edit (reversible; irreversible without backup) |
| HKCU Run keys beyond AIOS (WorkBuddy.WorkBuddy, OneDrive, MicrosoftEdgeAutoLaunch) | Default user-installed startup items | L-33 | SEPARATELY_AUTHORIZED — user may want to keep these |

| Field | Value |
|---|---|
| Phase-2 reversible alternative used | **Quarantine (move, never delete)** — 5 WorkBuddy assets moved to `D:\AIOS\_quarantine\retired-assets\20261008\`. See `quarantine_manifest.json` for SHA-256 + restore instructions. |

## 9. Within-scope archive directories (L-18..L-30)

| Path | Audit ID | Phase-2 disposition |
|---|---|---|
| `D:\AIOS\_archived_2026-09-18` (17 entries) | AR-01 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_archived_20260925_P0` (25 .py/.bak + 12 .pid + SSOT + .cmd + .ps1) | AR-02 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_archived_20260925_R259_popup_cure_rebuild` (4 .bak files) | AR-03 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_backup_aios_exe_周二022609_093048` + `_093503` (4 daemon binaries) | AR-04 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_backups` (3543 files; restore source for mirror) | AR-05 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_backups_2026-09-29` | AR-06 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_backups_relinked_1790674911` | AR-07 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_schtasks_bak_R344_*` + `_schtasks_bak_R349_*` (5 task XML) | AR-08 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_r274_install_backup` (6 .bak files) | AR-09 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_r348_model_swap_bak_20260930-092918` | AR-10 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\cloudtech-saas` (13 files) | L-28 | SEPARATELY_AUTHORIZED (service must be un-installed first) |
| `D:\AIOS\_dr_v3.0_uncompressed_workspace` | L-29 | SEPARATELY_AUTHORIZED |
| `D:\AIOS\_out` (3 PNG screenshots) | L-30 | SEPARATELY_AUTHORIZED (historical evidence) |

| Field | Value |
|---|---|
| Authorization needed | Recursive directory deletion |
| AGENTS.md rule | `delete any file` |
| Reversible alternative used | None — directories on disk, no mutation |

## 10. Service uninstall + scheduled task deletion (L-34..L-36)

| Operation | Audit ID | Phase-2 disposition |
|---|---|---|
| Uninstall 8 `daemons_v2` WinSW services (`winsw.exe uninstall *.xml`) | L-34 | SEPARATELY_AUTHORIZED |
| Delete 4 R65 `AIOS_*` residual tasks (already registered + Ready) | L-35 | SEPARATELY_AUTHORIZED |
| Stop + delete `\AIOS_E_Drive_DailyBackup_R1331` task (currently Running) | L-36 | SEPARATELY_AUTHORIZED — affects daily mirror |

| Field | Value |
|---|---|
| Authorization needed | `sc delete` + `schtasks /Delete` |
| AGENTS.md rule | `OS service restart` |
| Reversible alternative used | None — services / tasks still registered |

## 11. Git history rewrite (L-37)

| Operation | Audit ID | Phase-2 disposition |
|---|---|---|
| `git filter-repo` / `git rebase -i` to remove historical references | L-37 | **NOT RECOMMENDED** — history rewrite is destructive + breaks commit SHAs |

| Field | Value |
|---|---|
| Authorization needed | Explicit user authorization |
| AGENTS.md rule | (Multiple — see audit) |
| Reversible alternative used | None — only justification is audit revelation of sensitive material (AR-0061 `.env` / AR-0062 `.jwt_secret` paths were NOT read per contract) |

## 12. Cloud backup & E:\AI_Backup purge

| Path | Reason | Phase-2 disposition |
|---|---|---|
| Cloud backups (any provider) | Audit contract hard line | **NOT IN PHASE-2 SCOPE** — `delete cloud backups` explicitly forbidden by contract §2.13 |
| `E:\AI_Backup` mirror target | Audit contract hard line | **NOT IN PHASE-2 SCOPE** — `delete E:\AI_Backup` explicitly forbidden |

| Field | Value |
|---|---|
| Authorization needed | Outside Phase-2 — requires fresh round beyond this contract |
| AGENTS.md rule | `delete any file` + `OS service restart` (mirror) |

## 13. CloudTech-specific model / registry edits (L-11..L-17 phase-2 surface NOT done)

| Operation | Audit ID | Phase-2 disposition |
|---|---|---|
| Edit `45e357fa-…_memory.md` memoryBlock JSON (already moved; no further edit) | L-11 | **SATISFIED** by quarantine move (file removed from WorkBuddy loader path) |
| Edit `home-first-screen-cache.json` to remove 装修 entries | L-12 | **SATISFIED** by quarantine move |
| Edit `skills-installed-store.json` to remove 装修云管家 | L-13 | **SATISFIED** by quarantine move |
| Delete `zxygj-business-data` plugin directory | L-14 | **SATISFIED** by quarantine move |
| Archive `~/.workbuddy/sessions/23852.json` | L-15 | **SATISFIED** by quarantine move |
| Archive Codex pre-retirement sessions | L-16 | SEPARATELY_AUTHORIZED — separate file move |

## 14. Reconciliation summary

| Category | Phase-2 SAFE_REVERSIBLE done | Deferred to separate auth |
|---|---|---|
| Policy SSOT + lifecycle + gate + scanner + quarantine manifest | YES (this contract) | — |
| WorkBuddy persistent profile quarantine (5 assets) | YES — moved, manifest + DO_NOT_INDEX written | — |
| Live CloudTech gateway teardown | — | YES (L-01) |
| CloudTech Windows service stop+delete | — | YES (L-06) |
| 7 CloudTech scheduled task delete | — | YES (L-08 / L-09) |
| E:\AI_Backup mirror scope change | — | YES (L-17) |
| Root installer scripts delete | — | YES (L-04 etc.) |
| Out-of-scope `D:\CloudTech-*` directory delete | — | YES (L-02..L-05) |
| Cloud backup purge | — | YES (explicitly forbidden by contract) |
| `D:\AIOS\cloudtech-saas\` directory delete | — | YES (L-28, after service un-install) |
| Archive directories (`_archived_*`, `_backup*`) delete | — | YES (L-18..L-27) |
| 8 daemons_v2 WinSW services uninstall | — | YES (L-34) |
| 4 R65 residual tasks delete | — | YES (L-35) |
| Daily backup task stop+delete | — | YES (L-36) |
| Git history rewrite | — | NOT RECOMMENDED (L-37) |
| HKCU Run keys remove (WorkBuddy/OneDrive/Edge) | — | YES (L-32 / L-33) |
| Codex session archive | — | YES (L-16) |
| `_aios_cloudtech_bridge.py` module delete | — | YES (after bridge is decommissioned) |

## 15. Reversibility — everything done is reversible

Phase-2 SAFE_REVERSIBLE summary:
- Policy SSOT (`product_strategy.v1.json` + schema + sha256) → reversible (edit / replace)
- Lifecycle registry (`requirements_lifecycle.py`) → in-memory + JSON persistence (no destructive op)
- Scanner (`contamination_scanner.py`) → read-only
- Strategy gate (`strategy_gate.py`) → no I/O outside risk-envelope write (preserved contract)
- Quarantine (5 WorkBuddy assets) → **manifest at `D:\AIOS\_quarantine\retired-assets\20261008\quarantine_manifest.json` provides SHA-256 + restore instructions for every file**. No `os.remove`, no `shutil.rmtree`, no `del` of source.
- DO_NOT_INDEX.txt marker → reversible (delete marker)

The single irreversible change in this Phase-2 contract is:
- **None** — Phase-2 made no irreversible change.

## 16. Authorization needed to act on this manifest

To proceed with any item above, the user must:
1. Authorize the operation explicitly (per AGENTS.md `requires_authorization` rules).
2. Provide exact paths / operation / desired outcome.
3. Accept that this is a future planning round, NOT part of the current Phase-2 contract.

**End of deferred manifest.**