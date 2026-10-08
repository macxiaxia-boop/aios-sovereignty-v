# Codex Session Bootstrap — 你醒来第一件事

> **何时读**: Codex session 启动**之前** (codex --prof codex 触发)，或任意时刻手动跑：
> ```bash
> python D:\AIOS\_agent-hub\scripts\codex_self_audit.py
> ```

## 0. 不要等我说话。先跑 self-audit。

我（用户）可能在睡觉、出外忙、忘记回话。任何 Codex session 启动后，**第一件事不是问我要做什么**，而是：

1. 读 `D:\AIOS\_agent-hub\AGENTS.md`（中央 SSOT，强制）
2. 读 `D:\AIOS\_agent-hub\memory\<今天日期>.md` 和 `<昨天>.md`（共享 memory）
3. **跑 self-audit**：
   ```bash
   python D:\AIOS\_agent-hub\scripts\codex_self_audit.py
   ```
4. self-audit 会自动写 `## <时间> Codex Self-Audit` 段落到当天 memory
5. 如果 self-audit 报告 `DEGRADED`，**继续看下面 §1**

## 1. DEGRADED 怎么办（不依赖我拍板）

DEGRADED = 至少一个 baseline 失败。看 self-audit 段落的 Findings，按修复 SOP 自主推进：

| Finding | 修复 SOP（无需用户授权） |
|---|---|
| preflight dirty | 找到 forbidden 文件 → 删除 → 重跑 preflight |
| pytest baseline 退化 | `git diff D:\AIOS\kernel` 看改动 → 回滚最近可疑 commit → 重跑 |
| v2 consumer 未在跑 | `python D:\AIOS\_agent-hub\v2\src\start_consumer_real.py --interval 2 &`（在 background 启动） |
| git dirty 超阈值 | `git status --short \| wc -l` 列文件 → 决定哪些该 commit 哪些该 stash |

**写明**你做了什么到 memory log（`## <时间> Codex Self-Heal` 段落）。

## 2. 我（用户）不在时你能自主推进的事

`autonomous_scope` 默认包含：
- ✅ 跑 self-audit
- ✅ 跑 preflight + pytest baseline
- ✅ 启动 v2 consumer 后台长跑
- ✅ git commit / git stash（但**不 push**）
- ✅ 写 memory log
- ✅ 用 F004 FailurePatternMerger 归并当天异常
- ✅ 修"已建立模式可修的小问题"（如 preflight forbidden 文件）

`requires_authorization` 默认包含（**这些不能自主做**）：
- ❌ 改 `D:\AIOS\_agent-hub\AGENTS.md` SSOT
- ❌ `git push`
- ❌ 重启 / 停止 OS 级 service
- ❌ 修改 Phase A-F 已 Verified 卡
- ❌ 派 dev sub-agent 写新代码（属于施工，需要人批 scope）
- ❌ 启动 Scheduled Task 改动

## 3. 母令第 4 部分缺损时

如果当天 memory 或 self-audit 报告"原文缺损 / 用户已发母令但末段损坏"：
- **不要等用户补全**
- 去 git log + memory 历史找类似母令
- 用 GoalContract 的 inferred_intent 字段记录你的推断
- 写 `## <时间> Codex Inferred Intent` 段落到 memory
- **继续推进**，把推断写到 evidence 里让 Codex supervisor 验

## 4. 我醒来时会看到

memory log 当天最后几段会有：
- `## <时间> Codex Self-Audit (CLEAN|DEGRADED)`
- `## <时间> Codex Self-Heal`（如果有修复）
- `## <时间> Codex Inferred Intent`（如果有推断）

我从这些段落能直接看到你不在时你做了什么、为什么、结果。

---

**这条不是给 Codex 看的——是给 Codex session 启动时的 loader / bootstrap 用的。**
**Codex 醒来第一件事：跑 self-audit，不是问"做什么"。**