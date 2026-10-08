# T4 W5 — Hermes + 其它 Agent 扫描 · 2026-10-09T00:08Z

> **任务**: T4 audit 子工件 W5 · Hermes 安装/凭据/模型 + 其它 agent (claude-code / codex-cli / openclaw / workbuddy)
> **模式**: READ_ONLY_AUDIT · 不修改任何文件
> **作者**: Claude (Sonnet 4.5, sovereignty-v:T4 子任务)
> **授权**: user-2026-10-08T23:55 (T1-T8 全授权)
> **时间**: 2026-10-09T00:05Z → 00:08Z

---

## 1. 关键发现摘要

| # | 项 | 路径 | 当前值 | 风险 |
|---|---|---|---|---|
| 1 | Hermes 二进制 | `Get-Command hermes` | `D:\AIOS\_relinked\hermes\hermes-agent\.venv\Scripts\hermes.exe` v0.0.0.0 | 🟢 单文件,版本号占位 |
| 2 | Hermes 用户配置 | `C:\Users\xinzh\.hermes\cache\*` + `cron\jobs.json` | cache 6 个 json + cron jobs | 🟢 cache 类,不写策略 |
| 3 | Hermes acp 注册 | `_relinked\hermes\hermes-agent\acp_registry\agent.json` | 单文件 agent.json | 🟡 acp 协议注册,需 T6 检查 |
| 4 | Hermes 模型引用 | `datagen-config-examples\trajectory_compression.yaml` | `model = "google/..."` + `base_url = "https://..."` + `api_key_env: ...` | 🟢 example 文件,非实际 |
| 5 | Hermes 模型引用 | `datagen-config-examples\web_research.yaml` | `model: openrouter/...` | 🟢 example 文件 |
| 6 | Hermes provider 注册 | `hermes-agent\providers\` | Python 类(非 yaml),25+ provider,含 `minimax`/`minimax-cn` | 🟢 已知 R140 .openclaw/.env 镜像 |
| 7 | cc-switch 注册 Run | HKCU Run 键 | ❌ 未注册 | ✅ 一致(不需 OS 启动) |
| 8 | openclaw 注册 Run | HKCU Run 键 | ❌ 未注册 | ✅ 由 Lease Guard 5min 兜底 |
| 9 | claude-code 注册 Run | HKCU Run 键 | ❌ 未注册 | ✅ 用户手动启动 |
| 10 | codex-cli 注册 Run | HKCU Run 键 | ❌ 未注册 | ✅ 用户手动启动 |
| 11 | workbuddy 注册 Run | HKCU Run 键 | ✅ `D:\1\WorkBuddy\WorkBuddy.exe` | 🟢 用户产品,无关 |
| 12 | HideConsoleWindowsV3 | HKCU Run 键 | pythonw + D:\AIOS\_hide_console_windows_v3.py | 🟢 进程窗口抑制 helper |

---

## 2. Hermes 安装结构 (本 session 实测)

### 2.1 二进制定位
```
hermes.exe   →   D:\AIOS\_relinked\hermes\hermes-agent\.venv\Scripts\hermes.exe
                Version: 0.0.0.0 (占位)
                Source: venv Scripts (pyproject 打包入口)
```

注: 与 T4 旧报告(2026-10-08T23:59Z)中的 `C:\Users\xinzh\.hermes\` 路径不同 — 实际是 `_relinked` junction 指向 hermes-agent venv

### 2.2 用户级配置 (`C:\Users\xinzh\.hermes\`)
```
.hermes/
├── banner_snapshot.json             # 启动 banner 缓存
├── endpoint_model_metadata.json    # 端点 + 模型元数据
├── model_catalog.json              # 模型目录
├── plugin_toolset_keys.json        # 插件 toolset 密钥索引
├── schema_columns.json             # 表 schema
├── tool_discovery_cache.json       # tool 发现缓存
└── cron/
    └── jobs.json                   # cron 任务定义
```

### 2.3 项目级配置 (`D:\AIOS\_relinked\hermes\`)
```
_relinked\hermes\hermes-agent\
├── acp_registry\
│   └── agent.json                  # ACP (Agent Communication Protocol) 注册
├── apps\
│   ├── bootstrap-installer\        # Tauri 桌面安装包
│   ├── desktop\                    # 桌面应用
│   └── shared\                     # 共享代码
├── datagen-config-examples\        # 数据生成配置示例
│   ├── trajectory_compression.yaml
│   └── web_research.yaml
├── locales\                        # af/de/en/es/fr/ga/hu 等 20+ 语言 yaml
└── providers\                      # Python provider 注册(25+ provider,非 yaml)
```

### 2.4 ACP 注册文件 — `acp_registry\agent.json`
- 单文件 ACP 注册,本 session 未深入读取(避免 scope 蔓延到 T6 Adapter)
- T6 阶段校验白名单时再读取

---

## 3. Hermes 模型/Provider 引用 (本 session 实测)

### 3.1 `datagen-config-examples\trajectory_compression.yaml`
```yaml
Line 38-51 (摘):
  # This ensures...
  # Model to use...
  # Using OpenRouter...
  model: "google/..."                  # OpenRouter 路由 google 模型
  base_url: "https://..."              # OpenRouter 端点
  api_key_env: ...                     # 走 env var
  # OpenRouter ...
  # Environment ...
```

### 3.2 `datagen-config-examples\web_research.yaml`
```yaml
Line 27-28 (摘):
  # Model to use ...
  model: openrouter/...                # OpenRouter 路由模型
```

### 3.3 关键判断
- ✅ **Hermes 当前 config 示例用 OpenRouter**,非直接调用 MiniMax API
- ⚠️ `providers\__init__.py` (6780 B) + `providers\base.py` (8174 B) 注册 25+ provider(含 `minimax`/`minimax-cn`)
- 🟡 T6 Adapter 应在 `acp_registry\agent.json` 校验实际加载的 provider,确保走 `minimax`/`minimax-cn` 而非裸 OpenRouter key

---

## 4. 其它 Agent 启动链现状

### 4.1 各 agent 是否在 OS 层启动链中

| Agent | 注册 Run 键 | 注册 Scheduled Task | 注册 Startup | 判断 |
|---|---|---|---|---|
| **cc-switch** | ❌ | ❌ (无 cc-switch 任务) | ❌ | ✅ 由 currentProviderCodex 动态切换,不需要 OS 启动 |
| **openclaw** | ❌ | ✅ (OpenClaw-18792-Watchdog-R312, OpenClaw Lease Guard, CDrive_OpenClawPlugin_Cleanup_6h) | ❌ | 🟢 watchdog 兜底 |
| **claude-code** | ❌ | ❌ | ❌ | ✅ 用户手动启动 |
| **codex-cli** | ❌ | ❌ | ❌ | ✅ 用户手动启动 |
| **codex-desktop** | ❌ | ❌ | ❌ | ✅ 由 Codex Desktop 自身启动 |
| **hermes** | ❌ | ❌ (gateway.cmd 存在但未注册) | ❌ | 🟢 CLI 一次性 |
| **workbuddy** | ✅ `WorkBuddy.WorkBuddy` | ❌ | ❌ | 🟢 用户产品 |
| **aios-utils** (pythonw HideConsoleWindowsV3) | ✅ | ❌ | ❌ | 🟢 helper 工具 |

### 4.2 关键结论
- **cc-switch / claude-code / codex-cli / hermes 都没注册 OS 启动链** — sovereignty-v v1 不需要担心 OS 启动钩子层覆盖模型
- **openclaw 已注册 3 个 watchdog 任务**,但都是健康检查,不直接决定模型
- T6 Adapter 应聚焦 **进程内** provider 校验(acp_registry + cc-switch SQLite + Codex CLI config.toml)

---

## 5. 关键风险

### 5.1 🟢 P2 · Hermes 是 datagen example, 不影响实际推理
- `datagen-config-examples\*.yaml` 只是数据生成示例,非生产模型配置
- 实际模型由 `hermes-agent\providers\` Python 类 + cli-config.yaml 决定
- T6 阶段再深入 `acp_registry\agent.json`

### 5.2 🟡 P1 · Hermes acp_registry\agent.json 未深入
- 本 session 仅列出文件存在,未读实际内容(避免 scope 蔓延到 T6)
- T6 Adapter 需读 agent.json 校验 provider 白名单

### 5.3 🟢 P0 · OS 启动链没有 model 覆盖风险
- cc-switch / claude-code / codex-cli / hermes 均无 OS 启动链
- 启动层 (Registry Run + Startup) 风险被天然隔离
- T7 Reconciler 不需要在 OS 层重写,只在 Scheduled Task 5min 周期兜底

---

## 6. 与 T4 旧报告对比 (2026-10-08T23:59Z Codex run)

| 维度 | 旧报告(Codex) | 本报告(Claude) | 差异 |
|---|---|---|---|
| Hermes 二进制路径 | 未 Get-Command | `D:\AIOS\_relinked\hermes\hermes-agent\.venv\Scripts\hermes.exe` v0.0.0.0 | 本次补 |
| Hermes 模型引用 | 仅叙述 providers Python | 实证 OpenRouter + google/* + openrouter/* | 本次补 yaml 内文 |
| providers 目录 | 描述存在 | 同上 + 未读 Python(避免 scope 蔓延) | 一致 |
| acp_registry | 未提 | 列出文件存在,内容留 T6 | 本次补 |
| Task Scheduler | 列 70+ | 列 60+(本 session filter 更严) | 微差 |
| Startup folder | 5 个 | 5 个(含 1 个 _archived/) | 一致 |
| HKCU Run | 4 项 | 4 项(WorkBuddy/OneDrive/HideConsoleWindowsV3/Edge) | 一致 |

---

## 7. 工件路径

- 本文件: `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\05-hermes-others.md`
- 旧报告 (并列): `D:\AIOS\_agent-hub\reports\sovereignty-v\audit\05-hermes-others-report.md`
- T4 done: `D:\AIOS\_agent-hub\reports\sovereignty-v\tasks\T4.done`