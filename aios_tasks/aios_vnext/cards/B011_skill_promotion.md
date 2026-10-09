---
id: B011
title: Skill promotion pipeline (T0009 5 candidates → register)
owner: Codex + CC
priority: P0
track: 4 — VNext Phase B (Context)
preconditions: [B006]
estimated_minutes: 90
depends_on: [B006]
blocks: [B012]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. **E001-E004 promote**: 写入 `D:\AIOS\aios_kernel\skills\` (4 files):
   - `skill/preflight_anti_protocol_explosion.md`
   - `skill/codex_supervisor_pattern.md`
   - `skill/simulation_harness_100task.md`
   - `skill/5_element_evidence_pattern.md`
   每个含: frontmatter (id, version, title, description, promoted_at), body (使用示例 + 测试方法 + 来源 evidence link)
3. **E005 self-referential archive**: 写入 `D:\AIOS\aios_kernel\skills\_archived\E005_aios_evolution_log.md` + 解释为何不 promote 到 registry
4. **更新 Skill Registry** (B006 unified registry):
   - v5 Skill registry + 5 新 entry (4 promote + 1 archive_ref)
5. **测试**: 5 entry 全部 present, E001-E004 verified, E005 archived

## Forbidden
- ❌ 不准重复 promote (1 candidate → 1 entry)
- ❌ 不准触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Evidence Requirements
- [ ] 4 skill files 在 `D:\AIOS\aios_kernel\skills\`
- [ ] 1 archive file 在 `_archived/`
- [ ] Skill Registry v5 包含 5 entries
- [ ] pytest test_skill_registry.py 全 PASS
- [ ] preflight CLEAN

## Exit Criteria
1. evidence 全勾
2. pytest exit 0
3. status=Submitted

## Time Budget
90 分钟
