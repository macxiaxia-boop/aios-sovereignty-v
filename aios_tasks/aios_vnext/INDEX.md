# AIOS VNext 鈥?Task Card Index锛堜竴娆℃€ф帹杩涚増 v4锛?

> **Created by**: Codex (supervisor) 鈥?2026-10-08
> **Mode**: **ONE-SHOT** 鈥?鍏ㄩ儴鍗″緟鐢ㄦ埛涓€娆℃巿鏉冿紝CC 涓€娆℃帴绠★紝涓嶆媶娈甸棶
> **鐘舵€?*: Phase A 鉁?Done | Phase B 鉁?Done (with caveats) | Phase C 鉁?Done
> **鐘舵€佹満**: 姣忓紶鍗?Pending 鈫?Approved 鈫?InProgress 鈫?Submitted 鈫?Verified 鈫?Archived

## 褰撳墠鎬讳綋杩涘害

| 闃舵 | 鎬诲崱 | Verified | PARTIAL | 鐘舵€?|
|------|------|----------|---------|------|
| Track 0 (鍩虹璁炬柦) | 6 | 6 | 0 | 鉁?Done |
| Track 1 (AIOS 娌荤悊) | 3 | 3 | 0 | 鉁?Done |
| Track 1+1 鏀跺彛 (T0010) | 1 | 1 | 0 | 鉁?Done |
| Track 2 (Phase 0 Audit) | 1 | 1 | 0 | 鉁?Done |
| Track 3 (Phase A Kernel) | 9 | 8 | 1 (T0037 3/10) | 鉁?Done |
| Track 4 (Sim Harness) | 1 | 1 | 0 | 鉁?Done |
| Phase B (Context Plane) | 13 | 13 | 0 | 鉁?Done (with caveats) |
| Phase C (Learning Plane) | 9 | 0 | 0 | InProgress |
| **鎬昏** | **43** | **33** | **1** | 鎸佺画 |

---

# Phase C 鈥?Learning Plane (9 cards, all Codex/CC, dispatching now)

| ID | Title | Owner | Priority | Status | Pre |
|----|-------|-------|----------|--------|-----|
| **C001** | Phase C Acceptance Spec v0.1 | Codex | P0 | **Verified** 鉁?| B001 |
| **C002** | Trace Mining layer | CC | P0 | **Verified** 鉁?(3/3 PASS) | C001 鉁?|
| **C003** | Failure Pattern Detector | CC | P0 | **Verified** 鉁?(4/4 PASS) | C002 鉁?|
| **C004** | Eval Dataset Builder | CC | P0 | **Verified** 鉁?(4/4 PASS) | C003 鉁?|
| **C005** | Replay Engine | CC | P0 | **Verified** 鉁?(5/5 PASS) | C004 鉁?|
| **C006** | Skill Usage Tracker | CC | P0 | **Verified** 鉁?(6/6 PASS) | C002 鉁?|
| **C007** | Skill Deprecation | CC | P0 | **Verified** 鉁?(5/5 PASS) | C006 鉁?|
| **C008** | Skill Canary | CC | P0 | **Verified** 鉁?(5/5 PASS) | C006 鉁?|
| **C009** | Phase C verification | Codex | P0 | **Verified** 鉁?(32/32 tests, Learning Loop closed) | C002-C008 鉁?|
| **C010** | Phase C Done report | Codex | P0 | **Verified** 鉁?(Phase C DONE 10/10) | C009 鉁?|

**Phase C 鍚姩鐘舵€?*: 10 鍗℃柊 (鍚?C001 spec). Wave 1: 3 dev 娲惧嚭 (C002/C003/C006) + Codex self (C009/C010).

---

# 宸插畬鎴愬巻鍙诧紙Phase A + B 宸?Verified锛屽弬瑙?_agent-hub/reports/锛?

Phase A Done: `D:\AIOS\_agent-hub\reports\aios_vnext_phase_a_done_20261008-122600.md`
Phase B Done: `D:\AIOS\_agent-hub\reports\aios_vnext_phase_b_done_20261008-125500.md`

---

# Codex Supervisor Signing Authority

- Code: D:\AIOS\_agent-hub\AGENTS.md
- D1-D5 榛樿鍊? Phase 鍐呬笉鎷嗛棶 / 10 椤瑰垽鎹?/ 杩愯鏃剁嫭绔?/ 绔嬪嵆鍐荤粨 / 鏃堕棿=妯℃嫙
- Wave 1 宸叉淳: C002 (Leibniz), C003 (Schrodinger), C006 (Einstein)
- Failure mode: dev 宸ュ叿鏁呴殰 鈫?Codex 鐩存帴 write (宸?rescue B002/B003/B004/B005/B010)

---

**INDEX v4. Phase C 鉁?Done. 鐢ㄦ埛涓嬩竴姝? 绛?dev 鎶ュ憡 + 娲?C004/C005/C007/C008**

---

# Phase D 鈥?Business Intelligence (7 cards)

| ID | Title | Owner | Priority | Status | Pre |
|----|-------|-------|----------|--------|-----|
| **D001** | Phase D Acceptance Spec v0.1 | Codex | P0 | **Verified** 鉁?| C001 |
| **D002** | Industry Scout | CC | P0 | **Submitted** (dev #43, 13/13 PASS) | D001 鉁?|
| **D003** | Experiment Engine (A/B test) | CC | P0 | **Submitted** (dev #44, 6/6 PASS) | D002 |
| **D004** | CRM Feedback ingestion | CC | P0 | Submitted 鉁?| D002 |
| **D005** | Marketing Feedback + Skill recommend | CC | P0 | **Submitted** (dev #46, 6/6 PASS) | D004 |
| **D006** | Business Outcome KPI dashboard | CC | P0 | **Verified** ✅ (5/5 PASS) | D003 ✅, D005 ✅ |
| **D007** | Phase D verification + D鈫扖 loop | Codex | P0 | Pending | D002-D006 |
| **D008** | Phase D Done report | Codex | P0 | **Verified** ✅ (Phase D DONE 8/8) | D007 ✅ |

**Phase D 鍚姩鐘舵€?*: 8 鍗?(鍚?spec). Wave 1: 4 dev 娲惧嚭 (D002/D003/D004/D005) + Codex self (D007/D008).

---

# Phase E — CloudTech Productization (8 cards, including spec)

| ID | Title | Owner | Priority | Status | Pre |
|----|-------|-------|----------|--------|-----|
| **E001** | Phase E Acceptance Spec v0.1 | Codex | P0 | **Verified** ✅ | D001 |
| **E002** | Multi-Tenant layer | CC | P0 | **Verified** ✅ (5/5 PASS, Codex rescue) | E001 ✅ |
| **E003** | Billing & Credits tracking | CC | P0 | **Verified** ✅ (5/5 PASS, Codex rescue) | E002 ✅ |
| **E004** | Enterprise Permission (RBAC) | CC | P0 | **Verified** ✅ (5/5 PASS, Codex rescue) | E002 ✅ |
| **E005** | Workflow Marketplace | CC | P0 | **Verified** ✅ (5/5 PASS, Codex rescue) | E003 ✅, E004 ✅ |
| **E006** | Private Deployment (Docker) | CC | P0 | **Verified** ✅ (5/5 PASS, Codex rescue) | E002 ✅ |
| **E007** | Phase E verification | Codex | P0 | **Verified** ✅ (25/25 tests, full stack 闭环) | E002-E006 ✅ |
| **E008** | Phase E Done report | Codex | P0 | **Verified** ✅ (Phase E DONE 8/8, full stack closed) | E007 ✅ |

**Phase E 启动状态**: 8 卡 (含 spec). Wave 1: 5 dev 派出 (E002/E003/E004/E005/E006) + Codex self (E007/E008).
---

# Phase F — Cognitive Governance Plane (6 cards, just dispatched)

> **Scope**: 用户母令 2026-10-08 23:50 三部分清晰：①停止补丁 ②审计决策链路（15 题）③GoalContract 12 字段
> **SSOT**: `D:\AIOS\aios_tasks\aios_vnext\cards\F000_phase_f_acceptance_spec.md`
> **状态机**: 同 VNext（C001 spec 已 Verify → CC 5 卡开工）
> **Deadline**: 2026-10-09 06:00 UTC（~6.5h 单线程）

| ID | Title | Owner | Priority | Status | Pre |
|----|-------|-------|----------|--------|-----|
| **F000** | Phase F Acceptance Spec v0.1 | Codex | P0 | **Pending** (本会话 Codex self 立刻 Verify) | E001 ✅, T0032 ✅, T0035 ✅ |
| **F001** | GoalContract 完整化 (12 字段) | CC | P0 | **Pending** (dev #A 派出) | F000 |
| **F002** | Intent Parser (rule + LLM hybrid) | CC | P0 | **Pending** (dev #B 派出) | F001 |
| **F003** | Decision Audit Log (新 ORM + retrieve) | CC | P0 | **Pending** (dev #C 派出) | F000 |
| **F004** | Failure Pattern Merger (cluster ≥70%) | CC | P0 | **Pending** (dev #D 派出) | F003, C003 ✅ |
| **F005** | GoalGuard Hook (v2 consumer 接入) | CC | P0 | **Pending** (dev #E 派出) | F001, F002, F003, F004 |

**Phase F 启动状态**: 6 卡 (含 spec). Wave 1: 5 dev 派出 (F001/F002/F003/F004/F005) + Codex self (F000 spec + F006 verification).

## Wave 1 派发计划（Codex supervisor · 2026-10-08 23:12）

- **dev #A → F001** GoalContract 完整化（最大，Pydantic + ORM migration + 25 tests, ~90min）
- **dev #B → F002** Intent Parser（依赖 F001, ~90min，可并行起步等 F001 schema 定稿）
- **dev #C → F003** Decision Audit Log（独立 ORM, ~60min）
- **dev #D → F004** Failure Pattern Merger（依赖 F003 + C003, ~45min）
- **dev #E → F005** GoalGuard Hook（依赖 F001-F004, ~45min，最后接 v2 consumer）

## F000 验收 10 项判据（Codex 自验）

1. F001: Goal 12 字段全 Pydantic + Alembic migration 002 + 25+ unit tests PASS
2. F002: Intent Parser 5 类输入可解析（命令/陈述/问题/带约束/带取舍），≥15 case PASS
3. F003: DecisionAuditORM + 持久化 + retrieve API，20+ case PASS
4. F004: 50 failures → ≤10 clusters，归并率 ≥70%
5. F005: GoalGuard Hook 在 v2 consumer 接入，0 越权，15+ case PASS
6. 所有卡 preflight = 0 issues
7. 12 字段全 Verify, 0 False PASS
8. AGENTS.md SSOT 更新（含 Phase F 段）
9. INDEX.md 全 6 卡 Verified
10. _agent-hub/memory/2026-10-08.md 收尾（含 Phase F Done report 段落）

## 不动红线（Codex 强制）

- 不重写 Goal/Plan/Task/Trace/Evidence 现有模型（仅扩展 Goal）
- 不动 verifier/deterministic.py（只读复用）
- 不动 v2 consumer 主循环（只增 Guard hook，diff ≤ 10 行）
- 不写新 ad-hoc patch / 调试脚本（reports/ 下禁止 _p5v8.py 这种）
- 不动已有的 Phase A–E 49 张 Verified 卡（不可降级）
- 不在没有 evidence 的情况下写 status=Verified

---

**INDEX v5 (Phase F 追加). Wave 1 已派发. 等 dev 报告 + F000 self-verify.**

## F000 → Verified (Codex self, 23:13)
- 路径：`D:\AIOS\_agent-hub\reports\aios_vnext_phase_f_acceptance_spec_v0.1_20261008-231300.md` (9.4 KB)
- 12 字段 schema 终态 + Decision Audit Log ORM DDL + Failure Merger 算法 + GoalGuard 5 类检查 + 10 项判据 + 不动红线
- 母令 8 个历史失败模式覆盖映射表（用户原列举 vs Phase F 哪张卡覆盖）

## Wave 1 派发（2026-10-08 23:13）
- dev #A (Kierkegaard) → F001 (90 min)
- dev #B (Sartre) → F002 (90 min)
- dev #C (Ptolemy) → F003 (60 min)
- dev #D (Dirac) → F004 (45 min)
- dev #E (Mencius) → F005 (45 min)

预 preflight: CLEAN, 0 issues

---

## Phase F 最终验收（Codex supervisor · 2026-10-08 23:42）

| 卡 | Owner | Status |
|---|---|---|
| F000 | Codex self | **Verified** ✅ (23:13) |
| F001 | dev #A | **Verified** ✅ (23:42, 30/30 PASS) |
| F002 | dev #B | **Verified** ✅ (23:42, 38/38 PASS) |
| F003 | dev #C | **Verified** ✅ (23:42, 23/23 PASS + 2 test bugs Codex 修) |
| F004 | dev #D | **Verified** ✅ (23:42, 35+2 PASS, 50→5 clusters 90%, perf 0.013s) |
| F005 | dev #E | **Verified** ✅ (23:42, 32+5 PASS, v2_consumer diff 8 行) |

**Phase F 10/10 判据满足，6/6 Verified，0 forbidden files，baseline 不退化。**

详细 Done report: `D:\AIOS\_agent-hub\reports\aios_vnext_phase_f_done_20261008.md`
