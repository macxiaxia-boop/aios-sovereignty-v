#!/usr/bin/env python3
"""R282: atomic update of PROTOCOL_REGISTRY.json
- flips statuses for 7 existing entries
- appends 7 new decision-record entries
- rewrites current_by_family for all 7 families
- bumps audit_id + captured_at + totals
"""
import hashlib
import json
import os
import sys
import uuid
from pathlib import Path

REG_PATH = Path("D:/AIOS/_agent-hub/v2/governance/PROTOCOL_REGISTRY.json")
DECISIONS_DIR = Path("D:/AIOS/_agent-hub/v2/governance/decisions")


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Load current registry
with open(REG_PATH, "r", encoding="utf-8") as f:
    reg = json.load(f)

# --- Step 1: status flips for existing entries ---
flips = {
    "br-claudecode-openclaw":               ("current",   None),
    "chatgpt-bridge-task-protocol":         ("superseded", "r282-decision-chatgpt-bridge-task-protocol"),
    "cloudtech-xml-winsw":                  ("superseded", "r282-decision-cloudtech-xml-winsw"),
    "reconstruction-broken-bridges-report": ("superseded", "r282-decision-reconstruction-broken-bridges-report"),
    "reconstruction-tool-registry":         ("current",   None),
    "shared-identity-identity":             ("current",   None),
    "v2-health-snapshot":                   ("superseded", "r282-decision-v2-health-snapshot"),
}

by_id = {e["id"]: e for e in reg["entries"]}

# Append decision-record evidence on br-claudecode-openclaw
br = by_id["br-claudecode-openclaw"]
br["evidence"] = br.get("evidence", []) + [
    "R282_DEC_01: document-authority pointer (registry JSON is SSOT for br-claudecode-openclaw row)",
    "Live recheck 2026-09-29 14:43: V22 127.0.0.1:5099 LISTENING PID 23104 /health=200; OpenClaw 127.0.0.1:18792 LISTENING PID 23700 /healthz=HTTP 000 (degraded transient)",
    "Operational state remains loopback_only/unverified (no OpenClaw v2 inbox consumer observed); see R282_DEC_01",
]

for eid, (new_status, new_superseded_by) in flips.items():
    if eid not in by_id:
        print(f"WARN: entry {eid} not found in registry")
        continue
    by_id[eid]["status"] = new_status
    if new_superseded_by is not None:
        by_id[eid]["superseded_by"] = new_superseded_by

assert by_id["br-claudecode-openclaw"]["family"] == "bridge-claudecode-openclaw"

# --- Step 2: append 7 new decision-record entries ---
new_entries = [
    ("bridge-claudecode-openclaw",
     "r282-decision-bridge-claudecode-openclaw",
     "R282_DEC_01_bridge_claudecode_openclaw.md",
     "candidate",
     [
         "Decision record - candidate (evidence-only)",
         "Document-authority pointer resolves to br-claudecode-openclaw (current)",
         "Operational caveat: loopback_only/unverified preserved; v2 queue consumer round-trip still unproven",
         "See PROTOCOL_AUDIT.md R282 section",
     ]),
    ("chatgpt-bridge-task-protocol",
     "r282-decision-chatgpt-bridge-task-protocol",
     "R282_DEC_02_chatgpt_bridge_task_protocol.md",
     "current",
     [
         "Decision record - current (no runtime file exists; family AUTHORITATIVE ABSENT)",
         "39 byte-identical backup copies (sha256 5ca3cd76...) remain frozen rollback artifacts",
         "v2 hub task protocol triad (protocols/v1.md + schemas/task.schema.json + src/state_machine.py) is the replacement",
     ]),
    ("cloudtech-xml-winsw",
     "r282-decision-cloudtech-xml-winsw",
     "R282_DEC_03_cloudtech_xml_winsw.md",
     "current",
     [
         "Decision record - current (.bak XML NOT promoted; install.cmd broken by filename reference)",
         "CloudTechV22Monitor service NOT installed (sc query 1060)",
         "V22 upstream LISTENING PID 23104 /health=200 (operational state independent of adapter)",
         "Repair deferred to CLOUDTECH_REPAIR_PLAN.md (Option A: restore filename; Option B: edit scripts; NOT APPLIED)",
     ]),
    ("reconstruction-broken-bridges-report",
     "r282-decision-reconstruction-broken-bridges-report",
     "R282_DEC_04_reconstruction_broken_bridges_report.md",
     "current",
     [
         "Decision record - current (bridge registry is SSOT; broken-bridges report is historical narrative)",
         "reconstruction-broken-bridges-report entry flipped to superseded",
         "bridge registry tension_with metadata preserved as historical evidence",
     ]),
    ("reconstruction-tool-registry",
     "r282-decision-reconstruction-tool-registry",
     "R282_DEC_05_reconstruction_tool_registry.md",
     "candidate",
     [
         "Decision record - candidate (evidence-only)",
         "tool registry promoted candidate to current; namespace APP_CONNECTOR_FABRIC_PHASE_2_V1 is intentionally separate from R212-stepN-v1",
         "19 tools, 5 utility active, 8 generic candidate, 5 app-connector candidate, 1 failed (pip)",
     ]),
    ("shared-identity-identity",
     "r282-decision-shared-identity-identity",
     "R282_DEC_06_shared_identity_identity.md",
     "candidate",
     [
         "Decision record - candidate (evidence-only)",
         "shared-identity-identity promoted candidate to current; install-links.ps1 junctions ~/.workbuddy/IDENTITY.md to _agent-hub/SOUL.md by design",
         "Workbuddy IDENTITY.md byte-identical to SOUL.md (sha256 084f0b7c...); junction target wired by install-links.ps1 lines 21-29",
     ]),
    ("v2-health-snapshot",
     "r282-decision-v2-health-snapshot",
     "R282_DEC_07_v2_health_snapshot.md",
     "current",
     [
         "Decision record - current (health.json NOT regenerated per task instructions)",
         "health.json captured_at self-reports 2026-09-29T13:30:00Z but mtime is 12:56; CHANGELOG 2.0.3 health table partially stale",
         "Live recheck 2026-09-29 14:43: V22 healthy, OpenClaw /healthz HTTP 000 (degraded); no claim made about per-agent operational state",
     ]),
]

for family, dec_id, dec_filename, dec_status, dec_evidence in new_entries:
    dec_path = f"_agent-hub/v2/governance/decisions/{dec_filename}"
    full_dec = DECISIONS_DIR / dec_filename
    if not full_dec.exists():
        print(f"FAIL: decision record missing: {full_dec}")
        sys.exit(2)
    sha = sha256_file(full_dec)
    size = full_dec.stat().st_size
    entry = {
        "id": dec_id,
        "title": f"R282 Decision Record - family={family}",
        "path": dec_path,
        "version": "R282-2026-09-29",
        "status": dec_status,
        "family": family,
        "supersedes": [],
        "superseded_by": None,
        "evidence": dec_evidence,
        "hash": sha,
        "hash_size_bytes": size,
        "r282_role": "decision_record",
    }
    reg["entries"].append(entry)

# --- Step 3: update current_by_family for the 7 families ---
pointer_map = {
    "bridge-claudecode-openclaw":           "br-claudecode-openclaw",
    "chatgpt-bridge-task-protocol":         "r282-decision-chatgpt-bridge-task-protocol",
    "cloudtech-xml-winsw":                  "r282-decision-cloudtech-xml-winsw",
    "reconstruction-broken-bridges-report": "r282-decision-reconstruction-broken-bridges-report",
    "reconstruction-tool-registry":         "reconstruction-tool-registry",
    "shared-identity-identity":             "shared-identity-identity",
    "v2-health-snapshot":                   "r282-decision-v2-health-snapshot",
}

cbf = reg["current_by_family"]
for fam, ptr in pointer_map.items():
    if fam not in cbf:
        print(f"FAIL: family {fam!r} missing from current_by_family")
        sys.exit(2)
    cbf[fam] = ptr

# --- Step 4: update audit_id + captured_at + totals + policy ---
reg["audit_id"] = "system-audit-20260929-R282"
reg["captured_at"] = now_iso()
reg["policy"] = (
    "current-pointer order: current_by_family[family] > CANONICAL_INDEX pointer > explicit supersedes chain > hash/mtime as evidence only. "
    "mtime/hash are NEVER sole selectors. "
    "R282: decision records under governance/decisions/ may serve as current pointers when (a) no runtime file is legitimate, "
    "or (b) the runtime file is stale/broken/non-authoritative. Decision records have r282_role=decision_record and status "
    "current or candidate per the per-family decision."
)

# Recompute totals_by_status
status_counts = {"current": 0, "candidate": 0, "superseded": 0, "unknown": 0}
for e in reg["entries"]:
    st = e.get("status")
    if st in status_counts:
        status_counts[st] += 1
    else:
        print(f"WARN: entry {e.get('id')} has unknown status {st!r}")
reg["totals_by_status"] = status_counts

n_unresolved = sum(1 for v in cbf.values() if v is None)
n_current = sum(1 for v in cbf.values() if v is not None)
reg["totals"] = {
    "entries": len(reg["entries"]),
    "families": len(set(e["family"] for e in reg["entries"] if e.get("family"))),
    "current": n_current,
    "unresolved": n_unresolved,
}

# --- Step 5: atomic write ---
tmp_path = REG_PATH.with_name(f"{REG_PATH.stem}.{uuid.uuid4().hex[:12]}.tmp")
data = json.dumps(reg, ensure_ascii=False, indent=2)
with open(tmp_path, "w", encoding="utf-8") as f:
    f.write(data)
    f.flush()
    try:
        os.fsync(f.fileno())
    except OSError:
        pass
try:
    os.replace(tmp_path, REG_PATH)
except OSError as exc:
    try:
        os.remove(tmp_path)
    except OSError:
        pass
    print(f"FAIL: os.replace failed ({exc})", file=sys.stderr)
    sys.exit(2)

print(f"OK: R282 registry update applied")
print(f"  audit_id: {reg['audit_id']}")
print(f"  captured_at: {reg['captured_at']}")
print(f"  entries: {len(reg['entries'])}")
print(f"  families: {reg['totals']['families']}")
print(f"  current: {n_current} / {len(cbf)} (rest unresolved: {n_unresolved})")
print(f"  totals_by_status: {status_counts}")
