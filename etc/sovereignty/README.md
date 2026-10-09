# AIOS-SOVEREIGNTY-V · ModelPolicy v1

> Canonical ModelPolicy + Reconciler package for AIOS multi-agent stack.
> Owner: codex-supervisor · Authorizer: user-2026-10-08T23:55

## Files

| File | Purpose |
|---|---|
| `model-policy.v1.yaml` | Canonical policy (ed25519 signed) |
| `codex_supervisor.ed25519.{key,pub}` | Signer keypair · pub is committed, key is local-only (chmod 600) |
| `powershell_profile_aios.ps1` | PowerShell profile hook to invoke reconciler on shell start |
| `codex_supervisor.ed25519.key` | PRIVATE KEY (NEVER commit to remote) |

## What the policy does

- **allowlist** (canonical providers/models): `MiniMax-M3`, `MiniMax-M2.7`, `MiniMax-M2.7-highspeed` (+ 3 optional agnes-II)
- **denylist** (11 historical): `deepseek-v4-{pro,flash}`, `qwen3:14b`, `qwen2.5:7b`, `qwen3-coder-plus`, `qwen3.7-flash`, `agnes-2.5-flash` (R159b), `glm-4-flash`, `glm-4.7-flash`, `gpt-5.6-sol`, `openai/gpt-5.6-sol`
- **enforcement.cc_switch.common_config_claude**: lock Claude Code fallback chain to MiniMax-only
- **enforcement.cc_switch.common_config_codex**: lock Codex reasoning_effort = "high"
- **enforcement.codex_config_toml.profiles_legacy_cleanup**: [ollama, qwen25] to remove in next sweep
- **enforcement.openclaw** : write policy_allowlist table + mirror yaml
- **enforcement.hermes.cli_config_provider_first**: [minimax, minimax-cn]
- **credential_sync.ssot**: mcp_credentials.env (local, not in git)

## Reconciliation flow

```
python -m aios_kernel.governance.model_policy.reconciler [--mode {scheduled,onstart,daemon}] [--interval N] [--dry-run]
```

Modes:
- `scheduled` (one-shot, default) — invoked by AIOS_Sovereignty_Reconcile_5min Task Scheduler
- `onstart` (one-shot) — invoked by PowerShell profile hook
- `daemon` (loop with `--interval 30`) — invoked by WinSW service

## Adapters

| Adapter | Writes | Does NOT write |
|---|---|---|
| CodexAdapter | `~/.codex/config.toml` profiles (legacy cleanup); `~/.cc-switch/cc-switch.db` settings.common_config_codex | hooks.json, auth.json |
| ClaudeCodeAdapter | `~/.cc-switch/cc-switch.db` settings.common_config_claude.env (preserves permissions/hooks) | settings.json (frozen), CLAUDE.md, .mcp.json |
| OpenClawAdapter | `~/.openclaw/state/openclaw.sqlite` policy_allowlist table; `~/.openclaw/etc/policy.yaml` mirror; `~/.openclaw/.env` env_keys validate | 9 agent sub-databases; workspace-*/ files |
| HermesAdapter | (read-only verify — Hermes is CLI-on-demand, user-managed) | hermes-agent/providers/*.py; cli-config.yaml (suggest only) |

## CI gate

```bash
python D:\\AIOS\\kernel\\scripts\\ci_verify_sovereignty.py [--strict]
```

4 stages:
1. Verify ed25519 signature
2. Run unit tests (14)
3. Run integration/e2e/compat tests (12)
4. Secret scan (14 patterns × 6526 files)

Recommended: hook into `AIOS_E2E_Stress_CI_Gate` (Ready) as pre-deploy gate.

## Deployment

| Component | Status | Path |
|---|---|---|
| Scheduled Task (5min) | Ready | `\AIOS\AIOS_Sovereignty_Reconcile_5min` |
| WinSW service (30s loop) | Running | `aios-sovereignty-reconciler` (D:\AIOS\daemons_v2\winsw\) |
| PowerShell profile hook | Active | `D:\Documents\PowerShell\Microsoft.PowerShell_profile.ps1` |
| GitHub repo | public | https://github.com/macxiaxia-boop/aios-sovereignty-v |

## Red lines (Phase F + sovereignty-v)

1. ❌ Asymmetric write — never modify user-locked files (settings.json / CLAUDE.md / hooks.json)
2. ❌ Hardcode secrets — `<REDACTED>` placeholders, real values only in mcp_credentials.env
3. ❌ Bypass Adapter for fallback — handled by Reconciler auto-revert
4. ❌ Self-fill skill gaps — needs Decision Audit approval (Phase F decision_service)
5. ❌ Skip signature verification — load_policy fails closed on missing signature

## Operational runbook

| Symptom | Diagnosis | Fix |
|---|---|---|
| Reconciler drift on cc-switch common_config_claude | Some user/process overwrote env block | Wait 5 min (auto-revert) OR run `--mode scheduled` |
| pytest baseline DEGRADED (4 fail + 2 err) | Pre-existing tests in test_services_persistence.py + test_migration.py | Out of sovereignty-V scope; needs Phase A5 governance engineering |
| 02-env-snapshot.txt has real `sk-*` | (Fixed R2026-10-09T01:01Z via sanitization) | Run `scripts/ci_verify_sovereignty.py --strict` |
| WinSW service Stopped | winsw.exe not running | | `cd D:\\AIOS\\daemons_v2\\winsw\\aios-sovereignty-reconciler; .\\aios\\xies-reconciler.exe start`

## Reference

- Phase F governance package: `D:\\AIOS\\kernel\\src\\aios_kernel\\governance\\goal_guard.py`
- GoalContract 12 fields: `D:\\AIOS\\kernel\\src\\aios_kernel\\domain\\goal.py`
- DecisionAudit: `D:\\AIOS\\kernel\\src\\aios_kernel\\domain\\decision.py`
- Sovereignty-V final report: `D:\\AIOS\\_agent-hub\\reports\\sovereignty-v\\final\\aios-sovereignty-v-done-20261009.md`
