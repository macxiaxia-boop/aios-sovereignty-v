# R282 Decision Record · family=reconstruction-tool-registry

| Field | Value |
|---|---|
| Decision ID | `r282-decision-reconstruction-tool-registry` |
| Family | `reconstruction-tool-registry` |
| Audit round | R282 (2026-09-29, post-R281.2 PROTOCOL_AUDIT) |
| Verdict | **PROMOTE candidate → current** — namespace is intentionally separate, not a defect |
| Confidence | HIGH |
| Captured at | 2026-09-29T14:43:00Z |

## 1. Question

The protocol family `reconstruction-tool-registry` was UNRESOLVED because the registry file uses version field `APP_CONNECTOR_FABRIC_PHASE_2_V1` while every other R212 registry uses `R212-stepN-v1`. Is the namespace anomaly a defect, or is it intentional? If intentional, can the file be promoted to `current`?

## 2. Evidence (disk truth)

### 2.1 File of record

| Path | Size (B) | mtime | sha256 (12) | Version field | Tool count |
|---|---:|---|---|---|---:|
| `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_TOOL_REGISTRY.json` | 5,858 | 2026-09-27 01:20 | `e139d5309eb5` | `APP_CONNECTOR_FABRIC_PHASE_2_V1` | 19 |

### 2.2 Namespace comparison with siblings

| Family | Path | Version field |
|---|---|---|
| `reconstruction-system-registry` | `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_SYSTEM_REGISTRY.json` | `R212-step2-v1` |
| `reconstruction-agent-registry` | `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_AGENT_REGISTRY.json` | `R212-step4-v1` |
| `reconstruction-skill-registry` | `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_SKILL_REGISTRY.json` | `R212-step4-v1` |
| `reconstruction-mcp-registry` | `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_MCP_REGISTRY.json` | `R212-step4-v1` |
| **`reconstruction-tool-registry`** | **`AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_TOOL_REGISTRY.json`** | **`APP_CONNECTOR_FABRIC_PHASE_2_V1`** ← anomaly |

### 2.3 Why the namespace is intentionally separate

Reading the file content directly:

- 6 generic tools (ffmpeg / Whisper / WhisperX / PySceneDetect / MoviePy / OpenCV / auto-editor / Remotion) — all `status=candidate`, capability-mapped to VIDEO/AUDIO/SEARCH families (Phase 1 candidate set).
- 5 utility tools (Tavily / gh / pip / npm / python / git) — operational, `status=active` or `failed`.
- **5 app-connector tools** (Baidu Netdisk / Frappe ERPNext / Odoo 19 JSON-2 / Cross-App G5):
  - Each has `module` + `class` + `actions` + `transport` + `authority` + `credentials_required` + `evidence_ref` fields specific to the App Connector Fabric Phase 2 work.
  - `evidence_ref` points at `D:/AIOS/_workzone/app_connectors/evidence/phase2/` (and `phase5/` for the cross-app slice).
  - Phase 2 is **post-R212** work (it builds on top of the reconstruction but is its own deliverable).

The version field `APP_CONNECTOR_FABRIC_PHASE_2_V1` correctly signals:
- The file is the OUTPUT of App Connector Fabric Phase 2 work, not an input to the R212 reconstruction sweep.
- Renaming to `R212-stepN-v1` would be a misattribution (the file is not part of R212 step N).
- Keeping the distinct namespace preserves the traceability from registry row → evidence directory.

### 2.4 `required_decision` field on the existing registry entry

The R281.1 entry text: "namespace policy: rename to R212-step5-v1 OR keep separate namespace".

This decision RESOLVES that required decision: **keep the namespace as-is**.

### 2.5 No other candidate for the family

- No other `AIOS_TOOL_REGISTRY*` file exists in the tree.
- No rename proposal was committed; the existing file has stable content since 2026-09-27 01:20.

## 3. Decision

1. **Promote `reconstruction-tool-registry` entry to `status=current`.** The file IS the canonical tool registry; the namespace is intentionally distinct from R212-stepN, not a defect.
2. **`current_by_family[reconstruction-tool-registry] = reconstruction-tool-registry`.**
3. **The decision record is appended as a NEW entry `r282-decision-reconstruction-tool-registry` with `status=candidate`**, providing the rationale and the future-proofing guarantee that the namespace will not be silently renamed.
4. **Operational caveat preserved**: of the 19 tools, 8 are `candidate` (ffmpeg, Whisper, WhisperX, PySceneDetect, MoviePy, OpenCV, auto-editor, Remotion), 5 are `active` (Tavily, gh, npm, python, git), 1 is `failed` (pip), and 5 are app-connector `candidate` (Baidu Netdisk, Frappe, Odoo 19, Cross-App G5). This is the registry's internal status distribution; R282 does not modify any tool row.

## 4. Limitations

- This decision does NOT retrofit the file's internal status rows. The 8 candidate generic tools remain `status=candidate` — promoting them to `active` would require a separate codex round with runtime evidence (binary on disk, version probe, smoke test).
- This decision does NOT rename the version field. The distinct namespace is the rationale for the decision.

## 5. Superseded candidates

- No candidates are superseded. The previous `candidate` status on the existing entry was a registry-level placeholder (waiting for this decision), not a conflict with another file.

## 6. Verification timestamp

- File review: 2026-09-29T14:43:00Z (sha256 + mtime + content cross-check against sibling registries).
- Namespace reasoning: documented inline above (section 2.3).

## 7. References

- `AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_TOOL_REGISTRY.json` — the canonical file (now `current`).
- `D:/AIOS/_workzone/app_connectors/evidence/phase2/` — Phase 2 evidence directory referenced by the 4 connector rows.
- `D:/AIOS/_workzone/app_connectors/evidence/phase5/` — Cross-App G5 evidence directory.
- `CANONICAL_INDEX.json::reconstruction_registry.tool_registry` — current pointer in the index.
- R281.1 `PROTOCOL_AUDIT.md §3` — original observation of the namespace anomaly.
