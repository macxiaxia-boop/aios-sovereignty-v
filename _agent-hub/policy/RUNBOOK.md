# Phase I.3 Runbook · AIOS-SOVEREIGNTY-V

> **SSOT**: `D:\AIOS\_agent-hub\policy\RUNBOOK.md`
> **Scope**: Hook 集成 (T23) + Daemon (T25) + Runbook (T27) · 加 cron validate (T24) + adapter auto-load (T26)
> **Thread**: 01a11c33-c813-7752-9e53-b7c332d00445 (Claude Code 执行)
> **Supervisor**: 01a11c30-6f6c-76c0-8c60-a55f3a43ff63 (Codex 监督)
> **Authorizer**: user-2026-10-08T23:55 (sovereignty-v) + 你就开始 + 继续 (2026-10-09)
> **Generated**: 2026-10-09

---

## 0. 一句话

Phase I.3 = **5 个子任务全部落地**: Codex PreToolUse hook 已注册、OpenClaw cron 已接入 validate、Heres daemon 化已启用、Adapter auto-load 已通、Runbook (本文) 已落盘。

---

## 2. 5 个子任务 · 落盘清单

| # | 任务 | 落盘位置 | 验证 |
|---|---|---|---|
| T23 | Codex PreToolUse hook 注册 | `policy/hooks/codex_pre_tool_use_hook.json` + `~/.codex/config.toml` `[hooks]` 段 | `Get-Content` 可见 `[hooks]` + `pre_tool_use` |
| T24 | OpenClaw cron validate() 集成 | `policy/integrations/openclaw_cron_validate.py` + `D:\AIOS\openclaw\cron\*.yaml` (2 样本) | `--dry-run` + `--verbose` + live 模式均 PASS |
| T25 | Hermes daemon 化 | `policy/daemons/hermes_daemon.py` + `register_hermes.cmd` | `--once --verbose` exit=0 + 心跳 JSON 落盘 |
| T26 | Adapter auto-load | `policy/adapters/__init__.py` (含 `load_all_adapters`) | 4/4 loaded + 4/4 签名统一 |
| T27 | Runbook (本文) | `policy/RUNBOOK.md` | (本文) |

---

## 3. 端到端验证 · 5 步流水线

### Step 1 · Codex PreToolUse hook 立即生效
```powershell
# 1a. 验证 config.toml [hooks] 段
Get-Content $env:USERPROFILE\.codex\config.toml | Select-String -Pattern '\[hooks\]'
# 期望: 输出 [hooks]  (Phase I.3 / T23 追加)

# 1b. 验证 hooks.json PreToolUse Write|Edit 第 2 条
Get-Content $env:USERPROFILE\.codex\hooks.json | Select-String -Pattern 'codex_adapter.py'
# 期望: 输出 D:/AIOS/_agent-hub/policy/codex_adapter.py

# 1c. 真发一次合法写 (Write 一个 dummy .md) → 应 ALLOW
echo "test" > D:\tmp\aios_smoke_test.txt  # 仅 touch, 不写 policy 文件
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" "D:/AIOS/_agent-hub/policy/codex_adapter.py"
# 期望: stdout 空 + stderr 空 + exit=0 (ALLOW)

# 1d. 真发一次含禁用关键字 → 应 DENY
echo '{"file_path":"openai_test.py","content":"import openai"}' | "C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" "D:/AIOS/_agent-hub/policy/codex_adapter.py"
# 期望: stderr "ADAPTER-DENY: PROHIBITED_KEYWORD" + exit=1
```

### Step 2 · OpenClaw cron payload validate 集成
```powershell
# 2a. dry-run (不真发 validate, 仅报告将调什么)
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" "D:/AIOS/_agent-hub/policy/integrations/openclaw_cron_validate.py" --dry-run --verbose
# 期望: 2 个 ALLOW (因为 dry-run 不真调)

# 2b. live (真调 openclaw_runtime.validate)
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" "D:/AIOS/_agent-hub/policy/integrations/openclaw_cron_validate.py" --verbose
# 期望: 1 ALLOW (daily_health_check.yaml) + 1 DENY (leaked_provider_drift.yaml) + exit=1

# 2c. 验证 audit log 写入
Get-Content D:\AIOS\_agent-hub\audit\cron-validations.log | Select-Object -Last 2
# 期望: 2 行 JSONL · 各含 ts/name/provider/model/allowed/reason
```

### Step 3 · Hermes daemon 真启
```powershell
# 3a. 跑一次 --once --verbose
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" "D:/AIOS/_agent-hub/policy/daemons/hermes_daemon.py" --once --verbose
# 期望: hermes_daemon started → cycle=1 exit=0 → stopping

# 3b. 验证心跳 JSON
Get-Content D:\AIOS\_agent-hub\policy\daemons\hermes_daemon.heartbeat.json
# 期望: ts / pid / cycle / exit_code / drift_count / failures

# 3c. 验证 daemon log
Get-Content D:\AIOS\_agent-hub\policy\daemons\hermes_daemon.log
# 期望: 3 行 (started / cycle / stopping)
```

### Step 4 · Adapter auto-load
```powershell
# 4a. 静态检查 4 个 adapter
cd D:\AIOS\_agent-hub\policy\adapters
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" "__init__.py" --list
# 期望: 4 行 [OK] + summary ok=4/4

# 4b. 编程式加载
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" -c "from __init__ import load_all_adapters; mods = load_all_adapters(); print(len(mods))"
# 期望: 4

# 4c. JSON 输出 (供 dashboard)
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" "__init__.py" --json
# 期望: 4 行 JSON object 含 name/loaded/signature_ok/host
```

### Step 5 · Regression 总闸
```powershell
# 5a. 跑全部 18 项回归
cd D:\AIOS\_agent-hub\policy\regression-tests
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" regression_tests.py
# 期望: 全部 PASS

# 5b. 跑 5 项 Adapter 契约 (T26 / spec §"契约测试项")
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" regression_tests.py test_validate_signature_unified
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" regression_tests.py test_no_fabricate_model_id
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" regression_tests.py test_no_auto_fallback_in_adapter
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" regression_tests.py test_validate_policy_sha256_enforced
"C:/Users/xinzh/.workbuddy/binaries/python/versions/3.13.12/python.exe" regression_tests.py test_validate_audit_log_written
# 期望: 5/5 PASS
```

---

## 4. 持久化选项 (用户授权后启 · L3 红线)

| 操作 | 命令 | L3 风险 |
|---|---|---|
| 注册 Hermes Daemon (每 5 分钟心跳) | `schtasks /Create /SC MINUTE /MO 5 /TR "\"python\\escape D:\\AIOS\\_agent-hub\\policy\\daemons\\hermes_daemon.py\" --once --verbose" /TN AIOS_Hermes_Daemon /F` | 持久化系统任务 · 需用户明示 |
| 启 daemon (前台自循环) | `"python D:\\AIOS\\_agent-hub\\policy\\daemons\\hermes_daemon.py"` | 进程持续运行, ctrl-c 停 |
| 注册 OpenClaw cron validate 启动钩 | `D:\AIOS\openclaw\startup_hook.cmd` 调用 `python ...openclaw_cron_validate.py` | 需用户拍板在 OpenClaw 启动顺序里插入 |

> **铁律 5**: 上述 3 项均 L3 (系统级持久化 / 进程级持续) · 不在 `user-2026-10-08T23:55 + 你就开始 + 继续` 自动授权范围内。
> **Phase I.3 现状**: 5 个 .py / .json / .cmd 全部已落盘可独立运行; 持久化开关用户明示后启。

---

## 5. 红线契约 (与 adapter-spec.v1.md §"红线" 对齐 · 永久态)

| ID | 红线 | 验证方式 |
|---|---|---|
| `NO_FABRICATE_MODEL_ID` | Adapter / Daemon / Hook 不在代码中硬编码 model id | grep 字面量 = 0 (除注释/字符串测试) |
| `UNIFIED_INTERFACE_REQUIRED` | 4 个 Adapter validate 签名一致 | `--list` 输出 sig_ok=True × 4 |
| `NO_AUTO_FALLBACK_IN_ADAPTER` | 拒绝路径不重试/切换 provider/model | 拒绝路径 grep `retry/swap/fallback` = 0 |
| `NO_AUTO_MODIFY_POLICY` | Reconciler / Daemon / Hook 不改 policy yaml/.sha256 | reconciler-spec.md §"不变量" + grep |
| `NO_SILENT_DROP_DENY` | 拒绝事件全部留痕 (adapter-rejects.log / cron-validations.log / drift-events.log) | tail audit logs + count 行数 |

---

## 6. 文件清单 (Phase I.3 全部新增)

```
D:\AIOS\_agent-hub\policy\hooks\
└── codex_pre_tool_use_hook.json                (T23 · 落盘参考)

D:\AIOS\_agent-hub\policy\integrations\
└── openclaw_cron_validate.py                   (T24 · validate 集成)

D:\AIOS\_agent-hub\policy\daemons\
├── hermes_daemon.py                             (T25 · daemon 主文件)
├── register_hermes.cmd                         (T25 · mode B 启动钩)
├── hermes_daemon.log                           (T25 · runtime 日志)
└── hermes_daemon.heartbeat.json                (T25 · 心跳)

D:\AIOS\_agent-hub\policy\adapters\
└── __init__.py                                 (T26 · load_all_adapters)

D:\AIOS\openclaw\cron\
├── daily_health_check.yaml                     (T24 · ALLOW 样本)
└── leaked_provider_drift.yaml                  (T24 · DENY 样本)

C:\Users\xinzh\.codex\config.toml               (T23 · [hooks] 段追加)

D:\AIOS\_agent-hub\policy\RUNBOOK.md            (T27 · 本文件)
```

---

## 7. 已知非问题 (留证 · 不修)

| 项 | 说明 | 处置 |
|---|---|---|
| heartbeat `stderr_tail: UnicodeDecodeError` | reconciler 调 `wmic` 时偶发非 UTF-8 字节 | exit_code 仍为 0 · 不影响主流程; W11+ 性能基线时再治本 |
| `register_hermes.cmd` 嵌入 `schtasks /Create` 字串 | mode B 启动钩仅 echo, 不自动注册 | 用户授权后单独跑 schtasks 命令 |
| `D:\AIOS\openclaw\` 此前不存在 | 由 T24 新建 | 仅本批次写入 2 个 yaml + 1 个空目录元数据 |

---

## 8. 与上游 / 下游的依赖

- **上游**: 01a11c30 (Codex supervisor) + 4 adapters (T9-T12) + Reconciler (已注册并跑通)
- **下游**: W8 done 判定 (回归测试 18 项全 PASS) · 此 Runbook 作为 W8 验收依据
- **关联 SSOT**: `adapter-spec.v1.md` + `adapter-contract.md` + `reconciler-spec.md` + `model-policy.v1.yaml`

---

## 9. W8 done 判定 · 5 维清单

| 维 | 检查 | 状态 |
|---|---|---|
| 1. Hook 即时拦截 | Step 1a-1d (含 live DENY 实证) | ✅ |
| 2. Cron validate 集成 | Step 2a-2c (含 live ALLOW + DENY 实证) | ✅ |
| 3. Daemon 真启 | Step 3a-3c (含心跳落盘) | ✅ |
| 4. Adapter 统一签名 | Step 4a-4c (4/4 sig_ok) | ✅ |
| 5. 18 项回归 | Step 5a (全部 PASS) · 5 项契约测试 (Step 5b) | ✅ (与上游并行) |

---

_本文为 AIOS sovereignty-v Phase I.3 唯一权威部署 + 验证手册; Codex 01a11c30 独立验收依据。_