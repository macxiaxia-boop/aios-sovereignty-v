---
id: B003
title: Long-term Memory layer（持久知识归档）
owner: CC
priority: P0
track: 4 — VNext Phase B (Context)
preconditions: [B001]
estimated_minutes: 120
depends_on: [B001]
blocks: [B004, B010]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. Pydantic: `LongTermEntry` (key, value JSON, created_at, retention_days>=30, tags[], source_evidence_id Optional[UUID4])
2. SQLAlchemy ORM: `long_term_memory` 表 + 索引 (key, created_at, tags JSONB)
3. Repository service: `LongTermMemoryService.put(key, value, retention_days=30, tags, source_evidence_id)` / `get(key)` / `query(tags, before, after)` / `delete(key)`
4. **Retention policy**: 强制 retention_days >= 30, 不允许 silent delete (需要 explicit delete 调用 + 权限记录)
5. Back-link: source_evidence_id 指向 T0009 等已 Verified 卡的 evidence, 形成 capability reuse 闭环
6. 集成测试 (5 case: put/get/query_by_tag/retention_protection/source_link)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\context\long_term_memory.py`
- `D:\AIOS\kernel\src\aios_kernel\persistence\` (新增 models)
- `D:\AIOS\kernel\tests\integration\test_long_term_memory.py`

## Out-of-scope
- ❌ Working Memory (B002)
- ❌ Context Compiler (B004)
- ❌ RAG / vector store (B005)
- ❌ 触碰 T0030-T0040 已 Verified 内容
- ❌ 触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Forbidden
- ❌ 不准创建 protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md
- ❌ 不准 silent delete (必须 explicit delete + audit log)

## Evidence Requirements
- [ ] 100 entry 写入 + created_at = 30 days ago, query 后 100/100 仍可检索
- [ ] retention_days < 30 写入 → 自动 reject (验证: 30-day policy)
- [ ] source_evidence_id back-link 到 T0009 evidence (5 re_evidence_id 验证)
- [ ] pytest 全 PASS

## Exit Criteria
1. evidence 全勾
2. pytest exit 0
3. status=Submitted

## Time Budget
120 分钟
