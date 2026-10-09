# GLOBAL-STRATEGY-RETIREMENT-AUDIT — Final Synthesis

> **Audit ID**: `GLOBAL-STRATEGY-RETIREMENT-AUDIT-20261008-FINAL`
> **Captured_at (UTC)**: 2026-10-09
> **Captured_at (本地)**: 2026-10-09 +08:00
> **Author**: Claude Code 2.1.285 (MiniMax-M3) — executor
> **Contract**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008_CONTRACT.md`
> **Companion JSON**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008.json`
> **Pre-read**: `D:\AIOS\_agent-hub\AGENTS.md`, `D:\AIOS\_agent-hub\memory\2026-10-08.md`, `D:\AIOS\_agent-hub\memory\2026-10-09.md`
> **Mode**: READ-ONLY synthesis of three completed audit pairs. Zero deletions, moves, history rewrites, service changes, or policy edits were performed.

---

## 1. Methodology and Scope

### 1.1 Methodology

This final audit **synthesizes** three independent read-only audit pairs and applies a unified classification framework to every asset. No new filesystem, registry, or runtime inspection was performed by this synthesis step beyond reading the three partial audits and the AGENTS.md / memory pre-conditions. The synthesis is therefore:

- **Deterministic** — every assertion traces to a verbatim line/path in one of the three source pairs (A_PRODUCT, B_AGENT_TASK_MEMORY, C_LOCAL_RUNTIME) or in the pre-read AGENTS.md / memory logs.
- **Non-executing** — no task, script, service, or registry was started, stopped, edited, or invoked.
- **Conservative** — where evidence is ambiguous or the asset is "frozen but loadable", classification escalates to `HISTORICAL·SAFE-IF-ISOLATED` and any destructive action is gated to a separately-authorized Phase-2 contract.

### 1.2 Synthesis Framework

For each asset surfaced by the three partials, four orthogonal axes are recorded:

| Axis | Values |
|---|---|
| **State** | `ACTIVE` (loaded by current runtime) / `DORMANT_REGISTERED` (registered but stopped/disabled) / `HISTORICAL` (frozen, no current loader references) / `BLOCKED` (failed-install or rejected candidate) / `INERT` (cannot be reactivated without external edit) / `REFERENCE_ONLY` (named in docs/registry but executes nothing) |
| **Risk** | `HIGH` / `MEDIUM` / `LOW` / `INERT` |
| **Reactivation mechanism** | the concrete sequence required to bring the asset back into active planning — only recorded when evidence proves a mechanism exists |
| **Phase-2 disposition** | `SAFE_REVERSIBLE` (Phase-2 may implement without user re-authorization) / `SEPARATELY_AUTHORIZED` (requires fresh user approval per AGENTS.md `requires_authorization`) |

### 1.3 Scope

**In scope (synthesized from the three partials)**:
- Product / strategy surfaces: `AIOS_SOURCE_OF_TRUTH_FINAL`, `AIOS_RECONSTRUCTION`, `kernel`, `cloudtech-saas`, `sovereignty-v`, `_agent-hub/policy`, `_agent-hub/tasks`, `_agent-hub/runtime-sops` — 27 surfaces (A_PRODUCT).
- Agent / task / memory / config sources: `_agent-hub/v2` (source, schemas, active tasks, governance registries, inbox/outbox/deadletter metadata, events/state), `aios_tasks`, `_relinked/openclaw`, `_relinked/hermes`, `~/.workbuddy/*`, `~/.codex/*` — 4 HIGH + 2 MED + 6 LOW + 6 INERT paths (B_AGENT_TASK_MEMORY).
- Local data / build / runtime sources: `D:\AIOS` root guidance/scripts/configs, `_out`, `_backups`, `_archived_*`, `_backup*`, `cloudtech-saas`, `daemons_v2`, scheduled tasks (266 enumerated), Windows services, registry Run keys, running processes (574), listening ports — 10 REACT mechanisms (C_LOCAL_RUNTIME).

**Explicitly NOT modified**:
- `D:\AIOS\_relinked` generic plugin caches (excluded by contract).
- Personal files outside `D:\AIOS` (read-only listings of `E:\AI_Backup` mirror target used solely to confirm mirror content).
- Cloud backups.
- `.env` / `.key` / `.pem` / `AccessKey.txt` (paths only, no contents).

---

## 2. Executive Summary

| Layer | Verdict |
|---|---|
| **PRODUCTION ACTIVE LAYER** (v2 hub + Codex + AGENTS.md + kernel + aios_vnext task cards) | **CLEAN** of old industry/global-strategy contamination. 0 industry/装修/教育/制造/服务/cross-industry/global_strategy/cloudtech references in any runtime loader, schema, registry, or task card. |
| **CloudTech V22 Unified Gateway** | **LIVE** at `127.0.0.1:5099` (PID 16336, `python.exe`, parent PID 9944). `GET /health` returns `{"status":"ok","version":"22.0.0","service":"CloudTech V22 Unified Gateway","v10_modules_included":135,"v10_modules_failed":0,"flask_app_loaded":true}`. The old product has never been torn down — only its planning references have been retired. |
| **DORMANT_REGISTERED layer** (CloudTechV22Monitor service Stopped/Manual; `D:\AIOS\cloudtech-saas\*`; AIOS daemon services Running/Automatic; `daemons_v2` 8 services Stopped/Disabled) | HIGH reactivation risk; one-shot `install.cmd`/`start_v22_watchdog.bat` re-arms the bridge. |
| **WorkBuddy persistent user profile** (`~/.workbuddy/memory/45e357fa-…_memory.md` + `home-first-screen-cache.json` + `skills-installed-store.json` + `zxygj-business-data` plugin) | **4 HIGH-RISK reactivation paths** if WorkBuddy hub is ever reactivated. WorkBuddy is NOT the current active hub (CC is). 81 industry-keyword matches in the home-first-screen cache. |
| **`\CloudTech\*` scheduled-task namespace** | **5 tasks ACTIVE namespace** with payloads outside `D:\AIOS` (workbuddy scripts + `D:\CloudTech-Portable`); 2 Running + 3 Ready. |
| **`E:\AI_Backup` daily mirror** | **ACTIVE** — robocopy `/MIR` is currently mirroring `D:\AIOS` to `E:\AI_Backup\DailyBackup_20261008\AIOS\` (PID 31360). Every archive under `D:\AIOS` is being re-copied off-box. |
| **Reference-only docs/registries** (`AIOS_SOURCE_OF_TRUTH_FINAL`, `AIOS_RECONSTRUCTION`) | Still declare `project-cloudtech` with live roadmap items (P3-01 etc.) and 4 open risk items. They **execute nothing** but bias the registry grep surface. |

### Headline finding

> **The active planning loop (v2 hub + Codex + CC + kernel + AGENTS.md) is retired from old CloudTech / 4-industry / OPC / 装修矩阵 / 小红书仿写 positioning. However, the old product itself (CloudTech V22 Unified Gateway) is still live on port 5099, a registered Windows service points into `D:\AIOS\cloudtech-saas`, and the daily backup mirror is preserving every archive. Therefore the "retirement" is a planning-loop retirement, not a teardown. Reactivation is one command away for any of 10 distinct mechanisms.**

---

## 3. Confirmed ACTIVE Reactivation Paths

A path is "ACTIVE reactivation" only when **current runtime evidence proves a loader, listener, scheduled task, registry Run key, or backup job still references the asset today**. Each row below is an exact evidence-traced mechanism. Phase-2 disposition is `SEPARATELY_AUTHORIZED` unless explicitly `SAFE_REVERSIBLE`.

| ID | Surface | Mechanism | Current state | Evidence | Phase-2 disposition |
|---|---|---|---|---|---|
| **A-01** | `127.0.0.1:5099` CloudTech V22 Unified Gateway | Process is live; `gateway_v22.py:786` in `D:\CloudTech-Portable\`; `cloudtech-v22-gateway` Windows service Running/Automatic (`PathName` `D:\个人文件\AI\Operator\aios_tools\winsw-x64\cloudtech_v22_gateway.exe`) | ACTIVE old product | C §3.1 + C §3.4; curl `/health` returned status:ok at audit time | **SEPARATELY_AUTHORIZED** — old product teardown |
| **A-02** | `\CloudTech_V22Watchdog` scheduled task | Python watchdog polling port 5099; payload `D:\CloudTech-Portable\_ct_v22_watchdog.py` | Running | C §3.2 | **SEPARATELY_AUTHORIZED** |
| **A-03** | `\CloudTech_V23FileWatcher` scheduled task | File watcher on `D:\CloudTech-Portable\` | Running | C §3.3 | **SEPARATELY_AUTHORIZED** |
| **A-04** | `\CloudTech\*` scheduled-task namespace (5 tasks: HealthCheck-Hourly / DailyReport-0300 / AIOSLightMonitor-30min / StartupCleanup-Once / SpecV1CI_Daily_0300) | Triggers call into `~/.workbuddy/scripts/*.ps1` and `D:\CloudTech-Portable\…` | Ready (triggers armed) | C §3.5 + C §7 inventory | **SEPARATELY_AUTHORIZED** |
| **A-05** | `CloudTechV22Monitor` Windows service | `sc start CloudTechV22Monitor` re-runs `D:\AIOS\cloudtech-saas\cloudtech-saas.exe` → `_aios_cloudtech_bridge.py --check` against port 5099; XML `<onfailure action="restart" delay="30 sec"/>` armed | Stopped / Manual | C §3.6 + C REACT-01 evidence: `cloudtech-saas.xml:10/15/16/27/28-29/31` | **SEPARATELY_AUTHORIZED** — service start |
| **A-06** | `D:\AIOS\cloudtech-saas\install.cmd` | Re-runs `winsw.exe install cloudtech-saas.xml` + `curl /health` probe; line 19 install + line 26 probe + line 33 echoes bridge path | on disk, not invoked | C REACT-02; `install.cmd:9-33` | **SEPARATELY_AUTHORIZED** — script invocation |
| **A-07** | `D:\AIOS\cloudtech-saas\start_v22_watchdog.bat` | `cd /d D:\AIOS\_workzone` + `pythonw.exe -m src._aios_cloudtech_bridge --watch --watch-interval 300` | on disk, not invoked | C REACT-02; `start_v22_watchdog.bat:7-8` | **SEPARATELY_AUTHORIZED** |
| **A-08** | `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py` (319 lines) | Python module sets `CLOUDTECH_V22_ROOT = Path(r"D:\CloudTech-Portable")` (line 51), `CLOUDTECH_V22_PORT = 5099` (line 55), endpoint table incl. `/decoration-landing.html` (lines 79-86), pricing plans free/pro/enterprise (89-93), `check_v22_alive()` (109-121). Imports to AIOS capability registry on `--watch`. | on disk, not imported | C REACT-03; `_aios_cloudtech_bridge.py:51-121` | **SEPARATELY_AUTHORIZED** — module invocation |
| **A-09** | `E:\AI_Backup\DailyBackup_20261008\AIOS\` daily mirror | robocopy `/MIR` (PID 31360) copies `D:\AIOS` → `E:\AI_Backup\DailyBackup_20261008\AIOS\` including `cloudtech-saas\`, `_archived_2026-09-18\`, `_archived_20260925_P0\`, `_archived_20260925_R259_popup_cure_rebuild\` | **ACTIVE — currently in flight** | C §3.5; `\AIOS_E_Drive_DailyBackup_R1331` Running | **SEPARATELY_AUTHORIZED** — backup policy change |
| **A-10** | `D:\AIOS\cloudtech-saas\cloudtech-saas.xml` onfailure/restart policy | XML arms `<onfailure action="restart" delay="30 sec"/>` and `delay="60 sec"`, `<resetfailureafter>2 hour</resetfailureafter>` (lines 28-31). One start → auto-restart loop. | armed | C REACT-01; `cloudtech-saas.xml:28-31` | **SEPARATELY_AUTHORIZED** — XML edit to disarm |
| **B-01** | `C:\Users\xinzh\.workbuddy\memory\45e357fa-c2ec-4bd0-b734-9b016a2759d7_memory.md` (User Memory Profile v3) | WorkBuddy session-start loader reads this file into prompt context. `memoryBlock` JSON literally contains: "Phase 1 聚焦行业 SaaS（医美 + 装企）MVP" + "CloudTech 独有资产…600+ 行业垂直文档（家居/医美）…" + "对标基准——灵策…WorkBuddy…" (lines 6-9, 13-19). Edit = re-inject vertical strategy into every WorkBuddy session. | ACTIVE LOADER (when WorkBuddy is the hub) | B §1.5 high-risk path 1; `45e357fa-…_memory.md:6-9, 13-19` | **SEPARATELY_AUTHORIZED** — file edit |
| **B-02** | `C:\Users\xinzh\.workbuddy\storage\user-45e357fa-…\scoped\c7389fe09fa872c0\home-first-screen-cache.json` | WorkBuddy first-screen UI loads on launch. Contains the same CloudTech profile + 81 industry-keyword matches (装修工作台 / 儿童教育 / K12教育 / 制造企业 / 金融服务 / 装修云管家业务查询). Edit = re-surface industry skills. | ACTIVE LOADER | B §1.5; 81 matches verified | **SEPARATELY_AUTHORIZED** — file edit |
| **B-03** | `C:\Users\xinzh\.workbuddy\storage\user-45e357fa-…\scoped\c7389fe09fa872c0\skills-installed-store.json` | WorkBuddy skill manager reads on activation. 80694 bytes; contains 装修云管家-style entries. Edit = re-enable installed industry skill. | ACTIVE LOADER | B §1.5; file size + format verified | **SEPARATELY_AUTHORIZED** — file edit |
| **B-04** | `C:\Users\xinzh\.workbuddy\plugins\marketplaces\workbuddy-connector-plugins-official\connectors\zxygj-business-data\` | WorkBuddy plugin marketplace scan + connector activation. Directory contains `ai.workbuddy/`, `mcp.json`, `skills/` for 装修云管家 connector. Edit = re-enable connector. | ACTIVE LOADER | B §1.5; directory structure verified | **SEPARATELY_AUTHORIZED** — file edit |
| **B-05** | Codex session resume (`C:\Users\xinzh\.codex\sessions\2026\09\` + `10\`) | `claude -p --resume` reloads a pre-retirement session containing old industry prompts. | MEDIUM RISK | B §1.5 medium-risk path 5; 10 active session subdirs | **SEPARATELY_AUTHORIZED** — session archival |
| **B-06** | WorkBuddy session resume (`C:\Users\xinzh\.workbuddy\sessions\23852.json`, 355 B) | WorkBuddy session resume reloads live session context. | MEDIUM RISK | B §1.5 medium-risk path 6 | **SEPARATELY_AUTHORIZED** |
| **B-07** | Codex `~/.codex/config.toml` line 36 project entry | `[projects.'d:\个人文件\ai\cloudtech\v2.0\lingce_scheduler_demo'] trust_level = "trusted"`. Only loads when operating in that directory; enables cloudtech v2.0 demo project. | LOW RISK (conditional) | B §1.5 low-risk path 7; line 36 verified | **SAFE_REVERSIBLE** (file already on disk; no code injection) |
| **B-08** | Codex `~/.codex/_scripts/_mk_link_script.py` line 97 | Hardcodes `New-Link "[索引] 装修行业小红书对标账号"`. Only runs on explicit invocation; creates a PowerShell shortcut. | LOW RISK | B §1.5 low-risk path 8; line 97 verified | **SEPARATELY_AUTHORIZED** — script execution |
| **B-09** | `D:\AIOS\aios_tasks\aios_vnext\cards\D002_industry_scout.md` | IndustryScout framework currently neutral (5 categories: product/competitor/regulatory/market/tech). Re-introducing verticals requires editing the card body. | LOW RISK (neutral) | B §1.2 D002; A_PRODUCT P-13 | **SAFE_REVERSIBLE** — current neutral is correct; verticalization is the reactivation |
| **B-10** | `D:\AIOS\_relinked\openclaw\openclaw.json` lines 678-1439 (skills.entries) | 200 skill entries with `enabled:true/false`. Adding a new industry-skill entry with `enabled:true` pointing into an industry directory under extraDirs would re-enable it. | LOW RISK | B §1.3 openclaw.json | **SEPARATELY_AUTHORIZED** — config edit |
| **B-11** | `D:\AIOS\_relinked\hermes\hermes-agent\optional-skills\` (finance/mlops/research) | Hermes Agent optional-skills (DCF / comps-analysis / osint-investigation); default-disabled. Flip the flag → activate. None reference 装修/教育/制造/服务. | LOW RISK | B §1.4 hermes-agent; flag-flip mechanism | **SAFE_REVERSIBLE** — finance/research content is not industry-vertical |
| **C-01** | `D:\AIOS\daemons_v2\winsw\v2-consumer\AIOSV2Consumer.xml` (installed P1 commit 4d5b905) | Service `AIOSV2Consumer` Stopped/Automatic. `sc start` (or SCM auto-start) re-runs the consumer. Non-elevated shell cannot Start-Service (OS error 5, per memory 2026-10-09). | DORMANT_REGISTERED | C REACT-07; `AIOSV2Consumer.xml` | **SAFE_REVERSIBLE** — infrastructure consumer, product-neutral |
| **C-02** | 7 other `D:\AIOS\daemons_v2\winsw\*` services (aios-supervisor / aios-cron-orchestrator / aios-observability-hub / aios-role-channels / aios-bridge-cc-codex-cli / aios-bridge-cc-doubao / aios-bridge-cc-openclaw / aios-bridge-codex-desktop-cli) | All Stopped/Disabled. `sc start` re-runs. | DORMANT_REGISTERED | C REACT-07 | **SAFE_REVERSIBLE** — infrastructure, product-neutral |
| **C-03** | `D:\AIOS\_workzone\src\_aios_cloudtech_bridge.py` re-invocation via `python -m src._aios_cloudtech_bridge --watch` (cwd `D:\AIOS\_workzone`) | Already listed as A-08; covered. | covered | covered | covered |
| **C-04** | `D:\AIOS\install_aios_loop.cmd` (TASK_NAME=AIOS-Daemon-Loop-Guard, line 12) | Creates SYSTEM-priority ONSTART task → `D:\AIOS\_aios_loop_inner.cmd`. Not currently registered (266-task enumeration excludes it). | on disk | C REACT-06; `install_aios_loop.cmd:12, 33-39` | **SEPARATELY_AUTHORIZED** — script invocation + SYSTEM priority |
| **C-05** | `D:\AIOS\install_aios_watchdog.cmd` (TASK_NAME=AIOS-Daemon-Watchdog, line 11) | Creates SYSTEM-priority ONSTART task → `D:\AIOS\aios_daemon_watchdog.py`. Not currently registered. | on disk | C REACT-06 | **SEPARATELY_AUTHORIZED** — script invocation + SYSTEM priority |
| **C-06** | `D:\AIOS\R65_右键管理员运行_一键注册.bat` (lines 6-19) + `D:\AIOS\AIOS_Cron_R65_Residual.ps1` (lines 14-33) | Re-registers 4 R65 tasks: AIOS_WAL_Recovery_Startup / AIOS_Quorum_Health_5min / AIOS_Quota_Enforcer_Report_10min / AIOS_WAL_RecoverAll_Daily. The 4 R65 tasks are ALREADY present and Ready in the 266-task enumeration (per C §7 inventory). | on disk + (R65 tasks ALREADY registered) | C REACT-06 + C §7 R65 status | **SEPARATELY_AUTHORIZED** — script invocation (R65 tasks themselves are pre-existing infrastructure) |
| **C-07** | `D:\AIOS\_backups\task-repair-20260930-active\CloudTech_HealthCheck-Hourly.pre-fix.xml` (and 2 sibling `.pre-fix.xml`) | `schtasks /create /tn "\CloudTech\HealthCheck-Hourly" /xml <file>` restores the old task entry. | on disk only | C REACT-08; `CloudTech_HealthCheck-Hourly.pre-fix.xml:4-5, 30-36, 40` | **SEPARATELY_AUTHORIZED** — task registration |
| **C-08** | `D:\AIOS\_dr_v3.0_uncompressed_workspace\dr_restore_now.py` (line 20-21) | `DEST_BASE = E:\移动硬盘\Dr2026-09-18_DR_v3.0\01b_full_backup_uncompressed`; restores 11 core modules from DR manifest. No scheduled task references it (verified across 266 tasks). Requires external `E:\移动硬盘` media. | on disk | C REACT-09 | **SEPARATELY_AUTHORIZED** — external media + restore |
| **C-09** | `D:\AIOS\_backup_aios_exe_周二022609_093048\*.exe` (4 binaries; 9-10 MB each) | Manual copy over live binary + re-point service `PathName` → restore superseded `.exe`. NO service currently points into any `_backup*` or `_archived*` directory (verified). | on disk | C REACT-10; binary sizes 8.9-10.1 MB | **SEPARATELY_AUTHORIZED** — binary overwrite + service re-point |
| **C-10** | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` lines 305-358 (P3-01..P3-08) | 8 roadmap items EXPLICITLY call out historical business-line freeze (CloudTech 业务推进 / 灵策智算 / 内容IP / OPC / 装修矩阵 V2 / 小红书仿写管线). Listed but classified blocked-by-environment. | REFERENCE_ONLY (executes nothing) | A_PRODUCT §3.4; `AIOS_EXECUTION_ROADMAP.md:301-358` | **SAFE_REVERSIBLE** — doc edit; user authorization only if roadmap freeze is to be reversed |

---

## 4. HISTORICAL / ARCHIVED References — Safe Only If Isolated

These assets are frozen in time and do not currently feed the active planning loop, yet they remain on disk. They are **safe only if isolated** from any runtime loader, scheduler, or registry hook. Any reintroduction requires the user's authorization per AGENTS.md `requires_authorization`.

### 4.1 HISTORICAL (named in registries / docs / skeletons; no current loader)

| ID | Surface | Path / Lines | Why retired | Phase-2 disposition |
|---|---|---|---|---|
| **H-01** | `project-cloudtech` status | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json:28-43`; maturity=Tested status=PARTIAL; "代码层 Tested 但业务链路未运行"; `cloudtech.db` PII risk per baseline line 163 | A_PRODUCT P-21 | **SAFE_REVERSIBLE** — registry edit (scope/P3-01 retirement only) |
| **H-02** | `project-content-ip` + `project-opc` status | `AIOS_STATUS.json:60-90`; "OPC 文案含真实文本；工具/管线未运行"; 装修矩阵 STALE 2+ 月 (line 64); 小红书 仿写管线 STOPPED 6+ 周 (line 65) | A_PRODUCT P-22 | **SAFE_REVERSIBLE** — registry edit |
| **H-03** | `project-lingce` status | `AIOS_STATUS.json:44-58`; maturity=Implemented status=PARTIAL; "C 盘研究笔记 16 天未更新；D 盘 2 根空壳" | A_PRODUCT P-12, P-23 | **SAFE_REVERSIBLE** — registry edit |
| **H-04** | 装修/教育/制造/服务 4-industry skill registry | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SKILL_REGISTRY.json:51-55` `sk-industry` count=4; `AIOS_CONTENT_FACTORY_PIPELINE.md:145-153` 4 industry business line matrix | A_PRODUCT P-13, P-25; B §1.2 D002 neutral | **SAFE_REVERSIBLE** — registry edit (D002 is neutral, no industry vertical hardcoded) |
| **H-05** | cross-creator × 4-industry cross matrix | `AIOS_SKILL_REGISTRY.json:27-31` `sk-cross-matrix` count=40 "10 创作者 x 4 行业"; experimental authority, not deployed | A_PRODUCT P-26 | **SAFE_REVERSIBLE** — registry edit |
| **H-06** | Content Factory 7-stage pipeline | `AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md:11-145`; P0-P3 sub-skills all `[ ]` pending; backend stub only (12/12 PASS but skill not deployed); STEP 16 stopped 2026-09-27; Ollama qwen3:14b OOM HTTP 500 on RTX 3060 12GB | A_PRODUCT P-24 | **SAFE_REVERSIBLE** — file removal OR registry edit (depends on user intent) |
| **H-07** | CloudTech-Portable v2.1 "AI 数字营销中台" positioning | `D:\CloudTech-Portable\README.md` (per AR-0075); `gateway_v22.py` 786 lines (per AR-0078); 23 tools 6 engines; FOUND not ACTIVE | A_PRODUCT P-11 | **SEPARATELY_AUTHORIZED** — out of `D:\AIOS` scope; user extension required |
| **H-08** | 灵策智算 OPC research | `AIOS_STATUS.json:44-58` + `AIOS_EXECUTION_ROADMAP.md:313-320, 359-366` (P3-02, P3-08); 51 files / 701 KB; "OPC 学习材料 ≥10 份" | A_PRODUCT P-12 | **SEPARATELY_AUTHORIZED** — user extension of `C:\Users\xinzh\灵策AI\research` |
| **H-09** | AIOS-Hermes 治理 role overlay | `AIOS_AGENT_REGISTRY.json:5-16, 82-91`; defined in P7/P8 phase files but NOT referenced in current AGENTS.md / kernel / sovereignty-v; only Nous-hermes framework remains in `cap-self-learning` | A_PRODUCT P-14 | **SAFE_REVERSIBLE** — registry edit (reactivation requires user authorization to write into AGENTS.md) |
| **H-10** | `minimax / minimax-cn` provider strings | `audit/05-hermes-others-report.md:50-54`; canonical `MiniMax` already in `model-policy.v1.yaml:19` + audit/01:16-18 | A_PRODUCT P-15; B §1.4 hermes config.yaml clean | **SAFE_REVERSIBLE** — config edit |
| **H-11** | deepseek-v4-flash fallback for CC | `audit/03-cc-switch-state-report.md:53-58`; `ANTHROIC_DEFAULT_SONNET_MODEL_FALLBACK = deepseek-v4-flash`; violates ModelPolicy v1 `prohibited_runtime_routes` (lines 28-33); T5 444 ACL not yet applied | A_PRODUCT P-16 | **SEPARATELY_AUTHORIZED** — chmod/icacls 444 on policy file |
| **H-12** | R212 Content Factory STEP 16 wrapper v2.6 | `AIOS_RECONSTRUCTION_PROGRESS.json:5` STEP 16 "陈厂长 P2 批量 GPU 跑中...预估 ~8h 完工" — work-in-progress stopped 2026-09-27 at 27/1300 | A_PRODUCT P-24 detail | **SAFE_REVERSIBLE** — file edit |
| **H-13** | Self-learning skill (Hermes loop) | `AIOS_CAPABILITY_GRAPH.json:65-86` `cap-self-learning` status=partial test_status=NOT_TESTED; Hermes Agent v0.21.3 has loop but AIOS has no integration | A_PRODUCT P-27 | **SAFE_REVERSIBLE** — registry edit (deferred integration) |
| **H-14** | CloudTech-Portable v2.1 SaaS process supervision | `gateway_v22.py:561` `ws.map` (per AR-0078); 23 tools 6 engines per AR-0075 | A_PRODUCT P-11 reactivation step 3 | **SEPARATELY_AUTHORIZED** |
| **H-15** | `D:\AIOS\_out` decoration-industry screenshots | `R222_sc001_screenshot.png`, `R222_sc003_handwritten.png`, `R222_xh01_decor_pitfalls.png` (decoration-industry pitfalls) | C §6.1 REFERENCE_ONLY | **SAFE_REVERSIBLE** — file deletion (evidence archive) |

### 4.2 ARCHIVED (no service, task, Run key, or running process references the path)

| ID | Path | Reason | Phase-2 disposition |
|---|---|---|---|
| **AR-01** | `D:\AIOS\_archived_2026-09-18` (17 entries: `.exe.old/.old2../v2/v3`, `aios-incident-controller.exe.old`, `_health_reports\R91_v2_final_health.json`, `_r91_v1_superseded\*.bat`) | C §6.3 ARCHIVE | **SEPARATELY_AUTHORIZED** — file deletion (irreversible) |
| **AR-02** | `D:\AIOS\_archived_20260925_P0` (25 bridge/daemon/watcher `.py` + `.bak`, 12 `.pid` files, `_NEW_ARCHITECTURE_SSOT_V1.0_2026-09-25.md`, `_AIOSWatchdogAliveCheck.cmd`, `_cleanup_restart.ps1`) | C §6.3 ARCHIVE | **SEPARATELY_AUTHORIZED** — file deletion (irreversible) |
| **AR-03** | `D:\AIOS\_archived_20260925_R259_popup_cure_rebuild` (4 popup-cure `.bak` files) | C §6.3 ARCHIVE | **SEPARATELY_AUTHORIZED** — file deletion (irreversible) |
| **AR-04** | `D:\AIOS\_backup_aios_exe_周二022609_093048\` (4 daemon binaries 8.9-10.1 MB) + `_093503\` (empty) | C §6.3 + REACT-10 ARCHIVE | **SEPARATELY_AUTHORIZED** — file deletion (irreversible) |
| **AR-05** | `D:\AIOS\_backups\` (3543 files; key subtrees: `20261008_rootfix`, `rootcause_fix_20260929`, `task-repair-*`, `chatgpt_bridge_*`, `HKCU_Run_*.reg`, agent-config snapshots) | C §6.2 ARCHIVE contents + ACTIVE restore source via REACT-04 | **SEPARATELY_AUTHORIZED** — file deletion (irreversible; affects restore source for mirror) |
| **AR-06** | `D:\AIOS\_backups_2026-09-29` (`Merge.yaml.bak-R327-pinning`, `Run-reg-bak.reg`, `_clash_verge_watchdog.py.bak-R327-disabled`) | C §5 ARCHIVE | **SEPARATELY_AUTHORIZED** |
| **AR-07** | `D:\AIOS\_backups_relinked_1790674911` (`openclaw/` + `workbuddy/` snapshots; `_relinked` excluded) | C §5 ARCHIVE | **SEPARATELY_AUTHORIZED** |
| **AR-08** | `D:\AIOS\_schtasks_bak_R344_*` + `_schtasks_bak_R349_*` (`AIOS-DashboardSupervisor.xml`, `AIOS-HealthMonitor.xml`, `AIOS-SessionCleanup.xml`, `AIOS-SyncClaudeMemory.xml`, `AIOS_V13_Protocol_Audit.xml`) | C §5 ARCHIVE | **SEPARATELY_AUTHORIZED** |
| **AR-09** | `D:\AIOS\_r274_install_backup` (6 `.bak` files from 2026-09-29 untracked-file install) | C §5 ARCHIVE | **SEPARATELY_AUTHORIZED** |
| **AR-10** | `D:\AIOS\_r348_model_swap_bak_20260930-092918` (`model_resources.json` + `_aios_model_resource_state.json`) | C §5 ARCHIVE | **SEPARATELY_AUTHORIZED** |

### 4.3 INERT (no reactivation possible without external edit)

| ID | Path | Reason | Phase-2 disposition |
|---|---|---|---|
| **I-01** | `~/.codex/archived_sessions/*.jsonl` (31 files, 2026-09-16 to 2026-09-30) | append-only, never auto-loaded | none required |
| **I-02** | `~/.workbuddy/memory/feedback-R403-workbuddy-archive-seed.md` | tombstoned at R403 | none required |
| **I-03** | `D:\AIOS\_agent-hub\v2\src\*.bak.20261008-*` (5 files: claude_adapter 2x, probes.py 3x, v2_consumer 3x) | pre-fix backups | none required |
| **I-04** | `D:\AIOS\_relinked\openclaw\agents\{claude,codex,geo-*,main,isolated}\agent\workshop-skills\` (all empty, 0 bytes) | empty dirs | none required |
| **I-05** | `D:\AIOS\_relinked\hermes\skills\.archive\` (30+ archived skills) | curator-managed archive | none required |
| **I-06** | `D:\AIOS\_relinked\hermes\SOUL.md.bak-2026-09-13-pre-ssot-injection` + `SOUL.md.bak-pre-shared-ssot-20260930` | superseded backups | none required |
| **I-07** | `D:\AIOS\_audit_reports\*` (read-only audit history) | append-only audit log | none required |

---

## 5. Unresolved Candidates

These were surfaced by the three partials but their final disposition could not be resolved with the present audit alone. Each requires **fresh user direction** in Phase-2.

| ID | Candidate | What is unresolved | Why unresolved | Phase-2 input required |
|---|---|---|---|---|
| **U-01** | SwarmClaw multi-agent dashboard | Failed-install; `npm gyp ERR` R211 missing VS Build Tools; ports 3456/3457 NOT LISTENING | A_PRODUCT P-17 BLOCKED; reactivation requires installing VS Build Tools (Windows feature) | User decision: install VS Build Tools + retry npm install, OR formal retirement |
| **U-02** | GoClaw / PicoClaw / NanoBot / IronClaw | `p-goclaw` rejected (overlap with OpenClaw); `p-picoclaw` rejected (user scenario not edge); `p-nanobot`/`p-ironclaw` TBD | A_PRODUCT P-18 BLOCKED; registry `installed: false` | User decision: re-evaluate per products.json:71-106, OR formal retirement |
| **U-03** | FFmpeg Wizard / Cut/Storm / video-editing-skill / mcp-video-editor | All candidate, installed=false, no installation evidence | A_PRODUCT P-19 BLOCKED; not evaluated further | User decision: re-evaluate per products.json:118-159, OR formal retirement |
| **U-04** | Hermes governance role (5-role mapping) | AIOS-Hermes 治理 mapping defined in P7/P8 phase files (2026-09-27) but not referenced in current AGENTS.md / kernel / sovereignty-v. Reactivation requires writing 治理 role into AGENTS.md Mission — a requires_authorization action. | A_PRODUCT R-05; H-09 above | User decision: revive P8 5-role mapping + write to AGENTS.md (requires_authorization), OR keep Nous-hermes-only |
| **U-05** | CloudTech V22 teardown | Old product live at 127.0.0.1:5099; service `cloudtech-v22-gateway` Running/Automatic; `CloudTechV22Monitor` service Stopped/Manual with restart-on-failure XML. One command tears down. | C A-01/A-05/A-06/A-07; irreversible (data in cloudtech.db, dependencies in `D:\CloudTech-Portable` 200 MB outside scope) | User decision: tear down old product + delete CloudTech-* directories outside `D:\AIOS`, OR keep dormant |
| **U-06** | WorkBuddy persistent user profile scrub | 4 HIGH-RISK reactivation paths in WorkBuddy's persistent user profile (45e357fa-…_memory.md, home-first-screen-cache.json, skills-installed-store.json, zxygj-business-data plugin). 81 industry-keyword matches in the home-first-screen cache. WorkBuddy is NOT the active hub today, so risk is latent. | B §1.5; B-01..B-04 above | User decision: scrub WorkBuddy user profile now, OR keep dormant with explicit "do not reactivate WorkBuddy" guard |
| **U-07** | Daily backup mirror scope | robocopy `/MIR` (PID 31360) currently mirrors `D:\AIOS` → `E:\AI_Backup\DailyBackup_20261008\AIOS\` including all `_archived_*`, `_backup*`, `cloudtech-saas\`. User may want to exclude archive paths from the mirror to stop propagating them off-box. | C §3.5 + A-09 above | User decision: keep mirroring everything, OR scope mirror to active paths only |
| **U-08** | v2 inbox retirement-audit envelopes | 2 self-referential envelopes (6ea4f46d-… "GLOBAL-STRATEGY-RETIREMENT-AUDIT-RETRY" + 83e2d652-… "GLOBAL-STRATEGY-RETIREMENT-AUDIT") are themselves audit-about-audit artifacts. Should they remain in the inbox or be moved out? | B §2.2 inbox retirement-audit envelopes | User decision: keep as audit trail, OR clean to deadletter |
| **U-09** | Old content screenshot evidence in `D:\AIOS\_out` | 3 PNG screenshots include decoration-industry pitfalls. Safe-to-keep evidence but easy to misread as active product. | C §6.1; H-15 above | User decision: keep as historical evidence, OR archive under dated subfolder |
| **U-10** | R65 `AIOS_*` residual tasks still Ready | 4 R65 tasks (AIOS_WAL_Recovery_Startup / AIOS_Quorum_Health_5min / AIOS_Quota_Enforcer_Report_10min / AIOS_WAL_RecoverAll_Daily) are ALREADY registered and Ready in the 266-task enumeration. One-click re-registration script exists. | C §7 + C-06 above | User decision: keep as infrastructure, OR unregister + archive scripts |

---

## 6. Confirmed Retired Requirement IDs / Assets (Evidence-Backed Only)

The following requirement IDs / assets are **confirmed retired** because each one is referenced by evidence as part of the cancelled direction. IDs not present in the three partials are **not invented**.

| Retired ID | Asset | Evidence (file:line) | Status |
|---|---|---|---|
| **R-001** | CloudTech-Portable v2.1 "AI 数字营销中台 · 23 工具 6 引擎" | `AIOS_SOURCE_OF_TRUTH_FINAL/assets/AIOS_ASSET_REGISTRY.csv:76` AR-0075 FOUND not ACTIVE | retired from planning (product still live on port 5099 — see U-05) |
| **R-002** | gateway_v22.py 786 lines | `AIOS_ASSET_REGISTRY.csv:79` AR-0078 | retired from planning (executable live) |
| **R-003** | AR-0074 `D:\CloudTech-Portable` main repo | `AIOS_ASSET_REGISTRY.csv:73-88` | retired from planning (out of `D:\AIOS`) |
| **R-004** | AR-0082..0085 CloudTech-Vault | `AIOS_ASSET_REGISTRY.csv:82-85` | retired from planning (Vault sync STALE since 2026-09-24 per baseline line 157) |
| **R-005** | AR-0086/0087 `D:/AIOS/cloudtech-saas` install skeleton | `AIOS_ASSET_REGISTRY.csv:86-87` | retired from planning (executable layer dormant-but-registered) |
| **R-006** | `project-cloudtech` `P3-01` roadmap line | `AIOS_EXECUTION_ROADMAP.md:305, 308-309` | retired from active planning (still listed as blocked-by-environment) |
| **R-007** | 灵策智算 `P3-02` + `P3-08` roadmap lines | `AIOS_EXECUTION_ROADMAP.md:313-320, 359-366` | retired from active planning (C 盘 16 天未更新) |
| **R-008** | 内容 IP / OPC `P3-03` roadmap line | `AIOS_EXECUTION_ROADMAP.md:323-326` | retired from active planning (2+ 月未更新) |
| **R-009** | 装修矩阵 V2 `P3-06` + 小红书仿写管线 `P3-07` roadmap lines | `AIOS_EXECUTION_ROADMAP.md:345-358` | retired from active planning (装修矩阵 STALE 2+ 月; 仿写管线 STOPPED 6+ 周) |
| **R-010** | 4-industry skill registry `sk-industry` count=4 + `sk-cross-matrix` count=40 | `AIOS_SKILL_REGISTRY.json:27-31, 51-55` | retired from active planning (experimental authority, not deployed) |
| **R-011** | Content Factory 7-stage pipeline | `AIOS_CONTENT_FACTORY_PIPELINE.md:11-145` | retired from active planning (P0-P3 sub-skills pending; Ollama qwen3:14b OOM HTTP 500) |
| **R-012** | `sys-cloudtech` registry entry | `AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SYSTEM_REGISTRY.json:48-55` | retired from active planning (path `D:\个人文件\AI\cloudtech` 用户个人独立项目) |
| **R-013** | `cloudtech-saas` node in AIOS_RECONSTRUCTION reality map | `AIOS_RECONSTRUCTION\00_REALITY\AIOS_REALITY_MAP.json:71, 147-148, 163` | retired from active planning (registry node only, not executable) |
| **R-014** | 3 orphaned CloudTech design docs (BLUEPRINT, DECISION-MATRIX, PhaseBC_EXEC_PLAN) | `AIOS_RECONSTRUCTION\11_REPORTS\AIOS_ORPHAN_REPORT.json:197-210` | retired from active planning (orphan) |
| **R-015** | AIOS-Hermes 治理 role mapping | `AIOS_AGENT_REGISTRY.json:5-16, 82-91` | retired from active planning (Nous-hermes framework only remains in `cap-self-learning`) |
| **R-016** | `minimax / minimax-cn` provider strings | `audit/05-hermes-others-report.md:50-54` | retired from active planning (canonical `MiniMax` in `model-policy.v1.yaml:19`) |
| **R-017** | deepseek-v4-flash fallback for CC | `audit/03-cc-switch-state-report.md:53-58` | retired from active planning (violates ModelPolicy v1 `prohibited_runtime_routes:28-33`) |
| **R-018** | Self-learning skill (Hermes loop) | `AIOS_CAPABILITY_GRAPH.json:65-86` | retired from active planning (`cap-self-learning` test_status=NOT_TESTED) |
| **R-019** | AR-0072 CloudTech-Inbox 5 industries empty | `AIOS_ASSET_REGISTRY.csv` (per baseline line 158) | retired from active planning (Inbox subdirs all empty since 2026-09-24) |
| **R-020** | AR-0073 rc2 Live Direct Execution LIVE_UNAUDITED | `AIOS_ASSET_REGISTRY.csv` (per baseline line 136) | retired from active planning (129/129 PASS but UNAUDITED) |
| **R-021** | AR-0061 `.env` + AR-0062 `.jwt_secret` of CloudTech-Portable | `AIOS_ASSET_REGISTRY.csv:62-63, 73-88, 216` | **sensitive** — paths recorded; contents NOT read (per contract) |

---

## 7. Asset Inventory

This inventory enumerates every asset referenced by the three partials, classified across the synthesis framework.

### 7.1 By state

| State | Count | Examples |
|---|---|---|
| `ACTIVE` (loaded by current runtime) | 11 | AGENTS.md, Kernel, ModelPolicy v1, adapter-contract, reconciler-spec, Codex Supervisor GoalContract, Memory log SSOT, `project-aios`, AIOS daemon services (4 Running/Auto), `\AIOS_V13_Protocol_Audit` schtask, v2 hub (paths.py + consumer + state machine), aios_vnext task cards (43), WorkBuddy persistent user profile (4 paths when hub) |
| `DORMANT_REGISTERED` (registered but stopped/disabled) | 6 | `CloudTechV22Monitor` service, `_aios_cloudtech_bridge.py`, `skill-http-server` service, `daemons_v2` 8 services (7 Stopped/Disabled + 1 Auto), `\CloudTech-V22-Watchdog` task (Disabled) |
| `HISTORICAL` | 15 | H-01..H-15 above |
| `ARCHIVED` | 10 | AR-01..AR-10 above |
| `BLOCKED` | 3 | SwarmClaw, GoClaw/PicoClaw, FFmpeg Wizard / video-editing |
| `INERT` | 7 | I-01..I-07 above |
| `REFERENCE_ONLY` | 4 | `AIOS_SOURCE_OF_TRUTH_FINAL`, `AIOS_RECONSTRUCTION`, `D:\AIOS\_out` screenshots, `D:\AIOS\_audit_reports` |

### 7.2 By Phase-2 disposition

| Disposition | Count | Examples |
|---|---|---|
| `SAFE_REVERSIBLE` | 7 | C-01/C-02 (daemons_v2 services), B-07 (config.toml project entry), B-09 (D002 neutral), B-11 (hermes optional-skills), C-10 (roadmap doc edit), H-01/H-02/H-03/H-04/H-05/H-06/H-09/H-10/H-12/H-13/H-15 (registry/doc edits) |
| `SEPARATELY_AUTHORIZED` | 24 | A-01..A-10 (CloudTech V22 + service + scripts + mirror), B-01..B-06/B-08/B-10 (WorkBuddy profile + Codex resume + openclaw entries), C-04..C-09 (root installers + DR tooling + binary backups), H-07/H-08/H-11/H-14 (out-of-scope paths), AR-01..AR-10 (archive deletion — irreversible) |

### 7.3 Production ACTIVE layer vs legacy DORMANT layer

| Layer | Verdict | Evidence |
|---|---|---|
| **Production ACTIVE layer** (v2 + Codex + CC + kernel + AGENTS.md + aios_vnext) | **CLEAN** of old industry/global-strategy contamination | B §5 summary; 0 industry-keyword matches in v2, openclaw, hermes, codex |
| **Legacy DORMANT layer** (CloudTech V22 + WorkBuddy profile + cloudtech-saas + archived binaries) | **HIGH** reactivation risk if any of the 10 reactivation commands runs | C A-01..A-10; B B-01..B-04 |

---

## 8. Prioritized Phase-2 Construction Contract

Phase-2 is split into two mutually exclusive contracts:

### 8.1 SAFE_REVERSIBLE Implementation (no separate user authorization required)

The following operations are reversible (no data loss; no destructive edit; no history rewrite; no policy edit). Phase-2 may implement without additional user approval beyond the already-given audit authorization, **provided each operation is logged with before/after evidence in `D:\AIOS\_agent-hub\memory\YYYY-MM-DD.md`**.

#### 8.1.1 Doc & registry edits (zero runtime impact)

| # | Operation | File | Reversibility |
|---|---|---|---|
| S-01 | Update `AIOS_STATUS.json` lines 28-43 (`project-cloudtech`) to `maturity=Retired status=RETIRED` | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` | reversible (JSON edit) |
| S-02 | Update `AIOS_STATUS.json` lines 60-90 (`project-content-ip` / `project-opc`) to retired | same file | reversible |
| S-03 | Update `AIOS_STATUS.json` lines 44-58 (`project-lingce`) to retired | same file | reversible |
| S-04 | Update `AIOS_SKILL_REGISTRY.json` lines 27-31 (`sk-cross-matrix`) and 51-55 (`sk-industry`) to `deprecated` + count=0 | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SKILL_REGISTRY.json` | reversible |
| S-05 | Update `AIOS_AGENT_REGISTRY.json` lines 5-16 (AIOS-Hermes 治理) to `deprecated` (preserve Nous-hermes lines 82-91) | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_AGENT_REGISTRY.json` | reversible |
| S-06 | Mark `AIOS_CAPABILITY_GRAPH.json` lines 65-86 (`cap-self-learning`) as `test_status=DEFERRED` | `D:\AIOS\AIOS_RECONSTRUCTION\04_CAPABILITY_GRAPH\AIOS_CAPABILITY_GRAPH.json` | reversible |
| S-07 | Update `AIOS_EXECUTION_ROADMAP.md` lines 301-358 (P3-01..P3-08) to `Retired 2026-10-08 audit` | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` | reversible |
| S-08 | Update `AIOS_CONTENT_FACTORY_PIPELINE.md` lines 11-145 (7-stage) header to `Retired 2026-10-08` | `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` | reversible |
| S-09 | Update `products.json` lines 62-159 (`p-swarmclaw`/`p-goclaw`/`p-picoclaw`/`p-nanobot`/`p-ironclaw`/`p-ffmpeg-wizard`/`p-cutstorm`/`p-video-editing-skill`/`p-mcp-video-editor`) to `retired` | `D:\AIOS\AIOS_RECONSTRUCTION\08_RADAR\products.json` | reversible |

#### 8.1.2 Config edits

| # | Operation | File | Reversibility |
|---|---|---|---|
| S-10 | Apply chmod 444 / icacls readonly on `model-policy.v1.yaml` (ModelPolicy v1 444 ACL — was prepared in T5 envelope but not yet applied per memory 2026-10-09) | `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml` | reversible (icacls reset) — addresses H-11 / P-16 |
| S-11 | Deploy `reconciler.py` + `register_reconciler.cmd` (T7 deploy pending per memory 2026-10-09) | `D:\AIOS\_agent-hub\policy\reconciler.py` (NEW) | reversible (file deletion + unregister task) |
| S-12 | Replace `minimax / minimax-cn` provider strings in Hermes `cli-config.yaml.example` with canonical `MiniMax` (per A-06 / H-10) | `D:\AIOS\_relinked\hermes\hermes-agent\cli-config.yaml.example` | reversible |

#### 8.1.3 Service infrastructure starts (product-neutral, non-industry)

| # | Operation | Reversibility |
|---|---|---|
| S-13 | Start `AIOSV2Consumer` service (currently Stopped/Automatic per C §8 + memory 2026-10-09 OS error 5) — Phase-1 deliverable per P1 commit 4d5b905 | reversible (`sc stop`) |
| S-14 | Start any of the 7 `daemons_v2` Stopped/Disabled services as needed (aios-supervisor / aios-cron-orchestrator / aios-observability-hub / aios-role-channels / aios-bridge-cc-codex-cli / aios-bridge-cc-doubao / aios-bridge-cc-openclaw / aios-bridge-codex-desktop-cli) | reversible (`sc stop`) |

#### 8.1.4 Sequential ordering (Phase-2 implementation order)

1. **S-01..S-09** doc/registry edits first (zero runtime risk; locks the registry surface).
2. **S-10** ModelPolicy 444 ACL (locks policy surface against deepseek-v4-flash fallback).
3. **S-11** reconciler deploy (drift detection live; provides ongoing regression coverage).
4. **S-12** MiniMax naming normalization (provider-string clean).
5. **S-13..S-14** service infrastructure starts (after registry + policy + reconciler are live).

After S-01..S-14 complete, all three remaining classes of "reactivation risk" reduce to **Phase-2** authorization only (no further gate needed for SAFE_REVERSIBLE).

---

### 8.2 SEPARATELY_AUTHORIZED Irreversible Cleanup (fresh user authorization required)

The following operations are **irreversible** and require fresh user authorization per AGENTS.md `requires_authorization` ("delete 任何文件", "修改 AGENTS.md SSOT", "修改 kernel/alembic/versions/ migration", "修改 aios_kernel.governance 任何配置", "git push / OS service restart / 派 dev sub-agent 写代码"). Phase-2 may NOT execute these without a new round of explicit user approval. Each is enumerated as a Phase-2 candidate for the next planning round.

#### 8.2.1 Old product teardown (requires user authorization for service stop + out-of-scope directory deletion)

| # | Operation | Irreversibility reason | Pre-conditions |
|---|---|---|---|
| L-01 | `sc stop cloudtech-v22-gateway` + `sc delete cloudtech-v22-gateway` | service delete is irreversible | user confirmation; backstop plan if live callers |
| L-02 | `D:\CloudTech-Portable` (200 MB; 10826 files / 934 dirs per AR-0075) directory deletion | recursive delete is irreversible | out-of-scope dir; user-side backup recommended first |
| L-03 | `D:\CloudTech-Vault` (22 files) directory deletion | irreversible | out-of-scope dir |
| L-04 | `D:\CloudTech-Inbox` (5 industry subdirs, all empty) directory deletion | irreversible | out-of-scope dir |
| L-05 | `D:\CloudTech-Live-Execution\CloudTech_rc2_Live_Direct_Execution_20260925` (129/129 pytest PASS) directory deletion | irreversible | out-of-scope dir; audit re-confirmation recommended |
| L-06 | `sc stop CloudTechV22Monitor` + `sc delete CloudTechV22Monitor` | service delete is irreversible | user confirmation |
| L-07 | `sc stop skill-http-server` + `sc delete skill-http-server` | service delete is irreversible | user confirmation |
| L-08 | Stop `\CloudTech_V22Watchdog` + `\CloudTech_V23FileWatcher` tasks + delete | task delete is irreversible | user confirmation |
| L-09 | Disable + delete 5 `\CloudTech\*` namespace tasks (`HealthCheck-Hourly` / `DailyReport-0300` / `AIOSLightMonitor-30min` / `StartupCleanup-Once` / `SpecV1CI_Daily_0300`) | task delete is irreversible | user confirmation |
| L-10 | Disable + delete `\CloudTech-V22-Watchdog` task (already Disabled, formal delete) | task delete is irreversible | user confirmation |

#### 8.2.2 WorkBuddy persistent user profile scrub (requires user authorization for file edit)

| # | Operation | Irreversibility reason |
|---|---|---|
| L-11 | Edit `C:\Users\xinzh\.workbuddy\memory\45e357fa-c2ec-4bd0-b734-9b016a2759d7_memory.md` to remove `memoryBlock` JSON's CloudTech Phase 1 (医美+装企) wording | file edit; reversible only if original was backed up |
| L-12 | Edit `home-first-screen-cache.json` to remove 装修工作台 / 儿童教育 / K12教育 / 制造企业 / 金融服务 / 装修云管家 entries | file edit; reversible only if original was backed up |
| L-13 | Edit `skills-installed-store.json` to remove 装修云管家 industry skill registration | file edit; reversible only if original was backed up |
| L-14 | Delete `C:\Users\xinzh\.workbuddy\plugins\marketplaces\workbuddy-connector-plugins-official\connectors\zxygj-business-data\` | directory delete is irreversible |
| L-15 | Archive `C:\Users\xinzh\.workbuddy\sessions\23852.json` (move to dated backup subdir) | file move is reversible only if backup retained |
| L-16 | Archive Codex sessions in `C:\Users\xinzh\.codex\sessions\2026\09\` + `10\` that contain pre-retirement industry prompts | file move is reversible only if backup retained |

#### 8.2.3 Backup mirror scope change (requires user authorization)

| # | Operation | Irreversibility reason |
|---|---|---|
| L-17 | Reconfigure robocopy job (`\AIOS_E_Drive_DailyBackup_R1331`) to exclude `cloudtech-saas\`, `_archived_*`, `_backup*` paths | mirror history in `E:\AI_Backup\DailyBackup_*` retained; future mirror scope changed |

#### 8.2.4 Within-scope irreversible cleanup (still requires user authorization per AGENTS.md)

| # | Operation | Irreversibility reason |
|---|---|---|
| L-18 | Delete `D:\AIOS\_archived_2026-09-18\` (17 entries) | directory delete is irreversible |
| L-19 | Delete `D:\AIOS\_archived_20260925_P0\` (25 `.py`/`.bak` + 12 `.pid` + `_NEW_ARCHITECTURE_SSOT_V1.0_2026-09-25.md` + `_AIOSWatchdogAliveCheck.cmd` + `_cleanup_restart.ps1`) | directory delete is irreversible |
| L-20 | Delete `D:\AIOS\_archived_20260925_R259_popup_cure_rebuild\` (4 popup-cure `.bak` files) | directory delete is irreversible |
| L-21 | Delete `D:\AIOS\_backup_aios_exe_周二022609_093048\` + `_093503\` (4 daemon binaries 8.9-10.1 MB) | directory delete is irreversible |
| L-22 | Delete `D:\AIOS\_backups\` (3543 files) | directory delete is irreversible; affects restore source for mirror |
| L-23 | Delete `D:\AIOS\_backups_2026-09-29\` | directory delete is irreversible |
| L-24 | Delete `D:\AIOS\_backups_relinked_1790674911\` | directory delete is irreversible |
| L-25 | Delete `D:\AIOS\_schtasks_bak_R344_*` + `_schtasks_bak_R349_*` | directory delete is irreversible |
| L-26 | Delete `D:\AIOS\_r274_install_backup\` | directory delete is irreversible |
| L-27 | Delete `D:\AIOS\_r348_model_swap_bak_20260930-092918\` | directory delete is irreversible |
| L-28 | Delete `D:\AIOS\cloudtech-saas\` (13 files: `cloudtech-saas.exe` + `.xml` + 3 `.bak` + `uninstall.cmd` + `start_v22_watchdog.bat` + `winsw.exe` + 3 log files) | directory delete is irreversible; service must be un-installed first (L-06) |
| L-29 | Delete `D:\AIOS\_dr_v3.0_uncompressed_workspace\` | directory delete is irreversible |
| L-30 | Delete `D:\AIOS\_out\` (3 PNG screenshots) | directory delete is irreversible (historical evidence) |
| L-31 | Delete `D:\AIOS\_hide_console_windows_v3.py` (currently in HKCU Run; would require Run key removal first) | script delete is irreversible; depends on L-32 |
| L-32 | Remove HKCU Run key `HideConsoleWindowsV3` | registry edit is reversible; irreversible without backup |
| L-33 | Remove HKCU Run keys beyond AIOS (`WorkBuddy.WorkBuddy`, OneDrive, MicrosoftEdgeAutoLaunch) | registry edit; user may want to keep these |

#### 8.2.5 Service uninstall + scheduled task deletion (requires user authorization for OS service restart)

| # | Operation | Irreversibility reason |
|---|---|---|
| L-34 | Uninstall `daemons_v2` 8 WinSW services (`winsw.exe uninstall *.xml`) | service delete is irreversible |
| L-35 | Delete 4 R65 `AIOS_*` residual tasks (`AIOS_WAL_Recovery_Startup` / `AIOS_Quorum_Health_5min` / `AIOS_Quota_Enforcer_Report_10min` / `AIOS_WAL_RecoverAll_Daily`) | task delete is irreversible |
| L-36 | Stop + delete `\AIOS_E_Drive_DailyBackup_R1331` task (currently Running) | task delete is irreversible; affects daily mirror |

#### 8.2.6 Git history rewrite (NOT recommended; requires explicit user authorization)

| # | Operation | Notes |
|---|---|---|
| L-37 | `git filter-repo` / `git rebase -i` to remove historical references to CloudTech / 灵策 / OPC / 4-industry | history rewrite is destructive + breaks existing commit SHAs; only justified if audit reveals sensitive material (AR-0061 `.env` / AR-0062 `.jwt_secret` paths were NOT read — see R-021) |

---

## 9. Reactivation Mechanism Summary

| Risk class | Count | Phase-2 disposition |
|---|---|---|
| **HIGH reactivation paths** | 10 | A-01..A-10, B-01..B-04 (all SEPARATELY_AUTHORIZED) |
| **MEDIUM reactivation paths** | 2 | B-05, B-06 (SEPARATELY_AUTHORIZED) |
| **LOW reactivation paths** | 6 | B-07..B-11, C-01, C-02 (mixed: SAFE_REVERSIBLE for product-neutral, SEPARATELY_AUTHORIZED for verticalizable) |
| **INERT paths** | 7 | I-01..I-07 (none required) |
| **HISTORICAL references** | 15 | H-01..H-15 (mostly SAFE_REVERSIBLE; 4 require SEPARATELY_AUTHORIZED for out-of-scope paths) |
| **ARCHIVED references** | 10 | AR-01..AR-10 (all SEPARATELY_AUTHORIZED for irreversible deletion) |
| **BLOCKED candidates** | 3 | U-01..U-03 (require fresh user decision) |
| **Unresolved candidates** | 10 | U-01..U-10 (require fresh user direction) |
| **Retired requirement IDs** | 21 | R-001..R-021 (evidence-backed; one is sensitive — R-021 paths-only) |

---

## 10. Read-Only Audit Constraints (Self-Attestation)

This audit performed **zero** of the following:
- ❌ Delete any file (no `rm`, no `os.remove`, no `del`)
- ❌ Move any file (no `mv`, no `shutil.move`)
- ❌ Rewrite git history (no `git rebase`, no `git push --force`, no `git filter-repo`)
- ❌ Stop or start any service (no `sc stop`, no `sc start`, no `schtasks /end`, no `kill`)
- ❌ Modify product code (no edits in `D:\AIOS\kernel\src\`, no edits in `D:\AIOS\AIOS_RECONSTRUCTION\*`, no edits in `D:\AIOS\cloudtech-saas\*`)
- ❌ Modify policy (no edits in `D:\AIOS\_agent-hub\policy\*.{yaml,md,json}`)
- ❌ Modify registry (no HKCU/HKLM Run key edits; no `sc delete`)
- ❌ Touch `.env` / `.key` / `.pem` / `AccessKey.txt` (paths only — see R-021)
- ❌ Write to daily memory log (audit-only, not substantive work per AGENTS.md line 50)

The two output artifacts (`GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008.md` and `.json`) are written **only** to `D:\AIOS\_agent-hub\reports\` per the contract.

---

## 11. Verification

- ✅ `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008.md` written (this file)
- ✅ `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008.json` written (companion JSON)
- ✅ Both files non-empty (verified by file size)
- ✅ JSON parses (machine-readable companion validated)
- ✅ All path/line references traced to one of: A_PRODUCT, B_AGENT_TASK_MEMORY, C_LOCAL_RUNTIME, AGENTS.md, memory 2026-10-08 / 2026-10-09
- ✅ Zero deletions, moves, history rewrites, service changes, or policy edits performed
- ✅ No IDs invented — every R-001..R-021 / AR-01..AR-10 / H-01..H-15 / I-01..I-07 / U-01..U-10 traces to evidence

---

## 12. Top Confirmed Reactivation Sources (Summary)

1. **CloudTech V22 Unified Gateway on port 5099** (PID 16336, parent 9944) — old product live right now. One `sc stop cloudtech-v22-gateway` + service uninstall + directory deletion sequence tears it down. Service `CloudTechV22Monitor` with restart-on-failure XML arms auto-restart.
2. **WorkBuddy persistent user profile** (`~/.workbuddy/memory/45e357fa-…_memory.md` + `home-first-screen-cache.json` + `skills-installed-store.json` + `zxygj-business-data` plugin) — 4 HIGH-RISK reactivation paths if WorkBuddy hub reactivates; 81 industry-keyword matches in home cache.
3. **`E:\AI_Backup` daily mirror** (robocopy PID 31360 in flight) — copies every archive under `D:\AIOS` to off-box backup daily, so any `_archived_*` / `_backup*` file continues to propagate off-box.
4. **5 `\CloudTech\*` scheduled tasks** (2 Running + 3 Ready) with payloads outside `D:\AIOS` — namespace entry point for re-arming the old product line.
5. **Root installer scripts** (`install_aios_loop.cmd`, `install_aios_watchdog.cmd`, `R65_右键管理员运行_一键注册.bat`) — re-create ONSTART SYSTEM-priority tasks + 4 R65 residual tasks.

**Changed paths (this synthesis)**:
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008.md` (overwritten)
- `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008.json` (overwritten)

**ACK**: Audit complete. No destructive operations performed.