# Reconciler Spec v1

## 触发
- 定时：每 5 分钟
- 事件：runtime 启动 / 配置变更 / 会话恢复 / 用户主动触发

## 比对维度
| 维度 | 来源 | 期望 |
|---|---|---|
| default_model | ModelPolicy | MiniMax-M3 |
| fallback 链 | ModelPolicy | 仅 MiniMax 内已授权项 |
| cc-switch 当前 provider | cc-switch db | MiniMax |
| cron payload 模型 | OpenClaw cron/*.yaml | MiniMax-M3 |
| session restore 模型 | 会话持久化 | 不携带旧模型覆盖 |
| agent 自装 provider | 各 agent 配置 | MiniMax |
| 进程实际加载 | /proc/<pid>/environ 或 Windows 等价 | MiniMax |
| 出站域名 | 抓包/防火墙日志 | MiniMax 官方域名 |
| 环境变量覆盖 | 启动时 env | 不出现非 MiniMax 厂商 URL |

## 漂移分级
- L1 可逆安全：自动回滚基线
- L2 需审查：隔离 + 通知 + 等用户决策
- L3 中断风险：暂停 + 等待变更管理流程

## 并发
- 单实例 + 文件锁；多个 reconciler 互相覆盖 = 高频 bug，必须避免
- 所有写入原子化（write-then-rename）

## 输出
- D:\AIOS\_agent-hub\audit\drift-events.log（append-only JSONL）
- 格式见 drift-event.schema.json
