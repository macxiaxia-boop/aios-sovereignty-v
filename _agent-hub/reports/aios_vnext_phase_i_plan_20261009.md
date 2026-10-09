# AIOS Phase I · Sovereignty-V Full Execution Plan

> **Phase**: I (Full Execution of All Remaining Work · 紧接 Phase G + H)
> **开始**: 2026-10-09T09:38+08:00
> **监督**: 01a11c30 (Codex supervisor)
> **工程线程**: 01a11c33 (sovereignty-v)
> **用户授权**: "搭建执行任务，全部做掉" (2026-10-09)

---

## T16-T30 任务清单

| T 卡 | 标题 | 执行者 | 工作量 | 红线 |
|---|---|---|---|---|
| T16 | 修 codex_runtime.py self-test 旧用例（2 个 M2.7 用例 → M3 或删除） | Codex 直接 | 2 行 | 不改 validate() |
| T17 | 修 test_21 cosmetic (Reconciler stdout 断言) | Codex 直接 | 5 行 | 不改 Reconciler 行为 |
| T18 | 验收 父线程 strategy_policy.py + acceptance 测试 | Codex supervisor | 8 测试 | 不修改文件本身 |
| T19 | 验收 父线程 strategy_gate.py + acceptance 测试 | Codex supervisor | 6 测试 | 同上 |
| T20 | 验收 父线程 requirements_lifecycle.py + acceptance 测试 | Codex supervisor | 8 测试 | 同上 |
| T21 | 验收 父线程 contamination_scanner.py + acceptance 测试 | Codex supervisor | 8 测试 | 同上 |
| T22 | 验收 父线程 quarantine.py + acceptance 测试 | Codex supervisor | 6 测试 | 同上 |
| T23 | Codex PreToolUse hook 实际注册到 hooks.json | CC 写 | 1 文件 | 不动其它 adapter |
| T24 | OpenClaw cron payload validate() 集成 | CC 写 | 1 文件 | 同上 |
| T25 | Hermes daemon 化（CLI 一次性 → 持久 service） | CC 写 | 2 文件 | 不动 validate() |
| T26 | Adapter auto-load script (启动时统一加载) | CC 写 | 1 文件 | 不改 policy |
| T27 | Sovereignty-V runbook / 维护 SOP | CC 写 | 1 文件 | 不改任何代码 |
| T28 | 全套回归最终 PASS (含新增 30+ acceptance) | Codex 直接 | 5 行 | 0 fail 目标 |
| T29 | Phase I done report | Codex 直接 | 30 KB | 含全部 T*.done 引用 |
| T30 | memory 通知 + 工程线程 close-out + git status | Codex 直接 | 5 文件 | 不动 SSOT |

---

## 执行时序

### Phase I.1 — 立即修正（Codex supervisor，~5 min）
T16 → T17

### Phase I.2 — 父线程产物验收（Codex supervisor，~30 min）
T18 → T19 → T20 → T21 → T22

### Phase I.3 — Hook 集成 + Daemon（CC dispatch，~30 min）
T23 → T24 → T25 → T26 → T27

### Phase I.4 — 最终回归 + 关闭（Codex supervisor，~10 min）
T28 → T29 → T30

---

## 验收标准

- 所有 T 卡 done 落盘 (`tasks/T{16..30}.done`)
- 全部 regression 0 FAIL (含新增 ~36 项 acceptance)
- Reconciler 跑通 + 持续
- Phase I done report 含全部证据

---

## 风险

- 父线程产物可能与 sovereignty-v 红线冲突 · T18-T22 验收会暴露
- Hermes daemon 化涉及 OS service · 需 user 授权 (per SSOT requires_authorization)
- Codex hook 注册若影响现有 workflow · 需 user 拍板

---

_— Codex supervisor 01a11c30 · 2026-10-09T09:38+08:00 · Phase I 开局_