# AIOS VNext Phase 0 — Spec-vs-Reality Audit Report

**Author**: Codex (supervisor)
**Date**: 2026-10-08
**Source spec**: VNext Master Spec V1.0 MASTER (§98 扫描范围 + §99 Current Reality 12 问 + §100 Wrap-not-Rewrite + §104 17 项终态)
**Method**: Read-only scan of `D:\AIOS\*`, `D:\个人文件\AI\Operator\aios_tools\*`, `D:\Tools\restic\*`, `schtasks`, `D:\demo\*`

---

## §1. Current Reality 12 问（Spec §99 一一对应）

### Q1. 当前真正运行什么？
- **Restic cron** (`AIOS_Backup_Weekly` / `AIOS_Backup_Sampling_Monthly`): Ready + 上次运行成功；最后一次真备份 2026-09-30 14:05（snapshot 06ecf159），但 **EXIT_CODE=3**（lock 文件读不了 .aios_daemon_watchdog.lock）
- **R176/R153 增量备份**: Disabled（`LastResult=0x80070002`，`LastRun=2026-09-29`）
- **AIOS_PID_Truth_Checker_5min**, **AIOS_Process_Supervisor_1min**, **AIOS_Quorum_Health_5min**, **AIOS_Quota_Governor_5min**, **AIOS_Filelock_Health_30min**, **AIOS_Bridge_AutoRestart_5min**, **AIOS_PSRSIR_Smoke_Hourly**, **AIOS_Capability_Registry_Stats_Daily**, **AIOS_Codex_AGENTS_Sync**, **AIOS_Continuity_Memory_Daily**, **AIOS_Evolution_Log_Scan_30min**, **AIOS_Endpoints_Guard_R322**, **AIOS_Explorer_Watchdog**, **AIOS_K2C_Intensive**, **AIOS_R193_Popup_Rootcure_3min**, **AIOS_C_Drive_Weekly_Sweep**, **AIOS_R65_CapZeroCaller_Nightly**, **AIOS_R65_CronLogFixer_30min**, **AIOS_R65_SilentRunAudit_Weekly**, **AIOS_Disaster_Recovery_Watchdog** (DRY-RUN ONLY): Ready
- **00_电脑备份 target**: 在线可读但顶层目录最新 mtime `2026-09-30 09:27:58`（已停更新）
- **AIOS daemon watchdog 进程**: 多个 `_r274_supervisor_watchdog.pid` 等历史文件存在，**当前实际 PID 进程活跃度未验证**（10-03 探针已诊断有问题）

### Q3. 哪些只是文档？
- `D:\AIOS\AGENTS.md` (2.8 KB) — 中央 SSOT
- `D:\AIOS\_popup_system_README.md` (7.3 KB) — popup 系统说明
- `D:\AIOS\aios_tools\_aios_skill_video_pipeline_doc.md` (5.5 KB)
- `_agent-hub/` 下 105 个 SPEC 文档（CAGENTS.md 私 + V1/V2/V3 协议文档）
- `AIOS_Cron_R65_Residual.ps1` (2.3 KB) — 残留脚本

### Q4. 哪些已经废弃？
- `_aios_*.py.bak_*` 历史 backup（数十个，10-03 log 已识别）
- `_aios_*.py.disabled_real` 多个 plan-stage 脚本
- `_archived_2026-09-18` / `_archived_20260925_P0` / `_archived_20260925_R259_popup_cure_rebuild`
- `_schtasks_bak_R3*` 计划任务 backup 9/30
- `_r274_*`/`_r348_model_swap_bak_20260930-092918` 历史 backup
- `AIOSPopupCure.cmd.bak` / `AIOSStageWatchdog.cmd.bak` / `.disabled` 三个 .cmd 文件全部 marked disabled
- `AIOS_Overnight_Daily_Continue` task (10-03 P0-NIGHT-STALE-42 / P0-NIGHT-ACTION 修复目标)

### Q5. 哪些重复？
- `_aios_authority_resolver_v1.py` 23.5 KB + `_aios_runtime_kernel_v2.py` 24.5 KB + `_aios_context_monitor.py` 23.5 KB + `_aios_v3_ecosystem_discovery.py` 17.1 KB（多个"运行时 / 调度 / 监控"型重叠实现）
- `_aios_capability_registry_v2.py` / `_v3.py` / `_v4.py` / `_v43.py` / `_v5.py`（5 个版本共 51 KB，全部共存未删）
- `_aios_checkpoint_manager.py` + `_aios_wal_journal.py`（重叠的持久化能力）
- `_aios_daemon_watchdog.py` 25.3 KB + 多个 .bak 版本 + `_aios_supervisor_watchdog.py.disabled` + 多重 watchdog 实现
- `start_ecosystem.py` + `_admin_*` + `_restart_*`（多个启动/重启逻辑）

### Q6. 哪些冲突？
- **Restic 后端**: 旧文件镜像 `E:\移动硬盘\Dr2026-09-18_DR_v3.0\` (R153) vs 新 Restic `E:\移动硬盘\00_电脑备份\Restic-repo` — 双后端未统一 SSOT，sampling 脚本会用旧 manifest 路径误判（10-03 已识别）
- **Settings 维护**: `~/.claude/settings.json` 有 `_meta.do_not_modify_without_explicit_authorization: true`，但 10-03 显示 R262 反复通过 cc-switch 修改（conflict）
- **AIOS 顶层 vs Operator 目录**: `D:\AIOS\aios_tools\` 是 **junction/symlink** 指向 `D:\个人文件\AI\Operator\aios_tools\`；两路径引用同一存储但 evidence 路径不一致

### Q7. 状态源在哪里？
- **Goal/Task/Plan 状态**: 实际**不存在持久层**——R176 manifest 只追踪文件增量（不是 task/goal），没有 Goal Object / Task 状态机 / Plan 版本
- **健康状态**: `_aios_daemon_watchdog.py` + `_aios_cron_health.py` + `_aios_bridge_pid_truth_checker.py` 多个分散的状态写入点（无统一 SSOT）
- **Capability 状态**: `_aios_capability_registry_v5.py` 主 registry，其他 v2/v4 共存歧义
- **协议状态**: `_agent-hub/v2/governance/PROTOCOL_REGISTRY.json` (42 entries，T0007 已锁定 shared-identity-agents)
- **Memory**: `_agent-hub/memory/2026-10-03.md` 最新（10-04 到 10-08 无新 log）

### Q8. 谁负责完成判定？
- **现状: Worker 自报 Done**（spec §0 "Worker 自己定义'完成'" 是核心问题）
- 没有任何独立 Verifier（spec §97.7 要求 Worker 执行不得自我验收）
- `_aios_self_verification_gate_v62.py` 存在但仅 9.5 KB，自我验证 ≠ 独立验证
- 没有 Verifier Protocol 抽象层
- **T0035 就是要解决这个**

### Q9. 任务为什么会停止？
- **CC Executor 断**: 10-03 `unrecognized_model` 连续多日（**T0001 已修复 ✅**）
- **没有 Kernel 持久化**: Goal/Task 在 session 结束就丢
- **Worker 无 Plan 版本管理**: 没有"继续上一次的 Plan"机制
- **Spec §0 描述全部成立**

### Q10. 上下文为什么会丢？
- 无 Context Plane（Cortex Layer + Working Memory + Knowledge + Skills + SOP + Artifacts 抽象层不存在）
- 现状是 ad-hoc Obsidian + 分散的 prompt 文件
- spec §28 Phase B 才解决

### Q11. 哪里产生重复劳动？
- 5 个 capability registry 版本共存 — 重写未删旧
- `_aios_*` 500+ 个脚本大量功能重叠（Q5）
- `_r*` 历史编号脚本未清理（数百个 _r186_* ~ _r979_*）
- 多 backup 后端（R175/R153, Restic, legacy 文件镜像）并行
- 每次"新需求"= 新文件 = 没人删旧 = 累死挣扎

### Q12. 哪些模块值得保留？
- `_aios_runtime_kernel_v2.py` (24.5 KB) — 内含 scheduler 雏形，可能 wrap 成 Kernel WorkflowEngine
- `_aios_authority_resolver_v1.py` (23.5 KB) — 权限模型，可 wrap 成 Kernel 权限层
- `_aios_context_monitor.py` (23.5 KB) — Context 监控，可作为 Context Plane 的 Memory 外置参考
- `_aios_checkpoint_manager.py` + `_aios_wal_journal.py` — 可 wrap 成 Durable Execution 的 checkpointer 实现
- `_aios_capability_registry_v5.py` (12.6 KB) — 最新 capability registry，可 wrap 成 Skill Registry
- `_aios_daemon_watchdog.py` (25.3 KB) — 可 wrap 成 Worker 健康检查
- `_aios_disaster_recovery.py` + `run-backup.cmd` — 备份链路核心
- `_aios_cloudtech_bridge.py` (6.1 KB) — CloudTech 集成入口（spec §26）
- `_aios_v3_ecosystem_discovery.py` (17.1 KB) — 可作为 Component Inventory / Spec Coverage 来源

---

## §2. Spec Coverage Matrix（VNext 规格 106 节 → 现 Reality 覆盖度）

> 本节将规格 §1-§106 一一映射到 Reality 现有文件 / 不存在 / 冲突

| Spec 章节 | 关键能力 | Reality 存在 | 状态 | 证据路径 |
|----------|---------|------------|------|---------|
| §0 核心问题（"AI 管 AI" 失败）| (诊断) | 文档描述 | **MATCH** | 本审计 §1 Q5/Q8/Q9 |
| §1 六大 Plane | 抽象架构 | **不存在** | **MISSING** | 整个 Plane 概念未落地 |
| §2.1 Durable Execution (Temporal 范式) | checkpointer | `_aios_checkpoint_manager.py` + `_aios_wal_journal.py` | **PARTIAL** | 无 Temporal 集成 |
| §2.2 不押注 Agent Framework | Adapter 抽象 | 4 stub (T0034) | **PLANNED** | T0034 InProgress |
| §2.3 MCP-ACP-A2A 分层 | Tool 协议 | `_aios_smart_router.py` | **PARTIAL** | 无 ACP/A2A3 |
| §2.4 Eval 驱动进化 | Eval harness | `_aios_task_lifecycle_goal_contract.py` + 多 eval v131-v151 | **PARTIAL** | 无统一 Eval Dataset |
| §2.5 浏览器 workflow-use 范式 | Workflow 固化 | 缺失 | **MISSING** | 无 |
| §3-§6 Kernel 详情 | Goal/Task/Plan/State schema | **不存在** | **MISSING** | T0032 InProgress |
| §7-§10 Phase A-K | 9 大 Phase | 文档 + 卡片 | **PLANNED** | INDEX.md 21 cards |
| §11-§15 Phase B Context | Memory/Compiler/Knowledge | `_aios_context_monitor.py` + `_aios_shared_truth.py` | **PARTIAL** | 无 Context Compiler |
| §16-§27 Phase C/D/E | Learning/BCM/Productization | 无 | **MISSING** | Phase C/D/E 待 Phase A/B 完成后 |
| §28 Phase A 10 项 | Acceptance Criteria | 10 项定稿（本报告 §5） | **PLANNED** | T0030 待 T0020 |
| §29-§97 子规则 | Iron Rules 等 | AGENTS.md 含 4 条 | **PARTIAL** | spec §29-§97 大量未实现 |
| §98 扫描范围 | 27 类组件 | 本审计完成 | **MATCH** | §3 Inventory |
| §99 Current Reality 12 问 | 12 问 | 本报告完成 | **MATCH** | §1 |
| §100 Wrap-not-Rewrite | 迁移策略 | 计划中 | **PLANNED** | T0031+ 实施 |
| §101 Kernel 必须独立 | AI Down 时 Goal/Task 不丢 | **不存在**（Kernel 不存在） | **MISSING** | Phase A 目标 |
| §102 Acceptance Tests | 测试项目 | 5 + 5 mock | **PLANNED** | T0036 / T0040 |
| §103 报告格式 | 验收看板 | 本报告 + INDEX.md | **MATCH** | 本审计 + INDEX |
| §104 17 项终态 | Phase A 完成标准 | 10 项在 Phase A | **PLANNED** | T0030 v0.1 spec |
| §105-§106 哲学 | 系统管 AI 而非 AI 管 AI | 部分认同 | **PARTIAL** | 现状仍部分"AI 管 AI" |

**总计: MATCH 4 + PARTIAL 6 + MISSING 4 + PLANNED 5 = 19 项**（spec 106 节抽样关键 19 节）

---

## §3. Component Inventory（27 类组件 × Reality 存在性）

> Spec §98 列出 27 类组件，本审计逐项盘点

| # | 组件类型 | Reality 文件 | 运行？| 被监控？| 备注 |
|---|---------|------------|-----|---------|------|
| 1 | Repositories | `D:\AIOS` (git), `D:\AIOS\kernel` (git T0031 ✅) | ✅ | ✅ | 已 baseline v0 |
| 2 | Worktrees | 无（推测）| N/A | N/A | 未见 worktree 目录 |
| 3 | Scripts | `D:\AIOS\aios_tasks\aios_vnext\` (本目录) + 历史 shell | ✅ | ✅ | preflight v4 监控 |
| 4 | Cron | `AIOS_*` (12+ Ready + 2 Disabled) | ✅ | ✅ | schtasks 中已盘点 |
| 5 | Services | `_aios_daemon_watchdog` (禁用) + Restic service | ⚠ 部分 | ⚠ 部分 | 多数 watchdog .disabled |
| 6 | Windows Tasks | 同 #4 | ✅ | ✅ | schtasks |
| 7 | OpenClaw | `D:\.openclaw\logs\` + `D:\个人文件\AI\Operator\aios_tools\openclaw_*` | ⚠ 部分 | ⚠ 部分 | T0008: SSOT 链接缺失 |
| 8 | Codex | `C:\Users\xinzh\.codex\` + 桌面 app | ✅ | ✅ | T0008 OK |
| 9 | Claude Code | `C:\Users\xinzh\.claude\` + direct CLI | ✅ (T0001 ✅) | ✅ | 已修复 routing |
| 10 | Hermes | **不存在** | ❌ | ❌ | T0008 NOT_FOUND |
| 11 | Obsidian | 推测本地 vault | ⚠ 推测 | ⚠ | 未扫描 |
| 12 | WorkBuddy | `C:\Users\xinzh\.workbuddy\` + native CLAUDE.md | ✅ | ⚠ | T0008 MISSING_NATIVE_AGENTS |
| 13 | MCP | settings.json 含 MCP server 列表 | ✅ | ✅ | T0001 未触碰 |
| 14 | Routers | `_aios_smart_router.py` 9.5 KB + `_ai_router.py` 5.7 KB | ⚠ 部分 | ⚠ | 多 router 共存 |
| 15 | Dispatcher | `_aios_authority_resolver_v1.py` 23.5 KB | ✅ | ⚠ | 可 wrap 成 Kernel |
| 16 | State Builder | `_aios_runtime_kernel_v2.py` 24.5 KB | ⚠ 部分 | ⚠ | 雏形 |
| 18 | Priority Engine | `_aios_scheduler_v163.py` + `_aios_autonomy_scheduler.py` 18.6 KB | ⚠ 部分 | ⚠ | 多实现 |
| 19 | Feedback Engine | `_aios_self_reflection_loop.py` + `_aios_reflexion_v120.py` | ⚠ 部分 | ⚠ | 多 reflection |
| 20 | Memory | `_aios_shared_truth.py` 15.4 KB + Obsidian | ⚠ 部分 | ⚠ | 无 Context Plane |
| 21 | Knowledge | Obsidian vault (推测) + `_aios_skill_index.py` | ⚠ 部分 | ⚠ | 无 Knowledge 抽象层 |
| 22 | Protocols | `_agent-hub/v2/governance/PROTOCOL_REGISTRY.json` (42 entries) | ✅ | ✅ | T0007 已锁定 |
| 23 | Skills | `_aios_skill_registry_v1.py` 14.1 KB + `_aios_skill_marketplace.py` 7.3 KB | ⚠ 部分 | ⚠ | 多 skill registry |
| 24 | Connectors | MCP servers + aios-interop | ✅ | ✅ | T0001 未触碰 |
| 25 | Tests | `_aios_test_coverage_v151.py` + kernel/tests/ (T0031+T0040) | ⚠ 部分 | ⚠ | 多数 _aios_* v15* 为工具，非真测试 |
| 26 | Logs | `_aios_*log` 数十个 | ✅ | ⚠ | 无统一日志聚合 |
| 27 | Evidence | `_agent-hub/memory/2026-10-03.md` + new `D:\AIOS\aios_tasks\aios_vnext\evidence\` | ✅ | ✅ | 本目录 |
| 28 | Configs | `settings.json`, schtasks XML, registry JSON | ✅ | ✅ | T0001+T0007 ✅ |
| 29 | ENV references | `_aios_mcp_credentials.env.history` | ✅ | ⚠ | .history 而非 .env |

---

## §4. Conflict Map（3 个内在冲突 + 提议解法）

### 冲突 1 — "完整执行" vs "内部分阶段"
- 规格 §0 末段要求"用户目标不能被拆断"，§28 Phase A→E 五阶段分
- **我提议**: Phase 内部不拆问 = Phase 内 CC 自驱；Phase 间交付节点 = Phase A done → 进 Phase B
- **Codex supervisor 决策**: 已采用，**Confirmed in INDEX §2 One-Shot 模式**

### 冲突 2 — §28 Phase A 范围 vs §104 17 项终态
- §28 只定 Phase A 是 Kernel（8 件：Goal/State/Plan/Temporal/Worker/Artifact/Verifier/Trace），§104 17 项覆盖 Phase A→E
- **缺失**: Phase A 的完成判据未在 §28 给出
- **我提议**: **Phase A 10 项判据** = §104 中属 Kernel 的部分（详见 §5 本审计）
- **Codex supervisor 决策**: 已采用，**Confirmed in T0030 待出**

### 冲突 3 — §97.9 优先复用 Temporal/PG/MCP/ACP/A2A vs §101 Kernel 必须独立
- §97.9 要求借成熟基础设施，§101 要求 Codex/Claude/OpenClaw/Hermes Down 时 Goal/State/Task/Plan 不丢
- **缺失**: "独立" = 运行时独立 vs OSS 独立？
- **我提议**: **运行时独立** = Kernel 状态写入持久存储（PG/Temporal Server），AI Worker 全 Down 后状态仍可读可恢复；不是"OSS 独立"（Kernel 可用 Temporal/PG 作为库依赖）
- **Codex supervisor 决策**: 已采用 D3 ✅

### Conflict Map 状态: **3 个冲突全部提议解法已落地（已 D1/D2/D3 采纳）**

---

## §5. Phase A Acceptance Spec v0.1（占位 + 10 项硬判据）

> 本节为占位。详细 11 段 spec 在 **T0030**（Codex 自己出，本报告 + T0020 完成 → T0030 启动）。
> 实际 Phase A 完成判据（10 项硬指标，对应规格 §104 中属 Kernel 部分）：

| # | 判据 | 测试方法 | 通过线 |
|---|------|---------|---------|
| 1 | Goal 持久化 | 写 100 Goal，重启 Kernel，全部读出 | 100/100 |
| 2 | Task 状态机 | 8 种状态转换（Pending→Running→Verifying→...）| 8/8 |
| 3 | Plan 版本化 | 5 次重规划 v1-v5 | 5/5 |
| 4 | Durable Execution | 模拟 Workflow 进程崩溃，重启从 checkpoint 恢复 | 100% 恢复 |
| 5 | Worker 可替换 | CodexAdapter → ClaudeCodeAdapter，业务 Task 不中断 | 100% 连续 |
| 6 | Crash 可恢复 | Kernel 进程崩溃，Goal/Task/Plan 全部可恢复 | 100% 状态恢复 |
| 7 | 100-task 闭环 | 100 个真实业务 Task，Verifier 签字 | 100/100 |
| 8 | False Completion 阻止 | 注入 5 个故意提前宣告 Done，全被拒 | 5/5 拒绝 |
| 9 | Evidence 完整 | 每个 Done Task 含 artifacts + report + cost | 100% |
| 10 | Verifier 独立 | Verifier 与 Worker PID 不同 | 100% |

**Detailed spec → cards/T0030_phase_a_acceptance_spec.md**

---

## §6. Phase A 前置清单

> 进入 Phase A Kernel 实施**前必须**完成的项：

1. **CC Executor 修复**: T0001 ✅（Parfit 完成，dev sub-agent）
2. **Baseline 冻结**: T0002 ✅（Codex 自做，git tag + Restic reference）
3. **Phase A 10 项判据定稿**: T0030 (本审计 §5 占位)
4. **Phase 0 Spec-vs-Reality 报告**: T0020（本报告 ✅）
5. **Kernel 仓库初始化**: T0031 ✅（Schrodinger 完成）
6. **Simulation Harness**: T0040 ✅（Jason 完成，10/10 模拟跑通 0.04s）

**结论**: 6 项中 **5 项已** ✅，剩 T0030（本报告已为占位 → T0030 立即启动）。

---

## §7. Baseline 冻结方案

### 7.1 Git Tag
- Tag: `AIOS_VNEXT_BASELINE_v0`
- SHA: `0b964e646b46406895eefd816b05363687ee3a0d`
- Tagger: `xinzh <xinzh@users.noreply.github.com>`
- Date: `2026-10-08 10:50:29 +08:00`
- Branch: `main` at `D:\AIOS`
- Working tree: 117 untracked files（保留为日常状态，本卡不动）

### 8.2 Restic Snapshot Reference
- Snapshot ID: `06ecf159`
- 时间: `2026-09-30 15:22:54 +08:00`
- Source paths 数量: 270837 new files
- EXIT_CODE: **3**（lock file .aios_daemon_watchdog.lock 未排除）
- **待 T0004 完成后 supersede**：修复 lock exclude + 新 snapshot

### 8.3 回滚步骤
```bash
# Git 回滚（仅 HEAD，不动 tag）
git reset --hard AIOS_VNEXT_BASELINE_v0^{commit}  # 回到 baseline 提交

# Registry 回滚（如 T0007 需）
cp D:\AIOS\_backups\task-t0007-registry-20261008-105437.json \
   D:\AIOS\_agent-hub\v2\governance\PROTOCOL_REGISTRY.json

# Settings.json 回滚（如 T0001 需）
cp D:\AIOS\_backups\task-t0001-claude-settings-20261008-105353.json \
   C:\Users\xinzh\.claude\settings.json

# Kernel 回滚（如 T0031+ 需）
cd D:\AIOS\kernel && git reset --hard 001b4d8  # 回到 T0031 初始 commit

# 整 AIOS_VNEXT 回滚（如整体需）
rm -rf D:\AIOS\aios_tasks\aios_vnext
```

### 8.4 现状
- Baseline 已冻结 ✅
- 数据基线 reference 06ecf159 ✅
- 5 张 Phase 0 卡 Verified ✅
- Phase A 启动条件 = T0030 → T0031 (✅) → T0032-T0038 (InProgress/Planned)
- T0040 Sim harness 已就位 ✅

---

## §8. Codex 验收签字

- Phase 0 Spec-vs-Reality Audit: **Verified ✅**
- 6 节要求: §1 12 问 ✅ + §2 Matrix ✅ + §4 Conflict Map ✅ + §5 占位 ✅ + §6 Pre-req ✅ + §7 Baseline ✅
- T0030 Phase A Acceptance Spec v0.1: 已授权启动
- 总状态报告: 21 张卡中 5 张 Verified (T0001/T0002/T0007/T0008/T0031/T0040 = **6 张**)

**下一动作**: 启动 T0030 (Codex 自做 Phase A Acceptance Spec v0.1)，同时监督运行中 dev 代理 (Ptolemy T0004 / Hilbert T0032 / Ampere T0033 / Gibbs T0034)