# W14 · CloudTech 受控接入 · Plan

> **Phase**: W14 (CloudTech 受控接入)
> **创建**: 2026-10-09T10:30+08:00 by Codex 01a11c30 supervisor
> **用户授权**: "把待办全部做掉" (2026-10-09)
> **关联**: AGENTS.md Phase E (CloudTech Productization 2026-10-08 Verified)

---

## 1. 目标

把 CloudTech SaaS 的所有 AI 调用强制走 **ModelPolicy v1 · MiniMax 唯一 API** · 通过 4 runtime adapter · 不能绕开。

## 2. 范围

- CloudTech 前端 / 后端 / 数据库 / 模板 源码
- CloudTech 用到的 worker scripts（生成 / 翻译 / 评分 / 推荐）
- 任何 cron / heartbeat / session-restore 模型调用

## 3. 风险评估（继承 R1-R10 风险表）

| R | CloudTech 风险 | 检测方式 |
|---|---|---|
| R1 | backup 目录被自动扫描加载 | contamination_scanner.scan_path() |
| R2 | cc-switch 注入 deepseek fallback | 已根治（见 T31） |
| R3 | Cron payload 携带 deepseek/openai 覆盖 | contamination_scanner.scan_payload() |
| R4 | Session restore 重新激活旧模型 | hermes_daemon 心跳 |
| R5 | CloudTech 多个 worker 互覆盖 | Reconciler 单实例 + 锁 |
| R6 | CloudTech 不可拦截外部程序 | scan_active_assets() |
| R7 | backup 目录无 .aios-archive sentinel | contamination_scanner |
| R8 | policy 文件被改写 | sha256 + 签名 + 只写权收口 |
| R9 | MiniMax 不可用被误判 | unavailable_handling 段 |
| R10 | 用户授权 model id 误填/虚构 | policy allowed_models 段 |

## 4. 5 阶段实施

### Phase W14.1 · 扫描（read-only）
- 用 `ContaminationScanner` 扫 CloudTech 源码（前端 / 后端 / db / templates / workers）
- 输出 `reports/sovereignty-v/W14_scan.json`
- 列出所有非 MiniMax provider 引用
- 时长估计: 5-10 min · 完全 autonomous_scope

### Phase W14.2 · 报告 + 待 user 拍板
- 输出扫描报告
- 让 user 决定每个非合规引用怎么处理（移除 / 替换为 MiniMax / 接受风险）
- 时长: 用户决策时间

### Phase W14.3 · 替换 + 写 adapter 包装
- 对每个需要 AI 调用的位置，套 `policy/adapters/*_runtime.py` 的 `validate()` 包裹
- 生成 CloudTech-specific adapter (cloudtech_runtime.py) 接 model_policy.v1.yaml
- 时长估计: 30-60 min · 派 Claude Code 写

### Phase W14.4 · PreToolUse hook 装上
- 给 CloudTech 写盘的 hook 接 `policy/codex_adapter.py` 类似实现
- 任何写文件前 exit 1 if 含 prohibited_keywords
- 时长估计: 10-15 min · 派 CC

### Phase W14.5 · Reconciler 接入 CloudTech
- 改 Reconciler 让它也扫 CloudTech 源码
- 输出 drift log 多了 CloudTech 区块
- 时长估计: 5 min · Codex 直接改

## 6. 验收

- W14_scan.json 含所有 CloudTech provider 引用清单
- cloudtech_runtime.py 6/6 self-test PASS
- PreToolUse hook 在 CloudTech 写盘场景触发
- Reconciler 跑 CloudTech scan · drift 仍 = 0
- regression_tests.py 含 CloudTech adapter 测试 · 0 FAIL

## 7. 红线

- ❌ 不删 CloudTech 任何文件（除非用户明确批准）
- ❌ 不改 CloudTech 业务逻辑
- ✅ 只加 adapter wrapper（不改原始调用）
- ✅ 只加 hook 检测（不阻拦用户手动编辑）

## 9. 不在本 phase 范围

- ❌ 重新设计 CloudTech 架构
- ❌ 升级 CloudTech 功能
- ❌ 性能优化
- ❌ UI 改版

---

_— Codex 01a11c30 supervisor · 2026-10-09T10:30+08:00 · W14 plan ready · 等用户启动或派 CC_