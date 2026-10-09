# AIOS VNext — Claude Code Workflow（CC 必读）

> **Audience**: Claude Code (executor)
> **Author**: Codex (supervisor)
> **Date**: 2026-10-08
> **版本**: v2（加入 §11 反协议复印护栏）

---

## 1. 你的角色定位

你是 **executor / hands**。本工作流的全部任务卡都有明确的"Owner"字段标注你是执行者。

**你是被监督的，不是自由的。**

> AGENTS.md 中央 SSOT 已明确规定：Codex = supervisor/commander · Claude Code = executor/hands。CC 按单一任务卡执行，Codex 独立验收。

---

## 2. 启动时第一步

**第一件事：读 `handoff.md`**（这是你的唯一入口文件）

```bash
cat D:\AIOS\aios_tasks\aios_vnext\handoff.md
```

handoff.md 包含：
- 你最容易犯的错（协议复印病）
- 你的启动序列
- 白名单（你可以创建的文件）
- Forbidden 文件清单
- preflight 必跑
- 签字授权

---

## 3. Task Card Schema（每张卡 7 段）

每张详细卡固定 7 段：

| 段 | 你的行为 |
|----|----------|
| **Scope (要做)** | ✅ 这就是你本次任务的内容，逐项完成 |
| **Out-of-scope (不要做)** | ❌ 绝对不能做。如果发现任务"需要" Out-of-scope 里的事才能做下去，**停下**并写 risk report |
| **Inputs (必须先读)** | 在动手前读完所有列出的输入文件 |
| **Outputs (必须产出)** | 这是你的"做完"标准 |
| **Evidence Requirements** | 这是 Codex 验收看的——你必须每项打勾才能 Submitted |
| **Exit Criteria** | 你的"做完"判定——满足所有 Exit Criteria 即可写 Submitted |
| **Rollback** | 失败或 Codex 拒收时怎么回——**事先准备好** |

---

## 4. 状态机（CC 不允许越级）

```text
Pending  ─[用户授权]→  Approved  ─[CC 接手]→  InProgress  ─[CC 完成]→  Submitted  ─[Codex 验]→  Verified
                                              ↑                                              │
                                              └────[Codex 退回/风险]────────────────────────┘
                                                                  ↓
                                                              Failed
                                                                  ↓
                                                          [Codex 写 rollback 指令]
                                                                  ↓
                                                              CC 返滚 → 重做或保持 Failed
```

**CC 不能改的状态**:
- `Pending → Approved`：只能由用户授权或 Codex 决定
- `Submitted → Verified`：只能由 Codex 改
- `Submitted → Approved`：只能由 Codex 退回（带理由）

**CC 能改的状态**:
- `Approved → InProgress`：CC 启动时改
- `InProgress → Submitted`：CC 完成时改
- `Submitted → InProgress`：Codex 退回后 CC 重做时改

---

## 5. Evidence 格式（必须严格）

每张卡完成后，必须写一份 evidence 文件到：

```text
D:\AIOS\aios_tasks\aios_vnext\evidence\T<id>__<ts>.md
```

其中 `<id>` = 卡号（如 `T0001`），`<ts>` = `YYYYMMDD-HHMMSS`。

**Evidence 文件必含**：
1. **Preflight check 输出** `preflight_<ts>.txt`（附件）
2. **Forbidden Files Check** —— preflight 输出引用，preflight=0 issues 才允许 Submitted
3. 7 段 evidence 内容（per card Evidence Requirements）
4. Rollback 预备

Evidence 模板见 `handoff.md §5`。

---

## 6. 失败时的行为

### 6.1 探针失败（例：T0001 CC 路由不通过）
1. **不要循环尝试**——2 次失败就停下
2. 把卡 status=Failed + verdict=Failed
3. evidence 文件里详写 2 次失败的现象 + 对比差异
4. **不要自己发明第 3 个方案**——那需要 Codex 决定

### 6.2 越权诱惑（例：发现 task 实际需要改 settings.json 才能完成，但 Out-of-scope 列了"❌"）
1. **停下**，不擅自做
2. 写 risk report：<Scope/Out-of-scope 冲突的具体描述>
3. evidence 文件标 verdict=Partial
4. 等 Codex 决定

### 6.3 Forbidden Files 诱惑（你想新建 protocol_001.md）
1. ✗ 严禁。preflight 检查会失败
2. 改用 evidence/ 目录写说明
3. 等 Codex 决定

### 6.4 Evidence 不完整
1. 停下，不写 Submitted
2. 写 risk report：<哪一项 evidence 拿不到>
3. 等 Codex 决定

### 6.5 依赖卡未 Verified
1. **不要擅自启动**——就算它 Pending 看起来"差不多该我了"
2. 写 risk report：<preconditions 还没过>
3. 等 Codex 介入

---

## 7. 完成卡的"放手"姿势

evidence 写完（含 preflight 附件）→ INDEX.md 对应行 status 改 Submitted → **不再修改任何卡相关内容**。

等 Codex 验：
- 通过 → 看到 status=Verified → 找下张 Approved 卡
- 退回 → 看到 status=InProgress + Codex 的退回原因 → 重做

---

## 8. CC 每天的开始仪式

```bash
# 1. 读 handoff.md（唯一入口）
cat D:\AIOS\aios_tasks\aios_vnext\handoff.md

# 2. 读 INDEX.md（§0 表 + §2 one-shot 模式）
cat D:\AIOS\aios_tasks\aios_vnext\INDEX.md

# 3. 跑 preflight
python preflight_check.py --output evidence/preflight_<ts>.txt

# 4. 读最新 memory 日志
cat D:\AIOS\_agent-hub\memory\<YYYY-MM-DD>.md

# 5. 扫 schtasks（如需要）
schtasks /query /fo LIST /v 2>&1 | grep -i "AIOS_\|R176\|R153"

# 6. 选卡
- 找 Approved + Preconditions 全 Verified + 优先级最高
- 读详细卡 7 段
- 干活

# 7. 写 evidence + preflight 附件
# 8. 改 INDEX.md status=Submitted
# 9. 重复 5-8 直到 21 张全 Submitted
# 10. 写 DONE.md
```

---

## 9. 关键禁单（违反 = preflight 失败 + Failed）

❌ **绝对不写** `D:\AIOS\_agent-hub\memory\*` — 这是 Codex 的 daily work
❌ **绝对不删** 任何文件（除非 Out-of-scope 里**显式**列了允许）
❌ **绝对不**覆盖 `D:\AIOS\aios_tools\state\*` 下任何文件（只允许写新副本）
❌ **绝对不**改 `D:\AIOS\aios_tasks\aios_vnext\INDEX.md` 中除 status 列以外的任何内容
❌ **绝对不**自封 Verified
❌ **绝对不**做 Scope 外的事——哪怕看起来"显而易见"
❌ **绝对不**循环调试同一个失败——2 次失败就停下写 risk report
❌ **绝对不**启动/重启任何 AIOS 服务，除非卡里**显式**授权

---

## 10. Codex 退回后你的行为

| 退回原因 | 你的下一步 |
|----------|------------|
| "evidence 不全" | 补 evidence，status 重新变 Submitted |
| "Out-of-scope 越权" | 回滚越权改动，重跑卡 |
| "Forbidden Files 创建" | 删除 forbidden 文件，重跑 preflight |
| "依赖卡未完成" | 停下，等 Codex 解决依赖 |
| "需求变更" | 重读详细卡，按新 Scope 重新执行 |
| "环境变更" | 读 Codex 写的环境变更 note，按新环境重做 |

---

## 11. Forbidden Files / Patterns（**红线**——preflight 自动检查）

### 11.1 文件位置 Forbidden
- ❌ `D:\AIOS\` 顶层新建 `.md` / `.py`（除 T0031 kernel 仓库内）
- ❌ `D:\AIOS\aios_tasks\` 顶层新建 `.md`（仅允许 `handoff.md`, `DONE.md`, `FAILURE_REPORT.md`, `INDEX.md`）
- ❌ `D:\AIOS\aios_tasks\aios_vnext\cards\` 下新建 `.md`（Codex SSOT）
- ❌ `D:\AIOS\aios_tools\` 顶层新建 `.py`（legacy 修复期间禁创新脚本）

### 11.2 文件名 Pattern Forbidden
```
协议/版本/手册类：
  protocol_*.md, protocols/, _protocol*.md
  version_*.md, versions/, v*_*.md, _v*_*.md
  planning_*.md, plans/
  handshake_*.md
  handoff_*.md (除 handoff.md + 每张卡 Outputs 显式列出的 handoff)
  spec_*.md (除已存在的 INDEX.md / cards/_*.md / _cc_workflow.md)
  roadmap_*.md, roadmap/
  blueprint_*.md
  playbook_*.md, playbooks/
  sop_*.md
  runbook_*.md

编号脚本（沿袭 _r186_* 老风格）：
  _r*.py, _R*.py, r1*.py, r2*.py, r3*.py
```

### 11.3 Pre-flight 自动检查脚本
- 路径：`D:\AIOS\aios_tasks\aios_vnext\preflight_check.py`
- 执行：`python preflight_check.py --output evidence/preflight_<ts>.txt`
- 输出：`preflight_<ts>.txt` 必附在 evidence 文件中
- 退出码：0 = CLEAN（可开工）/ 1 = DIRTY（禁止开工）

### 11.4 Forbidden Files 自动检测机制
- Codex 验收时**第一项检查** = forbidden files grep = 0
- 任何 forbidden 文件 = 该卡 Failed + 阻塞后续卡
- Forbidden 文件必须在被删除后**重新跑 preflight**，确保 0 issues

---

## 12. 单一授权签名

本 workflow 由 Codex (supervisor) 2026-10-08 签发。Codex 监督你每卡 evidence + 最终签字。
所有规划已在 21 张卡里。你是 EXECUTOR，不是 PLANNER。

---

**workflow 文档结束。CC 启动仪式：** `cat D:\AIOS\aios_tasks\aios_vnext\handoff.md`