# CC START HERE — AIOS VNext One-Shot Handoff（**唯一入口**）

> **Issued by**: Codex (supervisor) — 2026-10-08
> **Audience**: Claude Code (executor) — 这是你**唯一**的入口文件
> **Authority**: AGENTS.md (`D:\AIOS\_agent-hub\AGENTS.md`) 中央 SSOT 已规定 Codex 监督、CC 执行

---

## 0. 你最容易犯的错（**先读这一段**）

CC 在历史上经常做的事：
- ❌ 看到任务卡后**自己再创一份** `protocol_001.md`、`protocol_002.md`...
- ❌ 自己创建 `version_v1.md`、`history.md`、`planning.md`
- ❌ 自己创建 `_r*.py` 编号脚本（沿袭 `_r186_*` 老风格）
- ❌ 自己创建 `handoff_*.md`（除本文件外）
- ❌ 在 `D:\AIOS\` 顶层堆新 `.md` 文件
- ❌ 在 `D:\AIOS\aios_tasks\` 顶层堆新 `.md` 文件（除本 handoff.md + DONE.md + FAILURE_REPORT.md）

**这次严禁。** 21 张卡已经由 Codex 设计完整。**你的工作 = 按卡干活 + 出 evidence。** 不再创造新规划/版本/协议文件。

---

## 1. 你的启动序列（按顺序执行，不许跳）

```bash
# 1. 读本文件（你已读）
cat D:\AIOS\aios_tasks\aios_vnext\handoff.md

# 2. 读总览（只看 D.13.0 §0 表 + D.13.2 §2 One-shot 模式）
cat D:\AIOS\aios_tasks\aios_vnext\INDEX.md

# 3. 读工作流（全文，重点 §11 禁创文件）
cat D:\AIOS\aios_tasks\aios_vnext\_cc_workflow.md

# 4. 列出所有卡
ls D:\AIOS\aios_tasks\aios_vnext\cards\

# 5. 跑 preflight 自检（关键）
python D:\AIOS\aios_tasks\aios_vnext\preflight_check.py

# 6. preflight 通过后，扫所有卡的当前状态
grep -E "^[ ]*\| \*\*(T|中)" D:\AIOS\aios_tasks\aios_vnext\INDEX.md
# 找到所有 status=Approved + 无未 Verified 前置 + 最高 priority 的卡

# 7. 读那张卡的全文
cat D:\AIOS\aios_tasks\aios_vnext\cards\<T_ID>_*.md

# 8. 严格按卡 §Scope 执行，不扩

# 9. 写 evidence 到 evidence/<T_ID>__<ts>.md（附 forbidden_files_check.txt）

# 10. 更新 INDEX.md（仅该卡行 status=Submitted —— 见 D.13.4 §4 Schema）

# 11. 重复 6-10 直到 21 张卡全 Submitted

# 12. 写 DONE.md（一次性收口报告）

# 13. 停
```

---

## 2. 你唯一允许创建的文件（**白名单**）

| 路径 | 用途 |
|------|------|
| `D:\AIOS\aios_tasks\aios_vnext\evidence\T<id>__<ts>.md` | 每张卡的 evidence（必含） |
| `D:\AIOS\aios_tasks\aios_vnext\evidence\T<id>__<ts>_*.txt` | evidence 附件（probe log / diff / report 等） |
| `D:\AIOS\aios_tasks\aios_vnext\DONE.md` | 21 张全完成时的最终收口报告 |
| `D:\AIOS\aios_tasks\aios_vnext\FAILURE_REPORT.md` | 仅当整体失败时 |
| `D:\AIOS\aios_tasks\aios_vnext\INDEX.md` | **仅改 status 列**，其他不改 |
| 详细卡 Scope "Outputs" 段**显式列出**的额外文件 | 必须严格按 Outputs 段列出的路径/文件名 |

**白名单以外的文件** = 全部 Forbidden。Codex 验收时第一项 grep 验证。

---

## 7. Forbidden Files / Patterns（**红线**）

```
D:\AIOS\ 顶层新建 *.md  ❌  全部禁
D:\AIOS\ 顶层新建 *.py  ❌  全部禁（T0032 启动后才允许在 D:\AIOS\kernel\ 下建 .py）
D:\AIOS\aios_tasks\ 顶层新建 *.md  ❌  仅允许 handoff.md / DONE.md / FAILURE_REPORT.md / INDEX.md（仅 status 列）
D:\AIOS\aios_tasks\aios_vnext\cards\ 下新建 *.md  ❌  Codex 写的 21 张是 SSOT，CC 不补
D:\AIOS\aios_tools\ 下新建 *.py  ❌  Track 0 legacy 修复期间禁创新脚本（T0004 限制除外）
协议类文件名  ❌
  - protocol_*.md / protocols/*.md / _protocol*.md
  - version_*.md / versions/*.md / v*_*.md / _v*_*.md
  - planning_*.md / plans/*.md
  - handshake_*.md
  - handoff_*.md（除本文件 + 每张卡 Outputs 显式列出的 handoff）
  - spec_*.md（除已存在的 INDEX.md / cards/_*.md / _cc_workflow.md）
  - roadmap_*.md / roadmap/*.md
  - blueprint_*.md
  - playbook_*.md / playbooks/*.md
  - sop_*.md（sop = Standard Operating Procedure；CC 不写 SOP，规划在卡里）
  - runbook_*.md
编号脚本  ❌
  - _r*.py（沿袭 _r186_*.py 老风格；T0031 kernel 仓库内的 .py 不在此禁）
  - _R*.py
  - r<number>.py
  - v1_*.py / v2_*.py
```

---

## 3. Preflight Check（**必跑**）

执行：`python D:\AIOS\aios_tasks\aios_vnext\preflight_check.py`

检查项：
1. `D:\AIOS\` 顶层新建 `.md` 数量 = 0（除了 handoff.md / DONE.md / FAILURE_REPORT.md 之外的 0）
2. `D:\AIOS\aios_tasks\` 顶层新建 `.md` 数量 ≤ 3（仅 handoff.md / DONE.md / FAILURE_REPORT.md）
3. `D:\AIOS\aios_tasks\aios_vnext\cards\` 下新建 `.md` 数量 = 0
4. `D:\AIOS\aios_tools\` 下新建 `.py` 数量 = 0（除 T0004 / T0006 显式授权）
5. 协议类文件名检查：grep 上面的所有 pattern = 0
6. `D:\AIOS\aios_tasks\aios_vnext\evidence\` 目录存在（CC 必创建）

输出：`preflight_<ts>.txt` 写到 evidence 目录，每张卡 evidence 必附此文件。

**如果 preflight 失败**：不进入任何卡，写 `FAILURE_REPORT.md`，通知 Codex。

---

## 4. 完成 Phase A 的 D0NE.md 必含项

```markdown
# DONE — AIOS VNext Phase A One-Shot Delivery

**CC Executor**: XX
**Started**: XX
**Finished**: XX
**Cards Processed**: 21/21
**Cards Failed**: 0 (or list)

## 1. 21 张卡状态汇总表（从 INDEX.md 复制）
## 2. Forbidden Files Check（preflight 输出累计）
## 3. Codex 验证状态汇总
## 4. 最终签字
```

---

## 5. 如果整个 one-shot 失败

写 `FAILURE_REPORT.md`：
```markdown
# FAILURE_REPORT — AIOS VNext One-Shot Delivery

**CC Executor**: XX
**Started**: XX
**Failed At**: <T_ID>
**Reason**: XX

## 1. 已完成的卡 (Verified/Submitted)
## 2. 失败卡详情 (Failed card + reason)
## 3. Forbidden Files Check 结果
## 4. 已回滚
## 5. 剩余阻塞
```

---

## 6. 签字授权

```yaml
issued_by: Codex (supervisor)
issued_at: 2026-10-08
authority_basis: D:\AIOS\_agent-hub\AGENTS.md §Mission + 4 Iron Rules
mode: ONE-SHOT (per user original request 2026-10-08)
cc_role: EXECUTOR (NOTPLANNER)
plan_source: D:\AIOS\aios_tasks\aios_vnext\cards\T*.md (21 cards)
evidence_destination: D:\AIOS\aios_tasks\aios_vnext\evidence\T*__<ts>.md
status_board: D:\AIOS\aios_tasks\aios_vnext\INDEX.md (CC writes status=Submitted; Codex writes status=Verified)
```

---

**handoff.md 结束。CC 第一步：** `python preflight_check.py`