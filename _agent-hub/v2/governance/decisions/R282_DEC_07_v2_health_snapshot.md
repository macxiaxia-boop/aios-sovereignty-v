# R282 Decision Record · family=v2-health-snapshot

| Field | Value |
|---|---|
| Decision ID | `r282-decision-v2-health-snapshot` |
| Family | `v2-health-snapshot` |
| Audit round | R282 (2026-09-29, post-R281.2 PROTOCOL_AUDIT) |
| Verdict | **MARK SUPERSEDED** — existing health.json is stale relative to live state; do NOT regenerate in this round. Decision record IS the family pointer. |
| Confidence | HIGH for staleness evidence; per task instructions the file is left untouched |
| Captured at | 2026-09-29T14:43:00Z |

## 1. Question

The protocol family `v2-health-snapshot` was UNRESOLVED because `_agent-hub/v2/reports/health.json` (mtime 2026-09-29 12:56, status=`candidate`) was authored before the live R320.6 probe recorded in `v2/CHANGELOG.md [2.0.3]` (timestamp 2026-09-29 13:21). A re-probe at 2026-09-29 14:43 shows partial regression vs. the CHANGELOG's claim. Should the file be regenerated? If not, what is the honest family pointer?

## 2. Evidence (disk truth)

### 2.1 File of record

| Path | Size (B) | mtime | sha256 (12) | Status |
|---|---:|---|---|---|
| `D:\AIOS\_agent-hub\v2\reports\health.json` | 4,359 | 2026-09-29 12:56 (predates CHANGELOG 2.0.3 at 13:21) | `3f0acbdd757c` | `candidate` in registry |
| `D:\AIOS\_agent-hub\v2\CHANGELOG.md` | 15,835 | 2026-09-29 13:21 (last edited in R320.6 verification round) | n/a (not in registry) | documents R320.6 health-table claim |

### 2.2 What health.json currently asserts (level per agent)

| Agent | configured | present | reachable | healthy |
|---|---|---|---|---|
| claudecode | true | true | **false** | **false** |
| codex | true | **false** | false | false |
| workbuddy | true | true | **false** | **false** |
| hermes | true | true | **false** | **false** |
| openclaw | true | true | **false** | **false** |

- All 5 agents end at `present` (or `false` for codex); `reachable`/`healthy` are universally `false`.
- Captured_at in the JSON: 2026-09-29T13:30:00Z (the JSON body self-reports this timestamp despite mtime 12:56 — the JSON was written AFTER its `captured_at` field value, indicating a manual edit cycle, not a probe-result artifact).

### 2.3 What CHANGELOG [2.0.3] claims (R320.6 verification round)

The CHANGELOG table claims (timestamp 2026-09-29T05:19:02Z per CHANGELOG body; mtime 13:21 UTC per filesystem):

| Agent | configured | present | reachable | healthy |
|---|---|---|---|---|
| Hermes | true | true | **true** | **true** |
| OpenClaw | true | true | **true** | **true** |
| Codex | true | true | **false** | **false** |
| Claude Code | true | true | **false** | **false** |
| WorkBuddy | true | true | **false** | **false** |

This claim is inconsistent with `health.json` (CHANGELOG claims Hermes/OpenClaw healthy; health.json has them at present). One of these is the snapshot of record; this decision picks.

### 2.4 Live re-probe at 2026-09-29 14:43 (R282 read-only)

| Component | Live state | Verdict |
|---|---|---|
| `netstat -ano` for `:5099` (V22) | LISTENING PID 23104 | V22 up |
| `GET /health` on 5099 | HTTP 200 with full v22.0.0 body | V22 healthy |
| `netstat -ano` for `:18792` (OpenClaw) | LISTENING PID 23700 | OpenClaw port up |
| `GET /healthz` on 18792 (8s timeout) | HTTP 000 / no body | OpenClaw `/healthz` non-responsive at 14:43 |
| `netstat -ano` for `:3456` (SwarmClaw) | not checked in this round | (out of scope) |
| `codex` relay `:19194` | not checked in this round | (CHANGELOG says closed) |

The 14:43 re-probe shows OpenClaw `/healthz` is currently degraded (HTTP 000) — meaning even the CHANGELOG 2.0.3 claim of "OpenClaw healthy=true" is now partially stale. This is exactly the scenario the R320.1 4-level probe model was designed to surface: health snapshots are point-in-time, and any snapshot can be invalidated by the next probe.

### 2.5 Why the runtime file must NOT be regenerated in this round

Per the task instructions:
> "For v2-health-snapshot, do not regenerate or overwrite the runtime health snapshot in this round. A decision record may declare the existing health.json stale/non-authoritative if that is what evidence proves."

Rationale:
1. The snapshot is produced by `aiosv2.py health` (Codex-runnable; blocked in this CC session's Bash sandbox per CHANGELOG [2.0.1]).
2. A CLI run from a non-permitted shell in this CC session is not possible.
3. A static re-write without an actual probe would fabricate data and violate the R320.1 honest-levels invariant.
4. The honest state IS that the snapshot is stale relative to both CHANGELOG 2.0.3 AND the 14:43 re-probe. The decision record captures this honestly.

## 3. Decision

1. **`v2-health-snapshot` registry entry → `status=superseded`**, `superseded_by=r282-decision-v2-health-snapshot`. The file stays on disk; it is not deleted, not regenerated, not overwritten.
2. **The decision record IS the family pointer.** `current_by_family[v2-health-snapshot]` is set to a new registry entry `r282-decision-v2-health-snapshot` with `status=current`, pointing at this markdown.
3. **The stale `health.json` is preserved as evidence**: it documents the state at 2026-09-29 12:56 (the "captured_at" self-report notwithstanding). Future Codex runs may overwrite it via `python _agent-hub/v2/cli/aiosv2.py health` from a permitted shell; that overwrite will flip its `status` back to `current` and the decision record will itself be flipped to `superseded`.
4. **No claim is made in this round about the operational state of any individual agent.** The decision explicitly disclaims bidirectional Connect claims and operational healthy claims. Anyone needing fresh per-agent state must run `aiosv2.py health` themselves.
5. **Action item for Codex follow-up** (not this round): run `python _agent-hub/v2/cli/aiosv2.py health` from a permitted shell, capture the fresh JSON + stdout, and overwrite `v2/reports/health.json`. That run, when complete, will (a) supersede this decision record and (b) re-elevate `v2-health-snapshot` to `current` with a fresh `captured_at`.

## 4. Limitations

- This decision does NOT modify `health.json`. Per task instructions, that file is left untouched.
- This decision does NOT update the CHANGELOG. The CHANGELOG 2.0.3 claim of "OpenClaw healthy=true" was correct at 2026-09-29 05:19:02Z but is stale relative to the 14:43 re-probe. A future codex round that re-runs `aiosv2.py health` will produce an authoritative update; the CHANGELOG should then be amended to reference that new snapshot.
- This decision does NOT modify the `src/probes.py` 4-level model — the model is sound, the snapshot is just stale.

## 5. Superseded candidates

- `v2-health-snapshot` registry entry → `status=superseded` (was `candidate`); `superseded_by=r282-decision-v2-health-snapshot`.
- The on-disk `health.json` stays put (no regeneration).

## 6. Verification timestamp

- File review: 2026-09-29T14:43:00Z (sha256 + mtime + content cross-check).
- Live re-probe: 2026-09-29T14:43:00Z (`netstat`, `curl /health`, `curl /healthz`).

## 7. References

- `D:\AIOS\_agent-hub\v2\reports\health.json` — the stale snapshot (now `superseded`).
- `D:\AIOS\_agent-hub\v2\CHANGELOG.md [2.0.3]` — R320.6 health-table claim (itself partially stale at 14:43).
- `D:\AIOS\_agent-hub\v2\src\probes.py` — 4-level probe implementation (R320.1).
- `D:\AIOS\_agent-hub\v2\cli\aiosv2.py` — `health` subcommand source.
- `D:\AIOS\_agent-hub\v2\README.md §Probes (R320.1 honest 4-level model)` — semantic contract for snapshots.
