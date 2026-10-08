# 只读审计清单 · AIOS-SOVEREIGNTY-V

## A1 — Codex
- 扫: `~/.codex/`、`.codex.toml`、`profile*`、CLI flags、`CODEX_*` env
- 对账: 文件 vs 进程实际加载 vs 出站域名
- 工具: `Get-ChildItem`, `Get-Content`, `Get-Process`

## A2 — ClaudeCode
- 扫: `~/.claude/`、`.claude.json`、`.bat`/`.ps1` 启动脚本、`ANTHROPIC_*` env、MCP server 配置
- 对账: 同 A1

## A3 — cc-switch
- 扫: 配置 DB、备份目录、启动钩子、多实例
- 关键: 是否存在 restore-on-launch / auto-switch-back

## A4 — OpenClaw
- 扫: `~/.openclaw/`、`agents/*.yaml`、`cron/*.yaml`、`gateway.yaml`、session 持久化
- 关键: cron payload 模型字段、heartbeat 模型、会话恢复时 model 字段

## A5 — Hermes / 其它 agent
- 扫: 各 agent 配置 + 外部 API 适配器
- 关键: 独立 provider 列表

## A6 — Windows 自动化
- 扫: Task Scheduler（`Get-ScheduledTask`）、自启动（`Get-CimInstance Win32_StartupCommand`）、`.env`、计划任务脚本
- 关键: 谁在第二天把旧配置拷回去

## A7 — 进程实际加载
- 启动后查进程 env、出站连接（`Get-NetTCPConnection`）
- 验证出站域名解析到 MiniMax 官方 IP 段

## A8 — 历史会话回放
- 选 1 个含旧模型覆盖的 session，restore 后立刻 diff model 字段

## 输出格式（每个探针）
- 探针 ID
- 扫描范围
- 找到的事实（路径 + 内容摘要 + sha256）
- 复活根因关联链（文件 → 修改程序 → 生效进程 → 实际请求 → 供应商）
- 与 Policy 对账结果
