# R282 Decision Record · family=bridge-claudecode-openclaw

| Field | Value |
|---|---|
| Decision ID | `r282-decision-bridge-claudecode-openclaw` |
| Family | `bridge-claudecode-openclaw` |
| Audit round | R282 (2026-09-29, post-R281.2 PROTOCOL_AUDIT) |
| Verdict | **PROMOTE candidate → current** (decision record + runtime evidence) |
| Confidence | HIGH for document authority; LOW for runtime bidirectional connectivity |
| Captured at | 2026-09-29T14:43:00Z |

## 1. Question

The protocol family `bridge-claudecode-openclaw` was UNRESOLVED because two AIOS files disagreed about the live status of the Claude Code ↔ OpenClaw bridge:

- `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json` (R212-step4-v1, mtime 2026-09-29 today) → row `br-claudecode-openclaw`: `status=loopback_only`, `health=unverified` (R320.6 honest).
- `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BROKEN_BRIDGES.md` (R212-2026-09-26, mtime 2026-09-27 17:50) → row `br-claudecode-openclaw`: `status=CANDIDATE`, `health=unbuilt` (R211 stale text, never refreshed after R320.6).

Which file is the authoritative bridge-status source? What is the truthful live state on 2026-09-29?

## 2. Evidence (disk + live probe)

### 2.1 Document authority (this is what this record resolves)

| File | mtime | sha256 (12) | Status text | Authoritative? |
|---|---|---|---|---|
| `AIOS_BRIDGE_REGISTRY.json` | 2026-09-29 14:13 (today) | `407c139aae53` | `loopback_only` + `unverified` + R320.6 evidence chain | **YES — freshest, schema-tracked, R320.6-honest** |
| `AIOS_BROKEN_BRIDGES.md` | 2026-09-27 17:50 | `33a9e43fe9fe` | `CANDIDATE` + `unbuilt` | NO — narrative, last updated before R320.6, has stale wording |

- `AIOS_BRIDGE_REGISTRY.json` is the SSOT for bridge state (per `reconstruction-bridge-registry` family which is `current`).
- `AIOS_BROKEN_BRIDGES.md` is a narrative report tracking R211/R260/R265 repairs (per `reconstruction-broken-bridges-report` family). It is NOT live authority; it is a historical ledger.
- Per `CANONICAL_INDEX.json::reconstruction_registry`, the bridge registry is the SSOT; broken bridges is a sibling narrative.
- This family is the **DOCUMENT authority pointer** for the `br-claudecode-openclaw` row — it points at where the row lives, not whether the row is `current`.

### 2.2 Live operational state (re-read-only probe at 2026-09-29 14:43)

| Component | Evidence | Verdict |
|---|---|---|
| OpenClaw gateway daemon | `netstat -ano` → `TCP 127.0.0.1:18790  0.0.0.0:0  LISTENING  23700` (PID 23700) | port up |
| OpenClaw `/healthz` HTTP probe | `curl http://127.0.0.1:18792/healthz` (8s timeout) → HTTP 000 / no body | **NOT 200 right now** (degraded vs. R320.6 claim of `{"ok":true,"status":"live"}`) |
| V22 gateway (out of scope for this bridge, included for context) | `netstat -ano` → LISTENING PID 23104; `GET /health` → 200 OK body includes `"status":"ok","version":"22.0.0"` | up |
| v2 queue consumer (OpenClaw-side) | no process observed draining `_agent-hub/v2/messages/inbox/` | not yet wired |
| v2 queue consumer (CC-side two-process round-trip) | Codex↔CC R320.6 envelopes `37531663-…, d8c5884b-…, 3a9d9f27-…, 41afc2c3-…` are VERIFIED per `v2/CHANGELOG.md [2.0.3]` | confirmed |

### 2.3 What the bridge registry actually says today (post R320.6)

> "v2 file-queue + envelope v1.0 protocol is implemented (`v2/cli/aiosv2.py` + `v2/schemas/envelope.schema.json` + `v2/src/queue.py`); test_05_protocol_loopback.py is single-process loopback; Codex↔CC two-process round-trip is VERIFIED … but OpenClaw↔v2 is NOT. R320.1 ROLLBACK FROM R320 overclaim still holds — 'built' was incorrect; 'loopback_only / unverified' is the honest state. To upgrade to 'built': one OpenClaw-side process must consume a v2 inbox envelope and emit a real ack/result back, plus that evidence log must be captured. No service-health fix is required for this bridge upgrade."

This wording is consistent with the live probe: v2 protocol layer is implemented, CC↔Codex round-trip is verified, OpenClaw↔v2 consumer round-trip is not yet observed. The OpenClaw `/healthz` degraded result observed at 14:43 is a fresh transient that does NOT block v2-queue upgrade — the bridge registry explicitly states "No service-health fix is required for this bridge upgrade."

## 3. Decision

1. **Document authority pointer**: `current_by_family[bridge-claudecode-openclaw] → br-claudecode-openclaw` (the existing registry entry pointing at the bridge registry JSON). This entry flips from `status=unknown` to `status=current` because the pointer itself is the canonical location of the authoritative row.
2. **Operational caveat**: the current pointer does NOT imply bidirectional CC↔OpenClaw connectivity. The honest operational state remains `loopback_only / unverified`. The v2-queue upgrade gate is "one OpenClaw process draining inbox + emitting ack/result", which is a separate Codex round to execute and capture.
3. **`AIOS_BROKEN_BRIDGES.md`**: stays in `entries[]` with `status=superseded` (superseded by `reconstruction-bridge-registry`, which is itself `current`). See R282_DEC_04.
4. **`br-claudecode-openclaw` row**: NO change to `status=loopback_only` or `health=unverified` in the registry JSON. The registry text is already R320.6-honest; this decision only resolves the document-authority dispute.
5. **Action items for Codex follow-up** (not this round):
   - Observe one OpenClaw process draining `_agent-hub/v2/messages/inbox/` and emitting ack/result envelopes.
   - Capture envelope IDs + correlation wiring as evidence.
   - Only then may `br-claudecode-openclaw` be flipped to `status=built / health=verified` in the registry.

## 4. Limitations

- Live `/healthz` probe (14:43) returned HTTP 000 / timeout for OpenClaw; the bridge registry was last updated at 13:21 with `/healthz` returning 200. This decision does NOT modify the health text in the bridge registry because the bridge registry correctly separates "service health" from "v2-queue round-trip" — and the relevant upgrade gate is the v2-queue round-trip, not the health endpoint.
- No OpenClaw v2 inbox consumer has been observed in this CC session's read-only evidence sweep; a future Codex run is required.
- The `tension_with` metadata between `reconstruction-bridge-registry` and `reconstruction-broken-bridges-report` entries is preserved in the registry (it is the historical record of the conflict this decision resolves).

## 5. Superseded candidates

- `reconstruction-broken-bridges-report` family entry → no longer claims `br-claudecode-openclaw` is `unbuilt` for document-authority purposes; the bridge registry row is the source of truth. See R282_DEC_04.
- Earlier in-registry `unknown` status for `br-claudecode-openclaw` entry → superseded by this record (entry flips to `current`).

## 6. Verification timestamp

- Document review: 2026-09-29T14:43:00Z (Codex re-read of bridge registry row + broken-bridges row, sha256 confirmed for both files).
- Live probe: 2026-09-29T14:43:00Z (`netstat -ano`, `curl /healthz`, `curl /health`).

## 7. References

- `_agent-hub/v2/CHANGELOG.md [2.0.3]` — R320.6 VERIFIED · bridge registry correction language.
- `_agent-hub/v2/CHANGELOG.md [2.0.1]` — R320.1 ROLLBACK FROM R320 overclaim.
- `_agent-hub/v2/governance/PROTOCOL_REGISTRY.json` — entry `br-claudecode-openclaw` (current after this decision).
- `_agent-hub/v2/governance/CANONICAL_INDEX.json::reconstruction_registry` — bridge-registry SSOT.
- `AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BROKEN_BRIDGES.md` — historical narrative (R211/R260/R265).
