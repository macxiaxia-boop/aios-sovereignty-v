# T5 Spec — ModelPolicy v1 YAML schema

> **任务**: T5 · 生成 ModelPolicy v1 YAML 规范（含 hash + 签名 + 只写权收口）
> **时间**: 2026-10-09T00:01Z
> **承接**: T1-T4 审计 + 用户长期决策 "AIOS 统一使用 MiniMax"

---

## 1. 文件定位

- **SSOT 文件**: `D:\AIOS\kernel\etc\sovereignty\model-policy.v1.yaml`
- **写权收口**: 只有 `codex` supervisor 可写; CC / OpenClaw / Hermes **只读**
- **对接 openclaw**: `~/.openclaw/state/openclaw.sqlite` 中 `policy_allowlist` 表 + `~/.openclaw/etc/policy.yaml` 镜像
- **对接 cc-switch**: cc-switch 启动时读取本文件, 写入 `common_config_*` 时受 schema 限制
- **hash + 签名**: sha256(content) + ed25519(codex_supervisor_priv) 双锁

## 2. Schema (v1)

```yaml
# model-policy.v1.yaml
schema_version: "1.0.0"
policy_id: "mp-2026-10-09-0001"   # monotonic, immutable once published
created_at: "2026-10-09T00:00:00+08:00"
created_by: "codex-supervisor"
authorizer: "user-2026-10-08T23:55"   # 全量授权 T1-T8
hash_alg: "sha256"
sig_alg: "ed25519"

# === 决策表: 哪些 model 是允许的 ===
allowlist:
  # 用户长期决策 (T1-T4 已确认 MiniMax 为 canonical)
  providers:
    - id: "MiniMax"
      display_name: "MiniMax"
      type: "primary"
      base_urls:
        - "https://api.minimaxi.com/v1"
        - "https://api.minimaxi.com/anthropic"
      auth:
        env_keys:
          - "MINIMAX_API_KEY"
          - "MINIMAX_CN_API_KEY"
          - "ANTHROPIC_AUTH_TOKEN"
        token_ref: "mcp_credentials.env"
      models:
        - id: "MiniMax-M3"
          role: [main, fallback, opus]
          reasoning_effort: ["high", "medium", "low", "none"]
          context_window: 100000
          max_output: 8000
          thinking_budget: 32000
        - id: "MiniMax-M2.7"
          role: [subagent, haiku, fallback]
          reasoning_effort: ["medium", "low"]
          context_window: 100000
          max_output: 8000
        - id: "MiniMax-M2.7-highspeed"
          role: [haiku, small_fast]
          reasoning_effort: ["low", "none"]
          context_window: 100000
          max_output: 8000

  # 显式拒绝 (历史 / 已废弃 / 用户已表态不再用)
  denylist:
    - id: "deepseek-v4-pro"
      reason: "R262: cc 是智障, 现在默认用的就是 MiniMax"
      effective_from: "2026-10-09T00:00:00+08:00"
      - id: "deepseek-v4-flash"
      reason: "R262 同上"
      - id: "qwen3:14b"
      reason: "ollama local — 用户已决定不再用 ollama 默认"
      - id: "qwen2.5:7b"
      reason: "同上"
      - id: "qwen3-coder-plus"
      reason: "用户没有把 qwen 接入默认"
      - id: "qwen3.7-flash"
      reason: "同上"
      - id: "agnes-2.5-flash"
      reason: "R159b 用户已改用 agnes-II"
      - id: "agnes-2.5-pro-alpha"
      reason: "可选但非 canonical, 列入可选区"
      - id: "agnes-3.0-flash"
      reason: "可选但非 canonical"
      - id: "glm-4-flash"
      reason: "智谱 — 非 canonical"
      - id: "glm-4.7-flash"
      reason: "智谱 — 非 canonical"
      - id: "gpt-5.6-sol"
      reason: "OpenAI Atlas — 非 canonical"
      - id: "openai/gpt-5.6-sol"
      reason: "同上 hermes 镜像"

  # 可选区 (denylist 之外但 allowlist 之内 = 明确允许)
  optional:
    - id: "MiniMax-M3"
      note: "默认 primary"
    - id: "MiniMax-M2.7"
      note: "subagent 默认"
    - id: "MiniMax-M2.7-highspeed"
      note: "小模型/快速"

# === 跨端执行约束 ===
enforcement:
  cc_switch:
    common_config_claude:
      ANTHROPIC_DEFAULT_OPUS_MODEL: "MiniMax-M3"
      ANTHROPIC_DEFAULT_SONNET_MODEL: "MiniMax-M3"
      ANTHROPIC_DEFAULT_HAIKU_MODEL: "MiniMax-M2.7"
      ANTHROPIC_SMALL_FAST_MODEL: "MiniMax-M2.7-highspeed"
      CLAUDE_CODE_SUBAGENT_MODEL: "MiniMax-M2.7"
      ANTHROPIC_DEFAULT_OPUS_MODEL_FALLBACK: "MiniMax-M3"
      ANTHROPIC_DEFAULT_SONNET_MODEL_FALLBACK: "MiniMax-M2.7"
      ANTHROPIC_DEFAULT_HAIKU_MODEL_FALLBACK: "MiniMax-M2.7"
      # ❌ 不再允许 deepseek fallback (R262 用户决策)
    common_config_codex:
      model_reasoning_effort: "high"
    common_config_openclaw:
      meta.migrations.modelPolicyAllowlist: true
  codex_config_toml:
      profiles_legacy_cleanup: ["ollama", "qwen25"]
      allowed_profiles: []
  cc_settings_json:
    # ⚠️ _meta.modify_protocol = "any 修改前必须先 ask_user"
    # ❌ 不要直接动 ~/.claude/settings.json — Reconciler 只做 fallback 校验,不动 settings.json 主块
    frozen: true
  openclaw:
    sqlite_table: "policy_allowlist"
    yaml_mirror: "~/.openclaw/etc/policy.yaml"
    gateway_hook: "aios_kernel.governance.model_policy_hook"
  hermes:
    cli_config_provider_first: ["minimax", "minimax-cn"]
    cli_config_provider_denylist: ["openrouter", "anthropic", "ollama-cloud", "copilot", "nous", "nous-api", "openai-codex", "gemini", "zai", "kimi-coding", "huggingface", "nvidia", "xiaomi", "arcee", "kilocode", "azure-foundry", "lmstudio"]
    # hermes 是 CLI 一次性, Reconciler 不强改 cli-config,只在 hook 层 reject

# === 凭据同步 ===
credential_sync:
  ssot: "mcp_credentials.env"   # 用户已有, 标 SSOT
  mirrors:
    - "~/.openclaw/.env"
    - "~/.claude/settings.json" (env.ANTHROPIC_AUTH_TOKEN, frozen — Reconciler 只校验, 不主动覆盖)
    - "~/.codex/auth.json"
    - "process.env.MINIMAX_API_KEY / MINIMAX_CN_API_KEY"
  rotation_protocol: "红线 #62 双轨 SSOT — 改 SSOT 后自动同步 4 处镜像"
  validator: "aios_kernel.governance.credential_sync.Validator"

# === 治理 ===
governance:
  owner: "codex-supervisor"
  required_signers: ["codex-supervisor-ed25519"]
  quorum: 1
  mutation_window:
    min_interval_seconds: 60
    max_changes_per_day: 10
  audit:
    log_table: "decision_audit"
    append_only: true
    boundary_check: "aios_kernel.governance.decision_service.DecisionService"

# === 签名 ===
signature:
  alg: "ed25519"
  public_key_path: "D:\\AIOS\\kernel\\etc\\sovereignty\\model-policy.v1.pub"
  value: "<待 codex_supervisor 私钥签名后填入>"
```

## 3. Schema 关键约束

### 3.1 只写权收口
- `~/.codex/config.toml` 任何 profile / model 字段变更 → 必须由 Reconciler 写入, 不是手写
- cc-switch 的 `currentProviderCodex` / `currentProviderClaude` 切换 → 必须由 Reconciler 校验后才能落库
- 用户手动改 `settings.json` env 块 → Reconciler **不**覆盖 (frozen), 但下次启动时检测到 drift 会**警告**而非强制恢复

### 3.2 拒绝语义
- `denylist` 是 fail-closed: 任何 cc-switch / openclaw / hermes 注入 denylist 模型 → Reconciler **立即 revert**
- `optional` 是 fail-open: 注入可选区模型 → Reconciler 仅 log, 不强制 revert

### 3.3 签名与 hash
- 每次 model-policy.v1.yaml 修改 → 重新计算 sha256 + ed25519
- 旧版本归档到 `D:\AIOS\kernel\etc\sovereignty\history\model-policy.v1.YYYYMMDD-HHMM.yaml.sig`
- Reconciler 启动时校验 signature → 不匹配 = FAIL + revert to last known good

## 4. 与 Phase F 复用

- **GoalContract 12 字段**: ModelPolicy 触发 goal 后, 经 `aios_kernel.intent.parser.IntentParser` 编译 → 写入 `aios_kernel.governance.goal_guard.GoalGuard`
- **Decision Audit Log**: 每次 policy 应用写一条 decision_audit
- **Intent Parser**: 用户口头 "切到 MiniMax-M2.7" 自动编译 → 触发 model_policy.apply
- **Failure Pattern Merger**: model drift 失败归并到 cluster "policy_drift"

## 5. 红线

- ❌ 不要直接写 `~/.claude/settings.json` (frozen · modify_protocol 要求 ask_user)
- ❌ 不要删 denylist 中的历史 provider (历史数据迁移回滚需要)
- ❌ 不要把 hermes / openclaw / cc-switch 任何 user-modified 字段自动覆盖
- ❌ 不要在 ModelPolicy 里硬编码 `sk-cp-...` 真实 token — 用 env var 名占位
- ❌ 不要做未授权 model add (任何新模型需走 DecisionService 审计链)

---

## 6. 落地工件

- `D:\AIOS\kernel\etc\sovereignty\model-policy.v1.yaml` (canonical)
- `D:\AIOS\kernel\etc\sovereignty\model-policy.v1.pub` (ed25519 公钥,生成时附)
- `D:\AIOS\kernel\etc\sovereignty\history\*.yaml.sig` (历史归档)
- `D:\AIOS\_agent-hub\reports\sovereignty-v\spec\01-model-policy-v1.md` (本文件)
- `D:\AIOS\_agent-hub\reports\sovereignty-v\spec\01-model-policy-v1.yaml` (示例 YAML, 待用户授权后复制到 canonical)
