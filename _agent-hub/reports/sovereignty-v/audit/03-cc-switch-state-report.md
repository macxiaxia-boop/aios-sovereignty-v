# T2 Audit — cc-switch 当前 provider + 备份 + 启动钩子

> **任务**: T2 audit · cc-switch state + backup + startup hook scan
> **时间**: 2026-10-08T23:55Z → 23:59Z
> **路径**: `C:\Users\xinzh\.cc-switch\`

---

## 1. 数据库总览

- **cc-switch.db**: SQLite, 17 tables
- **size**: 实时 DB（含 WAL）
- **关键 tables**:
  - `providers` (17 行) · 列出所有已注册 provider
  - `settings` (7 行 K-V) · 配置开关 + common_config_* JSON
  - `model_pricing` (189 行) · 定价表
  - `mcp_servers` (5 行) · MCP 服务注册表
  - `usage_*` (4+ tables) · 历史用量
  - `profiles` (空) · 用户 profile
- **backups/**: 11 个 `db_backup_YYYYMMDD_HHMMSS.db` (从 20260913 到 20261008)
- **backups/codex-history-provider-migration-v1/**: 20260815 deepseek 历史迁移包

---

## 2. providers 表 17 行（重点）

| id | app | name | base | enabled | 备注 |
|---|---|---|---|---|---|
| `default` | claude | default | `https://api.deepseek.com/anthropic` (deepseek-v4-pro) | 1 | ⚠️ 自动迁移遗留 |
| `claude-official` | claude | Claude Official | anthropic.com | 0 | official · 禁用 |
| `claude-desktop-official` | claude-desktop | Claude Desktop Official | claude.ai | 0 | official · 禁用 |
| `codex-official` | codex | OpenAI Official | chatgpt.com/codex | 0 | 存有 id_token · 禁用 |
| `gemini-official` | gemini | Google Official | ai.google.dev | 0 | official · 禁用 |
| `grokbuild-official` | grokbuild | Grok Official | x.ai | 0 | official · 禁用 |
| `deepseek` | openclaw | deepseek-v4-flash | api.deepseek.com | 0 | openclaw · 已存 |
| `qwen` | openclaw | qwen3-coder-plus | dashscope.aliyuncs.com | 0 | openclaw · 已存 |
| `agnes` | openclaw | agnes-2.5-flash | apihub.agnes-ai.com | 0 | openclaw · v1 旧 |
| `agnes-ii` | openclaw | agnes-2.5-pro-alpha | apihub.agnes-ai.com | 0 | openclaw · R152b 用户新 |
| `zhipu` | openclaw | glm-4-flash | open.bigmodel.cn | 0 | openclaw · 智谱 |
| **`minimax`** | openclaw | **MiniMax-M2** (MiniMax-M3/M2.7-highspeed) | `https://api.minimaxi.com/v1` | 0 | **canonical MiniMax** |
| `ollama` | openclaw | qwen2.5:7b | localhost:11434 | 0 | local |
| `MiniMax` | hermes | MiniMax-M2.7 | api.minimaxi.com | 0 | hermes 镜像 |
| `Ollama` | hermes | qwen3:14b | localhost:11434 | 0 | hermes 镜像 |
| `OpenAI via Atlas Cloud` | hermes | openai/gpt-5.6-sol | api.atlascloud.ai | 0 | hermes 镜像 |
| **`ca12d924-8362-4692-9cf6-f2823d391d2f`** | codex | **MiniMax** | platform.minimaxi.com | **1** | **当前 Codex provider** |

---

## 3. settings 表（关键 K-V）

| key | value 摘要 | 风险 |
|---|---|---|
| `default_skill_repos_initialized` | true | — |
| `official_providers_seeded` | true | — |
| `gemini_common_config_credentials_scrubbed_v1` | true | — |
| **`common_config_claude`** | `ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK = deepseek-v4-flash` 等 | 🔴 **覆盖 settings.json** |
| **`common_config_openclaw`** | `migrations.modelPolicyAllowlist: true` | 🟢 **sovereignty-v 锚点** |
| **`common_config_codex`** | `model_reasoning_effort = high` + trust_level 项目 | ✅ |
| `common_config_legacy_migrated_v1` | true | — |

### 3.1 common_config_openclaw (modelPolicyAllowlist 锚点)
```json
{
  "$schema": "https://openclaw.ai/schemas/config.json",
  "meta": {
    "lastTouchedVersion": "2026.8.1-beta.1",
    "migrations": {
      "modelPolicyAllowlist": true
    }
  },
  ...
}
```
→ OpenClaw 已经在 `lastTouchedVersion` 加了 `modelPolicyAllowlist: true` 迁移标记 · 这正是 sovereignty-v 目标

---

## 4. settings.json（独立 JSON 文件 · 与 DB 同目录）

```json
{
  "showInTray": true,
  "minimizeToTrayOnClose": true,
  "enableLocalProxy": false,
  "enableFailoverToggle": false,
  "preserveCodexOfficialAuthOnSwitch": false,
  "unifyCodexSessionHistory": false,
  "currentProviderClaude": "default",
  "currentProviderCodex": "ca12d924-8362-4692-9cf6-f2823d391d2f",
  ...
  "localMigrations": {
    "codexThirdPartyHistoryProviderBucketV1": {
      "completedAt": "2026-08-15T13:17:17.291450700+00:00",
      "targetProviderId": "custom",
      "sourceProviderIds": ["deepseek"],
      "migratedJsonlFiles": 93,
      "migratedStateRows": 93
    },
    "codexProviderTemplateV1": {
      "completedAt": "2026-08-15T13:17:17.431110300+00:00",
      "migratedProviderIds": ["default"]
    }
  }
}
```

---

## 5. 备份清单（11 个 db_backup_*.db）

| 文件 | 时间 | 备注 |
|---|---|---|
| db_backup_20260913_173042.db | 2026-09-13 | 最早 |
| db_backup_20260915_214654.db | 2026-09-15 | |
| db_backup_20260919_141050.db | 2026-09-19 | |
| db_backup_20260920_172844.db | 2026-09-20 | |
| db_backup_20260922_140920.db | 2026-09-22 | |
| db_backup_20260924_093202.db | 2026-09-24 | |
| db_backup_20260925_093202.db | 2026-09-25 | |
| db_backup_20260927_175607.db | 2026-09-27 | |
| db_backup_20260929_105159.db | 2026-09-29 | |
| **db_backup_20261008_093251.db** | **2026-10-08** | 最新 |

---

## 6. 启动钩子 (Windows autorun)

- ❌ **未发现 cc-switch 直接注册到 Task Scheduler**
- ❌ **未发现 cc-switch 直接注册到 Startup folder**
- 🟢 cc-switch 通过 `currentProviderCodex = ca12d924-...` 动态切换, 不需要 OS 启动钩
- 🟡 cc-switch 通过 `common_config_*` 写入 `~/.codex/config.toml` (Codex) + `~/.claude/settings.json` (CC) 是它"影响启动行为"的真正机制

---

## 7. 关键风险

### 7.1 🔴 P0 · common_config_claude 覆盖用户决策
- 当 CC 调用失败时, cc-switch 注入的 `ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK = deepseek-v4-flash` 会让 CC 切到 deepseek
- 用户说"每次都忘 minimax 默认", 这就是根因之一
- **必须**: ModelPolicy v1 锁定 cc-switch 的 `common_config_claude` 写入白名单

### 7.2 🟡 P1 · default provider 仍是 deepseek-v4-pro
- `default` provider 当前 `enabled=1`, base = `https://api.deepseek.com/anthropic`
- 这意味着如果 `currentProviderClaude` 重置到 default, CC 会走 deepseek
- **必须**: ModelPolicy v1 把 default 重命名为 `legacy-disabled` 或直接删

### 7.3 🟢 P0 · openclaw modelPolicyAllowlist 锚点已就位
- `common_config_openclaw.meta.migrations.modelPolicyAllowlist = true` 是 sovereignty-v 的天然钩子
- **直接复用**: T5 ModelPolicy v1 YAML 的 schema 应匹配 openclaw 迁移格式

---

## 8. 审计工件路径

- W3_cc_switch_report → 本文件 `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\03-cc-switch-state-report.md`
