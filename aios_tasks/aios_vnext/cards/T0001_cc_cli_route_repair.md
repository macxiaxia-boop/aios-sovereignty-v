---
id: T0001
title: CC direct CLI 路由修复
owner: CC
priority: P0
track: 0 — Executor Unblock
preconditions: []
estimated_minutes: 30
depends_on: []
blocks: [T0003, T0004, T0005, T0008, T0036, ...]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)
1. **只读探针**: 不修改任何文件，先用进程级、非持久化的环境变量（不要写到 `~/.claude/settings.json`）启动 CC direct CLI 探针：
   ```bash
   ANTHROPIC_MODEL="MiniMax-M3" ANTHROPIC_BASE_URL="<gateway>" claude --print "return the word 'OK'"
   ```
   - 目标: 30 秒内返回字符串 `OK`
   - 连续 2 次通过即视为探针成功

2. **读取 `C:\Users\xinzh\.claude\settings.json` 当前配置**（只读，备份到 `D:\AIOS\_backups\task-t0001-claude-settings-<ts>.json`）

3. **定位模型路由冲突点**: 检查以下文件中的 `model` 字段映射
   - `C:\Users\xinzh\.claude\settings.json`
   - `C:\Users\xinzh\.claude\settings.local.json`（如存在）
   - `D:\demo\start-cc-current.ps1`（launcher 脚本）
   - `~/.workbuddy/A2-path-launcher.sh`（共享 launcher）
   - 注意是 `MiniMax-M3` 还是别的 model id

4. **最小修改（仅在 1. 探针成功后）**:
   - 备份原文件
   - 在 `~/.claude/settings.json` 中加一行 `"ANTHROPIC_DEFAULT_MODEL": "<可用的 MiniMax-M3 gateway>"` 或修复显式 model 字段
   - **禁止删除**任何字段，**禁止改 aios-interop / playwright / MCP 列表**，**禁止动 token**

5. **回归验证**:
   - 用 direct CLI 重跑探针命令（不依赖 aios-interop）
   - 用 aios-interop 启动 CC 跑一个真实只读文件摘要（用 `D:\AIOS\AGENTS.md`）
   - 两次都通过

## Out-of-scope (不要做)
- ❌ 不要触碰 `C:\Users\xinzh\.codex\config.toml`（Codex 配置与本卡无关）
- ❌ 不要改 MCP server 列表
- ❌ 不要碰 GitHub MCP token
- ❌ 不要删任何 backup 文件
- ❌ 不要启动 WorkBuddy 改 launcher
- ❌ 不要碰 `D:\AIOS\aios_tasks\aios_vnext\*`
- ❌ 不要在 aios-interop 里测试 5+ 个工具调用（探针 = 1 次）
- ❌ 不要重写 launcher 脚本——只动 settings.json

## Inputs (CC 必须先读)
- `D:\AIOS\_agent-hub\memory\2026-10-03.md`（§P0-CC-CLI-ROUTE 段）
- `C:\Users\xinzh\.claude\settings.json`
- `D:\demo\start-cc-current.ps1`（10-03 提到的启动脚本）
- 任何 Agent 的 `.workbuddy\A2-path-launcher.sh`（如存在）
- `~/.workbuddy/secrets/github-token`（仅 cat，确认权限，仅确认不解码）

## Outputs (CC 必须产出)
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0001_<ts>.md`（CC workflow §格式，含 7 段）
2. 探针 stdout/stderr log（写到 `D:\AIOS\aios_tasks\aios_vnext\evidence\T0001_probe.log`）
3. `settings.json` 备份（路径已列在 §Scope 4.）
5. 修改后 `settings.json` 副本（如做了修改）
6. 风险/疑问清单（如有）

## Evidence Requirements (Codex 验收看的)
- [ ] 探针 1 30 秒内返回 `OK`，exit 0
- [ ] 探针 2（30 秒后）仍 `OK`，exit 0
- [ ] aios-interop 启动 CC 后能完成 1 次只读文件摘要（不报错 `unrecognized_model`）
- [ ] `settings.json` 修改前/后 diff（≤ 5 行，仅 model/gateway 字段）
- [ ] 未触碰 aios-interop/playwright/MCP 列表（grep 验证：原行 = 改后行）
- [ ] 未触碰 GitHub token 文件
- [ ] backup 文件存在且可读
- [ ] exit 0 + 20 秒内（仅 aios-interop 调用）

## Exit Criteria (CC 算做完)
1. evidence 全部勾选
2. evidence 文件落到正确位置
3. CC 把 status=Submitted 后等 Codex

## Rollback (失败怎么回)
1. 恢复 `settings.json` 修改前副本（路径：`D:\AIOS\_backups\task-t0001-claude-settings-<ts>.json`）
2. 清除临时进程环境变量（`ANTHROPIC_MODEL`、`ANTHROPIC_BASE_URL`）
3. MCP 配置保持原样
5. 写 `rollback_done_<ts>.log` 到 evidence 目录

## Time Budget
30 分钟（超出 = Submitted + 风险报告，不擅自延）

## Codex Acceptance Gate
Codex 独立重跑 3 个 evidence 步骤（探针 1 + 探针 2 + aios-interop 调用），全部通过 → status=Verified。
任何一项失败 → status=Failed + 阻塞 T0003、T0005、T0008、T0036。