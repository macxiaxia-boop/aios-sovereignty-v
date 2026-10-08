#!/usr/bin/env python3
# Helper to build the new PROTOCOL_REGISTRY.json with families + current_by_family.
# Computes real sha256 for each ≤20MB entry on disk.

import hashlib
import json
import os
import uuid
from pathlib import Path

ROOT = Path("D:/AIOS").resolve()
GOV = Path("_agent-hub/v2/governance")


def sha256_file(p, cap=20 * 1024 * 1024):
    h = hashlib.sha256()
    total = 0
    with open(p, "rb") as f:
        while True:
            buf = f.read(65536)
            if not buf:
                break
            h.update(buf)
            total += len(buf)
            if total >= cap:
                break
    return h.hexdigest()


# Each entry: id, title, path (relative to D:/AIOS or null), version, status,
# family, supersedes (list of entry ids), superseded_by (id or null),
# evidence (list of strings), hash (sha256 or null).
ENTRIES = [
    {
        "id": "agent-hub-v2-protocol",
        "title": "AIOS Hub v2 Bidirectional Protocol",
        "path": "_agent-hub/v2/protocols/v1.md",
        "version": "1.0",
        "status": "current",
        "family": "v2-bidirectional-protocol",
        "supersedes": [],
        "superseded_by": None,
        "evidence": [
            "Only file under _agent-hub/v2/protocols/",
            "CHANGELOG 2.0.0..2.0.3 records R320.1 / R320.6 audit + live round-trip",
            "README.md line 7: 'canonical, versioned, machine-validated extension'",
        ],
    },
    {
        "id": "v2-envelope-schema",
        "title": "AIOS Hub v2 Envelope JSON Schema",
        "path": "_agent-hub/v2/schemas/envelope.schema.json",
        "version": "1.0",
        "status": "current",
        "family": "v2-envelope-schema",
        "supersedes": [],
        "superseded_by": None,
        "evidence": [
            "protocols/v1.md line 32: 'SSOT: this file + the JSON Schema it points to'",
            "src/envelope.py runs validate_envelope on every build_envelope",
        ],
    },
    {
        "id": "v2-task-schema",
        "title": "AIOS Hub v2 Task Schema",
        "path": "_agent-hub/v2/schemas/task.schema.json",
        "version": "1.0",
        "status": "current",
        "family": "v2-task-schema",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["Only task schema; consumed by src/state_machine.py"],
    },
    {
        "id": "v2-state-schema",
        "title": "AIOS Hub v2 State Snapshot Schema",
        "path": "_agent-hub/v2/schemas/state.schema.json",
        "version": "1.0",
        "status": "current",
        "family": "v2-state-schema",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["Only state schema; consumed by src/state_machine.py save_state_snapshot"],
    },
    {
        "id": "v2-agent-registry",
        "title": "AIOS Hub v2 Cross-Agent Identity Registry (SSOT)",
        "path": "_agent-hub/v2/agents/agents.json",
        "version": "v2-2026-09-29",
        "status": "current",
        "family": "v2-agent-registry",
        "supersedes": [],
        "superseded_by": None,
        "evidence": [
            "README.md line 20: 'agents/agents.json ← canonical agent registry (SSOT)'",
            "Header field: 'SSOT for cross-agent identity'",
        ],
        "agents": ["codex", "claudecode", "workbuddy", "hermes", "openclaw"],
    },
    {
        "id": "v2-paths-ssot",
        "title": "AIOS Hub v2 Path Constants (SSOT)",
        "path": "_agent-hub/v2/src/paths.py",
        "version": "1.0",
        "status": "current",
        "family": "v2-paths-ssot",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["V2_ROOT constant", "Every other module imports from here"],
    },
    {
        "id": "v2-implementation-report",
        "title": "AIOS Hub v2 Implementation Report",
        "path": "_agent-hub/v2/reports/IMPLEMENTATION_REPORT.md",
        "version": "2.0.3",
        "status": "current",
        "family": "v2-implementation-report",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["41KB single source for v2 completion matrix"],
    },
    {
        "id": "v2-health-snapshot",
        "title": "AIOS Hub v2 Health Snapshot",
        "path": "_agent-hub/v2/reports/health.json",
        "version": "v2-2026-09-29",
        "status": "candidate",
        "family": "v2-health-snapshot",
        "supersedes": [],
        "superseded_by": None,
        "evidence": [
            "mtime 2026-09-29 12:56 (predates CHANGELOG 2.0.3 timestamp)",
            "Conflict with CHANGELOG 2.0.3 wording",
        ],
        "required_decision": "rerun aiosv2.py health to regenerate",
    },
    {
        "id": "reconstruction-system-registry",
        "title": "AIOS System Registry (R212 step2 v1)",
        "path": "AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_SYSTEM_REGISTRY.json",
        "version": "R212-step2-v1",
        "status": "current",
        "family": "reconstruction-system-registry",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["7 systems indexed"],
    },
    {
        "id": "reconstruction-agent-registry",
        "title": "AIOS Agent Registry (R212 step4 v1)",
        "path": "AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_AGENT_REGISTRY.json",
        "version": "R212-step4-v1",
        "status": "current",
        "family": "reconstruction-agent-registry",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["18 agents indexed"],
    },
    {
        "id": "reconstruction-skill-registry",
        "title": "AIOS Skill Registry (R212 step4 v1)",
        "path": "AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_SKILL_REGISTRY.json",
        "version": "R212-step4-v1",
        "status": "current",
        "family": "reconstruction-skill-registry",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["11 families / 340 packages / spec#3 rule"],
    },
    {
        "id": "reconstruction-mcp-registry",
        "title": "AIOS MCP Registry (R212 step4 v1)",
        "path": "AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_MCP_REGISTRY.json",
        "version": "R212-step4-v1",
        "status": "current",
        "family": "reconstruction-mcp-registry",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["11 MCP servers indexed"],
    },
    {
        "id": "reconstruction-tool-registry",
        "title": "AIOS Tool Registry",
        "path": "AIOS_RECONSTRUCTION/01_REGISTRY/AIOS_TOOL_REGISTRY.json",
        "version": "APP_CONNECTOR_FABRIC_PHASE_2_V1",
        "status": "candidate",
        "family": "reconstruction-tool-registry",
        "supersedes": [],
        "superseded_by": None,
        "evidence": [
            "Only registry that does NOT use R212-stepN-v1 namespace",
            "Freshest mtime among registries (2026-09-27 01:20)",
            "19 tools + connectors",
        ],
        "required_decision": "namespace policy: rename to R212-step5-v1 OR keep separate namespace",
    },
    {
        "id": "reconstruction-bridge-registry",
        "title": "AIOS Bridge Registry (R212 step4 v1)",
        "path": "AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json",
        "version": "R212-step4-v1",
        "status": "current",
        "family": "reconstruction-bridge-registry",
        "supersedes": [],
        "superseded_by": None,
        "evidence": [
            "9 bridges",
            "Modified 2026-09-29 (today)",
            "Tracks R320.6 status correction for br-claudecode-openclaw",
        ],
        "tension_with": "reconstruction-broken-bridges-report",
    },
    {
        "id": "reconstruction-broken-bridges-report",
        "title": "AIOS Broken Bridges Report (R212)",
        "path": "AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BROKEN_BRIDGES.md",
        "version": "R212-2026-09-26",
        "status": "candidate",
        "family": "reconstruction-broken-bridges-report",
        "supersedes": [],
        "superseded_by": None,
        "evidence": [
            "mtime 2026-09-27 17:50",
            "spec#37",
            "Tracks R211/R260/R265 repairs",
            "Lists br-claudecode-openclaw as CANDIDATE / unbuilt — CONFLICTS with bridge registry",
        ],
        "tension_with": "reconstruction-bridge-registry",
    },
    {
        "id": "reconstruction-capability-graph",
        "title": "AIOS Capability Graph (R212 step8 v1)",
        "path": "AIOS_RECONSTRUCTION/04_CAPABILITY_GRAPH/AIOS_CAPABILITY_GRAPH.json",
        "version": "R212-step8-v1",
        "status": "current",
        "family": "reconstruction-capability-graph",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["6 capabilities; spec#34"],
    },
    {
        "id": "reconstruction-canonical-candidates",
        "title": "AIOS Canonical Candidates (R212 step3 v1)",
        "path": "AIOS_RECONSTRUCTION/02_CANONICAL/AIOS_CANONICAL_CANDIDATES.json",
        "version": "R212-step3-v1",
        "status": "current",
        "family": "reconstruction-canonical-candidates",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["80 candidate AGENTS.md/CLAUDE.md paths"],
    },
    {
        "id": "reconstruction-reality-map",
        "title": "AIOS Reality Map (R212 step1 v2-targeted)",
        "path": "AIOS_RECONSTRUCTION/00_REALITY/AIOS_REALITY_MAP.json",
        "version": "R212-step1-v2-targeted",
        "status": "current",
        "family": "reconstruction-reality-map",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["Only -v2-targeted version field in tree"],
    },
    {
        "id": "reconstruction-progress",
        "title": "AIOS Reconstruction Progress",
        "path": "AIOS_RECONSTRUCTION/AIOS_RECONSTRUCTION_PROGRESS.json",
        "version": "R212-AIOS-RECONSTRUCTION",
        "status": "current",
        "family": "reconstruction-progress",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["Self-reports overall COMPLETE; P2/P6 in_progress; P7-P9 pending"],
    },
    {
        "id": "shared-identity-agents",
        "title": "Shared AGENTS.md (cross-agent)",
        "path": "_agent-hub/AGENTS.md",
        "version": "2026-09-28",
        "status": "current",
        "family": "shared-identity-agents",
        "supersedes": [
            "shared-identity-agents.workbuddy-bak-2026-09-22",
        ],
        "superseded_by": None,
        "evidence": ["Propagates to ~/.codex/AGENTS.md via install-links.ps1 / sync-from-hub.ps1"],
    },
    {
        "id": "shared-identity-agents.workbuddy-bak-2026-09-22",
        "title": "AGENTS.md (workbuddy junction .bak)",
        "path": "_relinked/workbuddy/AGENTS.md.bak (if exists) or junction source",
        "version": "2026-09-22",
        "status": "superseded",
        "family": "shared-identity-agents",
        "supersedes": [],
        "superseded_by": "shared-identity-agents",
        "evidence": ["backup from 2026-09-22"],
        "copy_count": 1,
    },
    {
        "id": "shared-identity-claude",
        "title": "Shared CLAUDE.md (cross-agent)",
        "path": "_agent-hub/CLAUDE.md",
        "version": "2026-09-28",
        "status": "current",
        "family": "shared-identity-claude",
        "supersedes": ["shared-identity-claude.userhome-bak"],
        "superseded_by": None,
        "evidence": ["Propagates to ~/.claude/CLAUDE.md via sync-from-hub.ps1"],
    },
    {
        "id": "shared-identity-claude.userhome-bak",
        "title": "CLAUDE.md (user home .bak)",
        "path": "C:/Users/xinzh/.claude/CLAUDE.md.bak",
        "version": "2026-09-28",
        "status": "superseded",
        "family": "shared-identity-claude",
        "supersedes": [],
        "superseded_by": "shared-identity-claude",
        "evidence": ["superseded 2026-09-28"],
        "copy_count": 1,
    },
    {
        "id": "shared-identity-memory",
        "title": "Shared MEMORY.md (cross-agent)",
        "path": "_agent-hub/MEMORY.md",
        "version": "2026-09-28",
        "status": "current",
        "family": "shared-identity-memory",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["CloudTech project context, competitive positioning"],
    },
    {
        "id": "shared-identity-soul",
        "title": "Shared SOUL.md (cross-agent identity)",
        "path": "_agent-hub/SOUL.md",
        "version": "2026-09-28",
        "status": "current",
        "family": "shared-identity-soul",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["Single source of truth for 'who I am' across agents"],
    },
    {
        "id": "shared-identity-user",
        "title": "Shared USER.md (cross-agent user profile)",
        "path": "_agent-hub/USER.md",
        "version": "2026-09-28",
        "status": "current",
        "family": "shared-identity-user",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["CloudTech founder profile, Chinese-speaking, structured output"],
    },
    {
        "id": "shared-identity-bootstrap",
        "title": "WorkBuddy BOOTSTRAP.md",
        "path": "_relinked/workbuddy/BOOTSTRAP.md",
        "version": "2026-09-29",
        "status": "current",
        "family": "shared-identity-bootstrap",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["Only file at workbuddy root; not propagated to other agents"],
    },
    {
        "id": "shared-identity-identity",
        "title": "WorkBuddy IDENTITY.md",
        "path": "_relinked/workbuddy/IDENTITY.md",
        "version": "2026-09-28",
        "status": "candidate",
        "family": "shared-identity-identity",
        "supersedes": ["shared-identity-identity.workbuddy-bak"],
        "superseded_by": None,
        "evidence": ["Exists only for WorkBuddy; install-links.ps1 also points IDENTITY.md at _agent-hub/SOUL.md"],
    },
    {
        "id": "shared-identity-identity.workbuddy-bak",
        "title": "IDENTITY.md (workbuddy .bak)",
        "path": "_relinked/workbuddy/IDENTITY.md.bak",
        "version": "2026-09-22",
        "status": "superseded",
        "family": "shared-identity-identity",
        "supersedes": [],
        "superseded_by": "shared-identity-identity",
        "evidence": ["backup from 2026-09-22"],
        "copy_count": 1,
    },
    {
        "id": "br-claudecode-openclaw",
        "title": "Bridge: Claude Code ↔ OpenClaw (status entry)",
        "path": "AIOS_RECONSTRUCTION/03_BRIDGES/AIOS_BRIDGE_REGISTRY.json",
        "version": "R212-step4-v1",
        "status": "unknown",
        "family": "bridge-claudecode-openclaw",
        "supersedes": [],
        "superseded_by": None,
        "evidence": [
            "bridge registry: status=loopback_only, health=unverified (R320.6)",
            "broken bridges report: status=CANDIDATE, health=unbuilt — CONFLICTS",
        ],
        "required_decision": "loopback_only vs unbuilt — user must confirm",
    },
    {
        "id": "chatgpt-bridge-task-protocol",
        "title": "TASK_PROTOCOL.md (chatgpt_bridge)",
        "path": "_backups/chatgpt_bridge_pre_rollback_to_V4P9-FINAL_20260927_151216/TASK_PROTOCOL.md",
        "version": None,
        "status": "superseded",
        "family": "chatgpt-bridge-task-protocol",
        "supersedes": [],
        "superseded_by": None,
        "evidence": ["3 identical copies across _backups/chatgpt_bridge_pre_rollback_*/; legacy bridge module, replaced by v2 hub"],
        "copy_count": 3,
    },
    {
        "id": "cloudtech-xml-winsw",
        "title": "CloudTech V22 WinSW Service Descriptor",
        "path": "cloudtech-saas/cloudtech-saas.xml.bak_C_1790215941",
        "version": None,
        "status": "candidate",
        "family": "cloudtech-xml-winsw",
        "supersedes": [],
        "superseded_by": None,
        "evidence": [
            "File renamed with .bak_C_1790215941 suffix",
            "install.cmd references 'cloudtech-saas.xml' (without suffix) which does NOT exist",
            "install.cmd will fail out-of-the-box",
        ],
        "required_decision": "restore xml file or update install.cmd reference",
    },
]


def main():
    # Compute hash for each entry that has path & exists & ≤20MB
    for e in ENTRIES:
        p = e.get("path")
        if not p:
            e["hash"] = None
            continue
        # Windows path; resolve against ROOT
        rel = p
        # If path contains ':' it's absolute Windows; skip hash
        if ":" in rel.split("/")[0] if "/" in rel else ":" in rel:
            e["hash"] = None
            e.setdefault("evidence", []).append(
                f"absolute path; hash not computed by this build: {p}"
            )
            continue
        ap = ROOT / rel
        if not ap.exists() or not ap.is_file():
            e["hash"] = None
            e.setdefault("evidence", []).append(
                f"path missing at build: {p}"
            )
            continue
        sz = ap.stat().st_size
        if sz > 20 * 1024 * 1024:
            e["hash"] = None
            e.setdefault("evidence", []).append(
                f"size {sz} > 20MB cap; hash not computed"
            )
            continue
        e["hash"] = sha256_file(ap)
        e["hash_size_bytes"] = sz

    # Build current_by_family: each family has exactly one current id (the
    # entry with status=current); families where no entry is current or where
    # multiple are current → null (UNRESOLVED).
    by_family = {}
    for e in ENTRIES:
        fam = e["family"]
        if e["status"] == "current":
            if fam in by_family:
                by_family[fam] = None  # ambiguous
            else:
                by_family[fam] = e["id"]
    # Ensure every family has a key
    families = sorted({e["family"] for e in ENTRIES})
    for fam in families:
        by_family.setdefault(fam, None)

    # Status counts
    from collections import Counter
    sc = Counter(e["status"] for e in ENTRIES)

    reg = {
        "schema": 2,
        "audit_id": "system-audit-20260929-R281.1",
        "captured_at": "2026-09-29T14:30:00Z",
        "policy": (
            "current-pointer order: "
            "current_by_family[family] > CANONICAL_INDEX pointer > "
            "explicit supersedes chain > hash/mtime as evidence only. "
            "mtime/hash are NEVER sole selectors."
        ),
        "totals_by_status": dict(sc),
        "totals": {
            "entries": len(ENTRIES),
            "families": len(families),
            "current": sum(1 for v in by_family.values() if v is not None),
            "unresolved": sum(1 for v in by_family.values() if v is None),
        },
        "current_by_family": by_family,
        "entries": ENTRIES,
    }

    out = GOV / "PROTOCOL_REGISTRY.json"
    tmp = out.with_name(f"{out.stem}.{uuid.uuid4().hex[:12]}.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)
    # Atomic replace; do NOT remove target on failure
    try:
        os.replace(tmp, out)
    except OSError as e:
        try:
            if tmp.exists():
                os.remove(tmp)
        except OSError:
            pass
        print(f"FAIL: {e}")
        return 2
    print(f"OK: wrote {out}")
    print(f"  entries: {len(ENTRIES)}")
    print(f"  families: {len(families)}")
    print(f"  current: {sum(1 for v in by_family.values() if v is not None)}")
    print(f"  unresolved: {sum(1 for v in by_family.values() if v is None)}")
    print(f"  by status: {dict(sc)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
