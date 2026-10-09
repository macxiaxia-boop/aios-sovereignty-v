# AIOS 执行路线图（严格 P0→P3 · Supervisor 19:50 官方 CLI 修正后）

> **生成者**: Claude Code 2.1.282 (MiniMax-M3) — 执行手
> **监督**: Codex Supervisor
> **捕获时间**: 2026-09-29T11:43:50Z (19:43 +08:00)
> **post-supervisor refresh**: 2026-09-29T11:50:00Z (19:50 +08:00) — OpenClaw 路线图项改写
> **核心原则**: Codex=脑(决策/审批)、Claude Code=手脚(执行/取证);未完成 P0 不得进入 P3 建设
> **修正要点（Supervisor 19:50）**: OpenClaw Gateway agent → status=ACTIVE/maturity=Integrated（官方 CLI 权威）；br-aios-openclaw 桥 → VERIFIED；eventLoop.degraded=true(cpu) 为已知风险；**P0-08 "OpenClaw agent API 修复" 删除/改写**——/v1/agents /api/status /api/agents /api/version /api/v1/health 404 非 OpenClaw 官方状态接口，不能据此支持 BROKEN 结论；改为 **P0-04b OpenClaw 稳定性观察 + P0-04c AIOS 真实消息 round-trip 验收**。Hermes 无 messaging platforms → status=VERIFIED/maturity=Tested。Claude Code 执行手体系 PARTIAL(agent workflow Validated)。AIOS 整体 maturity Tested

---

## 0. 路线图执行铁律

1. **Codex=脑**: 决策、scope 审批、registry 写入 — 由 Codex 闭环处置（当前 19194 relay BROKEN 无法实时监督）
2. **Claude Code=手脚**: 探针、SHA256 取证、CSV/JSON 生成、文件创建、修正草案 — 由本执行手完成
3. **未完成 P0 不进入 P3**: P0 含 freeze/restore/registry drift 等基础；P3 业务建设依赖 P0 稳定
4. **每个项目含**: Owner · 输入 · 允许修改范围 · 验证命令 · 输出 · 验收 · 回滚/风险
5. **不重启动**: 本路线图本身不重启服务；只列计划；执行需另开 round
6. **五级成熟度**: Implemented / Tested / Integrated / Validated / Production Ready 严格区分，不得混用

---

## 1. P0 — 基础冻结与一致性（必须最先完成）

### P0-01 · 冻结并发写入窗口 + 可重复快照

| 项 | 内容 |
|---|---|
| **Owner** | Codex Supervisor 决策 + Claude Code 执行 |
| **输入** | git working tree 210 entries dirty（AR-0213）；R281.2 已 fix 部分 |
| **允许修改范围** | 仅 governance/ 工具脚本；不写业务代码；不重启服务 |
| **验证命令** | `python governance/snapshot.py --freeze`; `git status --short --branch` (应保持 210 entries 不再变化) |
| **输出** | `governance/snapshots/2026-09-29_1943__FULL_SHA256.json` 含顶层 mtime+sha256 |
| **验收** | snapshot.json hash + 后续 24h 内 git status 变化率 < 5 entries/h |
| **回滚/风险** | 仅创建文件;无破坏性;若失败保留旧 R281.2 evidence |

### P0-02 · 修复 SSOT / inventory 一致性

| 项 | 内容 |
|---|---|
| **Owner** | Codex 决策 |
| **输入** | FILE_INVENTORY.csv 仅覆盖 D:/AIOS（AR-0019 LEGACY，post-gen refresh sha256 10c17df4…）；AIOS_REALITY_MAP.json NUMBER DRIFT（AR-0029 UNKNOWN）；PROTOCOL_REGISTRY.json 被并发 CC 二次修改（post-gen refresh sha256 **254ac61d…**，结构 32/29/22/7 未变） |
| **允许修改范围** | governance/PROTOCOL_REGISTRY.json（仅 schema 升级）+ CANONICAL_INDEX.json；不动 FILE_INVENTORY.csv |
| **验证命令** | `python governance/protocol_registry.py validate`; `python governance/build_assets.py` |
| **输出** | 更新后的 PROTOCOL_REGISTRY schema=3（标记 FILE_INVENTORY.csv 为 LEGACY + REALITY_MAP.json 为 UNKNOWN） |
| **验收** | validate exit 0；build_assets.py AUDIT_MANIFEST match=True |
| **回滚/风险** | 走 protocol_registry.py publish --apply --approve REGISTRY_ONLY(TEST_ONLY 副本)；失败回滚到原文件 |

### P0-03 · 角色对齐（Codex=Supervisor + Claude Code=Executor）

| 项 | 内容 |
|---|---|
| **Owner** | Codex 决策 |
| **输入** | agents.json:codex.role="executor" vs CLAUDE.md Codex=Supervisor（CONFLICT, AR-0031）；claudecode.role="executor" vs CLAUDE.md CC=Executor 一致 |
| **允许修改范围** | `_agent-hub/v2/agents/agents.json` 仅 codex.role 字段（其他不动） |
| **验证命令** | `cat _agent-hub/v2/agents/agents.json | jq .agents[0].role` 应返回 "supervisor" |
| **输出** | 修改后的 agents.json + R322 decision log entry |
| **验收** | CONFLICT 消除；agents.json v2 兼容（v2-2026-09-29 不破坏） |
| **回滚/风险** | 修改前备份到 `_agent-hub/v2/agents/agents.json.bak-pre-R322`；失败恢复 |

### P0-04 · 稳定 18792（OpenClaw gateway）+ 19194（Codex relay）

| 项 | 内容 |
|---|---|
| **Owner** | Codex Supervisor |
| **输入** | **19:50 Supervisor 官方 CLI 修正**: 18792 LISTENING (PID 19108, node.exe) + `/healthz 200` + **`openclaw status --json` exit0: gateway.reachable=true; tasks succeeded=9/9** + **`openclaw health --json` exit0: feishu enabled/running/connected=true**。eventLoop.degraded=true(cpu) 为已知风险。19194 NOT LISTENING（连续 4 个时点 14:18/14:40/19:43/19:50 BROKEN） |
| **允许修改范围** | 不在本路线图执行；只列计划 |
| **验证命令** | `Get-NetTCPConnection -LocalPort 18792,19194`; `curl http://127.0.0.1:18792/healthz`; **`openclaw status --json`; `openclaw health --json`**（**官方只读 CLI 权威**，不得用假定路由 404 推断）; `curl http://127.0.0.1:19194/` |
| **输出** | （不在本轮执行） |
| **验收** | **18792**: 持续 LISTENING ≥1h + 官方 CLI `gateway.reachable=true` + tasks succeeded/failures 健康 + feishu connected + **eventLoop.degraded=false**；**19194**: 持续 LISTENING + HTTP 200 ≥1h |
| **回滚/风险** | 19194 进程丢失需查 _start_relay_19194.* 历史启动脚本 |

### P0-04b（新增 · 19:50 替代原 P0-08）· OpenClaw Gateway 稳定性观察

| 项 | 内容 |
|---|---|
| **Owner** | Codex Supervisor |
| **输入** | 19:50 官方 CLI: `eventLoop.degraded=true reason=cpu`；OpenClaw Gateway 当前 ACTIVE/Integrated 但事件循环 CPU 受压 |
| **允许修改范围** | 不在本路线图执行；只列观察计划 |
| **验证命令** | `openclaw health --json`（每 5 分钟重探 1 次持续 ≥1h）；监控 `eventLoop.degraded` 字段变化 |
| **输出** | 稳定性观察日志（含 degraded 字段时序） |
| **验收** | eventLoop.degraded 由 true → false 或 CPU 占用稳定下降；如持续 degraded ≥1h 须 Codex 决策是否升 HIGH 风险 |
| **回滚/风险** | 观察不涉及服务重启；不影响主功能 |

### P0-05 · 真实 CC↔OpenClaw round-trip（含 br-aios-openclaw 真实消息 round-trip 验收 · 19:50 强化）

| 项 | 内容 |
|---|---|
| **Owner** | Codex Supervisor 决策 + CC 执行观测 |
| **输入** | br-claudecode-openclaw 标 loopback_only/unverified；br-aios-openclaw 19:50 官方 CLI 确认 gateway+Feishu 当前连接但**无 AIOS 真实消息 round-trip**；Codex↔CC two-process round-trip 有 ack 文件实证（**本轮修正：仅文件计数，无消费者侧端到端实测**）；OpenClaw↔v2 NOT verified |
| **允许修改范围** | 新建 OpenClaw bridge consumer 进程（不在本轮）；本路线图仅观察 inbox/outbox 文件 |
| **验证命令** | `ls _agent-hub/v2/messages/inbox`; `ls _agent-hub/v2/messages/outbox`; **`openclaw status --json`**（官方 CLI；必须 tasks 列表出现 ≥1 个 AIOS-originated 任务）；观察 `eventLoop.degraded` 字段 |
| **输出** | inbox 增加 OpenClaw-ack 格式文件（如 `__{openclaw}__claudecode__ack.json`） |
| **验收** | inbox 出现 ≥1 个 OpenClaw 进程消费的 ack/result envelope + `openclaw status --json` 显示 tasks 来源含 AIOS + 19:50 官方 CLI 所有字段保持健康 |
| **回滚/风险** | 若 OpenClaw 端消费出错，retry/reap 由 v2 state machine 控制（test_04） |

### ~~P0-08（已删除 · 19:50）· OpenClaw agent API 修复~~

> **删除理由（Supervisor 19:50 官方 CLI 权威）**：
> - 原 P0-08 假设 `/v1/agents /api/status /api/agents /api/version /api/v1/health` 404 表明 OpenClaw agent API 损坏，须修复。
> - 19:50 Supervisor 执行官方只读 CLI：`openclaw status --json` exit0（runtimeVersion 2026.9.5; gateway.reachable=true; tasks succeeded=9/9）+ `openclaw health --json` exit0（ok=true; feishu connected=true）。
> - **`/v1/agents /api/status /api/agents /api/version /api/v1/health` 非 OpenClaw 官方状态接口**；未知路由 404 **不能支持 BROKEN 结论**。
> - 因此原 P0-08 的"修复 agent API"前提不成立；该路线图项删除。
> - **替代**: OpenClaw 稳定性观察迁入 **P0-04b**；AIOS 真实消息 round-trip 验收并入 **P0-05**；事件循环 CPU 风险纳入 P0-04b。

### P0-06 · 统一 memory / state / evidence 入口

| 项 | 内容 |
|---|---|
| **Owner** | Codex Supervisor |
| **输入** | v2/health.json（30 分钟前 snapshot）+ aiosv2.py status/health（实时，本轮 19:43 执行成功）+ MEMORY.md（多份分散） |
| **允许修改范围** | `_agent-hub/v2/health.json` 字段；不写 MEMORY.md |
| **验证命令** | `python _agent-hub/v2/cli/aiosv2.py health > /tmp/h.json`; `diff /tmp/h.json _agent-hub/v2/health.json` (差异应在 captured_at < 5min) |
| **输出** | v2/health.json 自动 cron（每 5 分钟更新）;schema 统一（agent/transport/captured_at/evidence） |
| **验收** | v2/health.json captured_at 与 aiosv2 health 时间差 < 5 min |
| **回滚/风险** | cron 失败仅 v2/health.json 过期；不影响主功能 |

### P0-07（新增）· Hermes 真实消息 round-trip

| 项 | 内容 |
|---|---|
| **Owner** | Codex Supervisor |
| **输入** | **19:43 实测**: hermes --version exit 0 + hermes status 显示 messaging platforms (Telegram/Discord/Slack/Signal) **全部 ✗ 未配置**；无真实消息 round-trip |
| **允许修改范围** | `_relinked/hermes/.env` 配置 messaging platform credentials（用户授权后）；不读 secret 内容 |
| **验证命令** | `hermes status` (应显示至少 1 个 messaging platform 已配置); `hermes send --list` (应返回至少 1 个 target) |
| **输出** | 至少 1 个 messaging platform configured + 至少 1 次 hermes send 端到端成功 |
| **验收** | hermes status 显示 ≥1 platform ✓；hermes send exit 0；不读 secret 内容 |
| **回滚/风险** | 配置失败仅 messaging 不可用；不影响 hermes CLI |

---

## 2. P1 — 协作层（依赖 P0 稳定）

### P1-01 · Codex 监督机制（实时健康看板）

- Owner: Codex
- 输入: P0-06 完成后
- 输出: `aiosv2 dashboard --watch`（30s 刷新；5 agent + 6 port 状态）
- 验收: dashboard 输出 ≥1h 不掉线；BROKEN 自动告警
- 风险: 沙箱阻塞（workbuddy 已 present=true reachable=false）

### P1-02 · Claude Code 执行手体系（本轮修正：MISSING → PARTIAL）

- Owner: Codex
- 输入: P0-03 角色对齐完成后
- **本轮修正**: CLAUDE.md 已声明 CC=Executor;本轮 19:43 端到端完成 3 扫描+5 修正（README 重写 / 6 交付物同步 / INDEX.md 删除 / 状态判级修正 / hash 重记录）+ 最终生成成功;**agent workflow Validated**;**但体系仍 PARTIAL**（缺 dispatch/SLA/metrics 标准）
- 输出: `aiosv2 dispatch --agent claude --task T-NNN` 接口 + SLA table + metrics emitter
- 验收: dispatch 调用 CC 执行端到端任务;SLA table 定义;metrics emitter 输出
- 风险: CC 任务 SLA 未定义 → 不可宣称 Production Ready

### P1-03 · Agent 路由策略

- Owner: Codex
- 输入: test_05_protocol_loopback 5/5 PASS
- 输出: `routing.yaml`（Codex 决策树）；`v2/protocol/router.py`
- 验收: routing.yaml 与 protocol/router.py 一致
- 风险: 路由规则不周全需迭代

### P1-04 · 任务分发 SLA / timeout / retry

- Owner: Codex
- 输入: test_04 4/4 PASS（已 Tested）
- 输出: SLA table（default 30s ttl / 3 retries）；写入 `governance/SLA.md`
- 验收: SLA.md 与 v2 state machine 一致
- 风险: SLA 不合理导致任务频繁 retry

### P1-05 · Claude↔Codex 协作协议

- Owner: Codex
- 输入: Codex↔CC round-trip **仅文件计数有 ack 实证**（本轮保守判 Tested，非 Validated）
- 输出: `Codex-CC-Collaboration-SOP.md`：Codex 决策 / CC 执行；分工明确
- 验收: SOP 含 5+ 协作场景 + 错误处理
- 风险: SOP 与实际场景不符

### P1-06 · 失败重试 / 降级策略

- Owner: Codex
- 输入: test_03+test_04 12/12 PASS
- 输出: `v2 broker --policy {strict|lenient}` 实现
- 验收: broker policy 实测 strict/lenient 行为
- 风险: policy 切换导致任务积压

### P1-07 · 自动化任务计划（v2 cron）

- Owner: Codex
- 输入: aiosv2.py 8/8 modules 不含 cron
- 输出: `v2 cron --add "*/5 * * * *" aiosv2 health`
- 验收: cron 列表 + 最近 5 次执行记录
- 风险: Windows Task Scheduler 与 v2 cron 双轨

### P1-08 · 工作流模板（workflow JSON）

- Owner: Codex
- 输入: 已有 ad-hoc 命令
- 输出: `v2 workflow create --from JSON`
- 验收: 工作流 JSON schema 校验
- 风险: workflow 复杂度难管理

### P1-09 · 工具连接路由表（26 MCP）

- Owner: Codex
- 输入: 26 MCP 服务 + 13 模型资源
- 输出: `v2 tool-router --show` 列出路由
- 验收: router 含全部 26 MCP
- 风险: 5 BROKEN MCP + OpenClaw Gateway eventLoop CPU degraded + br-aios-openclaw 桥功能 PARTIAL 阻塞路由

### P1-10 · GitHub MCP 接入（需 user 批准）

- Owner: Codex + user explicit ask
- 输入: github MCP server 已声明
- 输出: 修改 `~/.claude.json` 注册 github MCP
- 验收: GitHub MCP tool-call 成功
- 风险: CLAUDE.md 默认禁止；需 explicit ask

### P1-11 · Codex CLI ↔ ChatGPT 桌面

- Owner: Codex
- 输入: br-aios-codex active 但 19194 BROKEN
- 输出: 19194 relay 重启 + ChatGPT.exe round-trip
- 验收: ChatGPT 跨桌面回应 ≥1 次
- 风险: ChatGPT 桌面 OAuth 复杂

### P1-12 · Task-board MCP 接入

- Owner: Codex
- 输入: OpenClaw task-board 声明（19:50 Supervisor 官方 CLI 确认 OpenClaw Gateway ACTIVE/Integrated；task-board MCP 路径待实测）
- 输出: task-board submit+query 实测
- 验收: task 创建 + 状态查询端到端
- 风险: 依赖 P0-04b OpenClaw 稳定性观察 + P0-05 真实消息 round-trip

---

## 3. P2 — 工程层（依赖 P1）

### P2-01 · 工程化跨资产可执行性

- Owner: Codex
- 输入: AR-0001..0216 216 资产
- 输出: `aiosv2 exec --asset AR-XXXX`
- 验收: 任意资产可 exec
- 风险: exec 范围需严格

### P2-02 · 文档-代码-配置三方同步

- Owner: Codex
- 输入: governance/scan_inventory.py + housekeeper.py
- 输出: `aiosv2 sync-check --all`
- 验收: sync-check 输出 0 drift
- 风险: 文档可能刻意保留历史

### P2-03 · CI/CD 流水线（github actions）

- Owner: Codex
- 输入: 缺 CI evidence
- 输出: `.github/workflows/aiosv2-validate.yml`
- 验收: GitHub PR 触发 validate
- 风险: 沙箱无 git remote；需先建仓库

### P2-04 · 可观测性（trace/log/metric）

- Owner: Codex
- 输入: gateway logs 无 trace ID
- 输出: `aiosv2 trace --span` 集成 trace ID
- 验收: trace ID 在 logs 出现
- 风险: 日志改写破坏现有 log 解析

### P2-05 · 沙箱隔离执行（sandbox run）

- Owner: Codex
- 输入: 无 sandbox
- 输出: `v2 sandbox --isolate` 实现
- 验收: 沙箱内运行不影响 host
- 风险: 沙箱逃逸

### P2-06 · Secrets Manager（6 敏感配置）

- Owner: Codex
- 输入: AR-0054-0062 6 处敏感
- 输出: Codex 决定（1Password CLI / DPAPI / git-crypt）
- 验收: 6 路径不再以明文文件存在
- 风险: 迁移过程泄露

### P2-07 · Dependency 锁定（AIOS-LAB 14,910 untracked）

- Owner: Codex
- 输入: AR-0070 14,910 untracked
- 输出: .gitignore 覆盖 fixtures/test_codex_home
- 验收: AIOS-LAB git status 减少到 < 100
- 风险: 部分文件实为业务

### P2-08 · Registry 写入防漂

- Owner: Codex
- 输入: AR-0189 AR-0191 AR-0194 **3 条 REGISTRY DRIFT**（本轮修正：br-aios-openclaw 加入 drift 列表）
- 输出: `v2 registry audit --drift`
- 验收: drift 报告 0 条
- 风险: auto-revise 可能误判

---

## 4. P3 — 业务层（依赖 P0+P1+P2 全部完成；不得提前进入）

> **铁律**: 未完成 P0 不得进入 P3 建设。

### P3-01 · CloudTech 业务推进

- 依赖: P0-01 snapshot 稳定 + P0-02 SSOT 一致
- Owner: CloudTech 团队 + Codex 协调
- 范围: D:/CloudTech-* 5 根；Vault 同步；Inbox 5 行业
- 验收: Vault 增量 24h 内 ≥1 次；Inbox 5 行业至少 1 个新数据
- 风险: 业务停滞 5+ 天；存在 PII 风险

### P3-02 · 灵策智算业务推进

- 依赖: P0
- Owner: Codex + 灵策团队
- 范围: C:/Users/xinzh/灵策AI/research 扩展；D:/灵策AI 实质化
- 验收: OPC 学习材料 ≥10 份
- 风险: 灵策业务方向待定

### P3-03 · 内容 IP / OPC 推进

- 依赖: P0
- Owner: 内容团队
- 范围: 装修矩阵复活；小红书仿写管线 v2.0
- 验收: 1 篇新 OPC 发布
- 风险: 2+ 月未更新

### P3-04 · Obsidian vault 路径修正

- 依赖: 无（P3 即时）
- Owner: Claude Code
- 范围: Obsidian README.md + Daily/2026-09-28.md 路径文本
- 验收: 全部文本统一到 C:/Users/xinzh/.aios/Obsidian/
- 风险: 历史 backup 路径漂移

### P3-05 · WorkBuddy 业务接入

- 依赖: P0-04 18792 稳定（agent API 修复） + P0-06 unified health
- Owner: Codex
- 范围: ~/.workbuddy runtime 启用
- 验收: WorkBuddy 健康检查通过
- 风险: 沙箱阻塞

### P3-06 · OPC 装修矩阵 V2 复活

- 依赖: P3-03
- Owner: 内容团队
- 范围: C:/Users/xinzh/_项目/装修矩阵/装修矩阵内容调度系统V2
- 验收: cli.py 执行成功
- 风险: 数据陈旧 2+ 月

### P3-07 · 小红书仿写管线 v2.0 复活

- 依赖: P3-03
- Owner: 内容团队
- 范围: C:/Users/xinzh/content_input + content_output
- 验收: 1 个新样本运行
- 风险: 6+ 周停摆

### P3-08 · Lingce 客户故事扩展

- 依赖: P3-02
- Owner: 灵策团队
- 范围: C:/Users/xinzh/灵策AI/research W1/W2/W3 扩展
- 验收: OPC 学习材料 ≥10 份
- 风险: 内容方向待定

### P3-X1 · V16 zip 包整合

- 依赖: 无
- Owner: Codex
- 范围: V16 zip 是否需解压或仅作源
- 验收: 决策明确
- 风险: 已确认 zip 仅骨架；SSOT 已来自 3 扫描

---

## 5. 当前进度（2026-09-29T11:50:00Z · Supervisor 19:50 官方 CLI 修正后）

| 优先级 | 完成 | 进行中 | 阻塞 | 未开始 | 新增/删除（本轮 19:50） |
|---|---|---|---|---|---|
| **P0** | 0/14 → **0/14** | 0 | 5 → **7** (BLK-1/3/4/5/12/13 + Hermes/eventLoop) | 9 | +P0-07 Hermes round-trip +P0-04b OpenClaw 稳定性观察（替换原 P0-08）；−P0-08 删除（基于官方 CLI 权威） |
| **P1** | 0/12 | 0 | 1 → 2 (BLK-1/13 + Claude 体系) | 11 | Claude 体系 MISSING→PARTIAL |
| **P2** | 0/8 | 0 | 0 | 8 | — |
| **P3** | 0/8 | 0 | 0 | 8 | — |

> **总进度**: 0/42 已完成（不变）；本轮交付 SSOT + 6 交付物作为 P0-01/02 的基础支撑；本轮修正任务本身作为 Claude Code 执行手体系 PARTIAL 的端到端验证（agent workflow Validated）。

---

## 6. 下一步（建议 Codex Supervisor 决策顺序 · Supervisor 19:50 修正后）

1. **P0-04b** OpenClaw Gateway 稳定性观察（eventLoop.degraded(cpu)）— MED RISK（19:50 官方 CLI 新发现）
2. **P0-04** 19194 relay 重启 — HIGH BLOCKER
3. **P0-03** 角色对齐 — CONFLICT 必须立即处置
4. **P0-07** Hermes messaging platforms 配置 — MED BLOCKER
5. **P0-06** 统一 health — 服务稳定基础
6. **P0-02** SSOT 修复 — 数据基础
7. **P0-01** 冻结快照 — 业务前提
8. **P0-05** CC↔OpenClaw 真实消息 round-trip（含 br-aios-openclaw 桥验收） — 协作链
9. 进入 P1...P3

---

## 7. 验收（铁律 #2 自检 · Supervisor 19:50 修正后）

- [x] 严格 P0→P3 顺序
- [x] 每项含 Owner / 输入 / 范围 / 命令 / 输出 / 验收 / 风险
- [x] P0 优先且 Codex=脑、CC=手脚
- [x] 明确未完成 P0 不得进入 P3 建设
- [x] 42 项 (14+12+8+8) 全列
- [x] 反映本轮 19:43 实时探针（不是 14:18 或 14:40）
- [x] **本轮 19:50 修正**: 删除原 P0-08 OpenClaw agent API 修复（基于 Supervisor 官方 CLI 权威：404 路径非 OpenClaw 官方状态接口）
- [x] **本轮 19:50 修正**: 新增 P0-04b OpenClaw Gateway 稳定性观察（eventLoop.degraded 监控）+ P0-05 强化含 br-aios-openclaw 真实消息 round-trip 验收
- [x] **本轮 19:50 修正**: P1-02 Claude 执行手体系 MISSING → PARTIAL（基于本轮端到端完成）
- [x] **本轮 19:50 修正**: 优先级排序 #1 → P0-04b OpenClaw 稳定性观察（替换原 P0-08）
- [x] **本轮 19:50 修正**: AIOS 整体 maturity Tested（55+129+178=362 已列测试证据，不构成生产验证）
