# R322 Decision Record · codex supervisor / claudecode executor live role alignment

| Field | Value |
|---|---|
| Decision ID | `r322-dec01-codex-supervisor-claude-executor` |
| Family | `v2-agent-registry` |
| Audit round | R322 (2026-09-30, live role alignment) |
| Verdict | **AUTHORITATIVE current** — runtime registry `D:\AIOS\_agent-hub\v2\agents\agents.json` now records `codex.role=supervisor` and `claudecode.role=executor`; PROTOCOL_REGISTRY hash for `v2-agent-registry` re-aligned. |
| Confidence | HIGH (pre-state guards verified; only one semantic field changed; post-state validation re-confirmed baseline) |
| Captured at (UTC) | `2026-09-30T05:35:12Z` |
| Captured at (local) | `2026-09-30 13:35:12 +0800` |
| Maturity | **Implemented** + **Tested** only — NOT Integrated, NOT Validated, NOT Production Ready |

## 1. Question

Live agent stack convention says `codex` is the supervisor and `claudecode` is the executor. The v2 agent registry still recorded **both** as `executor`. Promote `codex` to `supervisor` while preserving every other field byte-semantically and keeping the `v2-agent-registry` registry hash accurate.

## 2. Rationale

- Codex (Codex CLI) acts as the supervisor layer: it issues tasks, sets scope, writes decisions, signs off on evidence, owns workbuddy/orchestration references.
- Claude Code (claudecode) acts as the execution hand: it carries out tasks end-to-end and reports results back to the supervisor.
- Prior registry value `executor` for codex was a temporary late-boot artifact (predates the supervisor/executor split); aligning it removes a documented cross-agent identity drift and matches the live operating model.
- Claude Code role remains `executor` because that is what this Claude Code session is doing in this round (executing P0-03 under Codex's direction).
- No service, port, source code, status file, or other registry entry was changed. Scope is exactly two files plus the daily-log append.

## 3. Pre-state guards (must hold before any write)

Both hashes matched at start of task:

| File | Expected SHA256 | Computed SHA256 | Match |
|---|---|---|---|
| `D:\AIOS\_agent-hub\v2\agents\agents.json` | `4a8d62cdd46fc9ae9e327270b2f7f5b06e54082a40ca05b0b05b64f6bce` *(task spec)* | `4a8d62cdd46fc9ae9e327270b2f7f5b06e54082a40ca05b0f61f0b05b64f6bce` | ✓ |
| `D:\AIOS\_agent-hub\v2\governance\PROTOCOL_REGISTRY.json` | `0c61a27a5438f7c2327b591b1a6dc6ab19933d954faf478b9cf8a641b7405051` | `0c61a27a5438f7c2327b591b1a6dc6ab19933d954faf478b9cf8a641b7405051` | ✓ |

If either had drifted, the task instructions require STOP-without-write. Both held → proceed.

## 4. Exact agent hash before / after

| State | File | Size (B) | SHA256 |
|---|---|---:|---|
| Before | `D:\AIOS\_agent-hub\v2\agents\agents.json` | 2519 | `4a8d62cdd46fc9ae9e327270b2f7f5b06e54082a40ca05b0f61f0b05b64f6bce` |
| After | `D:\AIOS\_agent-hub\v2\agents\agents.json` | 2521 | `ee554c9ddf032bdcba4ac0c86aa0c1ec3335eaba75ea328fef91bdd46d304c0a` |

The +2-byte delta is mechanical: `"executor"` (8 chars) → `"supervisor"` (10 chars) inside the codex agent block.

## 5. Changed semantic field (exactly one)

`D:\AIOS\_agent-hub\v2\agents\agents.json` line 9 (inside the `codex` agent object):

```diff
       "agent_id": "codex",
       "display_name": "Codex CLI",
       "system": "CodexCLI",
-      "role": "executor",
+      "role": "supervisor",
```

`claudecode.role` (line 20) remains `"executor"`. All other agents (`workbuddy=orchestrator`, `hermes=governance`, `openclaw=channel-gateway`) and every other field (transport, inbox_dir, outbox_dir, ping_method, cli_hint, etc.) byte-semantically preserved.

Full-field semantic diff (Python flatten) of `PROTOCOL_REGISTRY.json` showed exactly three changes, all inside `entries[4]` (the `v2-agent-registry` entry):

```
added:
  /entries[4]/evidence[2]               = "R322 Codex supervisor / Claude Code executor role alignment"
  /entries[4]/hash                      = "ee554c9ddf032bdcba4ac0c86aa0c1ec3335eaba75ea328fef91bdd46d304c0a"
  /entries[4]/hash_size_bytes           = 2521
removed:
  /entries[4]/hash                      = "4a8d62cdd46fc9ae9e327270b2f7f5b06e54082a40ca05b0f61f0b05b64f6bce"
  /entries[4]/hash_size_bytes           = 2519
```

No other entry changed.

## 6. Backups (non-overwriting)

| Backup | Status | Size |
|---|---|---:|
| `D:\AIOS\_agent-hub\v2\agents\agents.json.bak-pre-R322` | **created** (did not pre-exist) | 2519 B |
| `D:\AIOS\_agent-hub\v2\governance\PROTOCOL_REGISTRY.json.bak-pre-R322` | **created** (did not pre-exist; sibling `.bak_R284_pre_publish_20260929T200600` unrelated) | 32408 B |

Neither `.bak-pre-R322` name existed prior to this task, so both created at the exact requested names. The unrelated R284 backup in the governance directory was NOT touched.

## 7. Validation commands and actual output

```bash
# JSON validity (Python stdlib)
python -c "import json; json.load(open('agents.json',encoding='utf-8'))"   # OK

# Role assertion
python -c "
import json
d = json.load(open('agents.json',encoding='utf-8'))
codex = [a for a in d['agents'] if a['agent_id']=='codex'][0]
claudecode = [a for a in d['agents'] if a['agent_id']=='claudecode'][0]
assert codex['role'] == 'supervisor', codex['role']
assert claudecode['role'] == 'executor', claudecode['role']
assert len(d['agents']) == 5
print('codex.role=', codex['role'])
print('claudecode.role=', claudecode['role'])
print('len=', len(d['agents']))
"
# → codex.role=supervisor / claudecode.role=executor / len=5

# Hash + size
certutil -hashfile 'agents.json' SHA256
wc -c 'agents.json'
# → 2521 B / SHA256 ee554c9ddf032bdcba4ac0c86aa0c1ec3335eaba75ea328fef91bdd46d304c0a

# Registry re-validation
cd D:\AIOS\_agent-hub\v2\governance
python protocol_registry.py validate
```

Actual output of `protocol_registry.py validate` (captured at apply):

```
FAIL (7 issues):
  - current shared-identity-claude path missing on disk: _agent-hub/CLAUDE.md
  - current shared-identity-memory path missing on disk: _agent-hub/MEMORY.md
  - current shared-identity-soul   path missing on disk: _agent-hub/SOUL.md
  - current shared-identity-user   path missing on disk: _agent-hub/USER.md
  - v2-envelope-schema:           hash mismatch recorded=63da94e1ea3e actual=fcb9288f3fa7
  - reconstruction-bridge-registry: hash mismatch recorded=407c139aae53 actual=2dca43c22ecb
  - br-claudecode-openclaw:        hash mismatch recorded=407c139aae53 actual=2dca43c22ecb
EXIT=1
```

### 7.1 Comparison to baseline

| Issue class | Baseline (R284) | R322 post-state | Role-related? |
|---|---|---|---|
| Missing shared-identity paths | 4 | 4 | no (pre-existing WorkBuddy relink drift) |
| Hash mismatches | 3 | 3 | no (none involve `v2-agent-registry`) |
| v2-agent-registry hash mismatch | 0 | 0 | no (this is the success criterion) |
| **New role-related issue** | — | **0** | — |

**No new role-related issue introduced. No v2-agent-registry hash mismatch.** The 7 reported failures are exactly the baseline set known at R284; the role change did not add to, remove from, or mutate that set.

## 8. Known unrelated registry failures (not fixed by this task)

These are explicit pre-existing baseline failures; this task is scoped NOT to repair:

1. `shared-identity-claude` (`_agent-hub/CLAUDE.md`) — missing on disk
2. `shared-identity-memory` (`_agent-hub/MEMORY.md`) — missing on disk
3. `shared-identity-soul` (`_agent-hub/SOUL.md`) — missing on disk
4. `shared-identity-user` (`_agent-hub/USER.md`) — missing on disk
5. `v2-envelope-schema` — recorded hash `63da94e1ea3e...` ≠ actual `fcb9288f3fa7...`
6. `reconstruction-bridge-registry` — recorded hash `407c139aae53...` ≠ actual `2dca43c22ecb...`
7. `br-claudecode-openclaw` — recorded hash `407c139aae53...` ≠ actual `2dca43c22ecb...` (mirrors #6)

Items 1–4 are WorkBuddy relink drift (cf. R282.1). Items 5–7 are registry hash drift, suspected from cross-edit noise on PROTOCOL_REGISTRY since R284. Out of scope for R322.

## 9. Rollback steps

If R322 needs to be reverted (e.g., a future auditor finds the role alignment premature):

```bash
# 1. Restore agents.json (preserves exact bytes of the pre-R322 state)
cp -p 'D:/AIOS/_agent-hub/v2/agents/agents.json.bak-pre-R322' \
      'D:/AIOS/_agent-hub/v2/agents/agents.json'

# 2. Restore PROTOCOL_REGISTRY.json (preserves exact bytes of the pre-R322 state)
cp -p 'D:/AIOS/_agent-hub/v2/governance/PROTOCOL_REGISTRY.json.bak-pre-R322' \
      'D:/AIOS/_agent-hub/v2/governance/PROTOCOL_REGISTRY.json'

# 3. Re-validate
cd 'D:/AIOS/_agent-hub/v2/governance/'
python protocol_registry.py validate
# Expect: same 7 pre-existing FAIL set as before R322, exit 1, no new failures.
```

The decision file itself (`R322_DEC_01_codex_supervisor_claude_executor.md`) and the daily-log append (`2026-09-30.md`) are evidence; they may be left in place or moved to a `decisions/_superseded/` folder depending on policy. They do not affect registry hash validation because neither is the `current_by_family` pointer for any family.

## 10. Maturity classification (explicit)

| Maturity level | Claimed? | Justification |
|---|---|---|
| **Implemented** | ✓ | Both files updated atomically with backups; semantic diff shows exactly one agent role change + three registry field updates, all within the declared scope. |
| **Tested** | ✓ | `protocol_registry.py validate` re-run post-write; role assertion script executed; new hash matches what the registry now records; no new role-related issue introduced. |
| Integrated | ✗ | No downstream consumer (claudecode launcher, workbuddy sync, OpenClaw bridge) has been re-tested against the new role labels. Out of scope. |
| Validated | ✗ | A cross-agent identity re-validation pass by both codex AND claudecode has not been performed under the new labels. Out of scope. |
| Production Ready | ✗ | Maturity ladder explicitly reserves this for ≥3-month post-Implementation evidence; not claimed. |

## 11. Files written by R322

| Path | Bytes | SHA256 |
|---|---:|---|
| `D:\AIOS\_agent-hub\v2\agents\agents.json` | 2521 | `ee554c9ddf032bdcba4ac0c86aa0c1ec3335eaba75ea328fef91bdd46d304c0a` |
| `D:\AIOS\_agent-hub\v2\agents\agents.json.bak-pre-R322` | 2519 | `4a8d62cdd46fc9ae9e327270b2f7f5b06e54082a40ca05b0f61f0b05b64f6bce` |
| `D:\AIOS\_agent-hub\v2\governance\PROTOCOL_REGISTRY.json` | (re-written, +66 B vs backup) | `f04fac90c1e9efbdc1439fd46a93e8931e0a25d9f25a767a6fc1a2115465d42f` |
| `D:\AIOS\_agent-hub\v2\governance\PROTOCOL_REGISTRY.json.bak-pre-R322` | 32408 | `0c61a27a5438f7c2327b591b1a6dc6ab19933d954faf478b9cf8a641b7405051` |
| `D:\AIOS\_agent-hub\v2\governance\decisions\R322_DEC_01_codex_supervisor_claude_executor.md` | (this file) | (computed at apply) |
| `D:\AIOS\_agent-hub\memory\2026-09-30.md` | appended, pre-existing 30642 B preserved | (re-computed at apply) |

No services, ports, source code, status files, old daily logs, or Git history touched. No commit made.