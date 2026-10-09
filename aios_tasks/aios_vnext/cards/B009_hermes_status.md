---
id: B009
title: Hermes Agent status 文档化
owner: Codex (self)
priority: P1
track: 4 — VNext Phase B (Context)
preconditions: [B001]
estimated_minutes: 20
depends_on: [B001]
blocks: [B012]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: false
---

## Scope (要做)
1. **探测 Hermes 路径**:
   - `D:\AIOS\hermes\` (不存在 per T0008)
   - `C:\Users\xinzh\.hermes\` (存在但仅是 Restic source, 非 agent)
   - `D:\AIOS\aios_tools\hermes*` (no match)
2. **判断**: Hermes Agent **未安装** (Not Found) — 已由 T0008 确认
3. **文档化**: `D:\AIOS\_agent-hub\reports\hermes_status_<ts>.md` 含:
   - 探测路径
   - 探测时间
   - 探测方法
   - 结论: NOT_INSTALLED
   - 推荐: Phase C/D 接入路径

## Forbidden
- ❌ 不准安装 Hermes (本卡仅文档化)
- ❌ 不准触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Exit Criteria
1. evidence 全勾
2. status=Verified ✅

## Time Budget
20 分钟
