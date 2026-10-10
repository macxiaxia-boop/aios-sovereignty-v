# 2026-10-10 · 自纠正:AGENTS.md 实际存在(原 audit 写错过)

> 在 2026-10-09 AIPM02-FOUNDATION 设计阶段,我之前在 `AIOS_COMPLETION_AUDIT.md` 和 `FINAL_LEARNING_REPORT.md` 写:
> "中央 SSOT 缺失: D:\AIOS\_agent-hub\AGENTS.md 不存在"
> **错误更正**(2026-10-10 实测):

```
$ Test-Path "D:\AIOS\_agent-hub\AGENTS.md"
True
```

文件**实际存在**,内容是 2026-09-30 起的原 bootstrap(SSOT 概念已存在)。我的 `Test-Path = False` 早期结果 flaky 或被并行会话修复。

## 影响

- D1 改为 manual review step,不在 "create file",而在 "merge content"(我选了 Option B - append 保留原内容 + 加 150 行 AIPM02 supplement)
- 后续 D1 commit `9249ffe` 实现了这一点
- 原 bootstrap 的 junction links (`_agent-hub/install-links.ps1` 等) 完整保留

## 后续

- 输出 docs 16 份 + APPROVED_INTEGRATION 13 份 + sandbox sim 真实跑 17 用例 + 一键 apply 脚本均完整
- 真实 apply 全套已在 main 上落地,详见 `2026-10-10-all-stages-done.md`
