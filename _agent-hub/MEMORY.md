# MEMORY.md - Cross-Agent Long-Term Memory

> **Purpose**: Long-term facts that ALL agents should know. Short-term/daily work goes in `memory/YYYY-MM-DD.md`.

## CloudTech Project Context

- **Project**: AI 数字营销中台 (AI Digital Marketing Middle Platform)
- **Owner**: CloudTech 科技 founder / product lead
- **Phase 1**: Industry SaaS (医美 medical aesthetic + 装企 home decor) MVP
- **Phase 2**: Tool-type platform升维

## Competitive Positioning

- **灵策** (current market leader reference): 15 agents / 46 real skills
- **WorkBuddy** (current best-in-class): 16+ MCP connectors, memory system, skill self-accumulation
- **CloudTech unique assets** (differentiators):
  - 1,989 competitive intelligence documents
  - 2,421 SaaS corpus documents
  - 600+ industry vertical documents (家居 home decor / 医美 medical aesthetic)
  - Multi-tenant SaaS, RBK, billing, private deployment

## Business Lines

1. **CloudTech 科技** — parent brand
2. **灵策AI** — self-developed digital employee SaaS (70% marketing + 30% management)
3. **灵策智算** — procurement channel product

## Multi-Agent Stack (2026-09-28)

| Agent | Role | Memory/Config |
|---|---|---|
| workbuddy | Primary conversationalist | Junction to `D:\AIOS\_agent-hub\` |
| claudecode | Execution agent | aios-interop + playwright (preserved); GitHub MCP pending |
| codex | Execution agent | WSL2 config.toml + GitHub MCP (post-FIX-ALL) |
| Hermes | Open-source agent (Nous Research) | Own FTS5 + Honcho system — NOT modified |
| OpenClaw | TBD | Awaiting user path info |

## Active Project Locations

- **Code assets**: `[path omitted]` (memory-truncated, real path in actual project)
- **Channel fix artifacts**: `C:\Users\xinzh\WorkBuddy\2026-09-28-17-53-41\.workbuddy\root-cause-fix\`
- **Shared hub**: `D:\AIOS\_agent-hub\`
- **Hermes root**: `D:\AIOS\_relinked\hermes\hermes-agent\`
- **aios toolchain**: `D:\个人文件\AI\Operator\aios_tools\`

## Key Debugging Lessons (2026-09-28 channel fix)

1. **PowerShell ≠ bash** — `cat > ... <<'EOF'` / `&>` / `&&` / `${var}` all fail in PowerShell 5.1
2. **GBK encoding trap** — Chinese system reads .ps1 as GBK; UTF-8 Chinese becomes garbled
3. **WSL2 needs its own Node** — Windows node not visible in WSL2 PATH
4. **Codex config lives in WSL2** — Windows `C:\Users\xinzh\.codex\` is IDE cache, not runtime config
5. **A3-token-inject.sh had `/path/to/` placeholder bug** — Fixed in v2 (use `$HOME`)

## User Preferences (Permanent)

- Simplified Chinese
- Structured output (tables / lists)
- Direct judgment, no vague confirmation
- AI address: "哥"
- Execution: end-to-end ("全部执行/落地")

---

_Edit here, all agents that read MEMORY.md see the change automatically via junction._
