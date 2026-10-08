# T4 W6 — Windows 启动链全景 · 2026-10-08T23:59Z

> **目的**: T4 audit 子工件 W6 · Windows 启动链 (Task Scheduler + Startup folder + Registry)

## 1. Task Scheduler 统计

- AIOS 核心 Ready: 50+
- AIOS 核心 Running: 2 (AIOS_E_Drive_DailyBackup_R1331, AIOS_MemoryBank_Dashboard_Render)
- AIOS 核心 Disabled: 8
- Codex 相关: Codex-Portable-Watchdog-R319 (Ready), CodexHealthWatchdog_R109 (Disabled)
- OpenClaw 相关: OpenClaw-18792-Watchdog-R312 (Ready), OpenClaw Lease Guard (Ready), CDrive_OpenClawPlugin_Cleanup_6h (Ready), OpenClaw Gateway (Disabled), OpenClaw-HealthMonitor (Disabled)
- CloudTech: AIOSLightMonitor-30min (Ready)
- SkillIndex-Rebuild (Ready)

## 2. Startup folder

```
%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
├─ AIOS_C_Disk_Watchdog.lnk              Ready
├─ AIOS_Relink_On_Startup.lnk            Ready (workspace relink 钩子)
├─ aios_mcp_gateway_autostart.cmd.disabled   R1267 治理后停用
├─ AIOS_R347_wlan_guard_recovery.lnk.disabled
└─ _archived_20260929/                   旧归档
```

## 3. Registry HKCU Run

| key | command |
|---|---|
| WorkBuddy.WorkBuddy | D:\1\WorkBuddy\WorkBuddy.exe |
| OneDrive | OneDrive.exe /background |
| HideConsoleWindowsV3 | pythonw + D:\AIOS\_hide_console_windows_v3.py |
| MicrosoftEdgeAutoLaunch_* | msedge.exe --no-startup-window |

## 4. cc-switch / openclaw / claude-code / hermes 启动链

| 命令 | 是否启动链 | 备注 |
|---|---|---|
| cc-switch | ❌ | 不需要 OS 启动钩, 通过 currentProviderCodex 动态切换 |
| openclaw | ⚠️ | Lease Guard 5min 周期任务 + Watchdog 5min, 无常驻 daemon |
| claude-code | ❌ | 用户手动启动 |
| hermes | ❌ | CLI 一次性, gateway.cmd 未注册 |

## 5. sovereignty-v 启动层策略

### 5.1 不能做
- ❌ 修改 Registry Run (Risk: 改崩 OS 启动)
- ❌ 删/改现有 Scheduled Task (Risk: 破坏已知守护)
- ❌ 改 Startup folder .lnk (Risk: 触发 workspace 重建)

### 5.2 应该做
- ✅ 新增 1 个 Scheduled Task: `AIOS_Sovereignty_Reconcile_5min` — 每 5 分钟跑一次 Reconciler
- ✅ 新增 1 个 PowerShell profile 钩 (codex/claude 启动时校验)
- ✅ Reconciler 只读 + 只写 `policy_allowlist` 表, 不动现有配置

## 6. 结论

- **T7 Reconciler 部署方案 = Task Scheduler 5min + 启动钩双轨** (而非二选一)
- 启动钩由 PowerShell profile 实现: `$PROFILE += "; & aios-sovereignty-reconciler.ps1 -AtStartup"`
- Task Scheduler 兜底: 每 5 分钟扫一次 model drift, drift 时强制 reconciler
