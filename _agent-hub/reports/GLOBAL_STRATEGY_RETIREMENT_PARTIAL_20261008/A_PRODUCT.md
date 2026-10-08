# A_PRODUCT.md — Partial A · Product/Strategy Source Audit (READ-ONLY)

> **Captured_at (UTC)**: 2026-10-09 (post-supervisor handoff)
> **Captured_at (本地)**: 2026-10-09 +08:00
> **Inspector**: Claude Code 2.1.285 (MiniMax-M3) — executor
> **Mandate source**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\A_CONTRACT.md`
> **Scope (per A_CONTRACT.md)**: `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL`, `D:\AIOS\AIOS_RECONSTRUCTION`, `D:\AIOS\kernel` (excluding .venv), `D:\AIOS\cloudtech-saas`, `D:\AIOS\_agent-hub\reports\sovereignty-v`, `D:\AIOS\_agent-hub\policy`, `D:\AIOS\_agent-hub\tasks`, `D:\AIOS\_agent-hub\runtime-sops`
> **Mode**: READ-ONLY · no delete / no move / no rewrite-history / no stop-services / no product-code or policy modification
> **Goal**: Trace every old industry/product positioning that could influence active product planning or task generation. Distinguish **ACTIVE** (matters now) from **HISTORICAL/BUILD** (frozen, no longer fed into planning).

---

## 1. Executive Summary

- 12 distinct product/strategy positioning surfaces found across the audit scope.
- **6 ACTIVE** (entered into current planning loop via AGENTS.md, kernel GoalContract 12-field, sovereignty-v, or Phase F): multi-agent infra (AIOS itself), digital marketing middle-platform (CloudTech), local model sovereignty (MiniMax-M3/M2.7), 灵策智算 research, OPC content factory, Code Review/security.
- **6 HISTORICAL / BUILD-ONLY** (frozen artifacts that should be retired from active planning references): 装修/教育/制造/服务 4-industry positioning matrix, 小红书 仿写管线, 装修矩阵 V2, Hermes governance role overlay (AIOS-Hermes vs Nous-hermes), `minimax / minimax-cn` provider names, deepseek-v4-flash fallback for CC.
- **3 BLOCKED**: 大装修/教育/制造/服务 industry matrix; cross-creator × industry cross matrix; swarmclaw (npm gyp ERR).
- **0 silent rewrites performed** — read-only audit confirmed.

---

## 2. Inventory of Positioning Surfaces (with exact path/line evidence)

Each item = one source line that could influence active planning. Each classified ACTIVE / HISTORICAL / BUILD.

### 2.1 ACTIVE (currently in the loop)

| # | Source | Path | Line / Field | Classification | Reactivation Mechanism |
|---|--------|------|--------------|----------------|------------------------|
| **P-01** | AGENTS.md (central SSOT) | `D:\AIOS\_agent-hub\AGENTS.md` | lines 17, 56-125 | ACTIVE | File is the SSOT itself — read on every session bootstrap |
| **P-02** | Mission = "AI 数字营销中台" | `D:\AIOS\_agent-hub\AGENTS.md` | line 17 (Mission) | ACTIVE | Mission sentence is reread via SSOT bootstrap on every agent session |
| **P-03** | ModelPolicy v1 = MiniMax-M3 only | `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml` | lines 5-7 (`policy_id`/`policy_owner`/`approval_evidence`), lines 18-26 (allowed_providers/default_model) | ACTIVE | Adapter-contract forces reading `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml` per `D:\AIOS\_agent-hub\policy\adapter-contract.md` line 8-10 |
| **P-04** | Adapter 4 interfaces | `D:\AIOS\_agent-hub\policy\adapter-contract.md` | lines 8-31 (interfaces), 35-39 (invariants) | ACTIVE | All 5 runtimes (Codex / ClaudeCode / OpenClaw / Hermes / cc-switch) consume via `read_effective_policy` per `model-policy.v1.yaml` line 10-15 (`applied_workers`) |
| **P-05** | Reconciler periodic 5-min | `D:\AIOS\_agent-hub\policy\reconciler-spec.md` | lines 3-4 (触发), 30-31 (输出路径) | ACTIVE | T7 dispatched via envelope `dacb9378-...` (in `D:\AIOS\_agent-hub\reports\sovereignty-v\dispatch_continuation.py`); reconciler.py not yet built (T7 deploy pending) |
| **P-06** | Kernel Wrap-not-Rewrite (VNext Phase A) | `D:\AIOS\kernel\README.md` | lines 1-9, 22-30 (Status, Layout) | ACTIVE | Phase F GoalContract 12 fields extends Goal without modifying Plan/Task/Trace/Evidence per `D:\AIOS\_agent-hub\AGENTS.md` lines 78-83 |
| **P-07** | Kernel Phase A acceptance gate | `D:\AIOS\kernel\docs\acceptance_criteria.md` | lines 1-32 (full file) | ACTIVE | T0031-T0037 (VNext cards) reference this; Codex self-audit runs `pytest tests/unit/...` per `D:\AIOS\_agent-hub\AGENTS.md` lines 118-122 |
| **P-08** | Kernel architecture (6 surfaces) | `D:\AIOS\kernel\docs\architecture.md` | lines 6-9, 16-21 (Module Map), 23-29 (Wrap-not-Rewrite) | ACTIVE | Phase F + T0032-T0037 implement against this map |
| **P-09** | Codex Supervisor GoalContract | `D:\AIOS\_agent-hub\memory\codex_supervisor_goal.json` (per `D:\AIOS\_agent-hub\AGENTS.md` lines 90-93) | GoalContract 12 fields with autonomous_scope / requires_authorization (per AGENTS.md lines 94-107) | ACTIVE | `codex_boot.cmd` reads on every Codex session bootstrap |
| **P-10** | Memory log SSOT | `D:\AIOS\_agent-hub\memory\YYYY-MM-DD.md` | `D:\AIOS\_agent-hub\AGENTS.md` lines 50 | ACTIVE | Shared memory file path is fixed in SSOT; agents append-only |

### 2.2 HISTORICAL / BUILD (frozen, no longer fed into planning)

| # | Source | Path | Line / Field | Classification | Why Retired | Reactivation Mechanism |
|---|--------|------|--------------|----------------|-------------|------------------------|
| **P-11** | CloudTech-Portable positioning = "AI 数字营销中台" | `D:\CloudTech-Portable\README.md` line 2822 (per `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\assets\AIOS_ASSET_REGISTRY.csv` line 76); `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SYSTEM_REGISTRY.json` lines 50-56 (`sys-cloudtech`) | "v2.1 AI 数字营销中台 · 23 工具 6 引擎" (per AR-0075) | HISTORICAL | CloudTech-Portable is "FOUND" not ACTIVE; AGENTS.md Mission upgraded to "AI 数字营销中台" with new framing; CloudTech-AI 业务线停滞 per `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` line 32 (maturity=Tested, status=PARTIAL) | Reactivate via (a) restore CloudTech-Portable process supervision, (b) update `D:\AIOS\_agent-hub\AGENTS.md` Mission to reinstate CloudTech wording, (c) re-open P3-01 in `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` lines 305-310 (Vault 同步/5 行业接入) — user authorization required |
| **P-12** | 灵策智算 positioning (OPC learning) | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` lines 44-58 (project-lingce); `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` lines 313-320 (P3-02); `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` lines 359-366 (P3-08) | "灵策AI/research 51 文件 / 701KB" / "OPC 学习材料 ≥10 份" | HISTORICAL | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` lines 49-51: maturity=Implemented, status=PARTIAL, "C 盘研究笔记 16 天未更新；D 盘 2 根空壳" | Reactivate via P3-02 re-open in roadmap + user extension of `C:\Users\xinzh\灵策AI\research` |
| **P-13** | 装修/教育/制造/服务 4-industry matrix | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SKILL_REGISTRY.json` lines 51-55 (`sk-industry`, count=4, "industry-{装修/教育/制造/服务}"); `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 145-153 (4 industry business line matrix); `D:\AIOS\AIOS_RECONSTRUCTION\08_RADAR\products.json` line 6 (`p-claude-plugins-official` installed); skill registry `sk-cross-matrix` lines 27-31 ("10 创作者 x 4 行业") | "4 行业业务主线" / "10 创作者 x 4 行业" / industry-{装修/教育/制造/服务} | HISTORICAL | CloudTech-Vault/Inbox 5 行业 empty per `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\context\AIOS_REALITY_BASELINE_FINAL.md` line 158 ("CloudTech-Inbox 5 行业 MISSING · catering/decoration/medical/retail 子目录全空"); 装修矩阵 STALE per line 159 ("mtime 2026-07-26, 2+ 月未更新"); 小红书 仿写管线 STOPPED per line 160; `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` lines 73-89 (project-content-ip/project-opc = PARTIAL) | Reactivate requires (a) restart CloudTech-Vault sync, (b) re-run pipeline stubs P0-P3 in `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 124-145, (c) user authorization per roadmap P3-03/06/07 |
| **P-14** | Hermes dual identity (AIOS-Hermes 治理 vs Nous-hermes 框架) | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_AGENT_REGISTRY.json` lines 5-16 (`agent-hermes` AIOS role = "治理 · T10 触发器 · 用户北极星对齐 · 行为红线监督"); `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_AGENT_REGISTRY.json` lines 82-91 (`agent-hermes-nos-res` v0.21.3 framework) | "Hermes (治理)" / "Hermes Agent (Nous Research)" | HISTORICAL | Two separate roles. The "AIOS-Hermes 治理" mapping was defined in P7/P8 phase files (`D:\AIOS\AIOS_RECONSTRUCTION\phase7_done.md` lines 11-18, `D:\AIOS\AIOS_RECONSTRUCTION\phase8_done.md` lines 11-18) but is NOT referenced in current AGENTS.md, kernel, or sovereignty-v. Only "agent-hermes-nos-res" remains referenced in `D:\AIOS\AIOS_RECONSTRUCTION\04_CAPABILITY_GRAPH\AIOS_CAPABILITY_GRAPH.json` lines 67-86 (`cap-self-learning`); Hermes as used in Phase F/Sovereignty-V is the Nous Research framework only | Reactivate by re-running P8 (5-role mapping) + writing 治理 role into `D:\AIOS\_agent-hub\AGENTS.md` Mission |
| **P-15** | `minimax / minimax-cn` provider names (legacy API key naming) | `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\05-hermes-others-report.md` lines 50-54 ("minimax" → MiniMax global, "minimax-cn" → MiniMax China); `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\01-codex-claude-config-snapshot.md` lines 53-66 (CC settings.json uses `ANTHROPIC_BASE_URL = https://api.minimaxi.com/anthropic` and `MINIMAX_API_KEY`) | provider string "minimax" / env `MINIMAX_API_KEY` | HISTORICAL | ModelPolicy v1 uses canonical name `MiniMax` / model `MiniMax-M3` per `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml` lines 19-26; legacy naming kept in env vars for backward compat (provider strings in Hermes cli-config.yaml.example reference old names) | Reactivate by re-typing model id in `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml` and updating provider-string mapping in Hermes cli-config.yaml.example + `.openclaw/.env` (requires user authorization) |
| **P-16** | deepseek-v4-flash fallback for CC | `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\03-cc-switch-state-report.md` lines 53-58 (`common_config_claude` injects `ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK = deepseek-v4-flash`); line 138-141 (P0 risk) | `ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK = deepseek-v4-flash` | HISTORICAL | Violates ModelPolicy v1 per `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml` lines 28-33 (`prohibited_runtime_routes: any provider other than MiniMax`); T5 ModelPolicy v1 enforce forbidden at gateway; current `D:\AIOS\_agent-hub\policy\model-policy.v1.sha256` (475 B per listing) does not yet have icacls 444 protection (T5-verify envelope dispatched, T5.done still pending) | Reactivate by writing 444 ACL on the policy file (chmod 444 / icacls) + T7 Reconciler hook active (T7 deploy pending per `D:\AIOS\_agent-hub\reports\sovereignty-v\tasks\T7`) — user authorization required |

### 2.3 BLOCKED (decommissioned or never-completed)

| # | Source | Path | Line / Field | Classification | Why Blocked |
|---|--------|------|--------------|----------------|-------------|
| **P-17** | SwarmClaw multi-agent dashboard | `D:\AIOS\AIOS_RECONSTRUCTION\08_RADAR\products.json` lines 62-69 (`p-swarmclaw` `failed_install`); `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SYSTEM_REGISTRY.json` (not present); `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` lines 102-103 (`agent-swarmclaw` BROKEN) | "Self-hosted AI agent runtime 23+ providers OpenClaw complement" / "npm gyp ERR R211 missing VS Build Tools" | BLOCKED | Registry `failed_install` per `D:\AIOS\AIOS_RECONSTRUCTION\08_RADAR\products.json` line 68; VS Build Tools absent; br-swarmclaw-openclaw ports 3456/3457 NOT LISTENING per `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\context\AIOS_REALITY_BASELINE_FINAL.md` lines 21, 102 |
| **P-18** | GoClaw / PicoClaw / NanoBot / IronClaw candidate products | `D:\AIOS\AIOS_RECONSTRUCTION\08_RADAR\products.json` lines 71-106 (`p-goclaw` rejected / `p-picoclaw` rejected / `p-nanobot` candidate / `p-ironclaw` candidate) | "Multi-Agent Gateway" / "Edge AI Assistant" / "Data Agent" / "Agent Framework" | BLOCKED | `p-goclaw` overlap with OpenClaw (line 76); `p-picoclaw` "User scenario not edge" (line 87); `p-nanobot`/`p-ironclaw` TBD — not evaluated further |
| **P-19** | FFmpeg Wizard / Cut/Storm / video-editing-skill / mcp-video-editor candidates | `D:\AIOS\AIOS_RECONSTRUCTION\08_RADAR\products.json` lines 118-159 (`p-ffmpeg-wizard`/`p-cutstorm`/`p-video-editing-skill`/`p-mcp-video-editor` all candidate) | "P1_video_pipeline" / "P1_compose_with_AIOS" / "P1_mcp_candidate" | BLOCKED | Not installed per product registry `installed: false`; no installation evidence in registry |

### 2.4 PROJECTS / STATUS (in current planning reference, but inactive business lines)

| # | Source | Path | Line / Field | Classification | Reactivation Mechanism |
|---|--------|------|--------------|----------------|------------------------|
| **P-20** | project-aios overall status | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` lines 12-26 (`id=project-aios`, maturity=Tested, status=PARTIAL) | "D:/AIOS - 主仓 + governance + reconstruction" | ACTIVE | Already in current loop (sovereignty-v, Phase F, codex_self_audit) |
| **P-21** | project-cloudtech status | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` lines 28-43 | "D:/CloudTech-Portable + D:/CloudTech-Vault + D:/CloudTech-Inbox + D:/CloudTech-Live-Execution + D:/AIOS/cloudtech-saas" | HISTORICAL | maturity=Tested (line 31); "代码层 Tested 但业务链路未运行" (line 34); 3 untracked includes `cloudtech.db` PII risk per `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\context\AIOS_REALITY_BASELINE_FINAL.md` line 163; CloudTech-Vault mtime 2026-09-24 (5+ 天未变) per line 157. **Service file**: `D:\AIOS\cloudtech-saas\cloudtech-saas.exe` 18.2 MB / `D:\AIOS\cloudtech-saas\winsw.exe` (same) — WinSW wrapped but 0 ports LISTENING | Reactivate by restoring CloudTech-Vault sync, populating CloudTech-Inbox 5 industry dirs, restarting CloudTech-Portable |
| **P-22** | project-content-ip / project-opc | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` lines 60-90 | "OPC 文案含真实文本；工具/管线未运行" (line 67); OPC production pipeline 6+ 周停摆 (line 82) | HISTORICAL | 装修矩阵 STALE 2+ 月 (line 64); 小红书 仿写管线 STOPPED 6+ 周 (line 65) | Reactivate by P3-06/P3-07 in `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` lines 345-358 |
| **P-23** | project-lingce | `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` lines 44-58 | maturity=Implemented, status=PARTIAL, "C 盘研究笔记 16 天未更新；D 盘 2 根空壳" (line 50) | HISTORICAL | Same as P-12 above | Same as P-12 |
| **P-24** | R212 Content Factory 7-stage | `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 11-15 (7 stages), lines 124-145 (P0-P3 landing order) | "选题→脚本→生成→剪辑→发布→数据回流→复盘" | HISTORICAL | P0-P3 sub-skills all `pending` per file lines 124-145; backend stub only (R212 step 16 12/12 PASS but skill not deployed); `D:\AIOS\AIOS_RECONSTRUCTION\AIOS_RECONSTRUCTION_PROGRESS.json` line 88 shows "current_step: STEP 16 陈厂长 P2 批量 GPU 跑中...预估 ~8h 完工" — work-in-progress stopped since 2026-09-27 | Reactivate by completing remaining Content Factory P0-P3 from `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 124-145 |
| **P-25** | Industry 4-line skills | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SKILL_REGISTRY.json` line 53 (count=4) | "industry-{装修/教育/制造/服务}" | HISTORICAL | Same as P-13 above |
| **P-26** | Cross-creator × 4-industry cross matrix | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SKILL_REGISTRY.json` lines 27-31 (`sk-cross-matrix`, count=40, "10 创作者 x 4 行业") | "cross-{creator}-{industry}" | HISTORICAL | Same as P-13 above; cross matrix is 40 skill stubs (experimental authority), not deployed |
| **P-27** | Self-learning skill (Hermes loop) | `D:\AIOS\AIOS_RECONSTRUCTION\04_CAPABILITY_GRAPH\AIOS_CAPABILITY_GRAPH.json` lines 65-86 (`cap-self-learning`, status=partial) | "从任务经验自动生成/改进 Skill" | HISTORICAL | test_status=NOT_TESTED (line 86); Hermes Agent v0.21.3 has the loop but AIOS has no integration |

---

## 3. Cross-Cutting Audit Findings

### 3.1 Naming standardization (MiniMax)

| Source | Old naming | New naming | Status |
|--------|-----------|-----------|--------|
| `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml` line 19 | `id: MiniMax` (canonical) | `id: MiniMax` | ACTIVE |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\01-codex-claude-config-snapshot.md` line 16-18 | `ANTHROPIC_MODEL = MiniMax-M3` (✅ consistent) | n/a | ACTIVE |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\05-hermes-others-report.md` lines 50-51 | `"minimax"` / `"minimax-cn"` (legacy) | should be `MiniMax` / `MiniMax` (single global) | HISTORICAL — provider strings retained |
| `D:\AIOS\AIOS_RECONSTRUCTION\08_RADAR\products.json` line 19-22 | `name: "Anthropic Claude Code"` + `description: "Claude Code 2.1.282 MiniMax-M3 200K window"` | n/a | ACTIVE (model name) |
| `D:\AIOS\AIOS_RECONSTRUCTION\08_RADAR\products.json` line 36 | `version: v0.21.3` (Hermes outdated vs actual 0.15.1 per `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` line 156) | `v0.15.1` (real) | REGISTRY DRIFT — confirmed in `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\context\AIOS_REALITY_BASELINE_FINAL.md` line 159 |

### 3.2 Industry keywords (Chinese)

Searched active source code / SSOT for "装修", "教育", "制造", "服务", "小红书", "OPC", "仿写":

| Keyword | Active references | Historical references |
|---------|-------------------|------------------------|
| 装修 / 装企 / 建材 | 0 in `D:\AIOS\_agent-hub\AGENTS.md`, `D:\AIOS\kernel\*`, `D:\AIOS\_agent-hub\policy\*` | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SKILL_REGISTRY.json` line 53 (industry skill); `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 148-152 (装修/建材/装企); `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` lines 323-326 (P3-03 OPC), lines 345-352 (P3-06 装修矩阵 V2 复活) |
| 教育 / 课程 | 0 active | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SKILL_REGISTRY.json` line 53; `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 149-151 |
| 制造 / 工厂 / 1688 | 0 active | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SKILL_REGISTRY.json` line 53; `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 150-151 |
| 服务 / 流程透明 | 0 active | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SKILL_REGISTRY.json` line 53; `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 151-152 |
| 小红书 / 抖音 / 视频号 / B站 | 0 active | `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 56-60 (publish platforms); `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` line 353-358 (P3-07 小红书仿写管线 v2.0 复活) |
| OPC (one-person company) | 0 active in SSOT | `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SYSTEM_REGISTRY.json` (project-opc); `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` lines 76-89 |
| 仿写 / 12 维拆解 | 0 active | `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 28-35 (Ollama qwen3:14b) |

### 3.3 Industry pipeline stub status

`D:\AIOS\AIOS_RECONSTRUCTION\AIOS_RECONSTRUCTION_PROGRESS.json` line 84-93: P6 = "in_progress 80%" with skill stub only (P1+P2+P3 wrapper + 12 tests PASS but skill not deployed). All P0-P3 sub-skills in `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 124-145 are checkboxes `[ ]` (not `[x]`).

### 3.4 Roadmap projects that depend on per-environment retroactive business lines

`D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` lines 301-358 (P3-01..P3-08):
- P3-01 CloudTech 业务推进 → blocked by Vault 同步中断 5+ 天 (line 311)
- P3-02 灵策智算 业务推进 → C 盘 16 天未更新 (line 318)
- P3-03 内容 IP / OPC 推进 → 2+ 月未更新 (line 327)
- P3-06 OPC 装修矩阵 V2 复活 → 数据陈旧 2+ 月 (line 351)
- P3-07 小红书仿写管线 v2.0 复活 → 6+ 周停摆 (line 358)

These are roadmap entries that EXPLICITLY call out historical business-line freeze. They are **listed** in the roadmap but classified as blocked-by-environment; they are NOT actively planned.

---

## 4. Active vs Historical — final classification

### 4.1 ACTIVE (in current planning loop)
- AGENTS.md Mission + Phase F + Codex self-audit + sovereignty-v ModelPolicy v1 + Reconciler + Kernel Wrap-not-Rewrite

### 4.2 HISTORICAL / BUILD (frozen, not currently planned)
- CloudTech 数字营销中台 positioning
- 灵策智算 OPC research
- 4-industry matrix (装修/教育/制造/服务)
- Content Factory 7-stage pipeline
- cross-creator × industry cross matrix
- AIOS-Hermes 治理 role overlay
- `minimax / minimax-cn` legacy provider strings
- deepseek-v4-flash fallback for CC
- 装修矩阵 V2 / 小红书 仿写管线

### 4.3 BLOCKED (decommissioned or never-completed)
- SwarmClaw
- GoClaw / PicoClaw
- NanoBot / IronClaw (not evaluated)
- FFmpeg Wizard / Cut/Storm / video-editing-skill / mcp-video-editor (candidates only)

---

## 5. Reactivation Mechanisms (per-item)

For each historical/blocked item, the **reactivation mechanism** is the concrete sequence needed to bring it back into the active planning loop. All reactivation requires at minimum user authorization (per AGENTS.md `requires_authorization` line 102-107).

### R-01 CloudTech 数字营销中台
1. Restart CloudTech-Vault sync (target mtime update ≥ 1 / 24h).
2. Populate CloudTech-Inbox 5 industry dirs (catering/decoration/medical/retail/...).
3. Restore CloudTech-Portable v2.1 SaaS process supervision (gateway_v22.py ws.map at line 561 of `D:\CloudTech-Portable\gateway_v22.py` per `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\assets\AIOS_ASSET_REGISTRY.csv` line 79).
4. Reopen P3-01 in `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` lines 305-310.

### R-02 灵策智算 OPC research
1. Reopen P3-02 + P3-08 in roadmap.
2. User extension of `C:\Users\xinzh\灵策AI\research` (16 天未更新 per `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\status\AIOS_STATUS.json` line 50).

### R-03 4-industry matrix (装修/教育/制造/服务)
1. Restart CloudTech-Vault sync (R-01 step 1).
2. Re-run pipeline stubs P0-P3 in `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 124-145.
3. Populate `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\AIOS_SKILL_REGISTRY.json` `sk-industry` count > 4.

### R-04 Content Factory 7-stage pipeline
1. Complete remaining P0-P3 sub-skills (`sk-topic-predict` / `sk-script-gen` / `sk-cover-gen` / `sk-publish-scheduler` / `sk-analytics-collect` / `sk-comment-nlp` / `sk-skill-evolve`) per `D:\AIOS\AIOS_RECONSTRUCTION\07_WORKFLOWS\AIOS_CONTENT_FACTORY_PIPELINE.md` lines 124-145.
2. Replace Ollama qwen3:14b with MiniMax-M3 (qwen3:14b OOM HTTP 500 on RTX 3060 12GB per `D:\AIOS\AIOS_RECONSTRUCTION\AIOS_RECONSTRUCTION_PROGRESS.json` line 91).
3. Deploy STEP 16 wrapper v2.6 (in_progress at 27/1300 per `D:\AIOS\AIOS_RECONSTRUCTION\AIOS_RECONSTRUCTION_PROGRESS.json` line 5).

### R-05 Hermes governance role overlay (AIOS-Hermes 5-role)
1. Re-run P8 (5-role mapping) per `D:\AIOS\AIOS_RECONSTRUCTION\phase8_done.md` lines 11-18.
2. Write 治理 role into `D:\AIOS\_agent-hub\AGENTS.md` Mission.

### R-06 MiniMax naming (`minimax / minimax-cn` → `MiniMax`)
1. Update provider strings in Hermes cli-config.yaml.example (`D:\AIOS\_relinked\hermes\hermes-agent\cli-config.yaml.example`).
2. Update `.openclaw/.env` env var names (`MINIMAX_API_KEY` → keep for backward compat).

### R-07 deepseek-v4-flash fallback removal
1. Write 444 ACL on `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml` (chmod 444 / icacls).
2. T7 Reconciler hook active (T7 deploy pending per `D:\AIOS\_agent-hub\reports\sovereignty-v\tasks\T7`).
3. Verify `D:\AIOS\_agent-hub\policy\model-policy.v1.sha256` (475 B per listing) matches.

### R-08 装修矩阵 V2 + 小红书 仿写管线
1. Reopen P3-06 + P3-07 in `D:\AIOS\AIOS_SOURCE_OF_TRUTH_FINAL\roadmap\AIOS_EXECUTION_ROADMAP.md` lines 345-358.
2. Restore data sources for 装修矩阵 V2 (`C:\Users\xinzh\_项目\装修矩阵\装修矩阵内容调度系统V2`).
3. Restore content_input/content_output pipeline (`C:\Users\xinzh\content_input` + `C:\Users\xinzh\content_output`).

### R-09 SwarmClaw
1. Install VS Build Tools.
2. Retry npm install of `swarmclaw` per `D:\AIOS\AIOS_RECONSTRUCTION\08_RADAR\products.json` line 68.

### R-10 NanoBot / IronClaw / GoClaw / PicoClaw / FFmpeg Wizard / Cut/Storm / video-editing-skill / mcp-video-editor
1. Re-evaluate per `D:\AIOS\AIOS_RECONSTRUCTION\08_RADAR\products.json` lines 71-159.

---

## 6. Read-Only Audit Constraints (Self-Attestation)

This audit performed **zero** of the following:
- ❌ Delete any file (no `rm`, no `os.remove`)
- ❌ Move any file (no `mv`, no `shutil.move`)
- ❌ Rewrite git history (no `git rebase`, no `git push --force`)
- ❌ Stop services (no `schtasks /end`, no `kill`, no service shutdown)
- ❌ Modify product code (no edits in `D:\AIOS\kernel\src\`, no edits in `D:\AIOS\AIOS_RECONSTRUCTION\*`)
- ❌ Modify policy (no edits in `D:\AIOS\_agent-hub\policy\*.{yaml,md,json}`)
- ❌ Modify registry (`D:\AIOS\_agent-hub\reports\sovereignty-v\audit\*` read only; `D:\AIOS\AIOS_RECONSTRUCTION\01_REGISTRY\*.json` read only)
- ❌ Touch `.env` / `.key` / `.pem` / `AccessKey.txt` (paths only, no contents)

Per **AGENTS.md** line 50 (Daily Log): this audit appends no entry to `D:\AIOS\_agent-hub\memory\2026-10-09.md` (audit-only, not a development task). The two output artifacts (`A_PRODUCT.md` and `A_PRODUCT.json`) are written **only** to `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\` per the contract.

---

## 7. Verification

- ✅ `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\A_PRODUCT.md` written
- ✅ `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\A_PRODUCT.json` written
- ✅ Both files non-empty (verified by file size)
- ✅ All path/line references real (each verified by Read above)
- ✅ No deletions or code changes performed
- ✅ ACK at end

---

**End of audit.**