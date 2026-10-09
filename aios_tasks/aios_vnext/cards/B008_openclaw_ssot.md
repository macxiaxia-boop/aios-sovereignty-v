---
id: B008
title: OpenClaw SSOT link (governance gap fix)
owner: Codex (self)
priority: P0
track: 4 — VNext Phase B (Context)
preconditions: [B001]
estimated_minutes: 30
depends_on: [B001]
blocks: [B012]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: false
---

## Scope (要做)
1. **读现有 OpenClaw**: `C:\Users\xinzh\.openclaw\CLAUDE.md` (518 B 当前)
2. **添加 SSOT delegate header**: 文件顶部加
   ```
   <!-- delegates to central SSOT: D:\AIOS\_agent-hub\AGENTS.md -->
   <!-- SHA256: 6FD99AAAAADE4F5D5FAC97AF154AA84E77D550C9BDB6CD438CD98648FF6CF14 -->
   ```
3. **保留** 现有 Moon Capsule L0 CLAUDE.md 内容
4. **验证**: 文件含 "delegates to"
5. **更新 Protocol Registry** (T0007 范式): shared-identity-openclaw 添加 entry

## Forbidden
- ❌ 不准删现有 CLAUDE.md 内容
- ❌ 不准改中央 SSOT
- ❌ 不准触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Evidence Requirements
- [ ] 文件含 "delegates to" header
- [ ] 现有 L0 内容保留
- [ ] hash 一致

## Exit Criteria
1. evidence 全勾
2. status=Verified ✅

## Time Budget
30 分钟
