# R282 Decision Record · family=chatgpt-bridge-task-protocol

| Field | Value |
|---|---|
| Decision ID | `r282-decision-chatgpt-bridge-task-protocol` |
| Family | `chatgpt-bridge-task-protocol` |
| Audit round | R282 (2026-09-29, post-R281.2 PROTOCOL_AUDIT) |
| Verdict | **AUTHORITATIVE ABSENT** — no current file, decision record IS the family pointer |
| Confidence | HIGH (no live file exists; only superseded backup copies) |
| Captured at | 2026-09-29T14:43:00Z |

## 1. Question

The protocol family `chatgpt-bridge-task-protocol` was UNRESOLVED because the only on-disk candidate is a `superseded` backup copy of `TASK_PROTOCOL.md` from the legacy chatgpt-bridge module (rolled back to V4P9-FINAL on 2026-09-27). No "current" runtime file exists for this family. Is a current file expected? Where does the canonical task protocol for this scope now live?

## 2. Evidence (disk truth)

### 2.1 On-disk candidates

```
$ find D:/AIOS/_backups -name TASK_PROTOCOL.md | wc -l
39

$ find D:/AIOS/_backups -name TASK_PROTOCOL.md -not -path '*/r240_test/*' -not -path '*/pre_rollback_to_V4P9-FINAL_*' | head
(none outside the two chatgpt_bridge backup namespaces)
```

- **39 identical copies** across two namespaces under `D:\AIOS\_backups\`:
  - `chatgpt_bridge_pre_rollback_to_V4P9-FINAL_<ts>/TASK_PROTOCOL.md` — 19 copies
  - `chatgpt_bridge_r240_test_<ts>/TASK_PROTOCOL.md` — 20 copies
- All 39 copies are **byte-identical** (sha256 `5ca3cd76b38d7cde192951d00c1e95e1c5d5c447467aa4b5da715a336a87f790`, 2,101 B, mtime 2026-09-27 00:31).
- The copy currently referenced by `PROTOCOL_REGISTRY.json` is `_backups/chatgpt_bridge_pre_rollback_to_V4P9-FINAL_20260927_151216/TASK_PROTOCOL.md`, marked `status=superseded`.

### 2.2 Where the legacy task protocol was used

- Legacy chatgpt_bridge module was the V4P8-era Claude ↔ Codex glue (R240 test runs).
- Replaced by the v2 hub bidirectional protocol + envelope schema on 2026-09-27 (rollout to V4P9-FINAL).
- All references to `chatgpt_bridge.TASK_PROTOCOL` in active code/config are absent post-R320.1: the `_agent-hub/v2/protocols/v1.md` + `_agent-hub/v2/schemas/task.schema.json` + `_agent-hub/v2/src/state_machine.py` triad IS the replacement task protocol for the v2 era.

### 2.3 No live chatgpt_bridge references

- No code under `D:\AIOS\_agent-hub\` imports `chatgpt_bridge` or `TASK_PROTOCOL.md` from `_backups/`.
- The 39 backup copies have not been modified since 2026-09-27 00:31 (the original rollback time).
- No newer `TASK_PROTOCOL.md` exists outside `_backups/`.

### 2.4 What the registry currently says

`PROTOCOL_REGISTRY.json` has one entry for this family (`chatgpt-bridge-task-protocol`, `status=superseded`, path `_backups/chatgpt_bridge_pre_rollback_to_V4P9-FINAL_20260927_151216/TASK_PROTOCOL.md`). This is **historical evidence** that the legacy protocol existed; it is NOT a current pointer.

## 3. Decision

1. **No current file exists** for the `chatgpt-bridge-task-protocol` family in the v2 era. The family is `AUTHORITATIVE ABSENT`.
2. **The decision record IS the family pointer.** `current_by_family[chatgpt-bridge-task-protocol]` is set to a new registry entry `r282-decision-chatgpt-bridge-task-protocol` with `status=current`, pointing at this markdown file.
3. **Legacy entry preserved**: the existing `chatgpt-bridge-task-protocol` registry entry stays in `entries[]` with `status=superseded`, `superseded_by=r282-decision-chatgpt-bridge-task-protocol`, and `copy_count=3 (verbatim identical)`. The 39 backup files are NOT promoted to `current`; they remain frozen rollback snapshots.
4. **Replacement scope**: the v2 hub task protocol triad (`v2/protocols/v1.md` + `v2/schemas/task.schema.json` + `v2/src/state_machine.py`) is the canonical task protocol for any post-R320.1 agent interaction. The `chatgpt-bridge-task-protocol` family now exists only as a historical archive pointer, not as a live protocol.

## 4. Limitations

- The 39 backup copies are NOT in scope for cleanup by this decision. They remain in `_backups/` until the next housekeeper pass that respects the `_backups/` retention policy (see `_agent-hub/v2/governance/RETENTION_POLICY.md`).
- If a user later wants to reinstate a chatgpt_bridge-specific task protocol (different from v2 hub), they should create a new file under a non-backup path AND publish a new current entry. This decision explicitly does not preempt that choice.

## 5. Superseded candidates

- All 39 byte-identical backup copies of `_backups/.../TASK_PROTOCOL.md` (sha256 `5ca3cd76…`) → superseded by v2 hub task protocol triad; remain frozen as rollback artifacts.
- The legacy `chatgpt-bridge-task-protocol` registry entry's `status` stays `superseded` (no change).

## 6. Verification timestamp

- Disk truth verification: 2026-09-29T14:43:00Z (`find D:/AIOS/_backups -name TASK_PROTOCOL.md | wc -l → 39`; sha256 cross-check on 3 namespaces → identical).
- Registry validation: pending (will run after the registry publish step).

## 7. References

- `_agent-hub/v2/protocols/v1.md` — current bidirectional protocol v1.
- `_agent-hub/v2/schemas/task.schema.json` — current task schema v1.0.
- `_agent-hub/v2/src/state_machine.py` — current task state machine implementation.
- `_agent-hub/v2/governance/RETENTION_POLICY.md` — backup retention rules.
- `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BROKEN_BRIDGES.md` — narrative report on bridge history (including legacy chatgpt_bridge deprecation).
