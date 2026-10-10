# AGENTS · Sandbox Network Warning (Add-on) · 2026-10-10

> **State**: ADD-ON (separate file — avoids touching merge-conflicted main AGENTS.md)
> **Author**: Codex supervisor (post-P0-recovery)
> **Permanent Storage**: Should eventually merge into `_agent-hub/AGENTS.md` after user resolves conflict state

---

## Sandbox Network Constraints (实测, 2026-10-10)

### 1. `git push` to github.com 永远 fail (L3 不退)
- 实测: `fatal: unable to access 'https://github.com/macxiaxia-boop/aios-sovereignty-v.git/': Failed to connect to github.com port 443 after 21054 ms`
- 实测: `fatal: unable to access 'https://...': Recv failure: Connection was reset`
- 实测: `curl https://github.com` 8s 超时 (`curl: (28) Connection timed out after 8016 milliseconds`)
- **结论**: sandbox 不通 github。 别指望 push 远端. 推远端必须走 desktop bundle / patch.

### 2. PowerShell `Test-NetConnection github.com -Port 443` 15s 超时
- 不要用 PS test-netconnection 测 github 是否通 — 15s 超时只是 timeout 信号, 不代表通不通

### 3. 无默认 gateway proxy 配置
- `curl` / `git` / `npm` 都没配 proxy 设置
- 用户如需开 proxy, 必须自定义 HTTP_PROXY/HTTPS_PROXY env var

### 4. 推远端替代方案 (按推荐度排序)
- **A**: 用户手动 `git push` (desktop / native shell, 不在 sandbox)
- **B**: patch bundle 写入, 用户在外部 pull
- **C**: 写 commit 到本地 branch, 用户 git fetch + merge 外部

### 5. 写代码避开长 polling
- HTTP requests 限 10s 超时 (8s observed)
- pytest 默认 timeout 8s on network ops
- 任何 webhook/notify endpoint 加 5s short-circuit

### 6. 推代码节奏
- commit = local always
- push = user-orchestrated (不在 sandbox)

---

## 历史背景 (为什么需要这段)

2026-10-10 凌晨 batch: 我们做了 T2 push 上线 `codex/R1348-reconcile` 分支, 但 sandbox 网络封 github, push 永远 fail, 必须 audit log 报真实原因。 失败不能靠"重试"修。

2026-10-10 白天 batch: 我们已记入 audit log `audit/2026-10-10-t2-push-blocked.md` 和 `audit/2026-10-10-t2-branch-done.md`。

---

## Permanent merge plan

一旦用户解 AGENTS.md 冲突 (likely via `git checkout --theirs` 或 `--ours`), 把本文件内容 copy-paste 进主 AGENTS.md 的 "MCP Channel Status" 段后或 "Standing Constraints" 段。

--- Codex supervisor · 写 sandbox 网络警告 add-on · 2026-10-10
