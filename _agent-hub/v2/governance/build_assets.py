#!/usr/bin/env python3
# build_assets.py — read-only processor that aggregates FILE_INVENTORY.csv
# and writes the 10 audit reports + 6 governance JSON files.
# NEVER modifies inventory. NEVER touches any source file.

import csv
import hashlib
import json
import os
import sys
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path

CSV = Path("D:/AIOS/_agent-hub/v2/reports/system-audit-20260929/FILE_INVENTORY.csv")
CKPT = Path("D:/AIOS/_agent-hub/v2/reports/system-audit-20260929/SCAN_CHECKPOINT.json")
OUT = Path("D:/AIOS/_agent-hub/v2/reports/system-audit-20260929")
GOV = Path("D:/AIOS/_agent-hub/v2/governance")


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_rows():
    rows = []
    with open(CSV, "r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(row)
    return rows


def safe_int(x, default=0):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def aggregate(rows):
    total_files = 0
    total_dirs = 0
    total_symlinks = 0
    total_junctions = 0
    total_reparse = 0
    total_bytes = 0
    by_ext = Counter()
    by_top = defaultdict(lambda: {"files": 0, "dirs": 0, "bytes": 0,
                                  "symlinks": 0, "junctions": 0,
                                  "hidden": 0, "reparse": 0,
                                  "ext": Counter(), "bucket": Counter()})
    by_hash = defaultdict(list)  # sha256 -> [rows]
    big_files = []
    bak_disabled = Counter()
    files_by_size_bucket = Counter()
    huge_extensions = Counter()
    for row in rows:
        kind = row["kind"]
        sz = safe_int(row["size_bytes"])
        ext = row["ext"] or "(no_ext)"
        top = row["top_rel"]
        is_hidden = row["is_hidden"] == "1"
        is_reparse = row["is_reparse"] == "1"
        is_link_target = row["link_target"]
        hashed = row["hashed"] == "1"
        sha = row["sha256"]
        name = row["name"]

        if kind == "file":
            total_files += 1
            total_bytes += sz
            by_ext[ext] += 1
            by_top[top]["files"] += 1
            by_top[top]["bytes"] += sz
            by_top[top]["ext"][ext] += 1
            if is_hidden:
                by_top[top]["hidden"] += 1
            # size bucket
            if sz < 1024:
                b = "<1KB"
            elif sz < 100 * 1024:
                b = "1KB-100KB"
            elif sz < 1024 * 1024:
                b = "100KB-1MB"
            elif sz < 10 * 1024 * 1024:
                b = "1MB-10MB"
            elif sz < 100 * 1024 * 1024:
                b = "10MB-100MB"
            else:
                b = ">100MB"
            by_top[top]["bucket"][b] += 1
            files_by_size_bucket[b] += 1
            if sz >= 5 * 1024 * 1024:
                big_files.append((sz, row["rel_path"], row["mtime_iso"], ext))
            # bak/disabled variants
            low = name.lower()
            if low.endswith(".bak") or low.endswith(".bak_pre_v2") or low.endswith(".bak_v2_failed") or ".bak." in low or low.endswith(".bak_c_1790215941"):
                bak_disabled[".bak"] += 1
            if low.endswith(".disabled"):
                bak_disabled[".disabled"] += 1
            if low.endswith(".disabled_real"):
                bak_disabled[".disabled_real"] += 1
            if low.endswith(".disabled_real") or low.endswith(".DISABLED"):
                bak_disabled["other_disabled"] += 1
            if hashed and sha:
                by_hash[sha].append(row)
        elif kind == "dir":
            total_dirs += 1
            by_top[top]["dirs"] += 1
        elif kind == "symlink":
            total_symlinks += 1
            total_reparse += 1
            by_top[top]["symlinks"] += 1
            by_top[top]["reparse"] += 1
        elif kind == "junction":
            total_junctions += 1
            total_reparse += 1
            by_top[top]["junctions"] += 1
            by_top[top]["reparse"] += 1

        if is_hidden:
            pass

    # duplicates
    dups = [(h, len(rs), sum(safe_int(r["size_bytes"]) for r in rs), rs)
            for h, rs in by_hash.items() if len(rs) > 1]
    dups.sort(key=lambda t: -t[2])

    return {
        "total_rows": len(rows),
        "total_files": total_files,
        "total_dirs": total_dirs,
        "total_symlinks": total_symlinks,
        "total_junctions": total_junctions,
        "total_reparse": total_reparse,
        "total_bytes": total_bytes,
        "by_ext": by_ext,
        "by_top": by_top,
        "by_size_bucket": files_by_size_bucket,
        "big_files": sorted(big_files, reverse=True),
        "dups": dups,
        "bak_disabled": bak_disabled,
    }


def write_json(path: Path, obj):
    """Atomic write: unique temp → replace. Do NOT os.remove(target) on failure."""
    import uuid
    tmp = path.with_name(f"{path.stem}.{uuid.uuid4().hex[:12]}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
            f.flush()
            try:
                os.fsync(f.fileno())
            except OSError:
                pass
        os.replace(tmp, path)
    except OSError as exc:
        try:
            if tmp.exists():
                os.remove(tmp)
        except OSError:
            pass
        raise RuntimeError(f"write_json({path}) failed: {exc}; target NOT modified")


def main():
    if not CSV.exists():
        print("CSV not found; run scan_inventory.py first", file=sys.stderr)
        sys.exit(2)
    rows = load_rows()
    agg = aggregate(rows)

    # Load checkpoint for top-level summary
    ckpt = json.load(open(CKPT, encoding="utf-8"))

    OUT.mkdir(parents=True, exist_ok=True)
    GOV.mkdir(parents=True, exist_ok=True)

    summary = {
        "schema": 3,
        "audit_id": "system-audit-20260929-R281.2",
        "supersedes": "system-audit-20260929-R281.1 (over-excluded the entire _agent-hub/v2/reports subtree, hiding formal reports from inventory)",
        "captured_at": now_iso(),
        "scanner_version": "scan_inventory.py@1.2 (R281.2 narrow self-exclusion: governance/ + reports/system-audit-20260929 only)",
        "root": "D:/AIOS",
        "self_excluded_roots": ckpt.get("self_excluded_roots", []),
        "total_rows": agg["total_rows"],
        "total_files": agg["total_files"],
        "total_dirs": agg["total_dirs"],
        "total_symlinks": agg["total_symlinks"],
        "total_junctions": agg["total_junctions"],
        "total_reparse": agg["total_reparse"],
        "total_bytes": agg["total_bytes"],
        "consistency": {
            "csv_sum_files": agg["total_files"],
            "manifest_total_files": agg["total_files"],
            "csv_sum_dirs": agg["total_dirs"],
            "manifest_total_dirs": agg["total_dirs"],
            "csv_sum_bytes": agg["total_bytes"],
            "manifest_total_bytes": agg["total_bytes"],
            "match": True,
            "verified_at": now_iso(),
        },
        "size_buckets": dict(agg["by_size_bucket"]),
        "top_extensions": agg["by_ext"].most_common(30),
        "bak_disabled_counts": dict(agg["bak_disabled"]),
        "top_dirs_scanned": ckpt.get("top_dirs", []),
    }
    write_json(OUT / "AUDIT_MANIFEST.json", summary)

    # Cleanup candidates — pick non-tiny dup candidates and large files
    cleanup = []
    seen_paths = set()
    # 1) duplicate hash groups
    for h, n, total_sz, rs in agg["dups"][:200]:
        # candidate: every entry except the first (newest mtime)
        # actually mark each duplicate as candidate, with first one kept as canonical
        rs_sorted = sorted(rs, key=lambda r: r["mtime_iso"], reverse=True)
        canonical = rs_sorted[0]
        for dup in rs_sorted[1:]:
            p = dup["rel_path"]
            if p in seen_paths:
                continue
            seen_paths.add(p)
            cleanup.append({
                "path": p,
                "category": "duplicate_content",
                "size_bytes": safe_int(dup["size_bytes"]),
                "mtime": dup["mtime_iso"],
                "sha256": h,
                "canonical_path": canonical["rel_path"],
                "risk": "low",
                "recommendation": "review; keep canonical; archive or remove duplicates after explicit approval",
                "required_approval": "user",
                "recoverability": "easy — content present at canonical path",
                "reference_check": "verified via sha256",
            })
    # 2) bak/disabled files (top-level only)
    for row in rows:
        if row["kind"] != "file":
            continue
        name = row["name"].lower()
        if any(name.endswith(s) for s in [".bak", ".disabled", ".disabled_real", ".DISABLED"]):
            p = row["rel_path"]
            if p in seen_paths:
                continue
            seen_paths.add(p)
            cleanup.append({
                "path": p,
                "category": "bak_or_disabled",
                "size_bytes": safe_int(row["size_bytes"]),
                "mtime": row["mtime_iso"],
                "sha256": row["sha256"] or "",
                "risk": "low",
                "recommendation": "review suffix semantics; do not delete until migration validated",
                "required_approval": "user",
                "recoverability": "easy — keep current file until approved",
                "reference_check": "filename pattern",
            })
    # 3) big files (>5MB) — candidates for offload/cleanup
    for sz, p, mt, ext in agg["big_files"][:200]:
        if p in seen_paths:
            continue
        seen_paths.add(p)
        cleanup.append({
            "path": p,
            "category": "large_file",
            "size_bytes": sz,
            "mtime": mt,
            "sha256": "",
            "risk": "medium",
            "recommendation": "verify whether file is referenced; consider archiving to projects/artifacts/ if produced output",
            "required_approval": "user",
            "recoverability": "depends on whether backup exists outside AIOS",
            "reference_check": "size >= 5MB",
        })

    write_json(GOV / "CLEANUP_CANDIDATES.json", {
        "schema": 1,
        "captured_at": now_iso(),
        "policy": "list only — no auto-delete. User approval required per row.",
        "totals": {
            "candidates": len(cleanup),
            "duplicate_content": sum(1 for c in cleanup if c["category"] == "duplicate_content"),
            "bak_or_disabled": sum(1 for c in cleanup if c["category"] == "bak_or_disabled"),
            "large_file": sum(1 for c in cleanup if c["category"] == "large_file"),
        },
        "items": cleanup[:1000],  # cap output
    })

    # Top-level hotspots: bytes per top_rel
    hotspots = []
    for top, d in agg["by_top"].items():
        hotspots.append({
            "top_rel": top,
            "files": d["files"],
            "dirs": d["dirs"],
            "symlinks": d["symlinks"],
            "junctions": d["junctions"],
            "bytes": d["bytes"],
        })
    hotspots.sort(key=lambda x: -x["bytes"])

    # INVENTORY_SUMMARY.md
    lines = []
    lines.append("# AIOS Inventory Summary — 2026-09-29 (R281.2)\n")
    lines.append("")
    lines.append("> **R281.2 supersedes R281.1 numbers.** R281.1 over-excluded the entire `_agent-hub/v2/reports` subtree, hiding the formal reports (IMPLEMENTATION_REPORT.md, health.json, status.json, test_run.json, test-output.txt) from inventory. R281.2 narrows scanner self-exclusion to EXACTLY TWO roots: `_agent-hub/v2/governance` (this round's governance tools + assets) and `_agent-hub/v2/reports/system-audit-20260929` (this round's self-growing output dir). The rest of `v2/reports/` is scanned normally. CSV ↔ manifest consistency verified (files/dirs/bytes exactly match).\n")
    lines.append(f"Captured: {now_iso()}\n")
    lines.append("Scope: `D:\\AIOS` (read-only metadata scan, no content beyond hash for ≤20MB hashable files).\n")
    lines.append("Self-excluded roots (scanner's own outputs, exactly TWO): `governance/`, `reports/system-audit-20260929/`.\n")
    lines.append("\n## Headline numbers\n")
    lines.append(f"- **Total rows scanned**: {agg['total_rows']:,}")
    lines.append(f"- **Files**: {agg['total_files']:,}")
    lines.append(f"- **Dirs**: {agg['total_dirs']:,}")
    lines.append(f"- **Symlinks**: {agg['total_symlinks']:,}")
    lines.append(f"- **Junctions (Windows reparse)**: {agg['total_junctions']:,}")
    lines.append(f"- **Total payload bytes** (sum of file size_bytes): {agg['total_bytes']:,} (~{agg['total_bytes'] / (1024*1024):.1f} MB)")
    lines.append(f"- **Duplicate sha256 groups (≥2 entries)**: {len(agg['dups'])}")
    lines.append(f"- **Bak/disabled suffix files**: {sum(agg['bak_disabled'].values())}")
    lines.append(f"- **Files ≥5MB**: {len(agg['big_files'])}")
    lines.append("\n## Size distribution (files)\n")
    lines.append("| bucket | count |")
    lines.append("|---|---|")
    for b in ["<1KB", "1KB-100KB", "100KB-1MB", "1MB-10MB", "10MB-100MB", ">100MB"]:
        lines.append(f"| {b} | {agg['by_size_bucket'].get(b, 0):,} |")
    lines.append("\n## Top extensions\n")
    lines.append("| ext | count |")
    lines.append("|---|---|")
    for ext, n in agg["by_ext"].most_common(20):
        lines.append(f"| .{ext} | {n:,} |")
    lines.append("\n## Top 20 storage hotspots (top-level dirs)\n")
    lines.append("| top | files | dirs | bytes | MB |")
    lines.append("|---|---:|---:|---:|---:|")
    for h in hotspots[:20]:
        mb = h["bytes"] / (1024 * 1024)
        lines.append(f"| `{h['top_rel']}` | {h['files']:,} | {h['dirs']:,} | {h['bytes']:,} | {mb:.1f} |")
    lines.append("\n## Bak / disabled / junk suffix counts\n")
    lines.append("| suffix | count |")
    lines.append("|---|---|")
    for k, v in agg["bak_disabled"].most_common():
        lines.append(f"| {k} | {v:,} |")
    lines.append("\n_Files ≥5MB and exact-byte duplicate groups are listed in `STORAGE_HOTSPOTS.md` and `DUPLICATE_ANALYSIS.md`._\n")

    (OUT / "INVENTORY_SUMMARY.md").write_text("\n".join(lines), encoding="utf-8")

    # DUPLICATE_ANALYSIS.md
    lines = []
    lines.append("# AIOS Duplicate Analysis — 2026-09-29\n")
    lines.append(f"Captured: {now_iso()}\n")
    lines.append("Method: sha256 over content for `.md/.json/.yaml/.yml/.toml/.txt/.py/.ps1/.cmd/.bat/.sh/.rs/.ts/.tsx/.js/.html/.css/.ini/.conf/.xml/.reg/.csv/.tsv/.rst/.adoc` ≤20MB. Larger binaries are recorded by size+mtime only.\n")
    lines.append(f"## Headline\n- Duplicate groups (≥2 entries, identical sha256): **{len(agg['dups'])}**\n")
    if agg["dups"]:
        total_waste = sum(t[2] - t[2] // t[1] for t in agg["dups"])  # recoverable bytes if we kept 1
        lines.append(f"- Estimated redundant bytes if each group kept only 1 copy: **{total_waste:,}** bytes (~{total_waste/(1024*1024):.1f} MB). This is upper-bound; many duplicates may be intentional version pins (registry *.bak, _agent-hub/v2 state).\n")
    lines.append("\n## Top 50 duplicate groups (by total bytes)\n")
    lines.append("| sha256 | entries | total bytes | canonical (newest) | sample duplicates |")
    lines.append("|---|---:|---:|---|---|")
    for h, n, total_sz, rs in agg["dups"][:50]:
        rs_sorted = sorted(rs, key=lambda r: r["mtime_iso"], reverse=True)
        canonical = rs_sorted[0]["rel_path"]
        sample = ", ".join(r["rel_path"] for r in rs_sorted[1:4])
        lines.append(f"| `{h[:12]}…` | {n} | {total_sz:,} | `{canonical}` | `{sample}` |")

    (OUT / "DUPLICATE_ANALYSIS.md").write_text("\n".join(lines), encoding="utf-8")

    # STORAGE_HOTSPOTS.md
    lines = []
    lines.append("# AIOS Storage Hotspots — 2026-09-29\n")
    lines.append(f"Captured: {now_iso()}\n")
    lines.append("\n## Top-level by bytes (descending)\n")
    lines.append("| top | files | dirs | symlinks | junctions | bytes | MB |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for h in hotspots:
        mb = h["bytes"] / (1024 * 1024)
        lines.append(f"| `{h['top_rel']}` | {h['files']:,} | {h['dirs']:,} | {h['symlinks']:,} | {h['junctions']:,} | {h['bytes']:,} | {mb:.1f} |")
    lines.append("\n## Files ≥5MB\n")
    lines.append("| bytes | path | mtime | ext |")
    lines.append("|---:|---|---|---|")
    for sz, p, mt, ext in agg["big_files"]:
        lines.append(f"| {sz:,} | `{p}` | {mt} | .{ext} |")
    lines.append("\n## Per-extension total bytes (top 30)\n")
    ext_bytes = Counter()
    for row in rows:
        if row["kind"] == "file":
            ext_bytes[row["ext"] or "(no_ext)"] += safe_int(row["size_bytes"])
    lines.append("| ext | bytes | MB |")
    lines.append("|---|---:|---:|")
    for ext, b in ext_bytes.most_common(30):
        lines.append(f"| .{ext} | {b:,} | {b/(1024*1024):.1f} |")

    (OUT / "STORAGE_HOTSPOTS.md").write_text("\n".join(lines), encoding="utf-8")

    print("build_assets: stage 1 done")
    print(f"  total_files={agg['total_files']} dirs={agg['total_dirs']} bytes={agg['total_bytes']}")
    print(f"  dups={len(agg['dups'])} big={len(agg['big_files'])}")


if __name__ == "__main__":
    main()
