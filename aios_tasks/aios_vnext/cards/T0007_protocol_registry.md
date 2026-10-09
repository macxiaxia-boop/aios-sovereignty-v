---
id: T0007
title: Protocol Registry 单条更新（shared-identity-agents）
owner: CC
priority: P1
track: 1 — AIOS 治理
preconditions: [T0002]
estimated_minutes: 20
depends_on: [T0002]
blocks: [T0010]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

10-03 log §P1-PROTOCOL-REGISTRY 提到：中央 hash = `6FD99...CF14`，registry 仍为 `27901fc...`/2052 B/旧 evidence。

1. **读 registry 当前内容**
   `D:\AIOS\aios_tools\state\protocol_registry.json`（如不存在则找 _agent-hub 或同级）

2. **备份**
   `Copy-Item protocol_registry.json D:\AIOS\_backups\task-t0007-registry-<ts>.json`

3. **更新 1 条** `shared-identity-agents`：
   - hash: 改为 `6FD99...CF14`（与中央 SSOT 一致）
   - size: 与新 hash 实际匹配
   - evidence: 引用 Baseline 冻结时间
   - 其他字段保持不变

4. **校验**：
   - 改后 hash 与中央 SSOT 哈希一致
   - 改后 size 与文件实际字节一致
   - JSON 合法
   - 其他 entry 全部不变

## Out-of-scope (不要做)
- ❌ 不要删 registry 中其他 entry
- ❌ 不要新增 entry（仅 update 1 条）
- ❌ 不要改 _agent-hub 中央 SSOT（那是 Codex 的工作）
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs
- T0002 Baseline 冻结后的 evidence（含中央 hash）
- `protocol_registry.json` 当前内容
- 10-03 log §P1-PROTOCOL-REGISTRY

## Outputs
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0007_<ts>.md`
2. 修改后 `protocol_registry.json`
3. 备份（路径已列）
4. diff 输出

## Evidence Requirements
- [ ] v1 备份存在
- [ ] diff 仅含 `shared-identity-agents` 1 条
- [ ] 改后 hash = 中央 SSOT `6FD99...CF14`
- [ ] 改后 size 与实际字节匹配
- [ ] JSON 合法（`python -m json.tool` 不报错）
- [ ] 其他 entry byte-for-byte 不变
- [ ] 硬链接（如有）仍成立

## Exit Criteria
1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex

## Time Budget
20 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. 读 v1 backup 与 v2 比对
2. diff 行 ≤ 5
3. 验证 hash
4. 验证 size
5. 验证 JSON 合法
全部通过 → status=Verified。