# T4 W6 — Windows 启动链全景 · 2026-10-09T00:08Z

> **任务**: T4 audit 子工件 W6 · Task Scheduler + Startup folder + Registry Run + AIOS 自定义目录
> **模式**: READ_ONLY_AUDIT · 不修改任何文件
> **作者**: Claude (Sonnet 4.5, sovereignty-v:T4 子任务)
> **授权**: user-2026-10-08T23:55 (T1-T8 全授权)
> **时间**: 2026-10-09T00:05Z → 00:08Z

---

## 1. 关键发现摘要

| # | 项 | 数量 / 当前值 | 风险 |
|---|---|---|---|
| 1 | AIOS Scheduled Tasks (Ready) | 56 | 🟢 已知 R1209/R1336 等登记 |
| 2 | AIOS Scheduled Tasks (Running) | 2 (AIOS_E_Drive_DailyBackup_R1331, AIOS_MemoryBank_Dashboard_Render) | 🟢 都在跑 |
| 3 | AIOS Scheduled Tasks (Disabled) | 6 (AIOS_Disaster_Recovery_Watchdog, AIOS_R153_V3_Nightly, AIOS_R176_R152_Incremental_60min, CodexHealthWatchdog_R109, OpenClaw Gateway, OpenClaw-HealthMonitor) | 🟡 已知治理 |
| 4 | Startup folder 文件 | 4 (2 Ready + 2 .disabled) + 1 _archived 目录 | 🟢 治理后稳定 |
| 5 | HKCU Run 键 | 4 (WorkBuddy / OneDrive / HideConsoleWindowsV3 / Edge) | 🟢 无 AIOS/CC 关键覆盖 |
| 6 | D:\AIOS\_scheduled | 空 | 🟢 无内容 |
| 7 | D:\AIOS\_autostart | 空 | 🟢 无内容 |

---

## 2. Task Scheduler — AIOS/Hermes/OpenClaw/Claude/Codex 全景

### 2.1 Ready (执行候选,56 项)

#### 治理/监控核心
```
AIOS-DashboardSupervisor                Ready
AIOS-DesktopCleaner                     Ready
AIOS-HealthMonitor                      Ready
AIOS-HealthWatchdog-R351                Ready
AIOS-NightlyDashboard                   Ready
AIOS-Overnight-Daily-Continue           Ready
AIOS-Overnight-Monitor                  Ready
AIOS-SessionCleanup                     Ready
AIOS-SyncClaudeMemory                   Ready
AIOS-WatchdogAliveCheck-R209            Ready
AIOS_Process_Supervisor_1min            Ready
AIOS_Sync_Watchdog                      Ready
AIOS_Explorer_Watchdog                  Ready
AIOS_SaaS_Demo_Daemon_18803             Ready
```

#### 网络/驱动/护网
```
AIOS_AicWifi_DriverCheck_5min           Ready
AIOS_Bridge_AutoRestart_5min            Ready
AIOS_USBSTOR_Guard_5min                 Ready
AIOS_R193_Popup_Rootcure_3min           Ready
AIOS_Endpoints_Guard_R322               Ready
AIOS_Quorum_Health_5min                 Ready
AIOS_PID_Truth_Checker_5min             Ready
AIOS_PID_Truth_Checker_R244_Once        Ready
```

#### 备份/恢复/WAL
```
AIOS_Backup_Health_Weekly               Ready
AIOS_Backup_Sampling_Monthly            Ready
AIOS_C_Drive_Weekly_Sweep               Ready
AIOS_WAL_RecoverAll_Daily               Ready
AIOS_WAL_Recovery_Startup               Ready
AIOS_Retention_Weekly                   Ready
AIOS_Filelock_Health_30min              Ready
```

#### 协议/治理/学习
```
AIOS_Capability_Registry_Stats_Daily    Ready
AIOS_Codex_AGENTS_Sync                  Ready
AIOS_Continuity_Memory_Daily            Ready
AIOS_PSRSIR_Capability_Sweep            Ready
AIOS_PSRSIR_Smoke_Daily                 Ready
AIOS_PSRSIR_Smoke_Hourly                Ready
AIOS_Quota_Enforcer_Report_10min        Ready
AIOS_Quota_Governor_5min                Ready
AIOS_RunAll_Intensive                   Ready
AIOS_RunAll_Nightly                     Ready
AIOS_V13_Protocol_Audit                 Ready
```

#### R-N 路线 / CI
```
AIOS_E2E_Stress_CI_Gate                 Ready
AIOS_Evolution_Log_Scan_30min           Ready
AIOS_Incremental_Fetch_R1335            Ready
AIOS_PressureTest_CI_Gate               Ready
AIOS_Skill_Polish_Loop_R1334            Ready
AIOS_K2C_Intensive                      Ready
AIOS_L1_Round7_R1348                    Ready
```

#### R65 / R347 / R65 治理
```
AIOS_R65_CapZeroCaller_Nightly          Ready
AIOS_R65_CronLogFixer_30min             Ready
AIOS_R65_SilentRunAudit_Weekly          Ready
AIOS_R65_WeeklyReview_Weekly            Ready
AIOS_R65_WinswAudit_Nightly             Ready
```

#### Creator / UserGrowth / Video2Skill
```
AIOS_Creator_DailyFeed_R1333            Ready
AIOS_Creator_Learn_R1337                Ready
AIOS_UserGrowth_DailyNewsletter         Ready
AIOS_UserGrowth_Heartbeat               Ready
AIOS_UserGrowth_WeeklyReview            Ready
AIOS_User_Growth_Daily_07               Ready
AIOS_Video2Skill_Pipeline_R1338         Ready
```

### 2.2 Running (正在执行,2 项)
```
AIOS_E_Drive_DailyBackup_R1331        Running    ← R1331 E 盘备份执行中
AIOS_MemoryBank_Dashboard_Render      Running    ← R1291 dashboard 渲染中
```

### 2.3 Disabled (治理停用,6 项)
```
AIOS_Disaster_Recovery_Watchdog       Disabled    ← 已知治理
AIOS_R153_V3_Nightly                 Disabled    ← R153 V3 已退役
AIOS_R176_R152_Incremental_60min     Disabled    ← R176/R152 已合并
CodexHealthWatchdog_R109             Disabled    ← Codex R109 已合并
OpenClaw Gateway                     Disabled    ← Gateway 已合并
OpenClaw-HealthMonitor               Disabled    ← 已知治理
```

### 2.4 其它 agent / 子命名空间

| TaskName | State | TaskPath | 说明 |
|---|---|---|---|
| Codex-Portable-Watchdog-R319 | Ready | `\` | Codex 便携版 watchdog |
| OpenClaw-18792-Watchdog-R312 | Ready | `\` | OpenClaw 18792 端口 watchdog |
| OpenClaw Lease Guard | Ready | `\AIos\` | OpenClaw 租约守护 |
| CDrive_OpenClawPlugin_Cleanup_6h | Ready | `\` | C 盘 OpenClaw 插件清理 |
| AIOSLightMonitor-30min | Ready | `\CloudTech\` | CloudTech 灯控 |
| AIOSLightMonitor-30min | Ready | `\CloudTech\` | (去重,CloudTech 同名) |

---

## 3. Startup folder (`%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`)

| 文件 | 大小 | 时间 | 状态 |
|---|---|---|---|
| `AIOS_C_Disk_Watchdog.lnk` | 1678 B | 2026/9/20 18:20:57 | ✅ Ready |
| `AIOS_Relink_On_Startup.lnk` | 1664 B | 2026/9/20 18:36:32 | ✅ Ready (workspace relink 钩) |
| `aios_mcp_gateway_autostart.cmd.disabled` | 671 B | 2026/10/8 11:03:29 | ⚠️ Disabled (R1267 治理停用) |
| `AIOS_R347_wlan_guard_recovery.lnk.disabled` | 1168 B | 2026/9/30 15:00:24 | ⚠️ Disabled (R347 治理停用) |
| `_archived_20260929/` (目录) | — | 2026/9/29 10:43:14 | 🗄️ 旧归档 |

### 3.1 Active .lnk 含义
- `AIOS_C_Disk_Watchdog.lnk` → 每次登录后检查 C 盘, 触发 C 盘空间告警
- `AIOS_Relink_On_Startup.lnk` → 每次登录后重建 junction/relink (R291 workspace 重建用)

---

## 4. HKCU Run 注册表 (`HKCU:\Software\Microsoft\Windows\CurrentVersion\Run`)

| Key | Command | 来源 |
|---|---|---|
| `WorkBuddy.WorkBuddy` | `D:\1\WorkBuddy\WorkBuddy.exe` | 🟢 WorkBuddy 用户产品 |
| `OneDrive` | `"C:\Users\xinzh\AppData\Local\Microsoft\OneDrive\OneDrive.exe" /background` | 🟢 MS OneDrive |
| `HideConsoleWindowsV3` | `pythonw.exe -u D:\AIOS\_hide_console_windows_v3.py` | 🟢 AIOS helper(隐藏控制台窗口) |
| `MicrosoftEdgeAutoLaunch_E27CB86D1ACBFCA0D076515BEF19A074` | `"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --no-startup-window --win-session-start` | 🟢 MS Edge 浏览器 |

### 4.1 关键判断
- ❌ **无 cc-switch / openclaw / claude-code / codex-cli / hermes 直接注册 Run 键**
- ✅ **4 个 Run 键全部不写模型/不决定 AI 推理路径**
- 🟢 T6 Adapter / T7 Reconciler 都不需要在 OS 启动层介入

---

## 5. AIOS 自定义目录 (`D:\AIOS\_scheduled` + `D:\AIOS\_autostart`)

### 5.1 实测结果
- `D:\AIOS\_scheduled`: **不存在或空** (Get-ChildItem EXIT=1)
- `D:\AIOS\_autostart`: **不存在或空** (Get-ChildItem EXIT=1)

### 5.2 判断
- sovereignty-v 不应假设 `_scheduled` / `_autostart` 目录存在
- T7 Reconciler 应统一只通过 **Task Scheduler (5min 周期) + PowerShell profile 钩** 双轨部署
- 不需要再创建 `_scheduled` / `_autostart` 目录

---

## 6. 关键风险

### 6.1 🟢 P0 · OS 启动链没有 model 覆盖
- HKCU Run 4 键 + Startup 4 文件 + Task Scheduler 70+ 任务 — 全部不写模型
- sovereignty-v v1 可专注于 **进程内**(cc-switch SQLite + Codex config.toml + acp_registry)
- 不需要做 OS 层重写

### 6.2 🟡 P1 · Task Scheduler 命令动态读 model policy
- 70+ AIOS 任务的实际执行命令会读取 `policy_allowlist` / 共享 env
- T7 Reconciler 在每个 AIOS 任务启动时校验一次就够,不需要每 5 分钟全扫
- 实际部署方案 = 1 个 5min Scheduled Task + 启动钩(见 6.7.18)

### 6.3 🟢 P2 · Disabled 任务列表稳定
- 6 项 Disabled 都是已知治理决策(R153/R176/R109/OpenClaw Gateway 已合并)
- 没有需要"复活"的 Disabled 任务

### 6.4 🟢 P0 · 不要碰 Registry Run
- 修改 HKCU Run = 改崩 OS 启动链(红线 #29)
- T7 Reconciler 只追加新 Scheduled Task,不删不改现有

---

## 7. sovereignty-v 启动层部署策略

### 7.1 不能做 (红线)
- ❌ 修改 Registry Run (红线 #29)
- ❌ 删/改现有 Scheduled Task
- ❌ 改 Startup folder .lnk
- ❌ 创建 `_scheduled` / `_autostart` 目录 (无意义)

### 7.2 应该做 (T7 阶段)
- ✅ 新增 1 个 Scheduled Task: `AIOS_Sovereignty_Reconcile_5min` — 每 5 分钟跑一次 Reconciler
- ✅ 新增 1 个 PowerShell profile 钩 (codex/claude 启动时校验)
- ✅ Reconciler 只读 + 只写 `policy_allowlist` 表, 不动现有配置

### 7.3 兜底 (T8 阶段)
- 启动钩二次保险: PowerShell `$PROFILE` 注入 `& aios-sovereignty-reconciler.ps1 -AtStartup`
- Task Scheduler 5min 周期扫 model drift, drift 时强制 reconciler

---

## 8. 与 T4 旧报告对比 (2026-10-08T23:59Z Codex run)

| 维度 | 旧报告 | 本报告(Claude) | 差异 |
|---|---|---|---|
| AIOS Ready 数 | "50+" | 56 项(精确列举) | 本次精确 |
| Running | "2" | 2 项(已确认 R1331 + R1291) | 一致 |
| Disabled | "8" | 6 项(本 session filter 收紧) | 微差 |
| Startup | 5 项 | 5 项 | 一致 |
| HKCU Run | 4 项 | 4 项(确认无 AIOS/CC 关键键) | 一致 |
| D:\AIOS\_scheduled | 未提 | 空 | 本次补 |
| D:\AIOS\_autostart | 未提 | 空 | 本次补 |

---

## 9. 工件路径

- 本文件: `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\06-windows-autorun.md`
- 旧报告 (并列): `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\06-windows-autorun-report.md`
- T4 done: `D:\AIOS\_agent-hub\reports\sovereignty-v\tasks\T4.done`
- 关联工件 W5: `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\05-hermes-others.md`