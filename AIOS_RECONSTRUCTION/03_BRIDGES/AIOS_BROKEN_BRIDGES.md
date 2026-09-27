# AIOS Broken Bridges Report · R212 · 2026-09-26

**spec#37 Broken Bridge Registry**

## Currently Broken / Partial

### 1. `br-aios-hermes` (AIOS → Hermes Agent)
- **Status**: PARTIAL · health = `broken_path`
- **Reason**: PATH 双实例冲突
  - `D:\AIOS\_relinked\hermes\hermes-agent` (v0.21.3, git install, 正确版本)
  - `C:\Users\xinzh\.hermes\hermes-agent` (v0.15.1, 不知道哪来的, PATH 优先级指向这里)
- **Last Success**: 2026-09-14 (R211 初始发现)
- **Repair Plan**:
  1. 修 PATH 让 `hermes` 指向 D 盘 v0.21.3
  2. 删 C 盘 v0.15.1 (或移到 `12_ARCHIVE/`)
  3. `git stash pop` 应用 `hermes-update-autostash-20260926-134849`
  4. 跟踪上游 NousResearch/hermes-agent 修 `_github_compare_behind` import 后再升
- **Blocker**: 上游 main 分支 broken

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

### ✅ `br-cc-marketplace` (Claude Code → Marketplace)
- **Status**: ACTIVE (R211 修复)
- 接入 `anthropics/claude-plugins-official` 314 plugins
- 5 插件已装: code-review / commit-commands / pr-review-toolkit / skill-creator / hookify

---

## Next Actions

1. **P0**: 修 `br-aios-hermes` PATH 冲突 (1-2 spawn)
2. **P1**: 装 VS Build Tools + 重试 SwarmClaw (需用户决定)
3. **P2**: 决定 `br-claudecode-openclaw` 是否建直接 bridge
