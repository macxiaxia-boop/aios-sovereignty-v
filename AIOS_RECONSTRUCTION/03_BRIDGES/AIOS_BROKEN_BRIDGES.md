# AIOS Broken Bridges Report · R212 · 2026-09-26

**spec#37 Broken Bridge Registry**

## Currently Broken / Partial

### 1. `br-aios-hermes` (AIOS → Hermes Agent)
- **Status**: ✅ **RESOLVED 2026-09-27 (R260 audit)** · moved to "Recently Repaired"
- **Root-cause analysis (R260)**: The R211 diagnosis was based on incorrect version labels (v0.21.3 D vs v0.15.1 C). Both binaries actually report **v0.15.1 (2026.5.29)** with identical pyproject.toml sha `65cad64739fd98a0`. There is no PATH conflict — both paths point to the same version.
- **Current state**: PATH priority correctly to D drive (`D:\AIOS\_relinked\hermes\hermes-agent\.venv\Scripts\hermes.exe`). Binary is functional.
- **Bridge registry updated**: `status=active, health=healthy` per `AIOS_BRIDGE_REGISTRY.json`.
- **Deferred**: Upgrade to upstream HEAD is blocked by proxy 127.0.0.1:7897 dead + DNS hijack of github.com → 20.205.243.166. User can manually restart clash-verge proxy or fix DNS to enable `hermes update`.

### 2. `br-swarmclaw-openclaw` (SwarmClaw → OpenClaw)
- **Status**: FAILED_INSTALL · health = `needs_build_tools`
- **Reason**: `npm install -g @swarmclawai/swarmclaw` 失败
  - `npm error gyp ERR! $npm_package_version 12.11.1`
  - 缺 Visual Studio Build Tools / windows-build-tools
- **Last Success**: N/A (从未成功)
- **Repair Plan**:
  1. 装 Visual Studio Build Tools 2022 (或 `npm install -g windows-build-tools`)
  2. 重试 `npm install -g @swarmclawai/swarmclaw`
  3. 验证 `swarmclaw --version`
  4. 启动 dashboard 与现有 OpenClaw Gateway 并行

### 3. `br-claudecode-openclaw` (Claude Code → OpenClaw)
- **Status**: CANDIDATE · health = `unbuilt`
- **Reason**: 没有显式 bridge,需要经 AIOS 中转
- **Last Success**: N/A
- **Repair Plan**: 评估是否需要直接 bridge,或继续经 AIOS 中转

---

## Recently Repaired (R211)

### ✅ `br-aios-hermes` (AIOS → Hermes Agent) — REPAIRED 2026-09-27 (R260 audit)
- False alarm: R211 diagnosis of "v0.21.3 D vs v0.15.1 C PATH 双实例冲突" was incorrect.
- Verified: both paths are v0.15.1 (2026.5.29) with identical pyproject.toml sha.
- PATH priority to D drive is correct.
- Registry: status=active, health=healthy.
- Upgrade deferred (proxy 7897 dead + DNS hijack blocks `hermes update`).

### ✅ `br-cc-marketplace` (Claude Code → Marketplace)
- **Status**: ACTIVE (R211 修复)
- 接入 `anthropics/claude-plugins-official` 314 plugins
- 5 插件已装: code-review / commit-commands / pr-review-toolkit / skill-creator / hookify

---

## Next Actions

1. **P0**: 修 `br-aios-hermes` PATH 冲突 (1-2 spawn)
2. **P1**: 装 VS Build Tools + 重试 SwarmClaw (需用户决定)
3. **P2**: 决定 `br-claudecode-openclaw` 是否建直接 bridge
