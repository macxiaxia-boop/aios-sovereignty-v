"""quarantine.py — Quarantine manifest + DO_NOT_INDEX marker builder.

This module is responsible for:
  - building a JSON manifest of every file/directory quarantined
    by the Phase-2 construction contract,
  - writing a `DO_NOT_INDEX.txt` marker in the quarantine root so
    scanners / indexers skip the tree,
  - computing SHA-256 of every file before move,
  - recording the source path, quarantine path, reason, and restore
    instructions for every entry.

The quarantine itself is performed by `apply_quarantine()` which
calls into the host's `shutil.move` (or `Path.rename`) — NEVER
`os.remove`.  Reversibility is mandatory.

Every entry in `quarantine_paths` from the Strategy Policy must be
present in the manifest or the function returns ok=False.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------- Constants
DEFAULT_QUARANTINE_ROOT = r"D:\AIOS\_quarantine\retired-assets\20261008"
DO_NOT_INDEX_FILENAME = "DO_NOT_INDEX.txt"
MANIFEST_FILENAME = "quarantine_manifest.json"


# ---------------------------------------------------------------- Models
@dataclass
class QuarantineEntry:
    source_path: str
    quarantine_path: str
    sha256: str | None
    size_bytes: int
    is_directory: bool
    reason: str
    policy_id: str
    policy_version: str
    retired_id: str | None = None  # one of R-001..R-020 if applicable
    quarantined_at: float = field(default_factory=lambda: time.time())
    restore_instructions: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------- SHA
def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def _sha256_dir(path: Path) -> dict[str, str]:
    """SHA-256 every regular file in `path` (recursive)."""
    out: dict[str, str] = {}
    for p in path.rglob("*"):
        if p.is_file():
            try:
                out[str(p.relative_to(path))] = _sha256_file(p)
            except Exception:
                continue
    return out


# ---------------------------------------------------------------- Manifest
def write_do_not_index_marker(quarantine_root: Path | str) -> Path:
    """Write DO_NOT_INDEX.txt + return path."""
    root = Path(quarantine_root)
    root.mkdir(parents=True, exist_ok=True)
    marker = root / DO_NOT_INDEX_FILENAME
    marker.write_text(
        "DO_NOT_INDEX — Quarantined retired-strategy assets\n"
        "=================================================\n"
        "These assets were moved here on 2026-10-09 by the Phase-2\n"
        "Global Strategy Retirement construction contract.\n"
        "\n"
        "Rules:\n"
        "  - DO NOT load, scan, or index any file under this directory\n"
        "    into an active planning loop, runtime loader, scheduled\n"
        "    task, registry, RAG source, or model prompt context.\n"
        "  - This directory is classified ARCHIVED_REFERENCE by the\n"
        "    strategy contamination scanner.\n"
        "  - Restoration requires user authorization per AGENTS.md\n"
        "    `requires_authorization` and must reference a manifest\n"
        "    entry in quarantine_manifest.json.\n"
        "\n"
        "Manifest path: {manifest}\n"
        "Policy: GLOBAL_PRODUCT_STRATEGY 2026-10-08\n"
        "Audit: GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008.md\n".format(
            manifest=root / MANIFEST_FILENAME,
        ),
        encoding="utf-8",
    )
    return marker


# ---------------------------------------------------------------- Apply
def apply_quarantine(
    *,
    policy: dict,
    quarantine_root: Path | str = DEFAULT_QUARANTINE_ROOT,
    actor: str = "Claude Code 2.1.285 (MiniMax-M3)",
    move: bool = True,
    extra_retired_reasons: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Move every entry listed in `policy["quarantine_paths"]` into
    `quarantine_root`.  Returns a summary dict (also written to disk
    as `<quarantine_root>/quarantine_manifest.json`).

    If `move=False`, no filesystem changes are made — only the manifest
    is computed and written.  This is for tests.

    `extra_retired_reasons` allows callers to map a source path → reason
    string; if not provided, a generic reason is used.
    """
    root = Path(quarantine_root)
    root.mkdir(parents=True, exist_ok=True)
    write_do_not_index_marker(root)

    entries: list[QuarantineEntry] = []
    seen: set[str] = set()
    missing: list[str] = []

    extra_retired_reasons = extra_retired_reasons or {}

    # Build a path → retired_id hint from the audit IDs that mention
    # these paths.  Conservative — only set when path appears in audit.
    # We don't read the audit contents here; use the policy's
    # quarantine_paths list as authoritative.

    for src in policy.get("quarantine_paths", []) or []:
        src_path = Path(src)
        # De-duplicate paths (the policy may list both with / and \\)
        src_str = str(src_path).lower()
        if src_str in seen:
            continue
        seen.add(src_str)

        if not src_path.exists():
            missing.append(str(src))
            continue

        # Decide a flat-ish quarantine path: relative to the original
        # root (so multiple files with same basename don't collide).
        # For WorkBuddy, the parent dirs are stable (memory/, storage/.../,
        # plugins/.../connectors/, sessions/).
        try:
            rel = src_path.name
            # Preserve the top-level "category" so audit traceability works
            parts = src_path.parts
            if len(parts) >= 2:
                # Use last 2 path segments to disambiguate
                rel = Path(*parts[-2:])
            dest = root / rel
        except Exception:
            dest = root / src_path.name

        # If dest exists already (re-run), pick a sibling
        if dest.exists():
            i = 2
            while True:
                cand = dest.with_name(f"{dest.name}.__dup{i}")
                if not cand.exists():
                    dest = cand
                    break
                i += 1

        # Compute hash + reason before move
        is_dir = src_path.is_dir()
        sha = None
        size = 0
        try:
            if is_dir:
                hashes = _sha256_dir(src_path)
                sha = hashlib.sha256(
                    json.dumps(hashes, sort_keys=True).encode("utf-8")
                ).hexdigest().upper()
                # compute size of all files
                size = sum(p.stat().st_size for p in src_path.rglob("*") if p.is_file())
            else:
                sha = _sha256_file(src_path)
                size = src_path.stat().st_size
        except Exception as exc:
            # record but proceed
            size = -1
            sha = f"error:{exc}"

        reason = extra_retired_reasons.get(
            str(src_path),
            "WorkBuddy persistent user profile asset containing retired "
            "vertical / industry / CloudTech Phase 1 (医美+装企) material; "
            "see audit B-01..B-04 / B-06 in GLOBAL_STRATEGY_RETIREMENT_AUDIT_20261008.json.",
        )

        # Move (or simulate)
        if move:
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(src_path), str(dest))
            except Exception as exc:
                missing.append(f"{src} (move failed: {exc})")
                continue

        entry = QuarantineEntry(
            source_path=str(src_path),
            quarantine_path=str(dest),
            sha256=sha,
            size_bytes=size,
            is_directory=is_dir,
            reason=reason,
            policy_id=policy.get("policy_id", "GLOBAL_PRODUCT_STRATEGY"),
            policy_version=policy.get("policy_version", "2026-10-08"),
            quarantined_at=time.time(),
            restore_instructions=(
                "To restore: use shutil.move from the quarantine_path back to "
                "the source_path. Requires user authorization per AGENTS.md "
                "`requires_authorization`. Verify hash matches the sha256 "
                "recorded above before reusing the asset."
            ),
        )
        entries.append(entry)

    manifest = {
        "policy_id": policy.get("policy_id", "GLOBAL_PRODUCT_STRATEGY"),
        "policy_version": policy.get("policy_version", "2026-10-08"),
        "quarantine_root": str(root),
        "quarantined_at": time.time(),
        "actor": actor,
        "marker_file": str(root / DO_NOT_INDEX_FILENAME),
        "entries": [e.to_dict() for e in entries],
        "missing": missing,
        "ok": len(missing) == 0,
        "note": (
            "Manifest is the authoritative record of reversible moves. "
            "No file was deleted. Restoration: see entries[].restore_instructions."
        ),
    }
    (root / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return manifest


# ---------------------------------------------------------------- Allowlist / Scanner hook
def is_quarantine_root(path: Path | str, quarantine_root: Path | str) -> bool:
    p = Path(path).resolve()
    q = Path(quarantine_root).resolve()
    try:
        p.relative_to(q)
        return True
    except ValueError:
        return False


__all__ = [
    "DEFAULT_QUARANTINE_ROOT",
    "DO_NOT_INDEX_FILENAME",
    "MANIFEST_FILENAME",
    "QuarantineEntry",
    "write_do_not_index_marker",
    "apply_quarantine",
    "is_quarantine_root",
]