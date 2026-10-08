# 任务卡 · 2026-10-08 · AIOS-SOVEREIGNTY-V

## T1 — 落盘 Policy SSOT 并签名（**只写新文件**）
- 写 D:\AIOS\_agent-hub\policy\model-policy.v1.yaml ✅ 已完成
- 写签名 manifest → model-policy.v1.sha256 ✅ 已完成
- ACL 设为只读
- 验收：Get-FileHash 与 manifest 一致

## T2 — 只读审计扫描（**禁止写盘**）
- 扫 Codex / ClaudeCode / cc-switch / OpenClaw / Hermes / Windows
- 4 路对账表（文件 / env / 进程 / 出站）
- 复活根因关联链（文件 → 修改程序 → 生效进程 → 实际请求 → 供应商）
- 输出：audit-report-2026-10-08.md

## T3 — cc-switch 痕迹专项（**只读**）
- 当前 provider / 备份目录 / 启动钩子 / 多实例
- 输出：cc-switch-trace-2026-10-08.md

## T4 — OpenClaw cron/heartbeat/session 痕迹（**只读**）
- agents/*.yaml / cron/*.yaml / gateway.yaml
- 输出：openclaw-trace-2026-10-08.md

## T5 — Adapter 实现（**写盘；需用户授权**）
- Codex / ClaudeCode / OpenClaw / cc-switch Adapter
- 验收：模拟请求不合规 → DENY + 日志可查

## T6 — Reconciler 实现 + 漂移事件落地（**写盘；需用户授权**）
- 单实例 + 文件锁
- 18 项回归测试

## T7 — 历史会话/旧配置安全归档（**写盘；需用户授权**）
- 旧 provider 备份 → D:\AIOS\_agent-hub\archive\legacy-2026-10-08\
- 加 .aios-archive 哨兵文件

## T8 — 18 项回归测试执行 + 报告（**只读 + 触发现成 Adapter**）
- 全跑 18 项
- 输出：regression-report-2026-10-08.md
- 全 PASS → verification_status: pending → active

## 红线
1. 任何写盘动作前必须先读 Policy + 校验 hash
2. 不得自行在 allowed_models 中编造 model id
3. 旧配置必须移入 archive 子目录，禁止原地删除
4. 不得修改审计日志历史
5. T5–T8 必须等用户明确授权
6. 删任何字符串前必须比对实际出站域名与计费记录
