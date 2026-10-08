#!/usr/bin/env python3
# Temporary helper to compute sha256 for ≤20MB protocol entries.
# Used by build_registry.py — does not modify anything.

import hashlib
import json
from pathlib import Path

ROOT = Path("D:/AIOS").resolve()

def sha256_file(p, cap=20*1024*1024):
    h = hashlib.sha256()
    total = 0
    with open(p, 'rb') as f:
        while True:
            buf = f.read(65536)
            if not buf:
                break
            h.update(buf)
            total += len(buf)
            if total >= cap:
                break
    return h.hexdigest()


def main():
    reg = json.load(open("_agent-hub/v2/governance/PROTOCOL_REGISTRY.json", encoding="utf-8"))
    print("Existing entries:", len(reg["entries"]))
    for e in reg["entries"]:
        p = e.get("path")
        if not p:
            e["hash"] = None
            continue
        ap = ROOT / p.replace("/", os_sep())
        if not ap.exists() or not ap.is_file():
            e["hash"] = None
            e.setdefault("evidence", []).append("path missing at audit")
            continue
        sz = ap.stat().st_size
        if sz > 20 * 1024 * 1024:
            e["hash"] = None
            e.setdefault("evidence", []).append(
                "size > 20MB cap; hash not computed"
            )
            continue
        e["hash"] = sha256_file(ap)
        e["hash_size_bytes"] = sz
        print("  " + e["id"].ljust(40) + " " + str(sz).rjust(10) + " " + e["hash"][:12] + "…")


def os_sep():
    import os
    return os.sep


if __name__ == "__main__":
    main()
