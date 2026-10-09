# Reconciler / Adapter 扩展提案 · 2026-10-09

> **执行者**: Codex (supervisor) · **本文件是提案 · 不是实现**
> **来源**: T1 审计发现 D2 真实回归 (Reconciler v6 假阳性 1849/次)
> **红线**: 不动 policy v2 · 不写新 R 编号 · 不直接实现
> **等批**: 用户拍板后单独立 R 编号施工

---

## 现状摘要 (T1 已记录)

| 项 | 数字 | 状态 |
|---|---|---|
| Reconciler 扫描目标 | 6 个 (`~/.codex`, `~/.claude`, `~/.openclaw`, `~/.hermes`, `_agent-hub`, `CloudTech-Portable`) | v6 ✅ |
| Policy 例外 (EX-005 已就绪后) | 8 个 path_globs + 1 个 env_var | 覆盖不全 ⚠️ |
| 4 adapter 公开签名 | `validate(model, provider, *, request_id) -> (bool, str)` | 统一 ✅ |
| 4 adapter 加载 | codex / claude_code / hermes / openclaw 全部 loaded + sig_ok | 100% ✅ |
| Drift 假阳性 / 全扫 | **1849 条** | 🔴 回归 |
| Drift 真问题 / 全扫 | **0 条** | ✅ 无 |

---

## 提案 EXT-A: Reconciler EX-005~EX-010 加固

### 目的
把当前 1849 假阳性降回 **< 50**，每条假阳性可溯源、可关闭、可审计。

### 候选 EX 规则

```yaml
model_policy:
  exception_rules:
    # EX-005 · Codex desktop global state (chat transcripts, contains 各种 model 名)
    - id: EX-005
      type: path_globs
      description: "Codex desktop global state JSON (chat history, not active config)"
      globs:
        - "~/.codex/.codex-global-state.json"
        - "C:/Users/*/.codex/.codex-global-state.json"
      allowed_keywords: ["*"]
      rationale: "Global state file 是 chat 历史记录容器, 非 active provider config"

    # EX-006 · Codex Python helper scripts (含模型名字符串, 但非 provider endpoint)
    - id: EX-006
      type: path_globs
      description: "Codex desktop Python helper scripts (.py with model name strings)"
      globs:
        - "~/.codex/aios-*.py"
        - "C:/Users/*/.codex/aios-*.py"
      allowed_keywords: ["*"]
      rationale: "aios-agents-md.py / aios-codex-skills.py 等 helper 含字符串但非 endpoint"

    # EX-007 · Codex user-side attachments (pasted text 含其他 AI 讨论记录)
    - id: EX-007
      type: path_globs
      description: "User-side attachments & pasted text (含历史 provider 关键词)"
      globs:
        - "~/.codex/attachments/*"
        - "C:/Users/*/.codex/attachments/*"
        - "~/.codex/computer-use/*"
        - "C:/Users/*/.codex/computer-use/*"
      allowed_keywords: ["*"]
      rationale: "用户粘贴内容 / 屏幕镜像, 不参与 provider routing"

    # EX-008 · Codex backups (含 auth.backup.* 和 _backup-2026*)
    - id: EX-008
      type: path_globs
      description: "Codex desktop backups (auth.backup.*, _backup-2026*)"
      globs:
        - "~/.codex/backups/*"
        - "C:/Users/*/.codex/backups/*"
        - "~/.codex/_backup-*/**"
        - "C:/Users/*/.codex/_backup-*/**"
      allowed_keywords: ["*"]
      rationale: "所有 _backup-* / backups/* 排除 · 当前 EX-004 仅覆盖 config.backup.* 不足"

    # EX-009 · CloudTech data (历史快照 / 候选 / briefing, 非 active AI 调用)
    - id: EX-009
      type: path_globs
      description: "CloudTech data subdirs (openapi_snapshots, v*_candidates, morning_briefing, skill_orchestrator)"
      globs:
        - "D:/CloudTech-Portable/data/openapi_snapshots/*"
        - "D:/CloudTech-Portable/data/v*_candidates/*"
        - "D:/CloudTech-Portable/data/morning_briefing/**"
        - "D:/CloudTech-Portable/data/skill_orchestrator/*"
      allowed_keywords: ["*"]
      rationale: "CloudTech active AI 调用 = MiniMax only (W14.1 verified) · data/ 全为历史快照 / 候选"

    # EX-010 · Codex run-bridge.py (被 stub 替换的安全脚本, 含 deepseek 字符串仅作 keyword deny 用)
    - id: EX-010
      type: path_globs
      description: "Codex run-bridge.py 安全 stub (含 deepseek 字符串仅为 deny pattern)"
      globs:
        - "~/.codex/run-bridge.py"
        - "C:/Users/*/.codex/run-bridge.py"
      allowed_keywords: ["*"]
      rationale: "run-bridge.py 是安全 stub, 含 deepseek 字符串是 DENY list 而非调用"
```

### 预期效果
- 用户侧假阳性 1743 → 估算 < 100（残留主要是 `~/.codex/*minimax*.config.toml` 外的用户配置文件，可继续补 EX-011+）
- CloudTech 假阳性 106 → 估算 0
- 总 drift 1849 → 估算 **< 50** ✅

### 实施成本
- 改 `policy/model-policy.v1.yaml` 加 6 条 EX
- 重算 `model-policy.v1.sha256`
- 写 `audit/policy-changes.log` 一行变更记录（含 evidence + user approval）
- 等用户批 EXT-A 之后单独立 R 编号 (建议 R1342)

---

## 提案 EXT-B: Adapter 加 probe 探活 + healthz

### 目的
4 个 adapter 现状只能 `validate(model, provider)` 做事前检查。生产运维希望加一个**只读探活方法**，让 Reconciler 可以远程询问 adapter "你这条 chain 还活吗"。

### 接口草图

```python
# 新增公共方法（在 4 adapter 中各加一个）
def healthz(*, request_id: str) -> dict[str, Any]:
    """只读探活。

    Returns:
        {
            "ok": bool,
            "reason": str,           # 不 ok 时填
            "model_default": str,    # 当前 default model id (只读)
            "provider_default": str, # 当前 default provider
            "ts": float,             # unix epoch
        }
    """
```

### 4 adapter 应各加的探活内容

| Adapter | 健康判定 |
|---|---|
| codex | `~/.codex/config.toml` 当前 active profile · 含 `minimax-m3` → ok |
| claude_code | `claude_code_runtime.py` 配置路径存在 · 含 MiniMax key → ok |
| hermes | hermes daemon PID 活跃 (1-min tick scheduler 仍跑) |
| openclaw | `~/.openclaw/gateway.yaml` 存在 · 9 agents 中 ≥8 配置 minimax → ok |

### Reconciler 端要新增调用
- 每次全扫时 ping 4 adapter `healthz` (1 次 / adapter)
- 4 个 ok 才认为 "chain healthy"
- 任一 fail → 写 alerts.jsonl (L3 告警)
- 与现有 L1/L2 drift 区分

### 实施成本
- 改 4 个 adapter runtime.py (5 → ~7 KB each)
- 改 reconciler.py 加 healthz 调用
- 加 4 adapter 探活的回归 test
- 等用户批 EXT-B 后单独立 R 编号 (建议 R1343)

---

## 提案 EXT-C: Reconciler 加 drift 溯源 hash 链

### 目的
当前 alerts.jsonl 每个 drift 是独立的 JSON object，难以做"重复告警抑制"和"复活根因溯源"。建议给每条 drift 加：
- `prev_drift_sha256`: 同一 path 的上一条 drift sha256
- `first_seen_ts`: 第一次出现该 path 的 drift 时间戳
- `recurrence_count`: 该 path 累计出现次数

### 预期效果
- 可写抑制规则: 同一 path + 同一 keyword 24h 内出现 ≥3 次 → 升级告警
- 可写溯源规则: 同一 path 的 first_seen_ts 与 `audit/policy-changes.log` 对齐 → 找根因
- 1849 条告警中可识别"沉睡死灰"vs"新出现"

### 实施成本
- 改 reconciler.py 加 hash 链 + 索引
- 改 `audit/drift-events.log` 写入结构（向后兼容）
- 加 regression test
- 等用户批 EXT-C 后单独立 R 编号 (建议 R1344)

---

## 提案 EXT-D: 跨 adapter 共享 default 模型 registry

### 目的
当前 4 adapter 各自维护 default_model 字符串。建议把 `MiniMax-M3` 提到 SSOT，让 Reconciler 检测"哪个 adapter 的 default 漂离了 SSOT"。

### SSOT 设计
- `policy/model-policy.v1.yaml` 现已含 `model_policy.default_model: MiniMax-M3`
- 4 adapter 加载时**只能从 policy 读 default**，不能在代码里硬编码
- 检测：启动 Reconciler 时拉一次 policy，巡检 4 adapter 的 default 字符串与 policy 一致性
- 不一致 → L3 告警

### 实施成本
- 改 4 adapter runtime 移除硬编码 default
- 改 `__init__.py::load_all_adapters()` 校验 default 来自 policy
- 加 regression test
- 等用户批 EXT-D 后单独立 R 编号 (建议 R1345)

---

## 提案 EXT-E: CloudTech scan target 加 v2+v3 兼容层

### 目的
当前 CloudTech 扫描范围 `D:/CloudTech-Portable`，EXCLUDED_PATH_TAGS 是手工清单。建议改成"自动识别 + 用户白名单"组合：
- 任何 `data/` 子目录默认 EXCLUDE（CloudTech 设计上 data 是历史快照，不是 active 路径）
- 任何 `*.py` 在 `src/` 或根目录 → INCLUDE（active 代码路径）
- 任何 `*.json` 在 `config/` → INCLUDE（active 配置）

### 实施成本
- 改 reconciler.py 加 dynamic-prefix-based discovery
- 加白名单配置文件（可在 policy/ 落)
- 等用户批 EXT-E 后单独立 R 编号 (建议 R1346)

---

## 优先级建议

| 提案 | 影响 | 工作量 | 优先级 | 建议 R |
|---|---|---|---|---|
| **EXT-A** (EX-005~010) | 高（消除 1800+ 假阳性） | 低（只改 policy YAML） | **P0** | R1342 |
| **EXT-B** (healthz) | 中（生产可观测性） | 中 | P1 | R1343 |
| **EXT-C** (drift hash 链) | 中（告警抑制 + 溯源） | 中 | P1 | R1344 |
| **EXT-D** (shared default) | 低 | 中 | P2 | R1345 |
| **EXT-E** (CloudTech 兼容) | 低 | 中 | P2 | R1346 |

---

## 不在本提案范围（拒绝扩展）

- ❌ 改 policy v2 schema / field 顺序
- ❌ 改 adapter `validate()` 签名（已统一，破坏 = 破坏 4 adapter 全部）
- ❌ 加新 provider（policy 锁定 MiniMax only）
- ❌ 改 Reconciler 持久化后端（继续用 JSONL + 文件锁，不引入 SQLite）
- ❌ 把 Reconciler 改为 Windows Service（保持 scheduled task + on-demand 调用）

---

## 等用户回复

请批 EXT-A / EXT-B / EXT-C / EXT-D / EXT-E 中的一个或多个（或者全部拒绝，让我先把现有 8/14 未复核维度跑完）。

按 R1339 acceptance, EXT-A 实施的前提是用户授权 "policy EX-005~010 添加"。

---

_— Codex (supervisor) · T3 扩展提案 · 5 项候选 + 优先级 + 估计工作量 · 等用户批 R 编号 · 2026-10-09_