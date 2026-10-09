# R1342-R1346 Extensions Implementation · 2026-10-09

> **作者**: Codex (supervisor)
> **范围**: EXT-A (R1342) 实修 · EXT-B/C/D/E (R1343-R1346) 提案 → 实施需独立授权
> **验收**: drift_count 实测 1849 → 217 (88% 下降)

---

## R1342 · EXT-A · 加 6 条 EX-005~010 · ✅ DONE

### 实施
- 改 `policy/model-policy.v1.yaml` 加 6 条 EX rules
- **EX-001~004 不动** ✅ (符合 "不动 policy v2 EX-001~004" 红线)
- 重算 sha256 · 同步 sha256 manifest
- append `audit/policy-changes.log`

### sha256 变化
| 项 | Before | After |
|---|---|---|
| sha256 | `BAF3D091AFC946C35AD53720FE5E4340893DA1BC49D93FD9E29553A14BFF3B27` | `01EF74360580617EE07E7C81F72265BDE074CF331D0BC71EA4246CB3D87FB92F` |
| size_bytes | 4641 | 7811 |
| EX count | 4 | 10 |
| default_model | `MiniMax-M3` | `MiniMax-M3` (unchanged) |
| verification_status | active | active (unchanged) |

### 实测效果（drift-events.log 最新 4 条）
```
ts=07:30:44  drift=1938  exception_globs=8   profile_count=976  (改前)
ts=07:37:17  drift=427   exception_globs=8   profile_count=321  (中间过渡)
ts=07:41:03  drift=269   exception_globs=8   profile_count=187
ts=07:43:07  drift=217   exception_globs=26  profile_count=175  (改后)
```

**drift 下降**: 1938 → 217 = **88.8% reduction** ✅
**exceptions**: 8 → 26 (4 EX rules + 6 new EX rules, total 26 path_globs)

### 新增 EX 详情
- **EX-005** · Codex `.codex-global-state.json` (chat 历史)
- **EX-006** · Codex `aios-*.py` helper 脚本
- **EX-007** · Codex `attachments/*` + `computer-use/*` (用户粘贴/屏幕镜像)
- **EX-008** · Codex `backups/*` + `_backup-*/**` (auth.backup.* 补 EX-004 漏洞)
- **EX-009** · CloudTech `data/openapi_snapshots/*` + `data/v*_candidates/*` + `data/morning_briefing/**` + `data/skill_orchestrator/*` (W14.1 verified CloudTech active = MiniMax only)
- **EX-010** · Codex `run-bridge.py` 安全 stub (含 deepseek 字符串仅作 deny pattern)

### 状态
- ✅ DONE · 1849 假阳性降 88%
- **剩余 217 条假阳性** 仍偏高, 建议下轮 Round 6 加 EX-011~015 (Codex `*~history*.json`, `codex-flags.json`, `_chat_history/*` 等更深层 Codex UI 状态)

---

## R1343 · EXT-B · 4 adapter 加 `healthz()` 探活 · ⏳ DEFERRED

### 状态
- 提案已在 T3 (`policy/reconciler-adapter-extensions.md`)
- **未实施** — 改 4 个 adapter runtime.py 各加 ~30 行
- 工作量: 2h
- **不在本会话实施** (Q2 范围太大, 优先级 EXT-A > EXT-B)

### 提案接口
```python
def healthz(*, request_id: str) -> dict:
    """只读探活。Returns: ok, reason, model_default, provider_default, ts"""
```

### 等用户授权后实施
- 改 4 个 adapter 各加 healthz()
- 改 reconciler.py 全扫时 ping 4 adapter
- 加 regression test

---

## R1344 · EXT-C · drift hash 链 + recurrence_count · ⏳ DEFERRED

### 状态
- 提案已在 T3
- **未实施**
- 工作量: 2h

### 提案
- drift event 加 `prev_drift_sha256` + `first_seen_ts` + `recurrence_count`
- 支持重复告警规则: `recurrence_count ≥ 3 in 24h → L3 升级`
- 支持溯源: `first_seen_ts` 对齐 `policy-changes.log`

---

## R1345 · EXT-D · 4 adapter 共享 default model registry · ⏳ DEFERRED

### 状态
- 提案已在 T3
- **未实施** — 涉及 4 adapter 硬编码 default_model 移除, 改从 policy 读
- 工作量: 2h

---

## R1346 · EXT-E · CloudTech scan dynamic prefix discovery · ⏳ DEFERRED

### 状态
- 提案已在 T3
- **未实施** — 加 dynamic prefix discovery (`data/` 默认 EXCLUDE, `src/` `config/` INCLUDE)
- 工作量: 2h

---

## 验收总览

| EXT | 提案 | 实施 | 状态 |
|---|---|---|---|
| EXT-A (R1342) | EX-005~010 | ✅ 完成 | drift 1849 → 217 (-88%) |
| EXT-B (R1343) | healthz() | ⏳ 提案 | deferred |
| EXT-C (R1344) | hash 链 | ⏳ 提案 | deferred |
| EXT-D (R1345) | shared registry | ⏳ 提案 | deferred |
| EXT-E (R1346) | dynamic prefix | ⏳ 提案 | deferred |

**总实施工作量**: 1 EXT (~30 min) / 5 EXT (8h 提案总) · 本会话完成 1/5

---

## 等用户回复

1. 批 R1343 / R1344 / R1345 / R1346 任意组合 (建议从 R1343 healthz 开始, 生产可观测性最高)
2. 加 R1347 = EXT-F: 加 EX-011~015 进一步降剩余 217 假阳性

---

_— Codex (supervisor) · EXT-A 完成 + EXT-B~E 提案 defer · 等用户批 R1343~1347 · 2026-10-09_