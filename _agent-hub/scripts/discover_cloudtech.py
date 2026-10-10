#!/usr/bin/env python3
# discover_cloudtech.py - EXT-E (R1346) 2026-10-10 recovery
# Dynamic discovery of CloudTech installation paths.
# Reads common prefixes (D:/C:/ + CloudTech-Portable / CloudTech / cloudtech-saas)
# and emits structured JSON to stdout for EX-rule integration.
from __future__ import annotations
import json, os
from pathlib import Path

CANDIDATE_ROOTS = [
    ("D:", "CloudTech-Portable"),
    ("D:", "CloudTech"),
    ("D:", "cloudtech"),
    ("D:", "CloudTech-Pro"),
    ("C:", "CloudTech-Portable"),
    ("C:", "CloudTech"),
    ("C:", "cloudtech"),
]
AIOS_CLOUDTECH_PARENTS = ["D:/AIOS", "D:/AIOS/kernel"]


def discover_paths():
    import time
    found = []
    timestamp = int(time.time())
    for drive, name in CANDIDATE_ROOTS:
        root = Path(f"{drive}/{name}")
        if root.is_dir():
            found.append({"prefix": str(root).replace("\\", "/"), "kind": "install_root", "source": "candidate_root"})
    for parent in AIOS_CLOUDTECH_PARENTS:
        p = Path(parent)
        if not p.is_dir():
            continue
        for entry in sorted(p.iterdir()):
            if entry.is_dir() and "cloudtech" in entry.name.lower():
                found.append({"prefix": str(entry).replace("\\", "/"), "kind": "internal_sibling", "source": "aios_child_scan"})
    uniq = {}
    for f in found:
        uniq.setdefault(f["prefix"], f)
    return {"generated_at": timestamp, "schema": "r1346-cloudtech-prefix-list-v1", "count": len(uniq), "prefixes": list(uniq.values())}


if __name__ == "__main__":
    print(json.dumps(discover_paths(), indent=2, ensure_ascii=False))
