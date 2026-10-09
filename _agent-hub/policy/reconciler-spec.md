# Reconciler Spec v1

> **SSOT**: `D:\AIOS\_agent-hub\policy\reconciler-spec.md`
> **依赖**: `D:\AIOS\_agent-hub\policy\model-policy.v1.yaml` (sha256 verified)
> **作者**: Codex (aios-sovereignty-v engineering thread, W9 派单)
> **生成时间**: 2026-10-09T00:0xZ

## 触发
- 定时：每 5 分钟（Task Scheduler, mode A 默认）
- 事件：runtime 启动 / 配置变更 / 会话恢复 / 用户主动触发 / 启动钩 (mode B 备选)

## 比对维度
| 维度 | 来源 | 期望 |
|---|---|---|
| default_model | ModelPolicy | MiniMax-M3 |
| fallback 链 | ModelPolicy | 仅 MiniMax 内已授权项 |
| cc-switch 当前 provider | cc-switch db | MiniMax |
| cron payload 模型 | OpenClaw cron/*.yaml | MiniMax-M3 |
| session restore 模型 | 会话持久化 | 不携带旧模型覆盖 |
| agent 自装 provider | 各 agent 配置 | MiniMax |
| 进程实际加载 | wmic process CommandLine | MiniMax |
| 出站域名 | 抓包/防火墙日志 | MiniMax 官方域名 |
| 环境变量覆盖 | 启动时 env | 不出现非 MiniMax 厂商 URL |

## 漂移分级
- **L1 可逆安全**：env 变量污染 → 自动记录 + 通知（不自动 rollback）
- **L2 需审查**：进程实际加载非 MiniMax provider → 隔离 + 告警 + 等用户决策
- **L3 中断风险**：policy 文件被改写 → 暂停 + sha256 失败 → 等变更管理流程

## 并发（强制）
- **单实例 + 文件锁**（多个 reconciler 互相覆盖 = 高频 bug，必须避免）
- 所有写入原子化（write-then-rename）
- Reconciler **NEVER** auto-modify policy 文件 / runtime config
- 发现 drift 仅记录 + 告警，**绝不自动改**

## 输出
- `D:\AIOS\_agent-hub\audit\drift-events.log`（append-only JSONL）
- 格式见 `drift-event.schema.json`
- Alert 路径：`D:\AIOS\_agent-hub\policy\reconciler\alerts.jsonl`

## R1 backup 防护
- 备份目录必须以 **`.aios-archive`** 哨兵命名
- Reconciler 跳过任何 `.aios-archive` 子树下的自动加载路径
- 备份恢复必须显式由 user 触发 + sha256 重新验签

## R8 policy 文件保护
- Reconciler 启动时 **强制** 比对 `model-policy.v1.sha256` 与实际文件 hash
- 不一致 → exit 3 + 立即告警（不进入 drift 扫描）

## R5 并发控制
- 锁文件：`D:\AIOS\_agent-hub\policy\reconciler\.lock`
- TTL 60s（超时强制释放并 alert）
- 启动时检查锁存在 + TTL 未过期 → 拒绝启动（避免双实例）

## 部署
- 默认 mode A：Task Scheduler 5 分钟间隔（`register_reconciler.cmd` 一键注册）
- 备选 mode B：Codex/CC 启动钩调用 `--once` 参数