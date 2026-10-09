# ModelPolicy v1 回归测试 1-18

每项测试对应 R1-R10 风险表（前一会话 `01a11c23` 风险表 + 当前 sovereignty-v 工程线程 `01a11c33` 派工单）。

## 用法

```powershell
cd D:\AIOS\_agent-hub\policy\regression-tests
python regression_tests.py            # 跑全部 18 项
python regression_tests.py test_13   # 只跑 test_13
```

## 测试映射

| # | 风险 | 验证 |
|---|---|---|
| 01 | R1.a | 备份 sentinel 不被自动加载 |
| 02 | R1.b | sentinel 布局识别 |
| 03 | R2.a | cc-switch fallback 不含非 MiniMax |
| 04 | R2.b | cc-switch current provider = MiniMax |
| 05 | R3.a | OpenClaw cron payload 不携带覆盖 |
| 06 | R3.b | OpenClaw heartbeat payload 合规 |
| 07 | R4.a | session restore 拦截 |
| 08 | R4.b | session restore 审计 |
| 09 | R5 | Reconciler 单实例 |
| 10 | R5.b | Reconciler 不修改 policy 文件 |
| 11 | R6 | 不可拦截程序显式登记 |
| 12 | R7 | .aios-archive 哨兵 |
| 13 | R8.a | policy sha256 pinned |
| 14 | R8.b | policy ACL 只读 |
| 15 | R9 | MiniMax 不可用不视为违规 |
| 16 | R9.b | Adapter 区分不可用 vs 违规 |
| 17 | R10.a | model id 未虚构 |
| 18 | R10.b | model id 有 evidence 字段 |

## 状态

- 由 codex 01a11c30（监督线程）直接写盘 —— T8 envelope 卡 unclaimed，Codex 接管
- 用户授权：2026-10-08T23:55 + "你就开始" + "继续" (2026-10-09T00:11)
- 落地时间：2026-10-09 00:11+08:00
- 关联工程线程：01a11c33（AIOS-SOVEREIGNTY-V · ClaudeCode 执行线程）

## 验收标准

```powershell
python regression_tests.py 2>&1 | Tee-Object last_run.log
```

全部 18 项 PASS = T8 PASS · 任一 FAIL = T8 FAIL · 写入 `last_run.log` 留证。