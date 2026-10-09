---
id: B007
title: WorkBuddy native AGENTS.md (governance gap fix)
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
1. **读中央 SSOT**: `D:\AIOS\_agent-hub\AGENTS.md` (SHA256=`6FD99AAAAADE4F5D5FAC97AF154AA84E77D550C9BDB6CD438CD98648FF6CF14` 等)
2. **写 WorkBuddy native**: `C:\Users\xinzh\.workbuddy\AGENTS.md`
   - 内容 = 中央 SSOT 内容 + WorkBuddy-specific 启动器注释
   - 显式 "delegates to central SSOT at D:\AIOS\_agent-hub\AGENTS.md" header
3. **验证**:
   - 文件存在
   - sha256 = 中央 SSOT 一致 (硬链接则自动一致; 非硬链接则拷贝并 verify hash)
   - 内容含 "delegates to"
4. **更新 Protocol Registry** (`T0007` 已有范式): shared-identity-workbuddy 添加 entry

## Forbidden
- ❌ 不准改中央 SSOT (D:\AIOS\_agent-hub\AGENTS.md)
- ❌ 不准建 protocol_*.md
- ❌ 不准触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Evidence Requirements
- [ ] `C:\Users\xinzh\.workbuddy\AGENTS.md` 存在
- [ ] 内容 hash = 中央 SSOT (硬链接自动 OR 拷贝并 verify)
- [ ] 内容含 "delegates to central SSOT"
- [ ] Protocol Registry updated

## Exit Criteria
1. evidence 全勾
2. status=Verified ✅ (Codex 自验)

## Time Budget
30 分钟
