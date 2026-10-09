# AIOS V16 事实源目录（Final Source of Truth）

> **生成者**: Claude Code 2.1.282 (MiniMax-M3) — 执行手
> **监督**: Codex Supervisor
> **captured_at (UTC)**: 2026-09-29T11:43:50Z
> **captured_at (本地)**: 2026-09-29 19:43 +08:00
> **post-generation refresh (final)**: 2026-09-29T11:43:50Z + 19:44 final re-hash；FILE_INVENTORY.csv sha256 10c17df4… / AUDIT_MANIFEST.json f5912cd6…（两者不变）；PROTOCOL_REGISTRY.json sha256 **56a0a5e8…→254ac61d…**（并发 CC 二次修改；最终 mtime 2026-09-29T11:44:32Z size 31182）
> **post-supervisor refresh (OpenClaw 修正 · 本轮 19:50)**: 2026-09-29T11:50:00Z
> **scope**: 基于已修正的三份现实扫描证据 (V16, 2026-09-29 14:15-14:36 本地) + 本轮重跑实时探针 (19:43) + Supervisor 官方只读 CLI 探针 (19:50)

---

## 1. 目录树（10 目录，7 文件）

```
D:/AIOS/AIOS_SOURCE_OF_TRUTH_FINAL/
├── README.md                          # 本文件
├── context/
│   └── AIOS_REALITY_BASELINE_FINAL.md # 现实基线（已存在/已运行/已验证/未完成/阻塞/风险）
├── assets/
│   ├── AIOS_ASSET_REGISTRY.csv        # 资产注册表（216 资产 AR-0001..AR-0216）
│   └── AIOS_GAP_MATRIX_FINAL.csv       # 缺口矩阵（P0×14 + P1×12 + P2×8 + P3×8 + X×1 = 43）
├── status/
│   └── AIOS_STATUS.json               # 项目/agent/连接器/任务/阻塞/校验/波动 JSON
├── roadmap/
│   └── AIOS_EXECUTION_ROADMAP.md      # P0→P3 路线图（Codex=脑、CC=手脚）
├── evidence/
│   └── AIOS_EVIDENCE_INDEX.md         # 证据索引（路径/mtime/size/SHA256/级别 + post-generation refresh）
├── history/                           # 空目录（未来真实索引；本轮未生成）
├── architecture/                      # 空目录（未来真实索引；本轮未生成）
├── code/                              # 空目录（未来真实索引；本轮未生成）
├── config/                            # 空目录（未来真实索引；本轮未生成）
└── tasks/                             # 空目录（未来真实索引；本轮未生成）
```

> **本轮不创建任何占位文件**：`history/`、`architecture/`、`code/`、`config/`、`tasks/` 五个目录保留为空，等待未来真实索引内容到位后再行填充。任何占位 INDEX.md 会污染"目录-索引"映射，故本轮明确不写。

---

## 2. 事实优先级（铁律 #1）

| 级别 | 来源 | 示例 | 权重 |
|---|---|---|---|
| **L0** | **本轮实时探针** (2026-09-29T11:43Z) | `Get-NetTCPConnection` / `curl /healthz` / `curl /v1/agents` / `aiosv2 status/health` / `git HEAD` | 最高 |
| L1 | 当前文件/Git (snapshot < 60s) | `git status --short`, `ls`, `stat` | 高 |
| L2 | 当日扫描报告 (V16 14:15-14:36) | `01/02/03_*` 6 文件 + 3 CSV/JSON | 中 |
| L3 | 历史报告 (R281.1 / R281.2 / R281.3 / R320.6) | `system-audit-20260929/*` | 低 |
| L4 | 设计/声明/愿景 (registry / docs) | `AIOS_BRIDGE_REGISTRY.json` 的 `status=active` 声明 | 最低 |

> **关键原则**: 实测 L0 > L1 > L2 > L3 > L4。任何与 L0 冲突的声明（如 registry 写 `active` 但端口实际 LISTENING 缺失，或 /healthz 200 但 agent API 全部 404）记为 **REGISTRY DRIFT**。

---

## 3. 六份交付物位置

| # | 文件 | 类型 | 路径 |
|---|---|---|---|
| 1 | 现实基线 | MD | `context/AIOS_REALITY_BASELINE_FINAL.md` |
| 2 | 资产注册表 | CSV | `assets/AIOS_ASSET_REGISTRY.csv` |
| 3 | 缺口矩阵 | CSV | `assets/AIOS_GAP_MATRIX_FINAL.csv` |
| 4 | 状态快照 | JSON | `status/AIOS_STATUS.json` |
| 5 | 执行路线图 | MD | `roadmap/AIOS_EXECUTION_ROADMAP.md` |
| 6 | 证据索引 | MD | `evidence/AIOS_EVIDENCE_INDEX.md` |

---

## 4. 六交付物自检清单（铁律 #2 · 修正后）

- [x] 七文件 = 1 README + 6 交付物；目录递归文件数 = **7**
- [x] 10 目录存在：`README.md` + `context/` + `assets/` + `status/` + `roadmap/` + `evidence/` + `history/` + `architecture/` + `code/` + `config/` + `tasks/`
- [x] `AIOS_ASSET_REGISTRY.csv`：216 行（AR-0001..AR-0216）；`Import-Csv` 可解析；状态枚举仅 `UNKNOWN/FOUND/VERIFIED/ACTIVE/BROKEN/LEGACY`；ID 唯一
- [x] `AIOS_GAP_MATRIX_FINAL.csv`：43 行；`Import-Csv` 可解析；分类枚举仅 `IMPLEMENTED/PARTIAL/MISSING/CONFLICT/BLOCKED`
- [x] `AIOS_STATUS.json`：`ConvertFrom-Json` 成功；顶层键含 `generated_at,source_version,projects,agents,connectors,tasks,blockers,validation,observed_volatility`；`validation.tested_count`（非 `tested_count_count`）存在
- [x] 所有 ACTIVE 仅由最新探针支持 — 本轮修正 OpenClaw/Hermes 状态（详见 §5）
- [x] `git HEAD` 不变：`0b964e646b46406895eefd816b05363687ee3a0d`（本轮仅只读探针，无 git 写）
- [x] 无 secret 值：6 个 .env/.pem/.key 仅记 path，文件无 token 出现
- [x] 内部文件路径正确：所有 `file_path:` 锚点对得上
- [x] post-generation refresh：FILE_INVENTORY.csv / AUDIT_MANIFEST.json / PROTOCOL_REGISTRY.json 三文件当前 SHA256 已重记录

---

## 5. 状态波动警告（22 分钟窗口 + 本轮 19:43 重探针 + Supervisor 19:50 官方 CLI 修正）

| 端口/服务 | 14:18 扫描结论 | 14:40 重探针 | 19:43 本轮 | **19:50 Supervisor 官方 CLI** | 最终判级 |
|---|---|---|---|---|---|
| 18792 (OpenClaw) | LISTENING + /healthz 200 | LISTENING（PID 变化）+ curl 000 | LISTENING (PID 19108) + /healthz 200 但 **404 路径探针**（非官方接口） | **`openclaw status --json` exit0: runtimeVersion 2026.9.5; gateway.reachable=true; connectLatencyMs=117; tasks total=9 succeeded=9 failures=0** | **ACTIVE** (gateway+Feishu 连接)；maturity=**Integrated**；**非 Validated / 非 Production Ready**；eventLoop.degraded=true(原因=cpu) 风险 |
| 19194 (Codex relay) | LISTENING + GET / 200 | NOT LISTENING | **NOT LISTENING** | NOT LISTENING | **BROKEN** |
| 3456/3457 (SwarmClaw) | BROKEN | BROKEN | **BROKEN** | BROKEN | BROKEN |
| 11434 (Ollama) | DOWN | DOWN | **DOWN** | DOWN | DOWN |
| 7897 (clash-verge) | LISTENING | LISTENING | **LISTENING** (PID 17632, verge-mihomo) | LISTENING | ACTIVE |

> **关键修正（Supervisor 官方 CLI 权威 · 19:50）**：
> 1. 19:43 误判 OpenClaw BROKEN 是基于 **`/v1/agents /api/status /api/agents /api/version /api/v1/health` 等假定路由返回 404**——这些路径**非 OpenClaw 官方状态接口**，不能据此判定故障。
> 2. 19:50 Supervisor 通过官方只读 CLI（`openclaw status --json` + `openclaw health --json`）确认：`gateway.reachable=true; connectLatencyMs=117; error=null; tasks total=9 succeeded=9 failures=0; feishu channel enabled/running/connected=true, lastError=null`。
> 3. 故最终判级：OpenClaw Gateway agent → **status=ACTIVE, maturity=Integrated**；明确**非 Validated / 非 Production Ready**；eventLoop.degraded=true（原因=cpu）为已知风险，须观察。
> 4. **br-aios-openclaw 桥** → **VERIFIED**（gateway 和 Feishu 当前连接可用，但**无 AIOS 真实消息 round-trip**，不可升 ACTIVE/Validated）。
> 5. **br-claudecode-openclaw 桥** → **保持 FOUND / loopback_only / unverified**（不得因 gateway 健康而升级）。

> **Hermes**：`hermes --version` exit 0（v0.15.1）+ `hermes status` 显示 MiniMax 配置；但 messaging platforms（Telegram/Discord/Slack/Signal）**全部 ✗ 未配置**，无真实消息 round-trip → status **VERIFIED**，maturity **Tested**，不得 ACTIVE/Integrated。

> **不混淆**: 14:18 / 14:40 / 19:43 三个时点的"ACTIVE / BROKEN"标签各自对应真实探针时刻；任何"生产可用"声明必须**实时探针复验**，不可用历史报告代证。

---

## 6. 修改范围（铁律 #4 · 修正后）

| 允许 | 内容 |
|---|---|
| ✅ 创建 | `D:/AIOS/AIOS_SOURCE_OF_TRUTH_FINAL/` 下 10 目录 + 7 文件 |
| ✅ 删除 | `D:/AIOS/AIOS_SOURCE_OF_TRUTH_FINAL/{architecture,code,config,history,tasks}/INDEX.md`（5 个空占位 INDEX.md；本轮修正删除） |
| ✅ 删除 | `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/_scan_helper.py` (5761 B) |
| ✅ 删除 | `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/_scan_data.json` (163304 B) |
| ✅ 删除 | `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/_scan_err.txt` (0 B) |

| 禁止 | 内容 |
|---|---|
| ❌ 修改 | 任何 V16 扫描报告、源代码、配置、registry、memory、git、服务、计划任务、进程 |
| ❌ 读取 | 任何 .env / .key / .pem / secret 内容 |
| ❌ 写占位 | `history/code/config/architecture/tasks/` 五个空目录本轮不创建占位 INDEX.md |

---

## 7. 当前状态（最终汇报 · Supervisor 官方 CLI 修正后 · 19:50）

- **git HEAD**: `0b964e646b46406895eefd816b05363687ee3a0d`（本轮无变化）
- **关键修正（Supervisor 官方 CLI 权威 · 19:50）**：
  1. **OpenClaw Gateway agent → status=ACTIVE, maturity=Integrated**（Supervisor 官方只读 CLI: `openclaw status --json` exit0; `openclaw health --json` exit0; gateway.reachable=true; connectLatencyMs=117; tasks total=9 succeeded=9 failures=0; feishu enabled/running/connected=true, lastError=null）；**明确非 Validated / 非 Production Ready**；eventLoop.degraded=true（原因=cpu）为已知风险
  2. **br-aios-openclaw 桥 → status=VERIFIED**（gateway+Feishu 当前连接可用但**无 AIOS 真实消息 round-trip**）；**不可升 ACTIVE / Validated**
  3. **br-claudecode-openclaw 桥 → 保持 FOUND / loopback_only / unverified**（不得因 gateway 健康而升级）
  4. **错误结论移除**: 原 19:43 "OpenClaw agent + bridge → BROKEN (agent API 全 404)" 是基于**非官方路由**的探测——`/v1/agents /api/status /api/agents /api/version /api/v1/health` **不是 OpenClaw 官方状态接口**；不能用未知路由 404 支持 BROKEN 结论
  5. **Hermes agent + bridge → status=VERIFIED, maturity=Tested**（无 messaging platforms 配置；无真实消息 round-trip）— 维持 19:43 判级
  6. **Codex 角色** vs **CC 角色** vs **agents.json** 仍 CONFLICT（待 P0-03 处置）
  7. **Codex→Claude Code 执行手体系** → **PARTIAL**（本轮 3 扫描 + 5 修正 + 最终生成成功，但缺标准 dispatch/SLA/metrics；agent workflow → Validated，非 Production Ready）
  8. **AIOS 整体 maturity** → **Tested**（非 Validated；55+129+178=362 测试证据已列但不构成生产验证）
  9. **CC agent workflow** → **Validated**（本轮端到端完成：3 扫描+5 修正+最终生成；含 6 交付物+README+5 INDEX.md 删除验证）
  10. **`validation.evidence_summary` 去重** → `55+129+178=362`（原 178 重复计数修正）
  11. **`tested_count_count` → `tested_count`**（字段命名修正）
  12. **post-generation refresh** → FILE_INVENTORY.csv / AUDIT_MANIFEST.json / PROTOCOL_REGISTRY.json 三文件 SHA256/mtime 重新记录
  13. **playwright** → **VERIFIED**（CC 本会话 MCP tool-call 成功；非实时 ACTIVE 因 CC 沙箱限制）
- **已证实 REGISTRY DRIFT（3 条）**: ① br-aios-codex-relay 标 active 但 19194 NOT LISTENING ② br-swarmclaw-openclaw 标 active 但 :3456/:3457 NOT LISTENING ③ br-aios-hermes 标 active 但 messaging platforms 未配置（无 round-trip）
- **br-aios-openclaw 不计入已证实 REGISTRY DRIFT(BROKEN)**：基于 Supervisor 官方 CLI 探针，gateway 和 Feishu 实际可用；桥功能本身 PARTIAL/未验证
- **角色冲突**: `_agent-hub/v2/agents/agents.json` 中 `codex.role="executor"`，与本任务 `CLAUDE.md` 规定 `Codex=Supervisor, Claude Code=Executor` **CONFLICT**
- **完成度**: 6 交付物 + README 共 **7 文件**；10 目录存在；自检通过
- **下步**: 待 Codex Supervisor 处置 P0-04 OpenClaw 稳定性观察 + 真实消息 round-trip 验收 + 角色 CONFLICT + Hermes/CC maturity 正式化
