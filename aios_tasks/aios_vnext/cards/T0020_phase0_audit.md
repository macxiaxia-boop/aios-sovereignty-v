---
id: T0020
title: Phase 0 Spec-vs-Reality 报告（Codex 主做）
owner: Codex（主）+ CC 辅助统计
priority: P0
track: 2 — VNext Audit
preconditions: [T0002]
estimated_minutes: 90
depends_on: [T0002]
blocks: [T0030]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: false
---

## Scope (要做)

按 VNext Master Spec §98–100 + §104 产出 7 节报告。

**Owner**: **Codex（主）**——读阶段 Codex 比 CC 稳。CC 仅做"列 schtasks + 列 _r* 脚本大小分布"等纯统计辅助。

**输出**: `D:\AIOS\_agent-hub\reports\aios_vnext_phase0_spec_vs_reality_<ts>.md`

**报告 7 节**：

### §1. Current Reality 12 问（按 Spec §99）
1. 当前真正运行什么？
2. 谁调用谁？
3. 哪些只是文档？
4. 哪些已经废弃？
5. 哪些重复？
6. 哪些冲突？
7. 状态源在哪里？
8. 谁负责完成判定？
9. 任务为什么会停止？
10. 上下文为什么会丢？
11. 哪里产生重复劳动？
12. 哪些模块值得保留？

每问 = 现状证据路径+行号 / UNKNOWN / N/A

### §2. Spec Coverage Matrix
规格 106 节 → 现行 Reality 哪个能对应 / 哪个不存在 / 哪个冲突
表格：spec_section | reality_file | evidence | status (MATCH/PARTIAL/MISSING/CONFLICT)

### §3. Component Inventory
按 Spec §98 要求的 27 类组件 × 现行文件存在性 × 是否运行 × 是否被监控
表格：component_type | existing_files | runtime | monitored

### §4. Conflict Map
3 个内在冲突 + 我提议的解读，等用户拍
- 冲突 1: 完整执行 vs 内部分阶段
- 冲突 2: §28 vs §104 (Phase A 完成判据缺失)
- 冲突 3: §97.9 vs §101 ("独立"语义)

### §5. Phase A Acceptance Spec v0.1
含上面 10 项判据 + 测试方法 + 通过线
（实际产出于 T0030——本节给出占位指向）

### §6. Phase A 前置清单
- CC executor 修复 (T0001)
- Baseline 冻结 (T0002)
- Phase A 10 项判据定稿 (T0030)

### §7. Baseline 冻结方案
- git tag: `AIOS_VNEXT_BASELINE_v0`
- Restic snapshot: T0002 产出
- 回滚步骤
- 时点

## Out-of-scope (不要做)
- ❌ 不要修改任何现有 AIOS 文件
- ❌ 不要写 Phase A 代码
- ❌ 不要碰任何 schtasks / settings / Restic 入口
- ❌ 不要写 memory 日志（Codex daily work）

## Outputs
1. `D:\AIOS\_agent-hub\reports\aios_vnext_phase0_spec_vs_reality_<ts>.md`
2. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0020_<ts>.md`（Codex 自签）

## Evidence Requirements
- [ ] §1 12 问全有
- [ ] §2 Matrix 行数 ≥ 30（spec 节数）
- [ ] §3 Inventory 行数 ≥ 27
- [ ] §4 Conflict 3 个全有
- [ ] §5 占位指向 T0030
- [ ] §6 前置 3 项全列
- [ ] §7 Baseline 4 项全有
- [ ] 报告 ≥ 200 行

## Exit Criteria
1. evidence 全部勾选
2. 报告落位置
3. Codex 自签 → Verified

## Time Budget
90 分钟

## Codex Acceptance Gate
本卡是 Codex 自签。Verified 后：
- INDEX.md 更新 Track 2 状态 = DONE
- T0030 启动条件满足