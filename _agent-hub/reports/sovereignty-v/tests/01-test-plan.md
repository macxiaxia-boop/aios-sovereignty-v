# T8 Plan — 回归测试 1-18 项 (PowerShell + Playwright 草稿)

> **任务**: T8 · 回归测试 1-18 项 Playwright/PowerShell 草稿落盘
> **时间**: 2026-10-09T00:05Z
> **承接**: T5 + T6 + T7 · ModelPolicy + Adapter + Reconciler 全栈

---

## 1. 测试分类

| 类别 | 数量 | 工具 |
|---|---|---|
| 单元测试 (Adapter 各端逻辑) | 6 | pytest |
| 集成测试 (cc-switch / openclaw sqlite) | 4 | pytest + sqlite3 |
| 端到端 (Reconciler 实际跑) | 4 | PowerShell |
| 兼容 (Hermes / Codex CLI / CC CLI) | 4 | PowerShell + Bash |

## 2. 测试清单 (18 项)

### 单元 (6 项)

| # | 名称 | 验证点 |
|---|---|---|
| 01 | test_codex_adapter_load_policy | CodexAdapter.load_policy() 正确读 model-policy.v1.yaml |
| 02 | test_codex_adapter_current_state | CodexAdapter.current_state() 正确读 ~/.codex/config.toml + cc-switch.db |
| 03 | test_claude_code_adapter_drift | CC Adapter 检测到 settings.json 中 ANTHROPIC_MODEL 被改成非 allowlist 模型 → fail_closed |
| 04 | test_openclaw_adapter_allowlist_table | OpenClawAdapter.apply() 正确写 sqlite policy_allowlist 表 |
| 05 | test_hermes_adapter_provider_first | HermesAdapter.apply() 正确把 minimax/minimax-cn 排到 cli-config.yaml provider_first |
| 06 | test_reconciler_quorum | Reconciler 4 端 quorum=1 时 1 个 fail_closed 触发整体 revert |

### 集成 (4 项)

| # | 名称 | 验证点 |
|---|---|---|
| 07 | test_cc_switch_common_config_claude_written | Reconciler.apply() 后, cc-switch.db settings.common_config_claude 中 fallback 全是 MiniMax |
| 08 | test_cc_switch_common_config_claude_drift_revert | 手动改 common_config_claude 为 deepseek → Reconciler 自动 revert |
| 09 | test_openclaw_sqlite_policy_allowlist_revert | 手动删 policy_allowlist 表行 → Reconciler 重写 |
| 10 | test_openclaw_env_credential_validate | .env 中 MINIMAX_API_KEY 缺失 → fail_closed (红线 #62 双轨 SSOT) |

### 端到端 (4 项)

| # | 名称 | 验证点 |
|---|---|---|
| 11 | e2e_powershell_reconcile_dry_run | `python -m reconciler --mode scheduled --dry-run` 返回 0 + 无写盘 |
| 12 | e2e_powershell_reconcile_real | `python -m reconciler --mode scheduled` 实际写 cc-switch.db + openclaw.sqlite + .env |
| 13 | e2e_drift_simulation | 模拟 user 改 ~/.codex/auth.json → Reconciler 检测 + report warn (不覆盖) |
| 14 | e2e_audit_decision_log | 每次 apply() 写一条 decision_audit 行 + 包含 policy_id + adapter_name + drift_kind |

### 兼容 (4 项)

| # | 名称 | 验证点 |
|---|---|---|
| 15 | compat_codex_cli_invoke | `codex -c model=...` 命令, args 中 model 不在 allowlist → 启动时报错 |
| 16 | compat_claude_code_invoke | `claude --model ...` 命令, model 不在 allowlist → fallback 到 MiniMax-M3 |
| 17 | compat_openclaw_gateway_start | OpenClaw gateway 启动时读 policy_allowlist 表 → non-allowlist provider reject |
| 18 | compat_hermes_mcp_serve | `hermes mcp serve --provider ...` provider 不在 allowlist → fallback 到 minimax |

## 3. 草稿落盘清单

| 路径 | 内容 | 行数估算 |
|---|---|---|
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_01_codex_load_policy.py` | 单元 01 | 80 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_02_codex_current_state.py` | 单元 02 | 100 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_03_cc_drift.py` | 单元 03 | 120 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_04_openclaw_table.py` | 单元 04 | 100 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_05_hermes_first.py` | 单元 05 | 80 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_06_reconciler_quorum.py` | 单元 06 | 90 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_07_cc_common_config.py` | 集成 07 | 90 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_08_drift_revert.py` | 集成 08 | 110 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_09_openclaw_revert.py` | 集成 09 | 90 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_10_env_credential.py` | 集成 10 | 80 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\e2e_11_dry_run.ps1` | 端到端 11 | 30 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\e2e_12_real.ps1` | 端到端 12 | 40 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\e2e_13_drift_sim.ps1` | 端到端 13 | 50 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\e2e_14_audit_log.ps1` | 端到端 14 | 40 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\compat_15_codex.ps1` | 兼容 15 | 30 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\compat_16_claude.ps1` | 兼容 16 | 30 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\compat_17_openclaw_gateway.ps1` | 兼容 17 | 30 |
| `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\compat_18_hermes.ps1` | 兼容 18 | 30 |

## 4. 草稿示例

### 4.1 单元 03 (CC Drift) 草稿

```python
# test_03_cc_drift.py
import sqlite3, json, shutil
from pathlib import Path
from aios_kernel.governance.model_policy.claude_code_adapter import ClaudeCodeAdapter
from aios_kernel/governance.model_policy.snapshot import PolicySnapshot

def test_claude_code_adapter_drift_fail_closed(tmp_path):
    # Arrange: 用户手动改 settings.json 中 ANTHROPIC_MODEL 为 deepseek-v4-pro
    settings_json = tmp_path / "settings.json"
    settings_json.write_text(json.dumps({
        "_meta": {"frozen": True},
        "env": {"ANTHROPIC_MODEL": "deepseek-v4-pro"}
    }))

    cc_switch_db = tmp_path / "cc-switch.db"
    db = sqlite3.connect(cc_switch_db)
    db.execute("CREATE TABLE settings (key TEXT, value TEXT)")
    db.execute("INSERT INTO settings VALUES ('common_config_claude', ?)",
               json.dumps({"ANTHROPIC_DEFAULT_OPUS_MODEL": "deepseek-v4-pro"}))
    db.commit()
    db.close()

    adapter = ClaudeCodeAdapter(settings_json_path=settings_json, cc_switch_db_path=cc_switch_db)
    policy = PolicySnapshot(
        policy_id="mp-test-001",
        sha256="0" * 64,
        sig_ed25519="0" * 128,
        allowlist=["MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed"],
        denylist=["deepseek-v4-pro", "deepseek-v4-flash"],
        optional=[],
    )

    # Act
    drift = adapter.verify(policy)

    # Assert
    assert drift.severity == "fail_closed"
    assert "deepseek-v4-pro" in drift.affected_paths
    assert drift.recommended_action == "revert"
```

### 4.2 端到端 12 (Real reconcile) 草稿

```powershell
# e2e_12_real.ps1
$ErrorActionPreference = "Stop"

Write-Host "=== E2E 12 · Real reconcile ===" -ForegroundColor Cyan

$python = "D:\AIOS\kernel\.venv\Scripts\python.exe"
$reconciler = "-m aios_kernel.governance.model_policy.reconciler"

# 1. 备份当前状态
$backupDir = "D:\AIOS\_agent-hub\reports\sovereignty-v\tests\e2e_12_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
New-Item -ItemType Directory -Force -Path $backupDir | Out-Null
Copy-Item "$env:USERPROFILE\.cc-switch\cc-switch.db" "$backupDir\cc-switch.db"
Copy-Item "$env:USERPROFILE\.openclaw\state\openclaw.sqlite" "$backupDir\openclaw.sqlite"

# 2. 跑 reconcile
& $python $reconciler --mode scheduled 2>&1 | Tee-Object "$backupDir\reconcile.log"

# 3. 验证结果
$ccDb = sqlite3 "$env:USERPROFILE\.cc-switch\cc-switch.db" ".tables"
Write-Host "cc-switch.db tables: $ccDb"

# 4. 比对备份
$currentMd5 = (Get-FileHash "$env:USERPROFILE\.cc-switch\cc-switch.db" -Algorithm MD5).Hash
$backupMd5 = (Get-FileHash "$backupDir\cc-switch.db" -Algorithm MD5).Hash
Write-Host "cc-switch.db changed: $($currentMd5 -ne $backupMd5)"

# 5. 失败时回滚
if ($LASTEXITCODE -ne 0) {
    Write-Host "FAILED — restoring backup" -ForegroundColor Red
    Copy-Item "$backupDir\cc-switch.db" "$env:USERPROFILE\.cc-switch\cc-switch.db" -Force
    exit 1
}

Write-Host "PASS" -ForegroundColor Green
exit 0
```

## 5. 运行框架

- **pytest**: `cd D:\AIOS\kernel\.venv && python -m pytest D:\AIOS\_agent-hub\reports\sovereignty-v\tests\test_*.py -v`
- **PowerShell e2e**: `pwsh D:\AIOS\_agent-hub\reports\sovereignty-v\tests\e2e_*.ps1`
- **PowerShell compat**: `pwsh D:\AIOS\_agent-hub\reports\sovereignty-v\tests\compat_*.ps1`
- **CI 集成**: 接入 AIOS_E2E_Stress_CI_Gate (Ready) 作为 gate step

## 6. 红线

- ❌ 真实生产环境的 cc-switch.db / openclaw.sqlite 在测试前必须备份 (上面已加)
- ❌ e2e 12 (real) 不能在生产跑 — 必须先 dev/staging
- ❌ compat 15-18 测试前要验证 codex/claude/openclaw/hermes CLI 真实可执行
- ❌ 任何测试失败不能自动重试超过 1 次 (防止 drift 累加)
- ❌ 测试不能写 user $PROFILE (T7 红线)

## 7. 落地工件

- `D:\AIOS\_agent-hub\reports\sovereignty-v\tests\01-test-plan.md` (本文件)
- 18 份测试草稿 (`tests/test_*.py` + `tests/e2e_*.ps1` + `tests/compat_*.ps1`)
