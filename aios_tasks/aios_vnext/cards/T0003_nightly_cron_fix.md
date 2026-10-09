---
id: T0003
title: 夜间 cron stale=42 + Argument 修复
owner: CC
priority: P0
track: 0 — Executor Unblock
preconditions: [T0001]
estimated_minutes: 50
depends_on: [T0001]
blocks: [T0031]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. **导出当前任务 XML**（备份）
   - `schtasks /query /xml /tn "\AIOS_Overnight_Daily_Continue" > D:\AIOS\_backups\task-t0003-schtask-Overnight-<ts>.xml`
   - 同样对其他类似命名任务（10-03 log 提到的 + schtasks 输出中的）

2. **定位 stale 处理**:
   - 读 `D:\demo\start-cc-current.ps1`（10-03 log §P0-NIGHT-STALE-42）
   - 找 missing/stale 输出与 exit 42 分支
   - **仅修**这一段：让 missing/stale 显式输出 `STALE_HANDOFF` 并 exit 42

3. **修 Argument 错位**:
   - 对每个相关的夜间任务：
     - `Arguments` 必须是完整 `-File "D:\demo\start-cc-current.ps1"`
     - `WorkingDirectory` 必须是 `D:\demo`
   - 不改 `Task To Run` 的脚本入口
   - 不改 `Schedule`

4. **触发 stale 拒绝测试（仅一次）**:
   - 手动用过期 handoff 调 `start-cc-current.ps1`，验证返回 `STALE_HANDOFF` + exit 42
   - 不启动 CC 业务
   - 不动现有其他 worktree
   - 不写 Git

5. **记录所有改动**:
   - 修改前 XML → 修改后 XML diff
   - launcher diff（仅 stale 分支）
   - 测试日志

## Out-of-scope (不要做)
- ❌ 不要改 CC 业务启动部分（仅 stale 分支）
- ❌ 不要跑真实业务
- ❌ 不要写 Git（不动 worktree）
- ❌ 不要启动 CC 进程（仅触发 stale 拒绝）
- ❌ 不要覆盖任何 backup
- ❌ 不要碰 OpenClaw 9-agent 调度
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs (CC 必须先读)
- `D:\AIOS\_agent-hub\memory\2026-10-03.md`（§P0-NIGHT-STALE-42 + §P0-NIGHT-ACTION 段）
- `D:\demo\start-cc-current.ps1`
- `schtasks /query /fo LIST /v` 完整结果（已附在 10-03 验收中）
- 现有相关 schtasks XML

## Outputs (CC 必须产出)
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0003_<ts>.md`
2. `T0003_xml_diff_<n>.txt`（每个修改任务的 XML diff）
3. `T0003_launcher_diff.txt`（start-cc-current.ps1 stale 分支 diff）
4. `T0003_stale_test_output.txt`（stale 拒绝测试 stdout/stderr）
5. 备份 XML（路径已列）

## Evidence Requirements (Codex 验收看的)
- [ ] 每个修改任务的 XML 备份存在
- [ ] Arguments 字段完整包含 `-File "D:\demo\start-cc-current.ps1"`
- [ ] WorkingDirectory = `D:\demo`
- [ ] Schedule / Trigger / 其他字段未变
- [ ] launcher diff 仅在 stale 分支，**无业务逻辑改动**
- [ ] 触发 stale 拒绝测试 exit=42（`0x2A` 或文字 `STALE_HANDOFF`）
- [ ] **无新 CC 进程被启动**（`tasklist` 验证）
- [ ] **无新日志**（CC log mtime < T0003 开始时间）
- [ ] **无 Git 写入**（worktree status 不变)
- [ ] backup 文件存在且可读

## Exit Criteria (CC 算做完)
1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex

## Rollback (失败怎么回)
1. `schtasks /delete /tn "\<name>" /f` 然后 `/xml` 重导
2. 或导入操作前 XML（备份路径已列）
3. launcher 改回原样
5. 写 rollback log

## Time Budget
50 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. `schtasks /query /xml /tn "\AIOS_Overnight_Daily_Continue"` 与备份 diff = 仅 Arguments+WorkingDirectory
2. `schtasks /query /fo LIST /v` 看到修复后的 Arguments
3. `tasklist` 当前没有新 CC 进程
4. launcher 文件与 baseline 的 git diff 仅在 stale 分支
5. 手动测试 stale 拒绝路径（Codex 自己跑一次）
全部通过 → status=Verified。