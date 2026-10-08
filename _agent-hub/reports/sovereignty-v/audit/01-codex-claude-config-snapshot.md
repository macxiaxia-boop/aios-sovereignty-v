# T1 Audit — Codex / Claude Code 配置 + 环境快照

> **任务**: T1 audit · Codex/Claude Code user-level + project-level config files + env vars
> **模式**: READ_ONLY_AUDIT · 不写任何现有配置文件
> **作者**: Codex (aios-sovereignty-v engineering thread)
> **时间**: 2026-10-08T23:55Z → 23:59Z
> **授权**: user-2026-10-08T23:55 (T1-T4 全授权 · T5-T8 全授权)

---

## 1. 关键发现摘要

| # | 项 | 路径 | 当前值 | 风险 |
|---|---|---|---|---|
| 1 | CC 实际默认模型 | `~/.claude/settings.json` env.ANTHROPIC_MODEL | `MiniMax-M3` | ✅ 与用户决策一致 |
| 2 | CC subagent 模型 | `~/.claude/settings.json` env.CLAUDE_CODE_SUBAGENT_MODEL | `MiniMax-M2.7` | ✅ 一致 |
| 3 | CC fallback（默认） | `~/.claude/settings.json` env.ANTHROPIC_DEFAULT_*_MODEL_FALLBACK | `MiniMax-M3/M2.7` | ✅ 一致 |
| 4 | **cc-switch common_config_claude fallback** | `~/.cc-switch/cc-switch.db` settings.common_config_claude | `ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK = deepseek-v4-flash` | 🔴 **覆盖 settings.json,违反用户决策** |
| 5 | Codex CLI 当前 provider | `~/.cc-switch/settings.json` currentProviderCodex | `ca12d924-8362-4692-9cf6-f2823d391d2f` (MiniMax) | ✅ |
| 6 | Codex CLI 备用 profiles | `~/.codex/config.toml` [profiles.ollama/qwen25] | `qwen3:14b` / `qwen2.5:7b` | 🟡 历史遗留,非当前 |
| 7 | Codex CLI auth | `~/.codex/auth.json` OPENAI_API_KEY | MiniMax token | ✅ |
| 8 | MCP servers (CC) | `~/.claude/.mcp.json` | 14 个 (filesystem/github/memory/fetch/context7/firecrawl/tavily/dailyhot/hot-trends/douyin/xiaohongshu/wechat/weibo/kuaishou/sequential-thinking) | — |
| 9 | MCP servers (Codex) | `~/.codex/config.toml` [mcp_servers.*] | 5 个 (automate/hermes-agent/playwright/windows-automation/windows-mcp) | — |
| 10 | Claude Code settings.json | `_meta.frozen_at = 2026-09-01T16:05:00` | `_meta.modify_protocol = "any 修改前必须先 ask_user"` | 🔒 **FROZEN · 任何修改前必须 ask_user** |

---

## 2. Codex 全栈配置

### 2.1 Codex Desktop
- **路径**: `C:\Users\xinzh\AppData\Roaming\Codex\`
- **性质**: Browser-style state (Codex is built on Chromium); IndexedDB / Local Storage / Sync Data
- **模型相关配置**: ❌ **无**（Codex Desktop 不直接配置模型,模型由 Codex CLI / Codex 配置文件驱动）
- **对话历史**: `01a11c33-c813-7752-9e53-b7c332d00445` (本会话即在 Codex Desktop 内运行)

### 2.2 Codex CLI `~/.codex/config.toml`
- **信任项目**: c:\users\xinzh, C:\Users\xinzh, d:\documents\chatgpt\codex, 多个 2026-09-28 workspace, localexecutionbridge workspace (12 项 trust_level=trusted)
- **沙箱**: `[windows] sandbox = "unelevated"`
- **Profiles** (历史遗留):
  - `ollama` → `qwen3:14b` model_reasoning_effort=medium
  - `qwen25` → `qwen2.5:7b` model_reasoning_effort=low
  - ❌ **没有 minimax profile**（需通过 cc-switch 路由 ca12d924-...）
- **Hooks** (hash-trusted, 已注册):
  - pre_tool_use / post_tool_use / user_prompt_submit / subagent_stop / stop
- **MCP servers** (5 个):
  - automate (hermes-agent)
  - hermes-agent (WSL)
  - playwright (npx)
  - windows-automation (node openclaw tool)
  - windows-mcp (.local/bin/windows-mcp.exe)

### 2.3 Codex CLI auth
- `auth.json.OPENAI_API_KEY` = `sk-cp-mfkOcQH4RKNdoXIFELSKiy36jMGkxY945S7ffwoM_uIaTZuROMoWyKboJE4lwgimzBGWsKoKMn4o8eIwzc0G_gCmn4sWeZj176aclDgaKXSkr33tjlv2xJ8`
- 即 MiniMax CN API key（与 `.openclaw/.env` 中 MINIMAX_API_KEY 同源 · 红线 #62 双轨）

---

## 3. Claude Code 全栈配置

### 3.1 CC settings.json · 🔒 FROZEN
- **路径**: `C:\Users\xinzh\.claude\settings.json`
- **`_meta.modify_protocol`**: "任何修改前必须先 ask_user 确认, watchdog / cc-switch / automation 也不得动这个文件"
- **`_meta.frozen_at`**: 2026-09-01T16:05:00
- **关键 env**:
  - `ANTHROPIC_BASE_URL = https://api.minimaxi.com/anthropic` (MiniMax)
  - `ANTHROPIC_AUTH_TOKEN = sk-cp-mfkOcQH4RKNdoXIFELSKiy36jMGkxY945S7ffwoM_uIaTZuROMoWyKboJE4lwgimzBGWsKoKMn4o8eIwzc0G_gCmn4sWeZj176aclDgaKXSkr33tjlv2xJ8` (MiniMax token)
  - `ANTHROPIC_MODEL = MiniMax-M3`
  - `ANTHROPIC_SMALL_FAST_MODEL = MiniMax-M2.7-highspeed`
  - `CLAUDE_CODE_SUBAGENT_MODEL = MiniMax-M2.7`
  - 所有 `ANTHROPIC_DEFAULT_*_MODEL_FALLBACK` = MiniMax-M3 或 MiniMax-M2.7
  - `_NOTES = R262: "cc 是智障, 现在默认用的就是 minimax, 每次都忘"`
- **用户注释**: "可选 model: agnes / ollama · Claude Code CLI 默认走 MiniMax 不动, 切换方式:cc-switch.exe / 自己手动改 ANTHROPIC_BASE_URL+ANTHROPIC_AUTH_TOKEN"

### 3.2 CC CLAUDE.md
- AIOS Current Shared Protocol Bootstrap (delegates to D:\AIOS\_agent-hub\AGENTS.md)
- Moon Capsule L0 Kernel (R377 立 · 2026-10-02)
- AIOS 认知治理 V5.0 SSOT (R121 立 · 2026-09-21)
- AIOS 工程母令 (R1337 立 · 2026-10-08)
- EXISTING CONFIGURATION (DO NOT TOUCH): aios-interop, playwright
- New MCP (GitHub) — Pending · 仅在用户明确要求时启用

### 3.3 CC .mcp.json (14 servers)
- filesystem (npm-global) · github · memory · fetch · context7 · firecrawl
- tavily-mcp · dailyhot · hot-trends
- douyin / xiaohongshu / wechat / weibo / kuaishou (tikhub remote)
- sequential-thinking

---

## 4. 关键风险

### 4.1 🔴 P0 · cc-switch common_config_claude fallback 覆盖
- cc-switch 通过 `common_config_claude` 注入 `ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK = deepseek-v4-flash`
- **当 CC 调用失败时, CC 会 fallback 到 deepseek,违反用户决策**
- 这正是用户 "每次都忘 minimax 默认" 的根本原因之一
- **必须**: ModelPolicy v1 强制 `common_config_claude` 不再注入 non-MiniMax fallback

### 4.2 🟡 P1 · Codex profiles 残留历史
- `[profiles.ollama]` 和 `[profiles.qwen25]` 仍在 `~/.codex/config.toml`
- 虽然不是 default, 但通过 `codex --profile ollama` 可激活
- **建议**: ModelPolicy v1 给 Codex config 加 allowlist 注释, 标注"残留, 不可激活"

### 4.3 🔵 P2 · Codex auth.json 单一 token 镜像
- `~/.codex/auth.json.OPENAI_API_KEY` 与 `~/.claude/settings.json.ANTHROPIC_AUTH_TOKEN` 镜像
- 与 `~/.openclaw/.env.MINIMAX_API_KEY` 镜像
- 凭据冗余 = 风险面扩大 · 红线 #62 双轨 SSOT 是已知问题

---

## 5. 审计工件路径

- W1_config_snapshot → `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\01-config-snapshot.json` (本报告)
- W2_env_snapshot → `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\02-env-snapshot.txt`
