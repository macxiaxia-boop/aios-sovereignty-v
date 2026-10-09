---
id: T0010
title: Track 0/1 综合验收（Codex 独立签字）
owner: Codex
priority: P0
track: 0+1 收口
preconditions: [T0001, T0002, T0003, T0004, T0005, T0006, T0007, T0008, T0009]
estimated_minutes: 60
depends_on: [T0001, T0002, T0003, T0004, T0005, T0006, T0007, T0008, T0009]
blocks: [T0030]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: false
---

## Scope (要做)

Codex 独立签字 Track 0/1 通过。

1. **收集所有 Track 0/1 evidence**：
   - T0001 → CC 路由探针
   - T0002 → Baseline 冻结
   - T0003 → 夜间 cron 修复
   - T0004 → Restic lock 修复
   - T0005 → R176/R153 SSOT 设计
   - T0006 → Sampling dual-backend
   - T0007 → Protocol Registry 更新
   - T0008 → Five-Agent handshake
   - T0009 → Growth/Capability 贯通

2. **独立重跑关键验证**（Codex 在 fresh 视角）：
   - CC 探针（类似 T0001）
   - Restic snapshot 列表
   - schtasks 输出（确认 T0003 修复）
   - Protocol Registry hash
   - 5 Agent handshake（如可能）

4. **Track 0/1 最终报告** `D:\AIOS\_agent-hub\reports\aios_vnext_track01_done_<ts>.md`：
   - 9 张卡状态汇总（Verified/Failed）
   - 关键证据引用
   - 已知遗留（如 WorkBuddy native AGENTS 缺失）
   - 进入 Track 2 (Phase 0 Audit) 的签字

5. **签字条件**：
   - 9 张卡全 Verified 或经用户签字豁免
   - 报告落到正确位置

## Out-of-scope (不要做)
- ❌ 不要修改任何 Track 0/1 产出
- ❌ 不要跑 Track 2/3/4 工作（这是签字关）
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence + 报告）

## Inputs
- T0001–T0009 全部 evidence

## Outputs (Codex 必须产出)
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0010_<ts>.md`
2. `D:\AIOS\_agent-hub\reports\aios_vnext_track01_done_<ts>.md`

## Evidence Requirements
- [ ] 9 张卡 status 检查
- [ ] 独立重跑 4 项关键检查
- [ ] 报告 5 段全在
- [ ] Codex supervisor sign
- [ ] 不动任何 Track 0/1 产出

## Exit Criteria
1. evidence 全部勾选
2. 报告落位置
3. Codex 自签 → Verified

## Time Budget
60 分钟

## Codex Acceptance Gate
本卡是 Codex 自签，无需 CC 验。
Verified 后：
- INDEX.md 更新 Track 0/1 状态 = DONE
- 用户可授权 CC 启动 Track 2（T0020 Phase 0 Audit）