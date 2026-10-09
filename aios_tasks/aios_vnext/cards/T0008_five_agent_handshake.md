---
id: T0008
title: Five-Agent handshake 验证
owner: CC
priority: P1
track: 1 — AIOS 治理
preconditions: [T0001]
estimated_minutes: 40
depends_on: [T0001]
blocks: [T0010]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
---

## Scope (要做)

10-03 log §P1-FIVE-AGENT-HANDSHAKE：CC/WorkBuddy/Hermes 无 hash 回执，WorkBuddy native AGENTS 缺失。本卡做 handshake 验证。

1. **5 个 Agent 各自只读回报**（不修改任何服务）：
   - Codex（`C:\Users\xinzh\.codex\`）
   - Claude Code（`C:\Users\xinzh\.claude\`）
   - WorkBuddy（`C:\Users\xinzh\.agents\` + `~/.workbuddy\`）
   - Hermes（如有，找 `D:\AIOS\hermes*` 或类似）
   - OpenClaw（如有，找 `D:\.openclaw\` 或 `~/.openclaw\`）

2. **每个 Agent 必须回报**：
   - 中央 AGENT SSHA hash（来自 `D:\AIOS\AGENTS.md`）
   - 当日 memory log 文件 hash（`D:\AIOS\_agent-hub\memory\2026-10-08.md`）
   - 入口路径（agent 启动时读的 AGENTS.md 路径）

3. **一次只测一个通道**——避免多 agent 并发改服务

4. **报告**：
   - 5 个 Agent × 2 个 hash = 10 个回执
   - 期望：5 对全部相同（同一中央 SSOT + 同一当日日志）
   - 超时/无回执 → FAIL

5. **WorkBuddy 特殊处理**：
   - WorkBuddy 可能没有 native AGENTS.md
   - 如缺失：记录为 `MISSING_NATIVE_AGENTS` 状态 + 报告（这是 10-03 已知的，不要私自补 native AGENTS）

## Out-of-scope (不要做)
- ❌ 不要修改任何 agent 的 native AGENTS.md
- ❌ 不要补 WorkBuddy native AGENTS（那是用户决策）
- ❌ 不要做 handshake 双向（先做单向回执）
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs
- T0001 CC 路由修复通过（保证 CC 也能回执）
- T0002 Baseline 冻结后的当日 memory 日志
- 10-03 log §P1-FIVE-AGENT-HANDSHAKE

## Outputs
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0008_<ts>.md`
2. `T0008_handshake_report.json`：
   ```json
   {
     "central_agents_md_hash": "<sha>",
     "daily_memory_hash": "<sha>",
     "agents": {
       "codex": {"status": "OK|MISSING|FAIL", "agents_md_hash": "<sha>", "daily_hash": "<sha>", "entry_path": "<path>"},
       "claude_code": {...},
       "workbuddy": {...},
       "hermes": {...},
       "openclaw": {...}
     }
   }
   ```

## Evidence Requirements
- [ ] 5 个 Agent 全部尝试 handshake
- [ ] 每个 Agent 报告 2 个 hash + 入口路径
- [ ] 5 个 Agent hash 一致（与中央 SSOT + 当日 memory）
- [ ] 超时/无回执显式标 FAIL
- [ ] WorkBuddy native AGENTS 缺失（如有）显式记录
- [ ] 没有触发任何 agent 修改配置

## Exit Criteria
1. evidence 全部勾选
2. CC 把 status=Submitted 后等 Codex

## Time Budget
40 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. 读 handshake report
2. 抽样 3 个 Agent 验证 hash
3. 验证 WorkBuddy MISSING 标记
全部通过 → status=Verified。