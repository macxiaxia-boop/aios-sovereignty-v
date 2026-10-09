---
id: B006
title: Skill Registry Consolidation (5 versions → 1 canonical)
owner: CC
priority: P0
track: 4 — VNext Phase B (Context)
preconditions: [B001]
estimated_minutes: 90
depends_on: [B001]
blocks: [B011]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. **现状调研**: 读 5 个版本 `_aios_capability_registry_v{2,3,4,43,5}.py`
2. **选 canonical = v5** (latest, most complete)
3. **Migration script** `D:\个人文件\AI\Operator\aios_tools\consolidate_capability_registry.py`:
   - Read entries of v2/v3/v4/v43 (parse pickle/json)
   - Merge into v5 registry (conflict: latest wins)
   - Rename old v2/v3/v4/v43 to `.deprecated`
   - Write `consolidation_report_<ts>.json` (per-source count, conflicts, final v5 count)
4. **v5 update**: 指向新合并的注册表 (backwards compat alias)
6. **测试**: 5 source entries 全数 present in v5 (无丢失), 无 duplicates

## Forbidden
- ❌ 删 _aios_capability_registry_v5.py (它是 canonical)
- ❌ 触碰 D:\AIOS\aios_tasks\aios_vnext\*（除 evidence）

## Evidence Requirements
- [ ] 5 source 全部读出 (v2/v3/v4/v43/v5)
- [ ] v5 registry 含所有合并 entry (无丢失, 无 duplicates)
- [ ] Old v2/v3/v4/v43 marked .deprecated (不删, 保留可读)
- [ ] consolidation_report JSON 合法
- [ ] preflight CLEAN

## Exit Criteria
1. evidence 全勾
2. status=Submitted

## Time Budget
90 分钟
