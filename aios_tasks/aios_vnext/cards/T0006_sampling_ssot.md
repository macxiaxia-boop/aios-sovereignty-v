---
id: T0006
title: Sampling dual-backend SSOT 实施
owner: CC
priority: P1
track: 0 — Production Health
preconditions: [T0005]
estimated_minutes: 30
depends_on: [T0005]
blocks: [T0010]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
基于 T0005 设计稿，做 **最小化实施**（仅采样脚本侧，禁动 backup）：

1. **找到采样脚本**（10-03 log §P0-R176-SAMPLING-SSOT）：
   - 位于 `D:\个人文件\AI\Operator\aios_tools\_aios_backup_sampling_v1.py`（10-03 已引用）
   - 读全文

2. **加显式后端选择**：
   - 函数 `select_backend(sample_request) -> Literal["legacy", "restic"]`
   - 强制每个 sample 必须选 1 个，禁止跨后端
   - 跨后端 sample_request → 显式 fail

3. **失败路径处理**：
   - 旧 manifest 退役路径（如 `D:\AIOS\dr_v3.0_uncompressed_workspace`）→ 标 `RETIRED` 后端
   - 任何指向退役路径的 sample → FAIL + 警告

4. **小样本 dry-run**：
   - sample_size = 10（不跑 100，避免误报）
   - `--dry-run` flag：列出将采样的路径，不实际验证
   - 必须默认显式 backend

5. **测试**：
   - 跨后端 sample → 期望 fail
   - 退役路径 sample → 期望 fail
   - 正常 restic 路径 sample → 期望 pass

## Out-of-scope (不要做)
- ❌ 不要修改 backup 健康检查脚本（那是 T0004 后 T0042 health freshness 的）
- ❌ 不要跑全量 sampling
- ❌ 不要修改 R176 manifest
- ❌ 不要修改 R152/R153
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs
- T0005 设计稿
- `D:\个人文件\AI\Operator\aios_tools\_aios_backup_sampling_v1.py`
- 10-03 log §P0-R176-SAMPLING-SSOT

## Outputs
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0006_<ts>.md`
2. `_aios_backup_sampling_v2.py`（备份 v1，改 v2）
4. 跨后端 + 退役路径的 test 报告

## Evidence Requirements
- [ ] v1 backup 存在
- [ ] `select_backend()` 函数实现
- [ ] 跨后端 sample → fail
- [ ] 退役路径 sample → fail
- [ ] dry-run flag 可用
- [ ] 3 个测试 case pass
- [ ] v1 backup 仍在

## Exit Criteria
1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex

## Time Budget
30 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. 读 v2 源码，确认 `select_backend()` 实现
2. 跑 3 个测试
3. 验证 v1 备份存在
全部通过 → status=Verified。