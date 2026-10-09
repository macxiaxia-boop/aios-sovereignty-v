# Partial B — Agent / Task / Memory / Config Source Audit (READ-ONLY)

> **Audit ID**: `B-AUDIT-2026-10-09`
> **Contract**: `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_PARTIAL_20261008\B_CONTRACT.md`
> **Mode**: READ-ONLY. No deletes, moves, history rewrites, service stops, or product/policy code changes.
> **Companion**: `B_AGENT_TASK_MEMORY.json` (machine-readable, same directory)

## 1. Loader Entry Points (Runtime Materialization)

### 1.1 AIOS Hub v2 — `D:\AIOS\_agent-hub\v2\`

| File | Line(s) | Function / Constant | What it materializes | Risk |
|---|---|---|---|---|
| `v2/src/paths.py` | 7 | `V2_ROOT = Path(r"D:\AIOS\_agent-hub\v2")` | Defines the only v2 root; SSOT path root | Low — fixed path |
| `v2/src/paths.py` | 10 | `AGENTS_JSON = V2_ROOT/"agents"/"agents.json"` | SSOT for cross-agent identity | Low — clean JSON |
| `v2/src/paths.py` | 11 | `PROTOCOL_V1 = V2_ROOT/"protocols"/"v1.md"` | Bidirectional protocol SSOT | Low — clean |
| `v2/src/paths.py` | 14-16 | `INBOX / OUTBOX / DEADLETTER` | Envelope bus roots | Low — inbox contains 2 self-referential retirement-audit tasks only |
| `v2/src/v2_consumer.py` | 772 | `_load_recipients()` | Reads `agents.json`; extracts `agent_id` list | Low — reads 5 clean agents |
| `v2/src/v2_consumer.py` | 686-687 | `tick()` → `_load_recipients()` | Per-tick recipient list | Low |
| `v2/src/v2_consumer.py` | 248 | `CAPABILITIES` (hardcoded routing) | recipient × message_type → adapter | Low — only `codex/claudecode/hermes/openclaw/workbuddy/broadcast` |
| `v2/src/v2_consumer.py` | 460-465 | goal_guard integration | Calls `goal_guard_hook.write_risk_envelope()` on risk | Low — goal guard active; 1 risk envelope in `risk/` |
| `v2/src/state_machine.py` | 56 | `submit_task()` | Writes `tasks/<task_id>.json`; logs NDJSON event | Low |
| `v2/src/state_machine.py` | 94 | `list_tasks()` | Globs `tasks/*.json` (excluding `.tmp`) | Low — 4 stale R320–R348 tasks only |
| `v2/src/state_machine.py` | 201 | `build_state_snapshot()` | Aggregates into `state/state.json` | Low |
| `v2/src/supervisor.py` | 15 | `tick()` | Calls `reap_expired` + `build_state_snapshot` + `save_state_snapshot` | Low |
| `v2/src/goal_guard_hook.py` | 15, 153 | `write_risk_envelope()` | Persists to `v2/messages/risk/<id>.json` | Low — 1 fatal catch in `risk/` |
| `v2/cli/aiosv2.py` | 60 | `cmd_status()` | Reads `agents.json` for `agents_in_registry` | Low |
| `v2/cli/aiosv2.py` | 239 | `cmd_submit_task()` | Calls `state_machine.submit_task()` | Low |
| `v2/src/validation.py` | 20 | `_load_schema()` | Lazy-loads `schemas/*.schema.json` | Low — schemas have no industry fields |
| `v2/schemas/envelope.schema.json` | v1.0 | fields: id, schema_version, message_type, sender, recipient, timestamp, idempotency_key, payload (+ optional correlation_id, artifact_refs[], text_chunks[], retry_count, ttl_ms, in_reply_to, trace) | None — no industry field | 0 |
| `v2/schemas/task.schema.json` | v1.0 | fields: task_id, title, state, assignee, owner, created_at, updated_at, lease_expires_at, heartbeat_at, input_payload, output_payload, error{code,message,details}, retry_count, max_retries, timeout_ms, correlation_envelope_id | None | 0 |
| `v2/schemas/state.schema.json` | v1.0 | fields: version, updated_at, tasks{task_id→task}, agents{agent_id→…}, counters | None | 0 |
| `v2/agents/agents.json` | 8-100 (5 agents) | registry: codex, claudecode, workbuddy, hermes, openclaw | None | 0 |

**Verdict (v2)**: zero industry/装修/教育/制造/服务/cross-industry/global_strategy/cloudtech references in any runtime loader, schema, or registry. Active tasks: 1 succeeded (R348), 2 queued (r286-lease*), 1 cancelled (test). No industry tasks.

### 1.2 aios_vnext Task Card System — `D:\AIOS\aios_tasks\`

| File | Lines | Function | Status |
|---|---|---|---|
| `aios_tasks/_aios_v13_protocol_audit.py` | full | schtasks monthly target (day 1, 09:00) — audits 6-AI protocol files | **ACTIVE** — single live cron |
| `aios_tasks/_aios_v13_cron_register.py` | 14-46 | `schtasks /create /tn AIOS_V13_Protocol_Audit /sc monthly /d 1 /st 09:00` | ACTIVE — registers cron |
| `aios_tasks/_aios_admin_runner.py` | full | UAC elevation via schtasks one-shot | ACTIVE |
| `aios_tasks/_aios_l1_exhaust_check.py` | 10, 26 | L1 automation checker | ACTIVE — references "工作量" generically (not industry vertical) |
| `aios_tasks/_r192_l5_execute_part2.py` | 7, 85, 88 | References `_archived-cloudtech/CloudTech-V2.0-2026-09-09` for deletion | ACTIVE — references cloudtech *only for archival* |
| `aios_tasks/_aios_admin_temp_9ee1a950.ps1` | 4, 5, 9, 31, 34, 43, 44, 56 | Stale temp PS1 — references `cloudtech-saas` service + `cloudtech.live_migration` module | STALE — temp file from prior cutover; not on any live cron path |
| `aios_tasks/aios_vnext/preflight_check.py` | 51 | Whitelist path `D:/AIOS/cloudtech-saas` | ACTIVE — whitelist entry (read-only check, not a loader) |
| `aios_tasks/aios_vnext/cards/D002_industry_scout.md` | full | `IndustryScout` module — generic signal-monitoring framework (RSS/API → 5 categories: product/competitor/regulatory/market/tech) | **ACTIVE** but neutral — no 装修/教育/制造/服务 verticals hardcoded |
| `aios_tasks/aios_vnext/handoff.md` | 0-§11 | CC start instructions + forbidden files checklist | ACTIVE — strict no-protocol-spam guard |
| `aios_tasks/aios_vnext/preflight_check.py` | full | CC self-check tool | ACTIVE |
| `aios_tasks/aios_vnext/_cc_workflow.md` | §11 | forbidden-files list | ACTIVE — protocol-spam guard |

**Verdict (aios_tasks)**: single live cron (`AIOS_V13_Protocol_Audit` monthly). Only generic "服务" in admin comments; no industry verticals. Cloudtech references are for archival only.

### 1.3 _relinked/openclaw — `D:\AIOS\_relinked\openclaw\`

| File | Lines | Function | Status |
|---|---|---|---|
| `openclaw/openclaw.json` | 81-90 | `agents.subagents.allowAgents` → `codex, geo-intent, geo-competitor, geo-strategy, geo-creator, geo-validator` | ACTIVE — runtime loader |
| `openclaw/openclaw.json` | 678-683 | `skills.load.extraDirs` → `D:\个人文件\AI\Operator\skills` + `D:\个人文件\AI\Operator\skills\skills` | ACTIVE — runtime |
| `openclaw/openclaw.json` | 685-1439 | `+skills.entries` ~200 skill names with enabled:true/false | ACTIVE — runtime |
| `openclaw/openclaw.json` | 1454+ | `plugins.entries` → memory-core, active-memory, ollama, openai, acpx, minimax, device-pair, anthropic, browser | ACTIVE — runtime |
| `openclaw/CLAUDE.md` | full | Delegates to central SSOT | ACTIVE — clean |
| `openclaw/MEMORY.md` | full | R402 entrypoint init | ACTIVE — clean |
| `openclaw/agents/{claude,codex,geo-*,main,isolated}/agent/workshop-skills/` | dirs | All empty (0 bytes) | ARCHIVE — no files |
| `openclaw/skills/` | 5 dirs | volcengine-cli/feedback/find-skills/knowledge-search/troubleshooting | ACTIVE — in extraDirs scan path; no industry references |
| `openclaw/plugin-skills/` | 1 dir | browser-automation@ | ACTIVE — no industry references |

**Verdict (openclaw)**: zero industry/装修/教育/制造/服务/cross-industry/global_strategy/cloudtech references in loader. Generic English "industry" only in volcengine-troubleshooting docs.

### 1.4 _relinked/hermes — `D:\AIOS\_relinked\hermes\`

| File | Lines | Function | Status |
|---|---|---|---|
| `hermes/config.yaml` | 1-275 | `mcp_servers` (40+), `v15_boundaries` (B1_allow/forbid, D3_prefix), `toolsets: hermes-cli`, `agent.reasoning_effort: medium` | ACTIVE — runtime loader; no industry refs |
| `hermes/AGENTS.md` | — | **MISSING** (no file at `_relinked/hermes/AGENTS.md`); Hermes uses SOUL.md as identity bootstrap | — |
| `hermes/SOUL.md` | full | Hermes identity bridge V1.0 — Chief Intelligence Officer role | ACTIVE — no industry keywords |
| `hermes/SOUL.md.bak-2026-09-13-pre-ssot-injection` | full | Pre-2026-09-13 backup | ARCHIVE — superseded |
| `hermes/SOUL.md.bak-pre-shared-ssot-20260930` | full | Pre-shared-ssot backup | ARCHIVE — superseded |
| `hermes/CLAUDE.md` | — | **MISSING** (no file at `_relinked/hermes/CLAUDE.md`) | — |
| `hermes/cron/jobs.json` | — | `aios-healthcheck` (*/5) + `aios-rag-watch` (daily 02:00) | ACTIVE — no industry refs |
| `hermes/hooks/` | dir | Empty (no files) | INERT |
| `hermes/hermes-agent/AGENTS.md` | full | NousResearch hermes-agent development guide | ACTIVE — bundled with hermes-agent source |
| `hermes/hermes-agent/skills/` | dirs | apple, autonomous-ai-agents, creative, data-science, devops, diagramming, domain, email, gaming, gifs, github, mcp, media, mlops, note-taking, productivity, red-teaming, research, smart-home, social-media, software-development, yuanbao | BUNDLED — default-disabled |
| `hermes/hermes-agent/optional-skills/` | dirs | finance (dcf-model, comps-analysis), mlops (instructor, inference/outlines), research (osint-investigation) | BUNDLED — disabled by default |
| `hermes/skills/` | 2 dirs + `.archive/` | yixiaoer + volcengine-* (ACTIVE); `.archive/` 30+ archived skills (ARCHIVE) | MIXED |
| `hermes/hermes-agent/.venv/Scripts/hermes.exe` | exe | v0.15.1 CLI | ACTIVE — binary |

**Verdict (hermes)**: zero industry/装修/教育/制造/服务/cross-industry/global_strategy/cloudtech in config/SOUL/cron. Generic "industry" appears only in optional-skills/finance DCF model docs.

### 1.5 User-Global Loaders — `C:\Users\xinzh\.workbuddy\` and `C:\Users\xinzh\.codex\`

| File | Lines | Function | Status |
|---|---|---|---|
| `~/.workbuddy/AGENTS.md` | full | Delegates to `D:\AIOS\_agent-hub\AGENTS.md` (SHA256 `6FD99AAAAADE4F5D5FAC97AF154AA84E77D3120C9BDB6CD438CD98648FF6CF14`) | ACTIVE — clean |
| `~/.workbuddy/CLAUDE.md` | full | Moon Capsule L0 kernel R401 seed | ACTIVE — clean |
| `~/.workbuddy/MEMORY.md` | full | R402 entrypoint init | ACTIVE — clean |
| `~/.workbuddy/memory/45e357fa-c2ec-4bd0-b734-9b016a2759d7_memory.md` | lines 6-9, 13-19 | **User Memory Profile v3** — embeds `memoryBlock` JSON with: "CloudTech 科技创始人…Phase 1 聚焦行业 SaaS（医美 + 装企）MVP…Phase 2 再升维至工具型平台" + "对标基准——灵策（15 agents / 46 real skills）、WorkBuddy（16+ MCP connectors…）" + "CloudTech 独有资产：1,989 篇竞品情报、2,421 篇 SaaS 语料、600+ 行业垂直文档（家居/医美）…" | **HIGH RISK — ACTIVE LOADER** — WorkBuddy reads this at session start |
| `~/.workbuddy/memory/MEMORY.md` | full | R402 entrypoint init | ACTIVE — clean |
| `~/.workbuddy/memory/workbuddy_seed.md` | full | WorkBuddy seed | ACTIVE — clean |
| `~/.workbuddy/memory/feedback-R403-workbuddy-archive-seed.md` | full | R403 archive seed | ARCHIVE — tombstoned |
| `~/.workbuddy/storage/user-45e357fa-c2ec-4bd0-b734-9b016a2759d7-personal/scoped/c7389fe09fa872c0/home-first-screen-cache.json` | line 6-34 + skills list (~150 entries) | **Home first screen cache** — contains the same CloudTech user profile block + skill marketplace data including: `装修工作台` (line 1188+), `儿童教育/K12教育` (lines 132, 224, 229, 3902, 3928), `制造企业` (line 10108-10112), `金融服务` (multiple lines), `装修云管家业务查询` | **HIGH RISK — LOADED ON FIRST LAUNCH** — WorkBuddy reads on session start |
| `~/.workbuddy/storage/.../scoped/.../skills-installed-store.json` | full | Skill registry cache with industry context (e.g., 装修云管家) | MEDIUM RISK — skill cache, loaded by skill manager |
| `~/.workbuddy/plugins/cache/workbuddy-builtin/welcomemode-work/{5.6.2,5.7.6}/prompt.tpl` | lines 19-24 | `industryModeSystemPromptAppend` variable (empty placeholder) | LOW RISK — template hook, currently empty |
| `~/.workbuddy/plugins/marketplaces/workbuddy-connector-plugins-official/connectors/zxygj-business-data/` | full | `plugin.json` + `SKILL.md` for 装修云管家 connector | MEDIUM RISK — installed connector |
| `~/.workbuddy/sessions/23852.json` | full | Active session (single file) | MEDIUM RISK — session resume could reload old context |
| `~/.codex/AGENTS.md` | full | Codex native bootstrap copy of central SSOT | ACTIVE — clean |
| `~/.codex/CLAUDE.md` | — | **MISSING** | — |
| `~/.codex/MEMORY.md` | — | **MISSING** | — |
| `~/.codex/memory/` | — | **MISSING** (directory does not exist) | — |
| `~/.codex/agents/architect.toml` | full | System architect role spec | ACTIVE — clean |
| `~/.codex/agents/developer.toml` | full | Executor developer role spec | ACTIVE — clean |
| `~/.codex/agents/reviewer.toml` | full | Reviewer role spec | ACTIVE — clean |
| `~/.codex/agents/security.toml` | full | Security auditor role spec | ACTIVE — clean |
| `~/.codex/agents/test-engineer.toml` | full | Test engineer role spec | ACTIVE — clean |
| `~/.codex/agents/*.bak-R129-pre-v5-20260921` | full | 4 backup files (architect/developer/reviewer/security/test-engineer) | ARCHIVE — explicitly marked `.bak-R129-pre-v5` |
| `~/.codex/config.toml` | line 36 | Project path `[projects.'d:\个人文件\ai\cloudtech\v2.0\lingce_scheduler_demo']` with `trust_level = "trusted"` | LOW RISK — only loaded when operating in that directory |
| `~/.codex/_scripts/_mk_link_script.py` | line 97 | PowerShell shortcut generator with `New-Link "[索引] 装修行业小红书对标账号"` | LOW RISK — static script, not loaded at runtime |
| `~/.codex/sessions/2026/{06,07,08,09,10}/` | 10 subdirs | Active session dirs | MEDIUM RISK — resume reloads context |
| `~/.codex/archived_sessions/` | 31 JSONL files | Historical sessions (2026-09-16 to 2026-09-30) | LOW RISK — append-only, never auto-loaded |
| `~/.codex/sessions/2026/06/02/` and similar | JSONL | Old session logs | ARCHIVE — temporal evidence |
| `~/.codex/plans/` | — | **MISSING** | — |

## 2. Active Tasks (state.json / inbox / outbox / deadletter)

### 2.1 `v2/state/state.json` (updated_at 2026-10-08T14:10:36Z)

| task_id | title | state | assignee |
|---|---|---|---|
| `35b6f323-0ff8-4163-93d6-1e27fa79759c` | R348 · aios_status stale defaults 根治 + 通道拓展 A/B/C/D 全部上线 | **succeeded** | claude_code |
| `782ff34b-f5d0-484e-bae5-d97cff2788ae` | r286-lease-debug | **queued** | r286-debug-agent |
| `832dccb4-3020-4771-ab54-ab17340a9c4e` | r286-lease | **queued** | r286-lease-agent |
| `901ad4b3-128f-4f26-8ab0-b15d4ef4eff3` | test | **cancelled** | codex |

No running tasks. No industry tasks present.

### 2.2 `v2/messages/inbox/` (39 envelopes, 2026-10-08 → 2026-10-09)

- 17 ack, 13 task, 7 result, 1 message, 1 error
- **2 self-referential retirement-audit envelopes** (NOT industry tasks — they audit the retirement itself):
  - `6ea4f46d-…task.claimed` (2026-10-08 23:47) — title `GLOBAL-STRATEGY-RETIREMENT-AUDIT-RETRY`, contract `D:\AIOS\_agent-hub\reports\GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008_CONTRACT.md`
  - `83e2d652-…task.claimed` (2026-10-08 23:41) — title `GLOBAL-STRATEGY-RETIREMENT-AUDIT`

### 2.3 `v2/messages/outbox/` (2 stranded acks from 2026-09-29)

- `2a16b62d-…__claudecode__codex__ack.json` + `19334d04-…__codex__claudecode__ack.json`
- Stale R320.6 artifacts; no active dispatcher.

### 2.4 `v2/messages/deadletter/` (6 files, 3 task.dead + 3 .reason.json pairs)

- `4c0597dc-…__codex__claudecode__task.dead` (2026-10-08 23:41) — read failure
- `5e15bccf-…__codex__claudecode__task.dead` (2026-10-08 22:35) — `result_enqueue_failed:TypeError` (P5 final adapter)
- `e82ad3a4-…__codex__hermes__task.dead` (2026-10-08 22:35) — `max_retries_exceeded:RuntimeError` (Hermes p8-t23-debug)

### 2.5 `v2/messages/risk/` (1 fatal-risk envelope)

- `e397a956-…goal_guard_risk.json` (2026-10-08 23:19) — `verdict: "fatal"`, `failed_checks: required_fields_missing (9), failure_modes_empty, permission_overrun`; goal guard correctly blocked dispatch.

### 2.6 `v2/tasks/` (4 task envelope state records, all stale 2026-09-30)

- R320.6 era; no live industry direction.

### 2.7 `v2/runs/` (13 task run state snapshots, stale 2026-09-30)

- R320–R348 era; no live industry direction.

### 2.8 `v2/logs/events.ndjson` (1.1 MB, 2026-09-29 → ongoing)

- Full operational history; 0 industry keyword matches.

## 3. Active vs Archive Classification

| Path | Classification | Criteria |
|---|---|---|
| `v2/src/*.py` | **ACTIVE** | imported at runtime via `python -m src.v2_consumer watch` or `aiosv2.py CLI` |
| `v2/agents/agents.json` | **ACTIVE** | loaded by `_load_recipients()` at `v2_consumer.py:772` |
| `v2/schemas/*.schema.json` | **ACTIVE** | lazy-loaded by `_load_schema()` at `validation.py:20` |
| `v2/state/state.json` | **ACTIVE** | rewritten by `supervisor.py:15 tick()` |
| `v2/messages/{inbox,outbox,deadletter,risk}/` | **ACTIVE** | written/read by `v2_consumer.py`, `envelope.py`, `goal_guard_hook.py` |
| `v2/governance/PROTOCOL_REGISTRY.json` | **ACTIVE** | read by external governance tools (not by runtime consumer) |
| `v2/agents/agents.json.bak-pre-R322` | **ARCHIVE** | pre-R322 backup; not loaded |
| `v2/governance/PROTOCOL_REGISTRY.json.bak*` (3 files) | **ARCHIVE** | pre-publish backups; not loaded |
| `v2/governance/PROTOCOL_REGISTRY.json.bak_R284_pre_publish_20260929T200600` | **ARCHIVE** | R284 pre-publish backup |
| `v2/governance/Housekeeper/cleanup/*` | **ARCHIVE** | housekeeper-managed cleanup candidates |
| `v2/reports/CLOUDTECH_REPAIR_PLAN.md` | **ARCHIVE** | historical execution report (WinSW service descriptor) |
| `v2/reports/CLOUDTECH_REPAIR_PLAN.md.pre_R284_20260929T200700.bak` | **ARCHIVE** | pre-R284 backup |
| `v2/reports/R283_CLOUDTECH_EXECUTION_REPORT.md` | **ARCHIVE** | historical execution report |
| `v2/reports/R284_CLOUDTECH_COMPLETION_REPORT.md` | **ARCHIVE** | historical completion report |
| `v2/reports/FILE_INVENTORY.csv` | **ARCHIVE** | V16 scan inventory (contains 装修 reference as historical path) |
| `v2/src/*.bak.20261008-*` (5 files: claude_adapter 2x, probes.py 3x, v2_consumer 3x) | **ARCHIVE** | pre-fix backups |
| `~/.workbuddy/memory/45e357fa-…_memory.md` | **ACTIVE** | read by WorkBuddy session-start loader |
| `~/.workbuddy/storage/.../home-first-screen-cache.json` | **ACTIVE** | loaded by WorkBuddy first-screen UI on launch |
| `~/.workbuddy/AGENTS.md`, `CLAUDE.md`, `MEMORY.md` | **ACTIVE** | session-start loaders |
| `~/.workbuddy/memory/feedback-R403-workbuddy-archive-seed.md` | **ARCHIVE** | tombstoned at R403 |
| `~/.workbuddy/plugins/cache/workbuddy-builtin/*` | **ARCHIVE-CACHE** | package-manager cache; regenerated; not editable for runtime reactivation |
| `~/.workbuddy/sessions/23852.json` | **ACTIVE** | live session |
| `~/.codex/AGENTS.md`, `agents/*.toml` (5 files) | **ACTIVE** | session-start loaders |
| `~/.codex/agents/*.bak-R129-pre-v5-20260921` (4 backups) | **ARCHIVE** | explicitly marked pre-v5 |
| `~/.codex/archived_sessions/` (31 JSONL files) | **ARCHIVE** | append-only history, never auto-loaded |
| `~/.codex/sessions/2026/{06,07,08}/` | **ARCHIVE** | old session dirs |
| `~/.codex/sessions/2026/{09,10}/` | **ACTIVE** | recent/current sessions |
| `~/.codex/_scripts/_mk_link_script.py` | **ARCHIVE-STATIC** | static Python script; not loaded at runtime |
| `~/.codex/config.toml` line 36 project entry | **CONDITIONAL** | only loaded when operating in that directory |
| `_relinked/openclaw/openclaw.json` | **ACTIVE** | session-start loader |
| `_relinked/openclaw/{CLAUDE.md,MEMORY.md}` | **ACTIVE** | session-start loaders |
| `_relinked/openclaw/agents/*/agent/workshop-skills/` | **ARCHIVE-EMPTY** | all empty dirs (0 bytes) |
| `_relinked/openclaw/skills/volcengine-*` (5 dirs) | **ACTIVE** | in `openclaw.json:678-683` extraDirs scan path |
| `_relinked/openclaw/plugin-skills/browser-automation@` | **ACTIVE** | plugin loader |
| `_relinked/hermes/config.yaml` | **ACTIVE** | session-start loader |
| `_relinked/hermes/SOUL.md` | **ACTIVE** | Hermes identity bootstrap |
| `_relinked/hermes/SOUL.md.bak-2026-09-13*` | **ARCHIVE** | pre-injection backup |
| `_relinked/hermes/SOUL.md.bak-pre-shared-ssot-20260930` | **ARCHIVE** | pre-ssot backup |
| `_relinked/hermes/cron/jobs.json` | **ACTIVE** | cron scheduler |
| `_relinked/hermes/skills/.archive/` (30+ dirs) | **ARCHIVE** | curator-managed, not loaded |
| `_relinked/hermes/hermes-agent/skills/` | **BUNDLED** | bundled with hermes-agent source; default-disabled |
| `_relinked/hermes/hermes-agent/optional-skills/` | **BUNDLED-DISABLED** | optional, default off |
| `aios_tasks/_aios_v13_protocol_audit.py` | **ACTIVE** | schtasks monthly target |
| `aios_tasks/_aios_v13_cron_register.py` | **ACTIVE** | schtasks register |
| `aios_tasks/_aios_admin_runner.py` | **ACTIVE** | UAC elevation |
| `aios_tasks/_aios_l1_exhaust_check.py` | **ACTIVE** | L1 checker |
| `aios_tasks/_r192_*.py` | **ARCHIVE** | R192-era one-shots |
| `aios_tasks/_r186_*` through `_r191_*` (15+ files) | **ARCHIVE** | R186-R191 era scripts |
| `aios_tasks/_aios_admin_temp_*.ps1` (12 files) | **ARCHIVE-TEMP** | ad-hoc temp PS1 files |
| `aios_tasks/aios_vnext/{INDEX.md, _cc_workflow.md, handoff.md, preflight_check.py}` | **ACTIVE** | session-start + preflight + workflow guard |
| `aios_tasks/aios_vnext/cards/*.md` (43 cards) | **ACTIVE** | task card system |
| `aios_tasks/aios_vnext/evidence/*.md` (90+ files) | **ARCHIVE-EVIDENCE** | execution evidence; history |

## 4. Reactivation Mechanisms (Confirmed)

### 4.1 HIGH-RISK reactivation paths

**Path 1 — WorkBuddy User Memory Profile rewrite**
- Target file: `C:\Users\xinzh\.workbuddy\memory\45e357fa-c2ec-4bd0-b734-9b016a2759d7_memory.md` (lines 6-9, 13-19)
- Loader: WorkBuddy session-start → reads `memory/45e357fa-…_memory.md` into prompt context
- Reactivation edit: replace `memoryBlock` JSON's "Phase 1 聚焦行业 SaaS（医美 + 装企）MVP…" + "CloudTech 独有资产…600+ 行业垂直文档（家居/医美）…" + "对标基准——灵策…WorkBuddy…"
- Outcome: re-injects CloudTech Phase 1 (医美+装企) vertical strategy into every WorkBuddy session

**Path 2 — WorkBuddy home-first-screen-cache.json rewrite**
- Target file: `C:\Users\xinzh\.workbuddy\storage\user-45e357fa-c2ec-4bd0-b734-9b016a2759d7-personal\scoped\c7389fe09fa872c0\home-first-screen-cache.json` (line 6-34 raw JSON + skills list)
- Loader: WorkBuddy first-screen UI loads on launch; skills list is consumed by skill marketplace
- Reactivation edit: restore industry-tagged skills (装修云管家, K12教育, 制造B2B SaaS, 金融服务) into the skills array
- Outcome: re-surfaces industry-tagged skills in WorkBuddy's home UI

**Path 3 — WorkBuddy skills-installed-store.json rewrite**
- Target file: `C:\Users\xinzh\.workbuddy\storage\user-45e357fa-…\scoped\c7389fe09fa872c0\skills-installed-store.json`
- Loader: WorkBuddy skill manager reads on skill activation
- Reactivation edit: restore 装修云管家 entry or other industry skill registrations
- Outcome: re-enables an installed industry skill

**Path 4 — WorkBuddy zxygj-business-data plugin reinstall**
- Target path: `C:\Users\xinzh\.workbuddy\plugins\marketplaces\workbuddy-connector-plugins-official\connectors\zxygj-business-data\`
- Loader: WorkBuddy plugin marketplace scan + connector activation
- Reactivation edit: re-add `plugin.json` + `SKILL.md` for 装修云管家 connector
- Outcome: re-enables the decoration-cloud-管家 connector for use

### 4.2 MEDIUM-RISK reactivation paths

**Path 5 — Codex session resume with old context**
- Target dirs: `C:\Users\xinzh\.codex\sessions\2026\09\` and `10\`
- Loader: Codex `claude -p --resume` or session reload
- Reactivation edit: resume a pre-retirement session containing old industry prompts
- Outcome: re-injects old context into a fresh Codex session

**Path 6 — WorkBuddy session resume**
- Target file: `C:\Users\xinzh\.workbuddy\sessions\23852.json`
- Loader: WorkBuddy session resume
- Reactivation edit: resume session 23852
- Outcome: re-injects WorkBuddy session context

### 4.3 LOW-RISK reactivation paths

**Path 7 — Codex `config.toml` project path activation**
- Target: `C:\Users\xinzh\.codex\config.toml` line 36 — `[projects.'d:\个人文件\ai\cloudtech\v2.0\lingce_scheduler_demo'] trust_level = "trusted"`
- Loader: Codex reads project entry only when operating inside that directory
- Reactivation edit: `cd d:\个人文件\ai\cloudtech\v2.0\lingce_scheduler_demo` then run codex
- Outcome: enables the cloudtech v2.0 demo project (already exists on disk; no code injection)

**Path 8 — Codex `_mk_link_script.py` execution**
- Target: `C:\Users\xinzh\.codex\_scripts\_mk_link_script.py` line 97
- Loader: only if explicitly executed (not auto-loaded)
- Reactivation edit: run `python _mk_link_script.py`
- Outcome: creates the "[索引] 装修行业小红书对标账号" PowerShell shortcut (file artifact only)

**Path 9 — aios_vnext D002 industry_scout runtime**
- Target: `D:\AIOS\aios_tasks\aios_vnext\cards\D002_industry_scout.md`
- Loader: only if the next VNext dispatch cycle activates D002
- Reactivation edit: edit the D002 card body to add 装修/教育/制造/服务 verticals
- Outcome: would reintroduce the old vertical direction into IndustryScout (currently neutral)

**Path 10 — aios_tasks/_aios_admin_temp_9ee1a950.ps1 execution**
- Target: `D:\AIOS\aios_tasks\_aios_admin_temp_9ee1a950.ps1` lines 4-56 (cloudtech-saas service control)
- Loader: only if explicitly executed; not on any live cron
- Reactivation edit: run the temp PS1
- Outcome: stops/starts the cloudtech-saas WinSW service (not an industry-agent loader)

**Path 11 — openclaw.json skills entries edit**
- Target: `D:\AIOS\_relinked\openclaw\openclaw.json` lines 678-1439 (skills.entries)
- Loader: openclaw.json session-start
- Reactivation edit: add a new skill entry with `enabled:true` pointing to an industry-skill directory
- Outcome: would re-enable any industry skill if it existed on disk under `extraDirs`

**Path 12 — hermes-agent optional-skills activation**
- Target: `D:\AIOS\_relinked\hermes\hermes-agent\optional-skills\` (finance/mlops/research)
- Loader: hermes-agent startup if optional-skills enabled flag is flipped
- Reactivation edit: flip the flag → skills become loadable
- Outcome: would activate finance DCF / comps-analysis / osint-investigation; none reference 装修/教育/制造/服务

### 4.4 INERT paths (no reactivation possible without external edit)

- `~/.codex/archived_sessions/*.jsonl` — append-only, never auto-loaded
- `~/.workbuddy/memory/feedback-R403-workbuddy-archive-seed.md` — tombstoned at R403
- `v2/src/*.bak.20261008-*` — pre-fix backups
- `_relinked/openclaw/agents/*/agent/workshop-skills/` — empty dirs
- `_relinked/hermes/skills/.archive/` — curator-managed archive
- `_relinked/hermes/SOUL.md.bak-*` — superseded backups

## 5. Summary

| Risk | Count | Loader paths | Mitigation required |
|---|---|---|---|
| **HIGH** | 4 paths | WorkBuddy session-start + first-screen UI + skill manager + plugin marketplace | User approval to scrub CloudTech Phase 1 strategy from `memory/45e357fa-…_memory.md` + `home-first-screen-cache.json` + `skills-installed-store.json` + `zxygj-business-data` plugin |
| **MEDIUM** | 2 paths | Codex/WorkBuddy session resume | Archive old sessions that contain pre-retirement context |
| **LOW** | 6 paths | Static scripts, config.toml project entries, optional skills, openclaw.json entries, aios_vnext D002 card | None unless user wants full purge |
| **INERT** | 6+ paths | — | None — already inert |

**Critical finding**: The HIGH-risk paths are all in WorkBuddy's persistent user profile (single file `45e357fa-…_memory.md` + UI cache `home-first-screen-cache.json`). WorkBuddy is **NOT** currently the active hub — Claude Code is (this session). Codex supervisor watches via inbox polling. Neither CC nor Codex loads from WorkBuddy's persistent storage at runtime. However, if WorkBuddy is ever reactivated, those 4 paths would re-inject the old industry direction.

**v2 + Codex active paths are clean.** No runtime loader in v2 or Codex reintroduces 装修/教育/制造/服务/cross-industry/global_strategy. PROTOCOL_REGISTRY's 29 current families reference industry only as historical governance metadata for the WinSW service descriptor (cloudtech-xml-winsw family, status=superseded → r284-fixed-cloudtech-xml status=current).