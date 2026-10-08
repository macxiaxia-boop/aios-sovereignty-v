# T3 Audit — OpenClaw agents/cron/gateway model 字段扫描

> **任务**: T3 audit · OpenClaw agents/*.yaml + cron/*.yaml + gateway model 字段
> **时间**: 2026-10-08T23:55Z → 23:59Z
> **路径**: `C:\Users\xinzh\.openclaw\`

---

## 1. 目录结构（顶层）

```
.openclaw/
├── agents/         # agent 定义 (sqlite in state/, 不在 agents/)
├── cache/          # 缓存
├── completions/    # 命令补全
├── extensions/     # 扩展
├── logs/           # 日志
├── media/          # 媒体
├── memory/         # 记忆库
├── npm/            # npm 资源
├── plugin-skills/  # 插件技能
├── skills/         # 技能
├── state/          # 状态数据库 (含 openclaw.sqlite)
├── tmp/            # 临时文件
├── tools/          # MCP 工具
├── workspace/      # 主工作区
├── workspace-claude/
├── workspace-codex/
├── workspace-isolated/
├── workspace-geo-{intent,competitor,strategy,creator,validator}/
└── .env            # ⚠️ 凭据镜像 (R140 治本)
```

## 2. openclaw.sqlite · 109 tables · 关键表

| table | rows | 用途 |
|---|---|---|
| **agent_databases** | 9 | 9 个 agent 各自的 sqlite (main, geo-{intent,competitor,strategy,creator,validator}, codex, claude, isolated) |
| **agent_database_leases** | 63 | agent DB 锁 (R346 lease-guard 治理) |
| **audit_events** | 97 | 审计事件 |
| **workspace_setup_state** | 9 | 9 个 workspace bootstrap 状态 |
| **workspace_attestations** | 9 | 9 个 workspace attestation sha256 |
| **session_dock_state** | 多 | session 状态 |
| **mcp_credentials** | — | MCP 凭据 (R140 治本锚点) |
| **provider_health** | — | provider 健康度 (sovereignty-v 校验钩) |
| **secret_surfaces** | — | secret surface 注册 |
| 其他 99+ tables | — | 内部运行状态 |

### 2.1 agent_databases 9 agents

| agent_id | path | schema_version | size_bytes |
|---|---|---|---|
| main | agents\main\agent\openclaw-agent.sqlite | 21 | 2.22 MB |
| geo-intent | agents\geo-intent\agent\openclaw-agent.sqlite | 21 | 3.66 MB |
| geo-competitor | agents\geo-competitor\agent\openclaw-agent.sqlite | 21 | 2.90 MB |
| geo-strategy | agents\geo-strategy\agent\openclaw-agent.sqlite | 21 | 3.64 MB |
| geo-creator | agents\geo-creator\agent\openclaw-agent.sqlite | 21 | 3.69 MB |
| geo-validator | agents\geo-validator\agent\openclaw-agent.sqlite | 21 | 3.50 MB |
| codex | agents\codex\agent\openclaw-agent.sqlite | 21 | 2.19 MB |
| claude | agents\claude\agent\openclaw-agent.sqlite | 21 | 2.19 MB |
| isolated | agents\isolated\agent\openclaw-agent.sqlite | 21 | 0.82 MB |

### 2.2 workspace_setup_state 9 workspaces (relinked 2026-09-30)

| workspace_key | path | bootstrap_seeded | setup_completed |
|---|---|---|---|
| 24a412... | d:\aios\_relinked\openclaw\workspace-geo-intent | 2026-09-30T13:41:17 | — |
| db45fc... | d:\aios\_relinked\openclaw\workspace-geo-competitor | 2026-09-30T13:51:00 | — |
| b611ce... | d:\aios\_relinked\openclaw\workspace | 2026-09-30T19:00:00 | — |
| 2ffb52... | d:\aios\_relinked\openclaw\workspace-isolated | 2026-10-01T01:58:53 | 2026-10-08T01:58:54 |
| 176370... | d:\aios\_relinked\openclaw\workspace-geo-strategy | 2026-10-07T14:16:42 | — |
| abe358... | d:\aios\_relinked\openclaw\workspace-geo-creator | 2026-10-07T14:16:46 | — |
| f16578... | d:\aios\_relinked\openclaw\workspace-geo-validator | 2026-10-07T14:16:52 | — |
| ce9958... | d:\aios\_relinked\openclaw\workspace-codex | 2026-10-07T14:16:56 | — |
| 9ddaad... | d:\aios\_relinked\openclaw\workspace-claude | 2026-10-07T14:17:03 | — |

### 2.3 workspace_attestations 全部 sha256 签名

---

## 3. agents/*.yaml 扫描结果

❌ **未在 `~/.openclaw/agents/` 找到任何 yaml 文件**
- agent 定义 100% 在 sqlite (`openclaw.sqlite` 和各 `openclaw-agent.sqlite`)
- T1 task_card 里假定的 `agents/*.yaml` 实际不存在 · 这是审计方法修正

---

## 4. cron/*.yaml 扫描结果

❌ **未在 `~/.openclaw/cron/` 找到 yaml**
- cron 任务在 system level Task Scheduler (见 T4 audit) + 内部 sqlite schedule tables

---

## 6. gateway model 字段

- ❌ **未发现独立 `gateway.yaml`** — openclaw 用 sqlite + CLI args 驱动 gateway
- `gateway/run.py` (926 KB · 大型 runtime) 处理实际推理路由
- `gateway/config.py` (96 KB) 处理 platform registry / channel / session reset
- **决定 gateway model 字段的是**: 各 agent 的 agent 配置 (sqlite), 不是 yaml

---

## 7. `.openclaw/.env` (R140 治本)

- **凭据镜像**: MINIMAX_API_KEY, ANTHROPIC_AUTH_TOKEN, DEEPSEEK_API_KEY/2, AGNES_API_KEY/II, ZHIPU_API_KEY, DASHSCOPE_API_KEY, DOUBAO_API_KEY, TAVILY_API_KEY, OPENCLAW_GATEWAY_TOKEN
- **关键注释**: "openclaw 加载顺序: ~/.openclaw/.env → ~/.config/openclaw/gateway.env → process.env"

---

## 8. 关键风险

### 8.1 🟢 P2 · OpenClaw agents 配置全在 sqlite
- **好处**: 没有散落的 yaml 文件污染, ModelPolicy v1 只写一个 policy 表
- **坏处**: 必须通过 openclaw CLI / sqlite 直接读写, 没有 yaml diff 工具可看
- **决定**: T5 ModelPolicy v1 落地为一个 sqlite schema (`policy_allowlist` table), 加 yaml 镜像 (`/etc/openclaw/policy.yaml`) 给 ops 看

### 8.2 🟢 P1 · modelPolicyAllowlist 迁移已就位
- `common_config_openclaw.meta.migrations.modelPolicyAllowlist = true`
- OpenClaw 已经预留了迁移标记
- **T5 直接对接这个迁移标记**, 让 `policy_allowlist` 表生效

### 8.3 🟡 P1 · 9 个 agent 各自有自己的 openclaw-agent.sqlite
- 每个 agent 可能有独立的 model 选择
- sovereignty-v v1 不动 agent 内部配置, 只在 **gateway 层** 强制 policy
- T7 Reconciler 只需要 hook 在 gateway, 不需要 hook 9 个 agent DB

---

## 9. 审计工件路径

- W4_openclaw_models → 本文件 `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\04-openclaw-models-report.md`
