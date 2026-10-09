---
id: T0002
title: AIOS_VNEXT_BASELINE_v0 双后端冻结
owner: CC
priority: P0
track: 0 — Executor Unblock
preconditions: []
estimated_minutes: 20
depends_on: []
blocks: [T0007, T0020]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. **Git Baseline 冻结**（如 D:\AIOS 是 git repo）
   - `cd D:\AIOS`
   - `git status`（必须 clean 才能 tag）
   - 如果不干净: `git stash push -m "vnext-baseline-prep-<ts>"` 然后 `git status` 再确认
   - `git tag -a AIOS_VNEXT_BASELINE_v0 -m "AIOS VNext baseline frozen at 2026-10-08, before Phase 0 audit"`
   - `git rev-parse AIOS_VNEXT_BASELINE_v0` 拿到 SHA，写入 evidence

2. **Restic Snapshot Baseline 冻结**（强制）
   - 读取 `D:\Tools\restic\run-backup.cmd`（确认源覆盖与锁定文件处理策略）
   - 如果存在 `D:\Tools\restic\run-backup.cmd.lock` 或 `.disabled`：不要运行，先报告 Codex
   - 执行前**精确排除**仅 `.aios_daemon_watchdog.lock`，**禁止**排除整个 state 目录
   - 执行：手动调用入口 `D:\Tools\restic\run-backup.cmd`，或运行一次 `restic -r E:\移动硬盘\00_电脑备份\restic-repo backup --tag AIOS_VNEXT_BASELINE_v0 --tag pre-frozen [optional backup-dir]`
   - 目标: 新 snapshot、0 errors、`EXIT_CODE=0`、既有源 paths 不减少
   - 等待完成后 `restic -r E:\移动硬盘\00_电脑备份\restic-repo snapshots --tag AIOS_VNEXT_BASELINE_v0` 拿到 snapshot id，写入 evidence

3. **Backup 元数据记录**
   - snapshot id
   - SHA
   - 时间
   - source paths 列表
   - 排除的 lock 文件清单（精确到路径）
   - 全部写入 evidence

## Out-of-scope (不要做)
- ❌ 不要修改 `run-backup.cmd`（T0004 才动）
- ❌ 不要覆盖任何 `D:\AIOS\aios_tools\state\*` 下文件
- ❌ 不要修改 schtasks
- ❌ 不要运行 R176/R153（保持 Disabled）
- ❌ 不要跑全量备份（必须增量）
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）
- ❌ 不要动 OpenClaw / Codex / WorkBuddy 任何配置
- ❌ 不要尝试解决 10-03 log 提到的任何 P0/P1（仅冻结，不修复）

## Inputs (CC 必须先读)
- `D:\AIOS\AGENTS.md`（中央 SSOT 确认）
- `D:\AIOS\_agent-hub\memory\2026-10-03.md`（§P0-BACKUP-LOCK 段了解 lock 问题）
- `D:\Tools\restic\run-backup.cmd`
- `D:\Tools\restic\logs\` 最新 log（确认上次成功时间）

## Outputs (CC 必须产出)
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0002_<ts>.md`
2. `T0002_git_tag_output.txt`（git tag + rev-parse 输出）
3. `T0002_restic_snapshot_output.txt`（restic snapshots 输出）
4. `T0002_restic_backup_log_tail.txt`（本次运行 log 末尾 50 行）
5. `T0002_baseline_manifest.json`：
   ```json
   {
     "git_tag": "AIOS_VNEXT_BASELINE_v0",
     "git_sha": "<sha>",
     "restic_snapshot_id": "<id>",
     "restic_snapshot_time": "<iso>",
     "excluded_lock_files": ["<exact paths>"],
     "source_path_count": <int>,
     "exit_code": 0
   }
   ```

## Evidence Requirements (Codex 验收看的)
- [ ] `git tag -l` 输出含 `AIOS_VNEXT_BASELINE_v0`
- [ ] `git rev-parse AIOS_VNEXT_BASELINE_v0` 返回非空 SHA
- [ ] `git show AIOS_VNEXT_BASELINE_v0 --stat` 不报错
- [ ] restic snapshot 列表含新 snapshot
- [ ] new snapshot 时间在 10-08 09:00 之后
- [ ] 既有 source paths 数量不减少（bcron log 关键 files 都在）
- [ ] `run-backup.cmd` 未修改（diff vs original = 0）
- [ ] schtasks XML 未变（`schtasks /query /xml` 与 Baseline 等同）
- [ ] evidence 文件 5 项全部在位
- [ ] exit 0

## Exit Criteria (CC 算做完)
1. evidence 全部勾选
2. manifest JSON 合法
3. CC 把 status=Submitted 后等 Codex

## Rollback (失败怎么回)
1. `git tag -d AIOS_VNEXT_BASELINE_v0`（删除未发布 tag）
2. restic snapshot 保留（不删除，不可逆；下次 GC 时会收走）
3. 不动 `run-backup.cmd`
4. 写 `rollback_<ts>.log`

## Time Budget
20 分钟（超出 = Submitted + 风险报告）

## Codex Acceptance Gate
Codex 独立跑：
1. `git tag -l | grep AIOS_VNEXT_BASELINE_v0`
2. `git rev-parse AIOS_VNEXT_BASELINE_v0`（验证 SHA 与 evidence 一致）
3. `restic snapshots --tag AIOS_VNEXT_BASELINE_v0`（验证 snapshot）
4. 比较 evidence `T0002_baseline_manifest.json` 与实际值
5. `schtasks /query /fo LIST /v > /tmp/schtasks_now.txt` 与 Baseline 比 diff = 0
全部通过 → status=Verified。