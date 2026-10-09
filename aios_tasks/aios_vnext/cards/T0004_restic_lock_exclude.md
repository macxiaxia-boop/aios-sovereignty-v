---
id: T0004
title: Restic lock 精确排除 + 增量验证
owner: CC
priority: P0
track: 0 — Production Health
preconditions: [T0001]
estimated_minutes: 45
depends_on: [T0001]
blocks: [T0005]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. **备份入口**（必须先做）
   - `Copy-Item D:\Tools\restic\run-backup.cmd D:\AIOS\_backups\task-t0004-run-backup-<ts>.cmd`

2. **精确排除仅 .aios_daemon_watchdog.lock**:
   - 读 `run-backup.cmd` 当前 exclude 段
   - **不允许**排除整个 `state` 目录
   - 仅精确添加/调整 `.aios_daemon_watchdog.lock`（单个文件路径）
   - 如已有类似精确排除：保持，仅补缺失
   - 不改源路径、不改目标、不改其他 exclude

3. **执行一次同源增量**:
   - 调用 `run-backup.cmd`
   - 等待完成（最长 30 分钟）
   - **不允许**全量备份（必须增量）
   - **不允许**修改 schtasks

4. **验证**:
   - 新 snapshot 已生成
   - 0 errors（log 里 grep `error` 行数 = 0）
   - `EXIT_CODE=0`
   - 既有源 paths 不减少（与 9-30 快照对比 source path 列表）

5. **记录**:
   - 修改前后 cmd diff
   - 本次运行 log 全文或末尾 100 行
   - snapshot 列表对比
   - source path 列表对比

## Out-of-scope (不要做)
- ❌ 不要排除整个 `D:\AIOS\aios_tools\state` 目录
- ❌ 不要新增其他 exclude
- ❌ 不要修改 schtasks
- ❌ 不要跑全量备份
- ❌ 不要动 source 路径集合
- ❌ 不要动 Restic repo 配置
- ❌ 不要覆盖 R172/R176 manifest
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs (CC 必须先读)
- `D:\Tools\restic\run-backup.cmd`（入口）
- `D:\Tools\restic\logs\backup-20260930-150848.log`（10-03 提到的最后成功 log）
- `D:\AIOS\_agent-hub\memory\2026-10-03.md`（§P0-BACKUP-LOCK 段）
- `D:\AIOS\aios_tools\state\*.lock`（确认存在哪些 lock 文件）
- 9-30 snapshot manifest（用于路径对比）

## Outputs (CC 必须产出)
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0004_<ts>.md`
2. `T0004_cmd_diff.txt`（修改前后 diff）
3. `T0004_run_log_tail.txt`（本次运行 log 末尾 100 行）
4. `T0004_snapshot_compare.json`：
   ```json
   {
     "old_snapshot_id": "06ecf159",
     "new_snapshot_id": "<新>",
     "new_snapshot_time": "<iso>",
     "exit_code": 0,
     "error_count": <int>,
     "source_paths_added": [],
     "source_paths_removed": [],
     "excluded_lock_files": [".<path>"]
   }
   ```

## Evidence Requirements (Codex 验收看的)
- [ ] `run-backup.cmd` 备份存在
- [ ] cmd diff **仅**精确调整 `.aios_daemon_watchdog.lock`（不超过 5 行）
- [ ] **没有**新增整个 state 目录排除
- [ ] 本次运行 EXIT_CODE=0
- [ ] 新 snapshot id ≠ 9-30 的 `06ecf159`
- [ ] 新 snapshot 列表含本次
- [ ] log 中 `error` 段（除"错误文件跳过"的最后一行）= 0
- [ ] 既有源 paths 数量不减少（可允许 +少量）
- [ ] 备份可还原（`restic snapshots` 看到新条目 + size > 0）

## Exit Criteria (CC 算做完)
1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex

## Rollback (失败怎么回)
1. 恢复 `run-backup.cmd` 修改前副本（`D:\AIOS\_backups\task-t0004-run-backup-<ts>.cmd`）
2. 新 snapshot 保留（不删除）
3. 写 rollback log

## Time Budget
45 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. `diff backup-cmd-mod vs backup-cmd-orig | wc -l` ≤ 5 行
2. `restic snapshots` 看到新 snapshot
3. 调 `restic check`（如可能） 验证 repo 完整性
4. 读 evidence 与源码比对
全部通过 → status=Verified。