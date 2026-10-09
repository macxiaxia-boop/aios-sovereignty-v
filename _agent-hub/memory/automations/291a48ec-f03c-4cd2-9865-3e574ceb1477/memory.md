# Automation: codex-daily-checkpoint

## Purpose
每日凌晨自动跑 `C:\Users\xinzh\.workbuddy\scripts\codex-daily-checkpoint.ps1`：
1. 杀 codex 进程
2. 对 6 个 WAL sqlite 跑 `PRAGMA wal_checkpoint(TRUNCATE)`
3. 清理 `.codex\.tmp` / `.codex\tmp` / `$env:TEMP` 旧文件
4. 报告 C 盘空间

输出追加到 `C:\Users\xinzh\.workbuddy\logs\codex-daily-checkpoint.log`。

## 首次执行（2026-09-29 09:05）

**结果摘要**：
- C 盘剩余：**32.8GB / 149.4GB**
- WAL checkpoint：6/6 全部成功，状态 `[(0,0,0)]`（busy=0/log=0/ckpt=0 = 全 checkpoint 达成）
- 清理文件数：`.codex\.tmp` **35 个** + `.codex\tmp` **0 个** + `TEMP > 7 天` **3 个** = **38 个**

## 已知问题
- **首次执行发现脚本缺 UTF-8 BOM**（红线 #29 违规）：脚本原为 UTF-8无 BOM，PowerShell 按系统 GBK 解析，全脚本报 parser error。
  - **治本**：已用 `[System.Text.UTF8Encoding $true]` 重写脚本为 UTF-8 BOM（0xEF 0xBB 0xBF）。
  - **下次运行**：若脚本被覆盖回无 BOM，需重新转码。

## 经验固化（建议沉淀为 skill）
- PowerShell 脚本含中文 + 缺 BOM = 必败：GBK 系统默认编码把 UTF-8 中文当 GBK 解 → 全脚本 syntax error。
- 红线 #29 治本路径：用 `New-Object System.Text.UTF8Encoding $true` 重写文件即可。