# AIOS 通信主干 P0 实际环境审计

**协议代号**: AIOS-COMMUNICATION-SPINE-RECOVERY-V1
**执行者**: Codex (本会话 = 本机 Win11 + Codex Desktop)
**日期**: 2026-10-08
**范围**: 只读 · 现状冻结 · 不修改任何配置 / 服务 / 文件
**SSOT**: `D:\AIOS\_agent-hub\AGENTS.md` + `_agent-hub/v2/README.md` + 本文件

---

## 1. 主机与运行时

| 字段 | 实测值 | 证据 |
|---|---|---|
| Host | DESKTOP-0JKD1FQ | `$env:COMPUTERNAME` |
| User | xinzh | `$env:USERNAME` |
| AIOS 根 | `D:\AIOS\` | Test-Path True |
| Codex Home | `C:\Users\xinzh\.codex\` | Test-Path |
| CC CLI | `D:\npm-global\claude.ps1` | `Get-Command claude` |
| CC 版本 | 2.1.285 | `claude --version` |
| 关键能力 | `-p/--print`、`--resume <id>`、`-c/--continue`、`--output-format stream-json`、`--json-schema`、`--mcp-config`、`--add-dir`、`--allowedTools` | `claude --help` |

---

## 2. 当前 Codex↔CC 桥接 service 状态（winsw）

| Service | 路径 | 状态 | 备注 |
|---|---|---|---|
| aios-bridge-cc-codex-cli | `D:\AIOS\daemons_v2\winsw\bridge-cc-codex-cli\winsw.exe` | **Stopped** | 自 2026-09-25 17:13 起 30 秒级 crash-loop |
| aios-bridge-cc-openclaw | `D:\AIOS\daemons_v2\winsw\bridge-cc-openclaw\winsw.exe` | Stopped | — |
| aios-bridge-cc-doubao | `D:\AIOS\daemons_v2\winsw\bridge-cc-doubao\winsw.exe` | Stopped | — |
| aios-bridge-codex-desktop-cli | `D:\AIOS\daemons_v2\winsw\bridge-codex-desktop-cli\winsx.exe` | Stopped | — |
| aios-supervisor | `D:\AIOS\daemons_v2\winsw\supervisor\winsw.exe` | Stopped | — |
| aios-cron-orchestrator | `D:\AIOS\daemons_v2\winsw\cron-orchestrator\winsx.exe` | Stopped | — |
| aios-role-channels | `D:\AIOS\daemons_v2\winsw\role-channels\winsx.exe` | Stopped | — |
| aios-observability-hub | `D:\AIOS\daemons_v2\winsw\observability-hub\winsx.exe` | Stopped | — |
| AIOSSupervisor | `D:\个人文件\AI\Operator\aios_tools\data\winsw\AIOSSupervisor-svc.exe` | Running | 新 winsw 路径 |
| AIOSCentralCollector | …AIOSCentralCollector-svc.exe | Running | 端口 18799 |
| AIOSSelfHeal | …AIOSSelfHeal-svc.exe | Running | — |
| AIOS_Autonomy_Daemon | …aios-mcp-gateway-svc.exe | Running | 端口 19194 (Codex relay) |

> **结论**：两套 winsw 并存；旧 `daemons_v2\winsw\` 系列全部 STOPPED 且 bridge-cc-codex-cli 处于无意义 console 重启循环；新 `个人文件\AI\Operator\aios_tools\data\winsw\` 只有 4 个核心在 Running。

---

## 3. 桥接 service 真实失败原因（winsw.wrapper.log 取证）

文件：`D:\AIOS\daemons_v2\winsw\bridge-cc-codex-cli\winsw.wrapper.log`（131915 bytes，2046 行）

```
2026-09-25 16:05:36  Started process 18840  ← 初次启动 OK
2026-09-25 16:56:15  Stopping… Stopping aios-bridge-cc-codex-cli
2026-09-25 16:56:15  ProcessKill 18840
2026-09-25 16:56:15  ERROR - Failed to stop service.
                    System.ComponentModel.Win32Exception (6): 句柄无效。
   at System.Diagnostics.Process.GetProcessTimes()
   at System.Diagnostics.Process.GetProcessTimes() … StopProcessTree
2026-09-25 16:56:48  Starting service… Started process 16968
2026-09-25 17:13:34 → 18:04+  反复 "Starting WinSW in console mode"，没有后续日志
```

**根因 1（直接）**: `_bridge_cc_to_codex_cli.py` 是占位脚本（文件头 30 行表明：写 PID + while sleep + 写心跳，无任何派单逻辑），被外力 SIGKILL 后 WinSW 试图 Stop 但 PID 18840 句柄已失效。

**根因 2（间接）**: WinSW 配置 `onfailure action=restart delay=30/60/120 sec` 重启策略在服务停止失败时持续触发，但每次 "Starting WinSW in console mode" 后无任何 stdout/stderr → watchdog 永远判定需要再启 → crash loop。

**根因 3（结构）**: 4 个旧 daemon（codex_polling / codex_to_cc_inbox_watcher / codex_to_cc_bridge_v2 / codex_cli_to_cc_inbox_watcher）被脚本注释承诺在 L2 期合并，至今仍是占位。

---

## 4. v2 代码真实状态（按 README/CHANGELOG）

**目录**: `D:\AIOS\_agent-hub\v2\`

| 组件 | 文件 | 状态 |
|---|---|---|
| Envelope (versioned, JSON-Schema) | `src/envelope.py`, `schemas/envelope.schema.json` | R320.1 hardened |
| File queue (enqueue/claim/ack/deadletter + idempotency) | `src/queue.py` | R320.1 hardened (cross-process lock, uuid tmp) |
| Cross-platform file lock | `src/lock.py` | msvcrt + fcntl |
| Task state machine | `src/state_machine.py` | heartbeat + reap_expired |
| Supervisor (reap + snapshot) | `src/supervisor.py` | watch loop |
| Multi-recipient consumer (gated) | `src/v2_consumer.py` | **AIOS_V2_CHANNEL_ENABLED=1 才启** |
| 4-level probes | `src/probes.py` | configured/present/reachable/healthy |
| CLI | `cli/aiosv2.py` | init/status/health/send/receive/ack/submit-task/update-task/watch/tick |
| Tests | 8 modules / 42 cases + R320.6 增量 | **55/55 by Codex R320.6 round-3** |
| Agent registry | `agents/agents.json` | 5 agents: codex / claudecode / workbuddy / hermes / openclaw |

**R320.6 实测闭环**（CHANGELOG 记录，2026-09-29）：
- 真实两进程 round-trip：Codex 进程 send → 独立 CC 进程 receive/claim/result → Codex 进程 receive/ack
- 修复 `cmd_ack` 默认 `dest=outbox` → `inbox`，加 `--correlation-id` / `--in-reply-to`
- 闭环测试 `55/0` pass

**当前 v2 inbox 实测**（2026-10-08 13:54 UTC）：
- inbox: 10 个 envelope（codex→claudecode: ack/result 多条）
- outbox: 2 个 envelope（ack audit-only）
- deadletter: 0
- tasks: 4（1 succeeded / 2 queued / 1 cancelled）

---

## 5. 当前健康度实测（`python v2/cli/aiosv2.py health`，2026-10-08 13:54Z）

| Agent | configured | present | reachable | healthy | 阻断 |
|---|---|---|---|---|---|
| codex | ✅ | ✅ | ✅ | ❌ | relay 19194 端口在但 healthy 缺实测 |
| claudecode | ✅ | ✅ | ❌ | ❌ | 无 live aios-interop MCP call |
| workbuddy | ✅ | ❌ | ❌ | ❌ | hub 文件不在 |
| hermes | ✅ | ✅ | ❌ | ❌ | exec sandboxed |
| openclaw | ✅ | ✅ | ✅(port) | ❌ | /healthz 非 200 |

---

## 6. 通道故障根因矩阵（按第五章 5.1）

| 现象 | 优先调查 | 本次实测结论 |
|---|---|---|
| Codex 无法发送 | 调用接口/权限/可达 | CC CLI v2.1.285 真存在；bridge service STOPPED 是唯一阻塞 |
| 消息发送后消失 | 持久化/ACK/队列生命周期 | v2 queue.enqueue 在 cross-process lock 下原子写；inbox 有 10 条历史 envelope 验证持久化 OK |
| CC 没接单 | Worker 进程/订阅/权限 | 没有真正"订阅 inbox 并执行任务"的进程在跑（consumer runner 未启；bridge 是空壳） |
| CC 收到不执行 | 启动参数/工具权限/输入解析 | 未实测（无法触发真实两进程模型级派单） |
| CC 执行不回复 | 输出通道/缓冲阻塞 | 未实测 |
| 有输出但 Codex 看不到 | 结果存储/回调/任务 ID 映射 | v2 inbox 由 Codex 主动 `receive --agent codex`；若不查则不见信 |
| 大任务易失败 | 消息大小/输出积压 | v2 envelope 含 chunking，最大 64KB/text chunk |
| 反复执行同任务 | ACK 丢失/租约过期 | v2 idempotency_index 防重；lease 未强制 |
| Codex 自动自己施工 | Worker 不可用降级 | 当前真实在发生——bridge 全停，CC v2 probe "reachable=false" |
| 手动 CC 可以 MCP,自动不行 | 自动调用参数/权限差异 | 未实测 |

---

## 7. 真实阻断（按 chapter 18 进度表）

| 阻断 | 根因 | 负责方 |
|---|---|---|
| 旧 bridge service crash-loop | `_bridge_cc_to_codex_cli.py` 占位 + WinSW Stop 失败 | 历史 daemon 设计缺陷 |
| v2 consumer runner 未启 | `AIOS_V2_CHANNEL_ENABLED` 默认 OFF，无 watchdog 启动 | 缺失 watchdog 入口 |
| CC main session 不能 exec python | R320.1 已知 sandbox 限制 | CC 运行时 |
| Codex relay port 19194 端口在但 healthy 缺证据 | 缺真实 MCP 健康检查调用 | 缺实测脚本 |
| OpenClaw /healthz 非 200 | 主 workspace plugin runtime 超时 | OpenClaw 端 |
| WorkBuddy hub 文件不在 | hub 路径变化 | hub 路径漂移 |

---

## 8. P0 不动的决定（P1/P2 起点）

**P0 阶段不修复任何东西**。以下事项**已具备修复前提**，留到 P1/P2：

1. v2 CLI 是真实可用的 Codex↔CC 文件层最小桥 — 已验证 `send/receive/ack/status/health` 全部能跑。
2. CC CLI v2.1.285 是真实可用的进程级桥 — `claude -p "<task>"` 是当前唯一能 100% 触达 CC 子进程的接口。
3. v2 inbox 已有 10 条历史 envelope — 可作为回归测试 fixture。
4. 没有"活"的派单 watchdog — 必须新增一条：将 `claude -p` 包装成从 v2 inbox pull→执行→ack/result→put 回 inbox 的循环。

---

## 9. 进度表（chapter 18）

| 项目 | 实测结果 |
|---|---|
| Codex → CC 连通性（进程层） | **PASS** (claude v2.1.285 可调) |
| Codex → CC 连通性（派单 daemon 层） | **FAIL** (所有 bridge service STOPPED) |
| Codex → CC 连通性（模型会话级闭环） | **BLOCKED** (本会话未实测；待 P2 烟雾测试) |
| CC 实际接单 | **0/0** (无活跃派单入口) |
| 双向消息闭环 | **PASS at CLI 级** (v2 R320.6 55/55)；**UNVERIFIED at 模型会话级** |
| 持久任务与恢复 | **PASS at v2 schema**；**UNVERIFIED at 跨会话恢复** |
| 当前接入工具 | 5 configured / 4 present / 1 reachable / 0 healthy |
| 工具真实使用率 | 无历史调用统计 |
| 自动续跑 | 未测试 |
| 独立验收 | 0/24 |
| 当前真实阻断 | 6 项，详见 §7 |
| 最终 Baseline | **不存在** (v2 R320.6 是最近 SSOT，但 daemon 层全断) |

---

## 10. P0 结论

- v2 **协议层**（envelope/queue/state_machine/CLI）**是真实可用的 SSOT**。
- v2 **执行层**（v2_consumer / bridge / watchdog）**没有真活在生产里跑**。
- **真实最小派单桥 = `claude -p "<task>"` + v2 `aiosv2.py send/ack` 文件层协议** — 已在 P0 中确认存在性。

P1 起点 = 用 `claude -p` 真做一次最小端到端派单（建任务 → 持久化 → 真实 CC 子进程执行 → 落结果文件 → Codex 验真），作为 P2 修复"最小真实桥梁"的活体 baseline。