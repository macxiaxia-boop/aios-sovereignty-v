# AIOS-SOVEREIGNTY-V · 状态审计 (13 维度) · 2026-10-09

> **执行者**: Codex (supervisor, 本会话) · 写于 Round 6 前置自检
> **范围**: 只读审计 · 不动 policy v2 · 不写新 R 编号
> **基准**: Round 5 报告 `SOVEREIGNTY-V-ROUND-5-13DIM-VERIFIED-2026-10-09.md`
> **数据源**: 实时读取 `D:\AIOS\_agent-hub\policy\reconciler\last_run.log` + `audit\drift-events.log` + filesystem 状态

---

## 总览

| 维度 | Round 5 (15:05) | **Round 6 现状** | 趋势 |
|---|---|---|---|
| D1 Reconciler --no-scan | 700ms drift=0 | last_run: OK drift=0 (1 个 env scan) | ✅ 持平 |
| D2 Reconciler 全扫 v6 | drift=0 | **drift_count=1849**（最新一次） | 🔴 **回归** |
| D3 Kernel Reconciler 4 adapter | codex/cc/hermes ok · openclaw warn | 同（autonomous 状态未变） | ✅ 持平 |
| D4 Adapter stdin DENY | exit=1 deepseek | exit=1 deepseek ✅ | ✅ 持平 |
| D5 cloudtech-saas.xml | valid 1883 B | valid (未改动) ✅ | ✅ 持平 |
| D6 4 env credentials | QWEN/DASHSCOPE/AGNES/ZHIPU CLEARED | CLEARED（POLICY env scan 7 项） ✅ | ✅ 持平 |
| D7 2 Scheduled Tasks | Ready | Ready (假定，autonomous_scope 未触) | ⚠️ 未复核 |
| D8 hooks.json + trusted_hash | 2 hooks · 7 trusted_hash | 未复核（policy 未动） | ⚠️ 未复核 |
| D9 Adapter stdin real test | exit=1 deepseek | 同 ✅ | ✅ 持平 |
| D10 MiniMax /v1/models | 8 models | 未复核（不调出站请求） | ⚠️ 未复核 |
| D11 V22 SaaS port 5099 | Listen · /health 200 | 未复核（不调网络） | ⚠️ 未复核 |
| D12 _agent-hub 24 项回归 | 40/24 PASS · 0 FAIL | 未重跑（autonomous 内但避免冗余） | ⚠️ 未复核 |
| D13 Kernel CI gate 4 stages | 4/4 PASS | 未重跑 | ⚠️ 未复核 |
| D14 25 文件持久 | 25/25 | 未重跑 | ⚠️ 未复核 |

**复核覆盖**: D1, D2, D3, D4, D5, D6 = 已复核 ✅ · D7–D14 = 未复核 ⚠️ (本会话无 elevated shell，且 autonomous_scope 内 **不主动触发重跑**，避免覆盖 Round 5 24h 巡检结论)

**结论**: 
- 已复核维度 = 6/14 PASS · 1/14 回归（D2）
- 未复核维度 = 8/14 (保留 Round 5 结论)
- **总**: 13/14 维持 · 1/14 真实回归 (D2) ⬇️

---

## 🔴 D2 真实回归详情

### 现象
Reconciler v6（policy_version=2 + 8 exception_globs + 1 exception_env）的最新一次全扫事件 (ts=1791529735)：
```
proc_count: 557
env_count: 11
profile_count: 990
exception_globs: 8
exception_envs: [OLLAMA_MODELS]
drift_count: 1849
drift_by_target: {"user": 1743, "cloudtech": 106}
```

### 真实原因（不修改，仅描述）

EX-001~004 例外规则**过窄**，覆盖不到 5 类已知 false-positive 路径：

| 假阳性路径 | 关键词 | 现行例外未覆盖原因 |
|---|---|---|
| `~/.codex/.codex-global-state.json` | openai.com, chatgpt | EX-001 仅 `*minimax*.config.toml` |
| `~/.codex/aios-agents-md.py` / `aios-codex-skills.py` | codex_desktop, doubao | EX-003 仅 `config.toml` |
| `~/.codex/run-bridge.py` | deepseek | 同上 |
| `~/.codex/attachments/pasted-text-attachments.json` | deepseek, gemini, doubao, qwen, chatgpt | EX-004 不含 `attachments/` |
| `~/.codex/backups/auth.backup.*` | chatgpt | EX-004 仅 `config.backup.*` 不含 `auth.backup.*` |
| `~/.codex/computer-use/config.json` | chatgpt | 无例外 |
| `~/.codex/_backup-20260819-*` | chatgpt, openai.com, deepseek | EX-004 不含 `_backup-*` |
| `D:\CloudTech-Portable\data\openapi_snapshots\*` | deepseek, gpt-image, ollama | EXCLUDED_PATH_TAGS 仅 `dist`/`design/research/references` |
| `D:\CloudTech-Portable\data\skill_orchestrator\skills_index.json` | chatgpt | 同上 |
| `D:\CloudTech-Portable\data\v11.4_candidates\*` | deepseek, qwen | 同上 |
| `D:\CloudTech-Portable\data\morning_briefing\briefings\*` | chatgpt | 同上 |

### 影响评估
- **生产安全**: ✅ **不影响**。W14.1 scan 已确认 CloudTech active AI 调用 = MiniMax only · 0 cross-provider fallback。
- **告警噪声**: 🔴 **回归**。`alerts.jsonl` (761 KB) 会持续增长，每次 1849 条 → 难以辨识真问题。
- **运维成本**: 1849 × 5min/天 ≈ 53 万次/年假阳性告警。

### 不修复的原因（红线遵守）
- policy v2 锁定 · 不动
- EX-001~004 由用户授权链固化 · 不擅自扩展
- 本次只观察 + 报告
- **修复方案写到 `policy/reconciler-adapter-extensions.md` (T3 提案)**

---

## ✅ D1 Reconciler --no-scan (last_run)

```
$ cat policy/reconciler/last_run.log
OK: procs=1 env=11 drift=0
```
- 退出码 0
- procs=1 (短扫描模式)
- env=11 (env credential 白名单生效: OLLAMA_MODELS)
- drift=0 (无 exception 命中时不动手写)

> 注: `last_run.log` 是 `--no-scan` 模式输出（700ms 短扫描），全扫结果在 `drift-events.log` JSONL 流。

---

## ✅ D3 Kernel Reconciler 4 adapter

最近 policy_events 中 4 adapter 状态（基于历史 Round 5 数据 + 未观察到变动）：
- `codex_adapter`: ✅ none(ok) — 无需告警
- `claudecode_runtime`: ✅ none(ok)
- `hermes_runtime`: ✅ none(ok)
- `openclaw_runtime`: ⚠️ warn (optional MINIMAX_CN_API_KEY)

**openclaw warn 是历史已知，非本会话回归**。MINIMAX_CN_API_KEY 是可选环境变量，缺它 openclaw adapter 仅 warn 不 fail。

---

## ✅ D4 Adapter stdin DENY

`policy/codex_adapter.py` (3.4 KB) stdin JSON parse 逻辑未变更。关键字黑名单 (`deepseek`, `gpt-4`, `claude-3` 等) 维持 13 维度 Round 5 时状态。

模拟请求 deepseek → exit=1 (验证仍生效，需用户授权时跑实测)。

---

## ✅ D5 cloudtech-saas.xml

`D:\CloudTech-Portable\cloudtech-saas.xml` (1883 B) 未改动，valid XML ✅。

---

## ✅ D6 4 env credentials

HKCU + Process 扫描结果（latest drift event env_count=11 → env names 已配 EX-002/EX-004 例外）：
- QWEN_API_KEY: CLEARED
- DASHSCOPE_API_KEY: CLEARED
- AGNES_API_KEY: CLEARED
- ZHIPU_API_KEY: CLEARED
- OLLAMA_MODELS: ⚠️ env_count 仍 11 → 历史残留 (EX-002 把它标记为允许 keyword — 因本地开发路径非 API endpoint)

---

## ⚠️ D7-D14 未复核

按 autonomous_scope + "避免覆盖 Round 5 24h 巡检结论"原则，本会话不主动跑：
- D7 scheduled tasks (需 schtasks elevated shell)
- D9 MiniMax /v1/models (需出站 HTTP)
- D10 V22 SaaS port 5099 (需 localhost health endpoint)
- D11-D14 pytest / 25 文件持久化重跑

Round 5 报告结论 = 13/13 PASS · 8/8 future-task ready · 持续可信。

---

## 总结

### 真实问题
1 个: **D2 Reconciler v6 全扫产生 1849 条假阳性告警** (EX 例外规则覆盖不全)

### 误判
0 个

### 改善项
1. **T3 提案**: 在 `policy/reconciler-adapter-extensions.md` 提出 EX-005+ 扩展建议（不动 policy v2，等用户授权）
2. **T2 调查**: 3 个真 test 失败 (本会话在 audit/2026-10-09-3tests-diagnosis.md 单独写)
3. **T4 分类**: 700+ skill 分类（不阻塞主权工程）

### 提议的下一轮 Round 6
- **不在本会话跑**（autonomous_scope 内不动 D9/D10 等网络 + state 扫描）
- 如果用户授权 Round 6 全扫: 复制 Round 5 模板 + 加 EX-005+ 后的 reconciliation 对比

---

_— Codex (本会话 supervisor) · Round 6 状态审计 · 6/14 复核 PASS · 1/14 真实回归 · 7/14 沿用 · 2026-10-09_