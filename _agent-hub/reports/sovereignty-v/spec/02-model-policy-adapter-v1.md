# T6 Spec — ModelPolicyAdapter v1 · 4 端适配层规范

> **任务**: T6 · 生成 ModelPolicyAdapter 规范 (Codex / Claude Code / OpenClaw / Hermes 四端)
> **时间**: 2026-10-09T00:02Z
> **承接**: T5 ModelPolicy v1 schema

---

## 1. 适配层目的

- ModelPolicy v1 是 declarative schema, 4 个端 (Codex/CC/OpenClaw/Hermes) 的执行机制不同
- Adapter 把同一个 policy **翻译成**每个端能识别的形式,运行时统一校验
- Adapter 是只读 + 写 own layer (cc-switch 写 cc-switch.db, openclaw 写 openclaw.sqlite, 等等)
- Adapter **不**写 user 手工改的文件 (例如 ~/.claude/settings.json)

## 2. 公共接口 (Python · 共享 base)

```python
# aios_kernel/governance/model_policy/adapter_base.py
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime

@dataclass
class PolicySnapshot:
    policy_id: str
    sha256: str
    sig_ed25519: str
    created_at: datetime
    allowlist: List[str]
    denylist: List[str]
    optional: List[str]

@dataclass
class DriftReport:
    adapter_name: str
    drift_kind: str   # "fallback_injection" | "profile_drift" | "provider_drift" | "missing_policy_table"
    severity: str     # "fail_closed" | "fail_open" | "warn"
    affected_paths: List[str]
    recommended_action: str  # "revert" | "warn" | "ignore"

class ModelPolicyAdapter(ABC):
    name: str = "abstract"

    @abstractmethod
    def load_policy(self) -> PolicySnapshot: ...

    @abstractmethod
    def current_state(self) -> Dict[str, any]:
        """读本端的 model 配置当前状态"""

    @abstractmethod
    def apply(self, policy: PolicySnapshot, dry_run: bool = False) -> DriftReport:
        """把 policy 翻译并写本端; 返回本次操作的 drift report"""

    @abstractmethod
    def verify(self, policy: PolicySnapshot) -> DriftReport:
        """读本端当前状态, 比对 policy, 报告 drift 但不写"""
```

## 3. Codex Adapter

```python
# aios_kernel/governance/model_policy/codex_adapter.py
class CodexAdapter(ModelPolicyAdapter):
    name = "codex"

    def __init__(self,
                 config_toml_path: Path = Path.home() / ".codex" / "config.toml",
                 cc_switch_db_path: Path = Path.home() / ".cc-switch" / "cc-switch.db"):
        ...

    def current_state(self) -> Dict:
        # 读 config.toml profiles + cc-switch.db providers + currentProviderCodex
        ...

    def apply(self, policy, dry_run=False) -> DriftReport:
        # 1. 校验 ~/.codex/config.toml 中 profiles 不在 allowlist → 移除 (legacy cleanup)
        # 2. 校验 cc-switch.db 中 currentProviderCodex 对应 provider.model 在 allowlist
        # 3. 如果在 denylist → 切到 allowlist 第一项 (Reconciler 触发)
        # 4. 写 cc-switch.db 中 common_config_codex (model_reasoning_effort = high)
        # 5. 不写 ~/.claude/settings.json (那是 CC Adapter 的事)
        ...
```

### 3.1 Codex Adapter 关键约束
- ✅ 可写: `~/.codex/config.toml` 的 [profiles.*] 段 (legacy cleanup)
- ✅ 可写: cc-switch.db 的 settings.common_config_codex
- ❌ 不可写: ~/.codex/auth.json (凭据由 CredentialSync 单独处理)
- ❌ 不可写: ~/.codex/hooks.json (hash-trusted, 任何修改走 hook 重新签名)

## 4. Claude Code Adapter

```python
# aios_kernel/governance/model_policy/claude_code_adapter.py
class ClaudeCodeAdapter(ModelPolicyAdapter):
    name = "claude-code"

    def __init__(self,
                 settings_json_path: Path = Path.home() / ".claude" / "settings.json",
                 cc_switch_db_path: Path = Path.home() / ".cc-switch" / "cc-switch.db"):
        ...

    def current_state(self) -> Dict:
        # 读 settings.json env 块 + cc-switch.db settings.common_config_claude
        ...

    def apply(self, policy, dry_run=False) -> DriftReport:
        # 1. ⚠️ settings.json 是 _meta.frozen — 只 verify 不 write
        # 2. 写 cc-switch.db settings.common_config_claude (model fallback 强制 MiniMax)
        # 3. 检测到 settings.json 漂移 → 报告 warn (用户手动改, Reconciler 不覆盖)
        ...
```

### 4.1 CC Adapter 关键约束
- ✅ 可写: cc-switch.db 的 settings.common_config_claude
- ❌ 不可写: ~/.claude/settings.json (frozen · _meta.modify_protocol)
- ❌ 不可写: ~/.claude/.mcp.json (用户手工管)
- ❌ 不可写: ~/.claude/CLAUDE.md (Moon Capsule L0 Kernel · R362 立)

## 5. OpenClaw Adapter

```python
# aios_kernel/governance/model_policy/openclaw_adapter.py
class OpenClawAdapter(ModelPolicyAdapter):
    name = "openclaw"

    def __init__(self,
                 openclaw_db_path: Path = Path.home() / ".openclaw" / "state" / "openclaw.sqlite",
                 openclaw_etc: Path = Path.home() / ".openclaw" / "etc" / "policy.yaml",
                 openclaw_env_path: Path = Path.home() / ".openclaw" / ".env"):
        ...

    def current_state(self) -> Dict:
        # 读 sqlite policy_allowlist 表 + 9 个 openclaw-agent.sqlite + .env
        ...

    def apply(self, policy, dry_run=False) -> DriftReport:
        # 1. 写 sqlite policy_allowlist 表 (canonical in openclaw)
        # 2. 镜像 yaml 到 ~/.openclaw/etc/policy.yaml (给 ops 看)
        # 3. 校验 ~/.openclaw/.env 凭据在 allowlist env_keys 中
        # 4. 9 个 openclaw-agent.sqlite 不动 (per-agent model 是 agent 内决策, gateway hook 兜底)
        ...
```

### 5.1 OpenClaw Adapter 关键约束
- ✅ 可写: sqlite policy_allowlist 表 (新建, 已声明)
- ✅ 可写: ~/.openclaw/etc/policy.yaml (新建镜像)
- ✅ 可写: ~/.openclaw/.env 的非凭据字段 (env_keys 校验)
- ❌ 不可写: 9 个 agent DB 各自的 model 字段 (per-agent 决策)
- ❌ 不可写: ~/.openclaw/workspace-*/ 下的任何项目级文件

## 6. Hermes Adapter

```python
# aios_kernel/governance/model_policy/hermes_adapter.py
class HermesAdapter(ModelPolicyAdapter):
    name = "hermes"

    def __init__(self,
                 hermes_home: Path = Path.home() / ".hermes",
                 cli_config_path: Path = Path.home() / ".hermes" / "cli-config.yaml"):
        ...

    def current_state(self) -> Dict:
        # 读 cli-config.yaml (model.provider / model.default) + process env
        ...

    def apply(self, policy, dry_run=False) -> DriftReport:
        # Hermes 是 CLI 一次性, 没有常驻 hook — Reconciler 只 verify + 写 hook 层警告
        # 1. 写 ~/.hermes/cli-config.yaml (model.provider_first: minimax/minimax-cn)
        # 2. 注入 model_aliases 字段, 把 minimax/minimax-cn 排到 --provider 选项前面
        # 3. ⚠️ hermes-agent/providers/ 是 Python 代码, Adapter 不动
        ...
```

### 6.1 Hermes Adapter 关键约束
- ✅ 可写: ~/.hermes/cli-config.yaml (model section)
- ❌ 不可写: hermes-agent/providers/*.py (Python 代码, 改需走代码审查)
- ❌ 不可写: ~/.hermes/gateway-service/hermes-gateway.cmd (WinSW 启动器)

## 7. Reconciler 协调 4 端

```python
# aios_kernel/governance/model_policy/reconciler.py
class ModelPolicyReconciler:
    def __init__(self, adapters: List[ModelPolicyAdapter], policy: PolicySnapshot):
        self.adapters = adapters
        self.policy = policy

    def reconcile(self, dry_run=False) -> List[DriftReport]:
        reports = []
        for adapter in self.adapters:
            snap = adapter.current_state()
            drift = adapter.verify(self.policy)
            if drift.severity == "fail_closed":
                # 强制 revert
                adapter.apply(self.policy, dry_run=dry_run)
                decision_audit.log(adapter.name, drift.kind, "reverted")
            elif drift.severity == "warn":
                decision_audit.log(adapter.name, drift.kind, "warned")
            reports.append(drift)
        return reports
```

## 8. 部署拓扑

```
┌─────────────────────────────────────────────────────────────┐
│  codex_supervisor (singleton, ed25519 sign)                 │
│  └─ ModelPolicy v1.yaml (canonical)                         │
│      ├─ CodexAdapter    → ~/.codex/config.toml + cc-switch  │
│      ├─ ClaudeCodeAdapter → cc-switch common_config_claude │
│      ├─ OpenClawAdapter → sqlite policy_allowlist + etc/   │
│      └─ HermesAdapter   → ~/.hermes/cli-config.yaml         │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ 每 5 分钟扫一次
                              │
┌─────────────────────────────────────────────────────────────┐
│  AIOS_Sovereignty_Reconcile_5min (Task Scheduler)           │
│  触发 ModelPolicyReconciler.reconcile()                     │
└─────────────────────────────────────────────────────────────┘
```

## 9. 红线

- ❌ 任何 Adapter 不写 user-locked 文件 (settings.json / CLAUDE.md / hooks.json 等)
- ❌ 任何 Adapter 不删历史 (只 mark legacy, 不 delete)
- ❌ 任何 Adapter 不改凭据 (凭据由 CredentialSync 单独处理)
- ❌ 任何 Adapter 不直接调用 LLM (Adapter 是 policy 层, 推理由各端自己)
- ❌ 任何 Adapter 不跨端覆盖 (例如 OpenClaw Adapter 不动 ~/.codex)

---

## 10. 落地工件

- `D:\AIOS\_agent-hub\reports\sovereignty-v\spec\02-model-policy-adapter-v1.md` (本文件)
- 未来落地: `aios_kernel/governance/model_policy/adapter_base.py` (待用户授权 git init)
- 未来落地: `aios_kernel/governance/model_policy/{codex,claude_code,openclaw,hermes}_adapter.py`
- 未来落地: `aios_kernel/governance/model_policy/reconciler.py`
