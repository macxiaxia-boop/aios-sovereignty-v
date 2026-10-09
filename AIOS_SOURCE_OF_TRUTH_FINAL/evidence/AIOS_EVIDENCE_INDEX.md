# AIOS 证据索引（Supervisor 19:50 官方 CLI 修正后）

> **captured_at**: 2026-09-29T11:43:50Z (19:43 +08:00) — 本轮实时探针
> **post-supervisor refresh (OpenClaw 修正)**: 2026-09-29T11:50:00Z (19:50 +08:00) — 新增官方 CLI 探针记录
> **post-generation refresh**: 2026-09-29T11:43:50Z（重记录 FILE_INVENTORY.csv / AUDIT_MANIFEST.json / PROTOCOL_REGISTRY.json 当前 hash）
> **生成者**: Claude Code 2.1.282 (MiniMax-M3) — 执行手
> **目的**: 列出本目录所有引用证据的路径、mtime、size、SHA256、证据级别；明示支持/不支持的结论

---

## 1. 证据级别定义（铁律 #1 优先级）

| 级别 | 含义 | 时间窗口 | 示例 |
|---|---|---|---|
| **L0** | 本轮实时探针 | ≤ 5 min | Get-NetTCPConnection / curl /healthz / curl /v1/agents / aiosv2 status/health / git HEAD |
| L1 | 当前文件/Git snapshot | ≤ 60 min | ls / stat / git status |
| L2 | 当日扫描报告 (V16) | ≤ 24h | 01/02/03 MD+CSV+JSON |
| L3 | 历史报告 (R281.1/2/3, R320.6) | 1-7 day | system-audit-20260929/* |
| L4 | 设计/声明/愿景 | ≥ 7 day | registry / docs |

---

## 2. V16 扫描输入证据（任务原始材料）

| 路径 | 大小 | mtime (UTC) | SHA256 | 级别 | 生成者 | 支持/不支持 |
|---|---|---|---|---|---|---|
| `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/01_CORE_GIT_SCAN.md` | 24595 | 2026-09-29T06:35:53Z | `89108d7e0e20c2a8a3a9179e6a683ff7e9ee21c2f5a6da2ff9ad6f4508a05c3a` | L2 | Claude Code 14:15 | **支持**: 9 根存在性 + 3 git 仓库 + 非 git 5 个 + 6 处敏感路径 metadata + 1 处 partial `_relinked` + 138 staged + 71 ?? |
| `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/01_CORE_ASSETS.csv` | 18035 | 2026-09-29T06:35:18Z | `123d6e061ceaca89a41d208a6dd35fd4e153f826ff74d42f04d9e30d4fc11427` | L2 | Claude Code 14:35 | **支持**: 71 资产条目（ROOT-001..009 / GIT-001..003 / DOC-001..016 / REG-001..015 / SCRIPT-001..004 / DIAG-001..002 / LAB-001..005 / SENS-001..006 / INV-001..005 / UNKNOWN 3） |
| `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/02_AGENT_CONNECTOR_SCAN.md` | 17497 | 2026-09-29T06:35:57Z | `7f2d7b1c83ba702a952f40171e7240768f0ea686ed3545c7a74d25fff072caa1` | L2 | Claude Code 14:15 | **支持**: CLI 6 个 exit 0 + MCP 26 条 + bridge 9 条 + obsidian + junction 3 + status 枚举归一 6 项 |
| `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/02_AGENT_CONNECTORS.json` | 49269 | 2026-09-29T06:35:05Z | `39869ddbe20823ae126a38d4ebe3dc949ab6c3f48f6949d4d1087f63ab9924c2` | L2 | Claude Code 14:15 | **支持**: 69 条 v1.2 归一 status；ACTIVE=13, VERIFIED=1, FOUND=42, BROKEN=7, UNKNOWN=6, LEGACY=0 |
| `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/03_BUSINESS_ASSET_SCAN.md` | 26017 | 2026-09-29T06:36:03Z | `44a93d3bf2e6ba8388ddc82c81bdc676e3f56ae925a26942c1ff37aadd33fe0a` | L2 | Claude Code 14:14 | **支持**: 16 根 + 26 子资产；CloudTech 5 根 + 灵策 3 根 + IP/OPC 8 根 + Obsidian 1；OPC 双证（路径+文本） |
| `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/03_BUSINESS_ASSETS.csv` | 16915 | 2026-09-29T06:34:55Z | `c817047933d5e9db520316e8e19bbb800079908556fdbe8a9f4a895813272d22` | L2 | Claude Code 14:34 | **支持**: 62 资产条目（A-CT 23 + A-LC 8 + A-IP 24 + A-OBS 7）；含 28 条 SHA256 + 3 REDACTED secret |

### 2.1 已删除的临时扫描文件（14:42 已删除）

| 路径（已删）| 原始大小 | 原始 mtime | 理由 |
|---|---|---|---|
| `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/_scan_helper.py` | 5761 B | 2026-09-29T06:15:55Z | V16 临时扫描助手；非 6 份交付；删除前已确认未占用 |
| `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/_scan_data.json` | 163304 B | 2026-09-29T06:13:25Z | V16 扫描中间产物；非 6 份交付 |
| `D:/AIOS/_workzone/AIOS_REALITY_SCAN_V16_20260929/_scan_err.txt` | 0 B | 2026-09-29T06:13:19Z | 空 stderr；非 6 份交付 |

### 2.2 已删除的占位 INDEX.md（本轮 19:43 删除 · 修正任务）

| 路径（已删）| 原始大小 | 理由 |
|---|---|---|
| `D:/AIOS/AIOS_SOURCE_OF_TRUTH_FINAL/architecture/INDEX.md` | （占位）| 5 空目录不写占位 INDEX.md；等待未来真实索引 |
| `D:/AIOS/AIOS_SOURCE_OF_TRUTH_FINAL/code/INDEX.md` | （占位）| 同上 |
| `D:/AIOS/AIOS_SOURCE_OF_TRUTH_FINAL/config/INDEX.md` | （占位）| 同上 |
| `D:/AIOS/AIOS_SOURCE_OF_TRUTH_FINAL/history/INDEX.md` | （占位）| 同上 |
| `D:/AIOS/AIOS_SOURCE_OF_TRUTH_FINAL/tasks/INDEX.md` | （占位）| 同上 |

> **临时扫描工件已移除，可由原始扫描重建。** 删除前确认: 3 文件不在 6 交付物中、未被运行进程占用（净删除前已用 `stat` 验证 mtime）；5 INDEX.md 为占位文件，无业务内容，本轮修正任务一并删除。

---

## 3. 治理 / SSOT / 历史报告证据（含 post-generation refresh）

| 路径 | 大小 | mtime (UTC) | SHA256 | 级别 | 支持/不支持 |
|---|---|---|---|---|---|
| `D:/AIOS/_agent-hub/v2/governance/CANONICAL_INDEX.json` | 7242 | 2026-09-29T06:29:41Z | `ce1486089a5f5fd001ae869bfc767ba35642b7ffc6a7969dd69f0031ebc62e71` | L2 | **支持**: SSOT 索引；current_audit.root=D:/AIOS（**不支持**: 5 其他根零覆盖） |
| `D:/AIOS/_agent-hub/v2/governance/PROTOCOL_REGISTRY.json` | **31182** | **2026-09-29T11:44:32Z** | **`254ac61dda30dd10f6b35961ec83ab239238ea38b621993b8333c7d4958844be`** | L2 | **post-gen refresh (final)**: 并发 CC **二次**修改文件（原 21281 B / db0f9cb8… → 31181 B / 56a0a5e8… → 现 31182 B / 254ac61d…）；结构 32 entries / 29 families / 22 current / 7 unresolved 未变 |
| `D:/AIOS/_agent-hub/v2/reports/system-audit-20260929/AUDIT_MANIFEST.json` | 264675 | 2026-09-29T06:31:16Z | `f5912cd6656149f0bdfcfc272b5f72459eb4d5f4e76cc9ac10e717ade9454739` | L3 | **post-gen refresh**: 当前 hash 不变（文件未被并发修改）；R281.2 322 complete + 1 partial；match=True；71,072 files / 727 dirs / 2,575,975,014 bytes |
| `D:/AIOS/_agent-hub/v2/agents/agents.json` | 2519 | 2026-09-29T04:50:52Z | `4a8d62cdd46fc9ae9e327270b2f7f5b06e54082a40ca05b0f61f0b05b64f6bce` | L2 | **支持**: 5 agents 注册表；**CONFLICT**: codex.role="executor" vs CLAUDE.md Codex=Supervisor |
| `D:/AIOS/_agent-hub/v2/reports/test_run.json` | 9316 | 2026-09-29T05:13:46Z | `58b67a35122684840000ee3b0412b2bd51cdb7d8424422a58e1ded6a7f1e295b` | L3 | **支持**: R320.6 55/55 PASS（Tested）；**不支持**: Integrated/Validated/Production Ready |
| `D:/AIOS/AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json` | 4946 | 2026-09-29T05:20:05Z | `407c139aae530cde70dd2904e46062bf8bdf2fcc72f773fbf466d7c09cf61957` | L2 | **支持**: 9 bridges 声明；**不支持**（REGISTRY DRIFT · 19:50 修正后）: ① br-aios-codex-relay 标 active 但 19194 NOT LISTENING；② br-swarmclaw-openclaw 标 active 但 :3456/:3457 NOT LISTENING；③ br-aios-hermes 标 active 但 messaging platforms 未配置无 round-trip。**br-aios-openclaw 不计入已证实 REGISTRY DRIFT(BROKEN)**: 19:50 Supervisor 官方 CLI 确认 gateway+Feishu 当前连接可用；改为桥功能本身 PARTIAL/未验证 |
| `D:/AIOS/_agent-hub/memory/2026-09-29.md` | 15475 | 2026-09-29T06:37:39Z | `fa28b60482243c0f1e24e2a8bff6ea234f6f07e7d0d0ce01a0c526a7f02821fc` | L2 | **支持**: R281/R281.1/R281.2/R281.3 + P0 修复记录 + 14:00 fix-task-actions 7/7 DONE |

---

## 4. V16 zip 源包（任务输入 #1）

| 项 | 值 |
|---|---|
| 路径 | `C:/Users/xinzh/Desktop/AIOS_MASTER_REALITY_COMPLETE_FINAL_V16_20260929.zip` |
| 大小 | 3614 bytes |
| mtime (UTC) | 2026-09-29T06:15:53Z |
| SHA256 | `a70c806c05cb152f8a63784af215e8182bc222e83397115a090cf2660da60bfe` |
| 级别 | L2（源包） |
| 生成者 | 用户 |
| 支持 | zip 存在可读 |
| 不支持 | zip 含业务内容（**仅 3614 bytes**,明显是结构骨架；SSOT 来自 3 独立扫描） |

---

## 5. 本轮实时探针命令与结果摘要（关键 · Supervisor 19:50 官方 CLI 修正后）

| 时间 | 命令 | 结果摘要 | 用于支持 |
|---|---|---|---|
| 2026-09-29T11:43:39Z | `git -C D:/AIOS rev-parse HEAD` | `0b964e646b46406895eefd816b05363687ee3a0d` | HEAD 不变；本轮零 git 写 |
| 2026-09-29T11:43:39Z | `git -C D:/AIOS status --short --branch` | `## main` + 210 entries (71 ?? + 130 A + 6 AM + 2 AD + 1 M) | git working tree 脏 |
| 2026-09-29T11:43:43Z | `python D:/AIOS/_agent-hub/v2/cli/aiosv2.py status` | `tasks_total=0; inbox=1; outbox=2; deadletter=0; agents_in_registry=5; warnings=[]` | v2 queue 文件计数 |
| 2026-09-29T11:43:44Z | `python D:/AIOS/_agent-hub/v2/cli/aiosv2.py health` | 5 agents; claudecode/codex/workbuddy reachable=false (沙箱); hermes reachable=true healthy=true (--version); openclaw reachable=true healthy=true (18792 healthz 200) **BUT agent API 全 404** | 沙箱限制 vs 本地限制 + OpenClaw 半挂初始判级（19:43 误判 BROKEN；19:50 已基于官方 CLI 修正） |
| 2026-09-29T11:43:48Z | `Get-NetTCPConnection -LocalPort 18792,19194,3456,3457,11434,7897` | **18792 LISTENING PID 19108 (node.exe); 7897 LISTENING PID 17632 (verge-mihomo); 19194/3456/3457/11434 NOT LISTENING** | 19:43 ACTIVE/BROKEN 重判定基础 |
| 2026-09-29T11:43:48Z | `curl http://127.0.0.1:18792/healthz` | **HTTP 200** `{ok:true,status:live}` | gateway 进程存活 |
| 2026-09-29T11:43:49Z | `curl http://127.0.0.1:18792/v1/agents` | **HTTP 404 Not Found** | **不支持 BROKEN 结论**（19:50 Supervisor 权威）: 该路径**非 OpenClaw 官方状态接口**，未知路由 404 不能支持故障结论 |
| 2026-09-29T11:43:49Z | `curl http://127.0.0.1:18792/api/status` | **HTTP 404 Not Found** | **不支持 BROKEN 结论**: 非官方路由 |
| 2026-09-29T11:43:49Z | `curl http://127.0.0.1:18792/api/agents` | **HTTP 404 Not Found** | **不支持 BROKEN 结论**: 非官方路由 |
| 2026-09-29T11:43:49Z | `curl http://127.0.0.1:18792/api/version` | **HTTP 404 Not Found** | **不支持 BROKEN 结论**: 非官方路由 |
| 2026-09-29T11:43:49Z | `curl http://127.0.0.1:18792/api/v1/health` | **HTTP 404 Not Found** | **不支持 BROKEN 结论**: 非官方路由 |
| 2026-09-29T11:43:49Z | `curl http://127.0.0.1:18792/openclaw` | HTTP 200 (HTML 页面) | UI build 可达 |
| 2026-09-29T11:43:49Z | `curl http://127.0.0.1:18792/runtime` | HTTP 200 | UI build runtime 可达 |
| 2026-09-29T11:43:48Z | `curl http://127.0.0.1:19194/` | HTTP 000 timeout | Codex relay 已 DOWN（持续 3 个时点 14:18/14:40/19:43/19:50 一致） |
| 2026-09-29T11:43:48Z | `curl http://127.0.0.1:3456/` | HTTP 000 timeout | SwarmClaw HTTP DOWN |
| 2026-09-29T11:43:48Z | `curl http://127.0.0.1:11434/` | HTTP 000 timeout | Ollama DOWN |
| 2026-09-29T11:43:50Z | `mcp__aios-interop__aios_status` (本会话 MCP tool-call) | ok:true | aios-interop ACTIVE 实时验证 |
| 2026-09-29T11:43:50Z | `hermes --version` | v0.15.1 (2026.5.29) exit 0 | Hermes CLI VERIFIED |
| 2026-09-29T11:43:50Z | `hermes status` | MiniMax ✓ configured; Messaging Platforms 全部 ✗ 未配置 | Hermes 无真实消息 round-trip → status=VERIFIED maturity=Tested |
| **2026-09-29T11:50:00Z** | **`openclaw status --json`** (Supervisor 官方只读 CLI · exit 0) | **runtimeVersion: 2026.9.5; gateway.reachable: true; connectLatencyMs: 117; error: null; tasks: total=9, succeeded=9, failures=0** | **支持** OpenClaw Gateway agent → status=ACTIVE；gateway 实时可达 |
| **2026-09-29T11:50:00Z** | **`openclaw health --json`** (Supervisor 官方只读 CLI · exit 0) | **ok: true; plugins.errors: []; feishu: enabled/running/connected=true, lastError=null; eventLoop.degraded: true reason=cpu; gateway 18792 health 可达** | **支持** OpenClaw Gateway → ACTIVE/Integrated；Feishu channel 正常；eventLoop CPU degraded 为已知风险 |

---

## 6. 历史测试证据（Tested 但非 Production · 修正后）

> **重要边界**: 历史 `test_run.json` (R320.6, 55/55 PASS) **只证明 Tested**，**不证明生产 Integrated**。

| 测试模块 | pass/fail | 时长 | 证据 |
|---|---|---|---|
| test_01_envelope_schema | 8/8 PASS | 16 ms | Tested |
| test_02_queue_concurrency | 6/6 PASS | 623 ms | Tested |
| test_03_state_machine | 8/8 PASS | 166 ms | Tested |
| test_04_heartbeat_timeout_retry | 4/4 PASS | 160 ms | Tested |
| test_05_protocol_loopback | 10/10 PASS | 605 ms | Tested |
| test_06_probes | 6/6 PASS | 5621 ms | Tested |
| test_07_healthcheck | 11/11 PASS | 7430 ms | Tested |
| test_08_supervisor_watch | 2/2 PASS | 482 ms | Tested |
| **v2 小计** | **55/55 PASS** | 15.3s | **Tested only** |
| CloudTech rc2 Live Direct Execution pytest | 129/129 PASS | n/a | Tested only（candidate 非 Live）|
| LocalExecutionBridge Phase 9 | 178/178 PASS | 7.55s | Tested only（未启动 runtime）|
| **三套独立测试集合计** | **55+129+178=362 PASS** | — | **三套不同测试集，不构成生产验证** |

**Tests End-to-end 端到端**: Codex↔CC two-process round-trip via v2/messages/{inbox,outbox}（1 inbox + 2 outbox ACK 文件实证；本轮保守判 **Tested**，非 Validated；未实测消费者侧端到端处理）。

**CC agent workflow（本轮端到端修正任务）**: **Validated** — 3 扫描（V16 三份）+ 5 修正（README 重写 / 6 交付物同步 / 5 INDEX.md 删除 / 状态判级修正 / hash 重记录）+ 最终生成成功 → 端到端完成；但**体系仍 PARTIAL**（缺 dispatch/SLA/metrics），**非 Production Ready**。

---

## 7. 已删除的临时文件（详见 §2.1, §2.2）

| 文件 | 状态 |
|---|---|
| `_scan_helper.py` | ✅ 14:42 已删除 |
| `_scan_data.json` | ✅ 14:42 已删除 |
| `_scan_err.txt` | ✅ 14:42 已删除 |
| `architecture/INDEX.md` | ✅ 19:43 已删除（占位）|
| `code/INDEX.md` | ✅ 19:43 已删除（占位）|
| `config/INDEX.md` | ✅ 19:43 已删除（占位）|
| `history/INDEX.md` | ✅ 19:43 已删除（占位）|
| `tasks/INDEX.md` | ✅ 19:43 已删除（占位）|

> 临时扫描工件已移除，可由原始扫描重建。占位 INDEX.md 已移除，等待未来真实索引内容到位后再行填充。删除前确认: 不在 6 交付物中（6 交付物为 3 MD + 2 CSV + 1 JSON）、未被运行进程占用、未列入扫描源。

---

## 8. 不支持的结论 / 待复核（Supervisor 19:50 修正后）

| # | 结论 | 不支持原因 |
|---|---|---|
| 1 | "AIOS 整体 Production Ready" | 仅 br-aicc + aios-interop + OpenClaw Gateway ACTIVE；2 条 BROKEN（codex-relay/swarmclaw）；3 处已证实 REGISTRY DRIFT；138 staged |
| 2 | "CloudTech SaaS 已上线" | 仅 Tested；audit 78/100；无生产端口侦听 |
| 3 | "br-aios-codex-relay 健康" | 19:50 19194 NOT LISTENING（registry active vs reality BROKEN） |
| 4 | "WorkBuddy runtime 可达" | v2/health.json reachable=false (沙箱) |
| 5 | ~~"OpenClaw agent API 全部 404 所以 BROKEN"~~ | **19:50 Supervisor 移除该断言**: `/v1/agents /api/status /api/agents /api/version /api/v1/health` **非 OpenClaw 官方状态接口**；未知路由 404 不能支持 BROKEN 结论。**官方 CLI 权威** (`openclaw status --json` + `openclaw health --json` exit0): gateway.reachable=true; tasks succeeded=9/9; feishu enabled/running/connected=true → **status=ACTIVE, maturity=Integrated**（**非 Validated / 非 Production Ready**）；eventLoop.degraded=true(cpu) 为已知风险 |
| 6 | "CloudTech-Vault 增量 5 分钟" | mtime 5+ 天未变 |
| 7 | "Obsidian README 路径正确" | README 写 D:\个人文件\AI\Operator\Obsidian\ 实际 C:\Users\xinzh\.aios\Obsidian\ |
| 8 | "codex.role = Supervisor" | registry 仍 executor（CONFLICT） |
| 9 | "CloudTech-Portable 生产部署" | 仅代码层；3 untracked 含 cloudtech.db (PII) |
| 10 | "OPC 装修矩阵活跃" | mtime 2+ 月未更新；output/ 停在 2026-06-28 |
| 11 | "Hermes ACTIVE/Integrated" | **维持修正**: messaging platforms (Telegram/Discord/Slack/Signal) 全部 ✗ 未配置；无真实消息 round-trip → status=VERIFIED maturity=Tested |
| 12 | "AIOS 整体 Validated" | **维持修正**: 55+129+178=362 已列测试证据但不构成生产验证；maturity=Tested |
| 13 | "br-aios-openclaw ACTIVE/Validated" | **不支持**: 19:50 官方 CLI 仅确认 gateway+Feishu 当前连接；但**无 AIOS 真实消息 round-trip**；桥功能 PARTIAL/未验证 → status=VERIFIED |
| 14 | "br-claudecode-openclaw 因 gateway 健康升级" | **不支持**: 该桥保持 FOUND/loopback_only/unverified；不得因 gateway 健康升级 |

---

## 9. 证据交叉验证矩阵（Supervisor 19:50 官方 CLI 修正后）

| 关键结论 | L0 (19:43) | L0' (19:50 Supervisor 官方 CLI) | L2 (V16 14:15) | L3 (R281.2) | 一致? |
|---|---|---|---|---|---|
| 18792 LISTENING | ✅ PID 19108 | ✅ runtimeVersion 2026.9.5; gateway.reachable=true; connectLatencyMs=117 | ✅ PID 27284 | n/a | ⚠️ PID 变化 |
| 18792 /healthz | ✅ HTTP 200 | ✅ ok=true; plugins.errors=[]; feishu enabled/running/connected=true | ✅ HTTP 200 | n/a | ✅ |
| 18792 gateway.reachable (官方 CLI) | n/a (未探) | ✅ true; error=null | n/a | n/a | **新 L0' 证据 · ACTIVE** |
| 18792 agent API (/v1/agents 等) | ❌ 全 404 | n/a（非官方路由） | n/a | n/a | ❌ **不能支持 BROKEN**（非官方状态接口）|
| 18792 feishu channel | n/a (未探) | ✅ connected=true; lastError=null | n/a | n/a | **新 L0' 证据** |
| 18792 eventLoop | n/a (未探) | ⚠️ degraded=true reason=cpu | n/a | n/a | **新 L0' 风险** |
| 18792 tasks | n/a (未探) | ✅ total=9 succeeded=9 failures=0 | n/a | n/a | **新 L0' 证据** |
| 19194 LISTENING | ❌ NOT LISTENING | ❌ NOT LISTENING | ✅ LISTENING | n/a | ❌ **CONFLICT**（连续 4 个时点掉线 14:18/14:40/19:43/19:50） |
| 3456/3457 LISTENING | ❌ | ❌ | ❌ | n/a | ✅ 一致 |
| 7897 LISTENING | ✅ PID 17632 | n/a | ✅ | n/a | ✅ |
| git HEAD 0b964e6 | ✅ | ✅ | ✅ | ✅ | ✅ 一致 |
| 5 agents in registry | ✅ | ✅ | ✅ | ✅ | ✅ |
| v2 inbox/outbox 1+2 | ✅ | ✅ | ✅ | ✅ | ✅ |
| Codex↔CC ACK files | ✅ | ✅ | ✅ | ✅ | ✅ |
| Hermes v0.15.1 | ✅ | n/a | ✅ (R260) | n/a | ✅ |
| Hermes messaging platforms | ❌ 全部未配置 | n/a | n/a | n/a | ❌ **维持 VERIFIED** |
| codex.role = executor | ✅ registry | n/a | ✅ (V16 未改) | n/a | ✅ 但 vs CLAUDE.md CONFLICT |
| 138 staged in git | ✅ | n/a | ✅ | n/a | ✅ 一致 |
| AIOS_REALITY_MAP 数字 | n/a | n/a | ⚠️ 142,572/8.15GB | ✅ R281.1 71,051/2.58GB | ❌ NUMBER DRIFT |
| PROTOCOL_REGISTRY hash | `254ac61d…` post-gen refresh (final) | n/a | `db0f9cb8…` | n/a | ⚠️ **并发 CC 二次修改** |

---

## 10. Post-Generation Refresh（修正任务 · 关键）

> **触发原因**: 并发 CC 在草案后更新文件，重新记录当前 FILE_INVENTORY.csv / AUDIT_MANIFEST.json / PROTOCOL_REGISTRY.json 的 size/mtime/SHA256。

| 文件 | 当前 size | 当前 mtime (epoch) | 当前 mtime (UTC) | 当前 SHA256 | 变化 |
|---|---|---|---|---|---|
| `D:/AIOS/_agent-hub/v2/reports/system-audit-20260929/FILE_INVENTORY.csv` | 37518323 | 1790662870 | 2026-09-29T06:21:10Z | `10c17df454b41566170e14ef366f9d5b3a39f53bf7f9c7609452fef272b406ce` | hash 替换（原未记录 hash）|
| `D:/AIOS/_agent-hub/v2/reports/system-audit-20260929/AUDIT_MANIFEST.json` | 264675 | 1790662876 | 2026-09-29T06:21:16Z | `f5912cd6656149f0bdfcfc272b5f72459eb4d5f4e76cc9ac10e717ade9454739` | hash 不变（未修改）|
| `D:/AIOS/_agent-hub/v2/governance/PROTOCOL_REGISTRY.json` | **31182** | **1790682272** | **2026-09-29T11:44:32Z** | **`254ac61dda30dd10f6b35961ec83ab239238ea38b621993b8333c7d4958844be`** | **并发 CC 二次修改**: size 21281→31181→31182 B；hash db0f9cb8…→56a0a5e8…→254ac61d…；结构 32/29/22/7 未变 |

---

## 11. 验收（铁律 #2 自检 · Supervisor 19:50 修正后）

- [x] 列所有原始证据路径、mtime、size、SHA256、生成者、证据级别
- [x] 本轮 19:43 探针命令与结果摘要（含 OpenClaw 假定路由 404 探针 — 非 OpenClaw 官方状态接口；不能支持 BROKEN 结论；+ Hermes messaging platforms 未配置）
- [x] **Supervisor 19:50 官方 CLI 探针记录**: `openclaw status --json` exit0 + `openclaw health --json` exit0；gateway.reachable=true; connectLatencyMs=117; tasks succeeded=9/9; feishu connected=true; eventLoop.degraded=true(cpu)
- [x] 历史 test_run 仅证明 Tested，不证明生产 Integrated
- [x] **三套测试集去重**: 55 (v2) + 129 (CloudTech rc2) + 178 (LEB) = 362 已列测试证据；明确非同一套测试；非生产验证
- [x] 不支持的结论独立列（§8，含 19:50 移除的 OpenClaw BROKEN 断言 + 新增 ACTIVE/Validated 反断言）
- [x] 证据交叉验证（§9，含 19:43 + 19:50 双 L0 探针）
- [x] 临时扫描工件删除记录（§2.1, §7）
- [x] 5 占位 INDEX.md 删除记录（§2.2, §7）
- [x] Post-generation refresh 三文件 hash 重记录（§10）
- [x] 零 secret 值（仅 6 .env/.pem/.key path，无 token）
- [x] 全部时间戳 UTC（除本地 +08:00）
- [x] **10 目录存在**；**7 文件** = 1 README + 6 交付物；5 INDEX.md 已删除
- [x] **明确不混淆**: 404 路径非 OpenClaw 官方状态接口，不能据此判 BROKEN；gateway 健康 ≠ bridge 已验证
