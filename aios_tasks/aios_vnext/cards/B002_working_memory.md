---
id: B002
title: Working Memory layer（短时 session 状态）
owner: CC
priority: P0
track: 4 — VNext Phase B (Context)
preconditions: [B001]
estimated_minutes: 90
depends_on: [B001]
blocks: [B010]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. Pydantic: `WorkingMemoryEntry` (key, value JSON, session_id, created_at, expires_at)
2. SQLAlchemy ORM: `working_memory` 表 + 索引 (session_id, key)
3. Repository service: `WorkingMemoryService.put(key, value, ttl=24h)` / `get(key)` / `list_keys(session_id)` / `clear_session(session_id)`
4. PG checkpointer 集成: kernel 重启从 working_memory 持久层恢复
5. 单元测试 + 集成测试 (5 case: put/get/expire/session_isolation/restart_recovery)

## 路径
- `D:\AIOS\kernel\src\aios_kernel\context\working_memory.py`
- `D:\AIOS\kernel\src\aios_kernel\persistence\` (新增 models)
- `D:\AIOS\kernel\tests\integration\test_working_memory.py`

## Out-of-scope
- ❌ Long-term Memory (B003)
- ❌ Context Compiler (B004)
- ❌ RAG / vector store (B005)
- ❌ Skill Registry (B006)
- ❌ 改 T0030-T0040 已 Verified 的 schema/adapter
- ❌ 触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）
- ❌ 触碰 `D:\AIOS\kernel\tests\sim\*`（T0040 已完成）

## Forbidden
- ❌ 不准创建 protocol_*.md / version_*.md / handoff_*.md / _r*.py / 顶层 .md

## Evidence Requirements
- [ ] 100 WorkingMemoryEntry 写入 + 重启 Kernel + 全部读出
- [ ] Session isolation (session A 不可见 session B)
- [ ] Expire 机制 (24h TTL)
- [ ] pytest tests/unit + tests/integration 全 PASS
- [ ] preflight CLEAN

## Exit Criteria
1. evidence 全勾
2. pytest exit 0
3. status=Submitted

## Time Budget
90 分钟
