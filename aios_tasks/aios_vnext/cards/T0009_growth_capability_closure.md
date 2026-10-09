---
id: T0009
title: Growth/Capability Closure 一条真实素材贯通
owner: CC + 用户
priority: P1
track: 1 — AIOS 治理
preconditions: [用户提供素材]
estimated_minutes: 60
depends_on: []
blocks: [T0010]
status: Pending
created: 2026-10-08
codex_supervisor_signoff_required: true
needs_user_input: true
---

## Scope (要做)

10-03 log §P1-GROWTH-CAPABILITY-CLOSURE：日报 0、成长日志 1、六类 JSONL 缺失、能力 usage 0/31。本卡做 1 条真实素材贯通：让 growth → Paul-Elder → learning → reflection → decision → evolution → capability reuse 跑通一次。

1. **用户提供 1 条真实业务素材**：
   - 用户在第一次回复时已隐含给出（10-08 粘贴的两份文档 + 选择 D1-D5）
   - 用户**必须确认**这条素材为本卡使用（不能默认）
   - 如果用户说"这条 + 之前的回复是素材" → 使用
   - 如果用户说"用 X 替代" → 使用 X

2. **CC 跑完整流程**（用真实素材作为输入）：

   a. **growth 记录**：素材触发 growth 路径
   b. **Paul-Elder 提问**：基于素材生成 5 个批判性问题（要素 / 目的 / 假设 / 观点 / 后果）
   c. **learning log**：记录提问答案
   d. **reflection JSONL**：由 reflection 触发
   e. **decision JSONL**：基于 reflection 形成决策
   f. **evolution JSONL**：决策转化为 skill 升级候选
   g. **capability reuse**：候选 skill 被某能力引用，含 `re_evidence_id` 回指素材

3. **真实素材要求**：
   - 至少 1 个真实 source（业务产物 / 代码 / 文件）
   - 至少 1 个 timestamp
   - 至少 1 个关联 ID
   - 至少 1 个 `re_evidence_id` 回指

4. **失败处理**：
   - 空输入必须 NO_DATA（不是 fake PASS）
   - 任一步缺 source/timestamp/ID → FAIL
   - `re_evidence_id` 缺失 → FAIL

## Out-of-scope (不要做)
- ❌ 不要用 LLM 假造素材
- ❌ 不要用历史 placeholder
- ❌ 不要写日报（那是 daily memory 的事）
- ❌ 不要触碰 `D:\AIOS\aios_tasks\aios_vnext\*`（除 evidence）

## Inputs
- 用户提供真实素材（首次回复已隐含："这是我的构思你想想该怎么帮我落地" / "你帮我搭建一个任务待办清单" / 等等）
- 10-03 log §P1-GROWTH-CAPABILITY-CLOSURE

## Outputs
1. `D:\AIOS\aios_tasks\aios_vnext\evidence\T0009_<ts>.md`
2. 7 个 JSONL 文件增量（按 evidence/ 内子目录存放）
3. capability reuse 引用文件

## Evidence Requirements
- [ ] 用户明确确认素材使用范围
- [ ] 7 个 JSONL 全部含 source + timestamp + 关联 ID
- [ ] 至少 1 个 `re_evidence_id` 真实回指
- [ ] 没有 fake PASS
- [ ] 没有 LLM 假造数据
- [ ] 没有重复 T0009 记录（唯一性）

## Exit Criteria
1. evidence 全部勾选
2. 用户确认贯通
4. CC 把 status=Submitted 后等 Codex

## Time Budget
60 分钟

## Codex Acceptance Gate
Codex 独立验证:
1. 抽样 5 个 JSONL 行
2. 验证 `re_evidence_id` 真实回指
3. 验证素材与业务对应
全部通过 → status=Verified。

## 用户需要回复

> "T0009 素材用 [你之前已给的素材 X] + [新的真实素材 Y]"
>
> 或 "T0009 用之前 AIOS VNext 全部对话作为素材"