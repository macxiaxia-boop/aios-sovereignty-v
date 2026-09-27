# AIOS Broken Bridges Report · R212 · 2026-09-26

**spec#37 Broken Bridge Registry**

## Currently Broken / Partial

### 1. `br-aios-hermes` (AIOS → Hermes Agent)
- **Status**: ✅ **RESOLVED 2026-09-27 (R260 audit)** · moved to "Recently Repaired"
- **Root-cause analysis (R260)**: The R211 diagnosis was based on incorrect version labels (v0.21.3 D vs v0.15.1 C). Both binaries actually report **v0.15.1 (2026.5.29)** with identical pyproject.toml sha `65cad64739fd98a0`. There is no PATH conflict — both paths point to the same version.
- **Current state**: PATH priority correctly to D drive (`D:\AIOS\_relinked\hermes\hermes-agent\.venv\Scripts\hermes.exe`). Binary is functional.
- **Bridge registry updated**: `status=active, health=healthy` per `AIOS_BRIDGE_REGISTRY.json`.
- **Deferred**: Upgrade to upstream HEAD is blocked by proxy 127.0.0.1:7897 dead + DNS hijack of github.com → 20.205.243.166. User can manually restart clash-verge proxy or fix DNS to enable `hermes update`.

### 2. `br-swarmclaw-openclaw` (SwarmClaw → OpenClaw) — **RESOLVED 2026-09-27 (R265)**
- **Status**: ✅ **RESOLVED 2026-09-27 (R265)** · moved to "Recently Repaired"
- **Old status**: FAILED_INSTALL (R211) → INSTALLED_BUILD_BLOCKED (R262) → ACTIVE (R265)
- **R265 evidence**:
  - `npm install -g @swarmclawai/swarmclaw@1.9.39` ✅ (npmmirror.com registry, npm prefix changed to `C:\npm-prefix` to avoid Windows drive-colon path conflict)
  - `swarmclaw doctor` ✅: "Package version: 1.9.39 / Next CLI available: yes / **Standalone bundle: yes**"
  - `swarmclaw server start --detach` ✅: PID 21760 LISTENING 0.0.0.0:3456 (HTTP) + 0.0.0.0:3457 (WS)
- **2 patches applied** to `C:\npm-prefix\node_modules\@swarmclawai\swarmclaw\`:
  1. **`next.config.ts`** (added webpack hook): `config.resolve.alias` maps `'next/dist/client/next.js'` and `'next/dist/client/app-next.js'` to `path.resolve(PROJECT_ROOT, 'node_modules/next/dist/client/{next,app-next}.js')` — fixes Next.js 16.2.4 webpack Windows absolute path bug (`./D:/npm-global/...` cannot resolve)
  2. **`src/components/shared/connector-platform-icon.tsx`**: rename `SiSlack` → `SiSlackware` (react-icons/si dropped SiSlack, only SiSlackware exists in v5+)
- **WARNING**: Patches in `node_modules/` will be **lost on reinstall**. Before any `npm install -g @swarmclawai/swarmclaw` again, save `/c/npm-prefix/node_modules/@swarmclawai/swarmclaw/{next.config.ts,src/components/shared/connector-platform-icon.tsx}` first and re-apply.
- **Bridge registry updated**: `status=active, health=healthy`
- **OpenClaw relationship**: OpenClaw 18792 PID 23908 remains primary daemon (R236 Plan B); SwarmClaw :3456 adds connector-platform UI on top

### 3. `br-claudecode-openclaw` (Claude Code → OpenClaw)
- **Status**: CANDIDATE · health = `unbuilt`
- **Reason**: 没有显式 bridge,需要经 AIOS 中转
- **Last Success**: N/A
- **Repair Plan**: 评估是否需要直接 bridge,或继续经 AIOS 中转

---

## Recently Repaired (R211 + R265)

### ✅ `br-swarmclaw-openclaw` (SwarmClaw → OpenClaw) — REPAIRED 2026-09-27 (R265)
- Standalone bundle built ✅
- Server running PID 21760 LISTENING :3456 + :3457
- 2 patches in `C:\npm-prefix\node_modules\...`: next.config.ts (webpack.alias) + connector-platform-icon.tsx (SiSlack → SiSlackware)
- OpenClaw 18792 still primary (R236 Plan B LOCKED)

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
