# T4 Audit — Hermes + Windows autorun 全链路扫描

> **任务**: T4 audit · Hermes + 其它 agent providers + Windows autorun chain
> **时间**: 2026-10-08T23:55Z → 23:59Z

---

## 1. Hermes 安装位置与结构

- **根目录**: `C:\Users\xinzh\.hermes\`
- **子结构**:
  ```
  hermes-agent/         # Python package (~150+ files)
    ├─ providers/       # __init__.py + base.py + README.md (Python package)
    ├─ gateway/         # config.py(96KB) + run.py(926KB) + session.py(56KB) + 20+ 其他
    ├─ agent/           # acp_adapter, acp_registry, agent 实体
    ├─ plugins/         # 插件系统
    ├─ skills/          # 技能
    ├─ cron/            # 定时任务
    ├─ cli-config.yaml.example (示例配置)
    ├─ hermes_bootstrap.py / setup-hermes.sh
    ├─ mcp_serve.py / run_agent.py
    └─ (RELEASE_v0.2.0 ~ v0.15.1 + README + LICENSE)
  hermes-gateway.cmd    # WinSW 启动器 (400 bytes, 在 gateway-service/)
  state-snapshots/      # 状态快照
  sessions/             # 会话历史
  sandboxes/            # 沙箱
  cron/                 # cron 任务
  memories/             # 记忆库
  skills/               # 技能库
  hooks/                # 钩子
  pairing/              # 配对
  audio_cache/, image_cache/, images/, logs/, backups/
  ```

## 2. Hermes providers 体系 (Python, 不在 yaml)

### 2.1 hermes-agent/providers/
- `__init__.py` (6780 bytes) · 多 provider 注册
- `base.py` (8174 bytes) · BaseProvider 抽象
- `README.md` (3356 bytes) · 文档
- ❌ 无 yaml 配置 — 全部 Python 类
- 注册的 provider 从 cli-config.yaml.example 可见, 支持 **25+ provider**:
  - `auto` / `openrouter` / `nous` / `nous-api` / `anthropic` / `openai-codex` / `copilot`
  - `gemini` / `zai` / `kimi-coding` / **`minimax`** / **`minimax-cn`** / `huggingface`
  - `nvidia` / `xiaomi` / `arcee` / `ollama-cloud` / `kilocode` / `azure-foundry`
  - `lmstudio` / `custom` / `ollama` / `vllm` / `llamacpp`

### 2.2 minimax / minimax-cn provider (关键)
- cli-config.yaml.example 注明:
  - `"minimax"` → "MiniMax global (requires: MINIMAX_API_KEY)"
  - `"minimax-cn"` → "MiniMax China (requires: MINIMAX_CN_API_KEY)"
- 默认 base_url = `https://openrouter.ai/api/v1` (example) — 用户实际使用时应切到 minimax

---

## 3. Hermes gateway 组件

### 3.1 gateway/config.py (96 KB)
- 处理 platform registry · channel · session reset · delivery · display_config
- 加载 yaml/env/cli 三层配置
- 不直接决定 model 字段 — model 由 `model.default` 和 `provider` 决定

### 3.2 gateway/run.py (926 KB)
- Hermes runtime · 处理 channel · session · delivery · stream_consumer/dispatch
- **是真正执行模型推理的地方**

### 3.3 gateway-service/hermes-gateway.cmd (400 bytes)
- WinSW 启动器 · 启动 `hermes mcp serve --accept-hooks` 或类似命令
- 未在 Task Scheduler 注册常驻任务 (Hermes gateway 当前是 CLI 一次性)

---

## 4. Hermes 凭据

- 通过环境变量 `MINIMAX_API_KEY` / `MINIMAX_CN_API_KEY` 识别
- `.openclaw/.env` 已镜像 (R140 治本)
- Hermes 自身不存 token — 全部走 env

---

## 5. Windows Autorun 全景

### 5.1 Task Scheduler (70+ AIOS 相关任务 · Ready/Running/Disabled)

#### AIOS 核心 (40+)
- AIOS-DashboardSupervisor · AIOS-DesktopCleaner · AIOS-HealthMonitor
- AIOS-HealthWatchdog-R351 · AIOS-NightlyDashboard
- AIOS-Overnight-Daily-Continue · AIOS-Overnight-Monitor
- AIOS-SessionCleanup · AIOS-SyncClaudeMemory · AIOS-WatchdogAliveCheck-R209
- AIOS_AicWifi_DriverCheck_5min · AIOS_Backup_Health_Weekly
- AIOS_Bridge_AutoRestart_5min · AIOS_Capability_Registry_Stats_Daily
- AIOS_Codex_AGENTS_Sync · AIOS_Continuity_Memory_Daily
- AIOS_Creator_DailyFeed_R1333 · AIOS_Creator_Learn_R1337
- AIOS_E2E_Stress_CI_Gate · AIOS_Endpoints_Guard_R322
- AIOS_Evolution_Log_Scan_30min · AIOS_Explorer_Watchdog
- AIOS_E_Drive_DailyBackup_R1331 (**Running**)
- AIOS_Filelock_Health_30min · AIOS_Incremental_Fetch_R1335
- AIOS_K2C_Intensive · AIOS_MemoryBank_Dashboard_Render (**Running**)
- AIOS_PID_Truth_Checker_5min · AIOS_PressureTest_CI_Gate
- AIOS_Process_Supervisor_1min · AIOS_PSRSIR_Capability_Sweep
- AIOS_PSRSIR_Smoke_Daily/Hourly · AIOS_Quorum_Health_5min
- AIOS_Quota_Enforcer_Report_10min · AIOS_Quota_Governor_5min
- AIOS_R193_Popup_Rootcure_3min · AIOS_Retention_Weekly
- AIOS_RunAll_Intensive/Nightly · AIOS_SaaS_Demo_Daemon_18803
- AIOS_Skill_Polish_Loop_R1334 · AIOS_Sync_Watchdog
- AIOS_USBSTOR_Guard_5min · AIOS_UserGrowth_DailyNewsletter/Heartbeat/WeeklyReview
- AIOS_V13_Protocol_Audit · AIOS_Video2Skill_Pipeline_R1338
- AIOS_WAL_RecoverAll_Daily · AIOS_WAL_Recovery_Startup
- ...等 60+ 个

#### Disabled (治理状态)
- AIOS-Disaster_Recovery_Watchdog (Disabled)
- AIOS_R153_V3_Nightly (Disabled)
- AIOS_R176_R152_Incremental_60min (Disabled)
- CodexHealthWatchdog_R109 (Disabled)
- OpenClaw Gateway (Disabled)
- OpenClaw-HealthMonitor (Disabled)
- _multi_watchdog (Disabled)
- PatternValidationQueue-Sat (Disabled)
- Pipeline-F-ContentCalendar (Disabled)
- TimeModelRouter (Disabled)

#### Codex / OpenClaw / CloudTech / Skill 相关
- Codex-Portable-Watchdog-R319 (Ready)
- OpenClaw-18792-Watchdog-R312 (Ready)
- OpenClaw Lease Guard (\AIos\, Ready)
- CDrive_OpenClawPlugin_Cleanup_6h (Ready)
- AIOSLightMonitor-30min (\CloudTech\, Ready)
- SkillIndex-Rebuild (\AIos\AIos\, Ready)

### 5.2 Startup folder (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`)
- `_archived_20260929/` (旧归档)
- `AIOS_C_Disk_Watchdog.lnk` (Ready)
- `aios_mcp_gateway_autostart.cmd.disabled` (R1267 治理后停用)
- `AIOS_R347_wlan_guard_recovery.lnk.disabled`
- `AIOS_Relink_On_Startup.lnk` (Ready · 用于 workspace relink)

### 5.3 Registry HKCU\Software\Microsoft\Windows\CurrentVersion\Run
- `WorkBuddy.WorkBuddy` → `D:\1\WorkBuddy\WorkBuddy.exe`
- `OneDrive` → OneDrive.exe /background
- `HideConsoleWindowsV3` → pythonw + D:\AIOS\_hide_console_windows_v3.py
- `MicrosoftEdgeAutoLaunch_E27CB86D1ACBFCA0D076515BEF19A074` → msedge.exe

❌ **未发现 cc-switch / openclaw / claude-code / hermes 直接注册 Run 键**

---

## 6. 关键风险

### 6.1 🟢 P2 · Hermes 是 CLI 一次性, 没有常驻 daemon
- gateway-service/hermes-gateway.cmd 存在但**未在 Task Scheduler 注册常驻任务**
- Hermes 当前是用户手动 `hermes <cmd>` 调用
- sovereignty-v v1 不需要动 Hermes (它通过 env + provider 字符串选模型, T6 Adapter 加白名单检查即可)

### 6.2 🟡 P1 · Task Scheduler 有 70+ AIOS 任务, 其中少数 Running
- 只有 2 个真正 Running (AIOS_E_Drive_DailyBackup_R1331 + AIOS_MemoryBank_Dashboard_Render)
- 其余 Ready 但未触发 — 这些任务的命令会 **动态读取 model policy**, 因此 T7 Reconciler 在每个 AIOS 任务启动时校验一次即可

### 6.3 🟢 P0 · Windows autorun 没碰 model — 自动切换需要尊重 OS 层
- 不修改 Registry Run
- 不动现有 Scheduled Task
- T7 Reconciler 用新 Scheduled Task 兜底 + 启动钩二次保险

---

## 7. 审计工件路径

- W5_hermes_others → 本文件 `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\05-hermes-others-report.md`
- W6_windows_autorun → 本文件 (合并报告)
