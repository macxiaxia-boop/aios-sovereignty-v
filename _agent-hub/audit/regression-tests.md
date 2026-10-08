# 18 项回归测试 · AIOS-SOVEREIGNTY-V

| # | 测试 | 步骤 | 验收 |
|---|---|---|---|
| 1 | 修改配置后立即运行 | 触发模型调用 | 日志显示 MiniMax |
| 2 | 重启 Codex | 杀进程→启→调 | 同上 |
| 3 | 重启 ClaudeCode | 同上 | 同上 |
| 4 | 重启 cc-switch | 同上 | CLI 配置仍 MiniMax |
| 5 | 重启 OpenClaw Gateway | 同上 | 所有 sub-agent MiniMax |
| 6 | 恢复历史 Codex 会话 | restore | 会话不携带旧模型覆盖 |
| 7 | 恢复历史 ClaudeCode 会话 | restore | 同上 |
| 8 | 跑原 Cron | trigger cron | payload 走 MiniMax |
| 9 | 跑 AIOS 业务 | 业务入口 | 全程 MiniMax |
| 10 | 跑子 Agent | 递归 | 全部 MiniMax |
| 11 | 并发任务 | 10 并发 | 无 race 回滚 |
| 12 | 模型切换器重载 | reload | 仍是 MiniMax |
| 13 | 断网恢复 | 断→恢复 | 无 fallback 触发 |
| 14 | 模拟系统重启 | reboot | 策略原子恢复 |
| 15 | 模拟旧配置恢复 | 注入旧 .json | Reconciler 检测+告警/回滚 |
| 16 | 模拟不允许的模型选择 | env 注入 | Adapter 拒绝+日志 |
| 17 | 验证拒绝行为 | 读 reject log | 可审计 |
| 18 | 验证 MiniMax 兼容协议未坏 | 真实业务调用 | 业务正常 |

**PASS 准则：18/18；任何 1 项 FAIL → 不可声明工程完工。**
