# AIOS Broken Bridges Report · R212 · 2026-09-26

**spec#37 Broken Bridge Registry**

## Currently Broken / Partial

### 1. `br-aios-hermes` (AIOS → Hermes Agent)
- **Status**: ✅ **RESOLVED 2026-09-27 (R260 audit)** · moved to "Recently Repaired"
- **Root-cause analysis (R260)**: The R211 diagnosis was based on incorrect version labels (v0.21.3 D vs v0.15.1 C). Both binaries actually report **v0.15.1 (2026.5.29)** with identical pyproject.toml sha `65cad64739fd98a0`. There is no PATH conflict — both paths point to the same version.
- **Current state**: PATH priority correctly to D drive (`D:\AIOS\_relinked\hermes\hermes-agent\.venv\Scripts\hermes.exe`). Binary is functional.
- **Bridge registry updated**: `status=active, health=healthy` per `AIOS_BRIDGE_REGISTRY.json`.
- **Deferred**: Upgrade to upstream HEAD is blocked by proxy 127.0.0.1:7897 dead + DNS hijack of github.com → 20.205.243.166. User can manually restart clash-verge proxy or fix DNS to enable `hermes update`.

### 2. `br-swarmclaw-openclaw` (SwarmClaw → OpenClaw) — **NEW STATE 2026-09-27 (R262)**
- **Status**: INSTALLED_BUILD_BLOCKED · health = `needs_nextjs_path_fix`
- **Old status (R211)**: FAILED_INSTALL · health = `needs_build_tools`
- **R262 evidence**:
  - `npm install -g @swarmclawai/swarmclaw@1.9.39` ✅ (npmmirror.com registry reachable, ~3 min, package files complete)
  - `swarmclaw doctor` ✅: "Package version: 1.9.39 / Next CLI available: yes" — install **healthy**
  - `swarmclaw server --build` ❌: Next.js 16.2.4 webpack `Module not found: Can't resolve './D:/npm-global/node_modules/@swarmclawai/swarmclaw/node_modules/next/dist/client/next.js'` — Windows absolute path colon issue
  - **NOT a VS Build Tools issue** — no C++ compile required (Next.js pure JS)
  - node-gyp v12.4.0 already present (newer than R211 v12.11.1 — original gyp ERR is gone)
  - node v26.8.2 + npm 11.17.0 + Python 3.11.15 — modern stack, no native compile blockers
- **Tested mitigations** (all failed or partial):
  1. `rm -rf @swarmclawai/swarmclaw && npm install -g` (fresh) → same build error
  2. `npm config set prefix C:\npm-prefix` (no-colon path) + reinstall → package files copied but npm bin shim path-stamped to D:\npm-global
  3. Force kill all node.exe + retry → same build error
- **Real root cause**: Next.js 16.2.4 webpack can't resolve relative `./D:/absolute/path` on Windows where absolute path starts with drive letter
- **Repair options** (任选):
  1. Wait for Next.js upstream fix
  2. `swarmclaw run` or `swarmclaw server start` (may use dev mode, bypass prebuild)
  3. Patch `next.config.ts` to set `webpack.resolve.alias['next/dist/client/next.js']` to absolute path without `./
  4. Use OpenClaw directly (no SwarmClaw UI) — R236 Plan B LOCKED, OpenClaw 18792 daemon fully functional
- **OpenClaw Plan B impact**: 0 — OpenClaw 18792 PID 23908 LISTENING + ESTABLISHED, all bridges work via OpenClaw

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
