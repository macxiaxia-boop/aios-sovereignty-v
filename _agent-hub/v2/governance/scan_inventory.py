#!/usr/bin/env python3
# scan_inventory.py — streaming read-only file metadata scanner.
# Writes CSV row-by-row + per-toplevel checkpoint JSON.
# NEVER deletes / moves / renames. NEVER follows reparse points.
#
# Usage:
#   python scan_inventory.py [--root D:/AIOS] [--out D:/AIOS/_agent-hub/v2/reports/system-audit-20260929]
#
# Output:
#   <out>/FILE_INVENTORY.csv
#   <out>/SCAN_CHECKPOINT.json
#   <out>/SCAN_ERRORS.txt
#
# Default-deny destructive ops: this file does not import shutil.os.remove,
# does not call os.rename/os.replace on user files, does not run any subprocess
# that could mutate the FS.

import argparse
import csv
import hashlib
import json
import os
import stat
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

CSV_HEADER = [
    "scan_id",            # 32-hex sha256 over (root, rel_path, mtime_ns, size)
    "root",               # e.g. D:/AIOS
    "rel_path",           # POSIX relative path from root
    "abs_path",           # absolute path as given by Path
    "parent_rel",         # POSIX rel path of parent dir
    "top_rel",            # first component under root (top-level dir/file)
    "name",               # basename
    "kind",               # file | dir | symlink | junction | other
    "size_bytes",         # int; 0 for non-files
    "mtime_iso",          # UTC ISO-8601
    "mtime_ns",           # int
    "ext",                # lowercase or "" for none
    "is_hidden",          # bool
    "is_reparse",         # bool — Windows reparse point (symlink/junction)
    "link_target",        # string target if reparse; else ""
    "hashed",             # bool — content hashed this run
    "sha256",             # 64-hex if hashed; else ""
    "hash_size_bytes",    # int bytes actually hashed (may be partial)
    "scanned_at_iso",     # timestamp of scan record
]

HASHABLE_EXT = {".md", ".markdown", ".json", ".yaml", ".yml", ".toml", ".txt",
                ".py", ".ps1", ".cmd", ".bat", ".sh", ".rs", ".ts", ".tsx",
                ".js", ".cjs", ".mjs", ".html", ".css", ".ini", ".conf",
                ".xml", ".reg", ".csv", ".tsv", ".rst", ".adoc"}

# Dirs that contain huge/cached/binary content; we still count & size them
# but we do NOT recurse into them or hash anything inside.
SKIP_RECURSE_NAMES = {
    ".git", "node_modules", ".venv", "venv", "env", "__pycache__",
    ".cache", "cache", "dist", "build", "target", ".next", ".nuxt",
    ".parcel-cache", ".turbo", ".gradle", "vendor", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox", "node_modules",
}

# A partial scan threshold: if a single dir scan takes > N seconds, mark partial.
PARTIAL_DIR_SECONDS = 120.0


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_windows_reparse(st_mode: int) -> bool:
    """Return True if a Windows reparse-point bit is set in st_mode."""
    try:
        return bool(stat.S_ISLNK(st_mode)) or (os.name == "nt" and (
            st_mode & 0xA000 == 0xA000  # S_IFLNK / reparse bit
        ))
    except Exception:
        return False


def kind_of(p: Path) -> tuple[str, bool, str]:
    """Return (kind, is_reparse, link_target)."""
    try:
        st = os.lstat(p)
    except OSError as e:
        return ("other", False, f"lstat-failed:{e.errno or '?'}")

    mode = st.st_mode
    if stat.S_ISLNK(mode):
        # symlink / junction
        target = ""
        try:
            target = os.readlink(p)
        except OSError as e:
            target = f"readlink-failed:{e.errno or '?'}"
        return ("symlink", True, target)

    if os.name == "nt":
        # detect junction / reparse via attributes
        try:
            attrs = os.stat(p).st_file_attributes  # type: ignore[attr-defined]
            if attrs & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
                target = ""
                try:
                    target = os.readlink(p)
                except OSError:
                    pass
                return ("junction", True, target)
        except (AttributeError, OSError):
            pass

    if stat.S_ISDIR(mode):
        return ("dir", False, "")
    if stat.S_ISREG(mode):
        return ("file", False, "")
    return ("other", False, "")


def safe_metadata(p: Path) -> dict:
    """Return stat-derived metadata; never raises."""
    out = {
        "size_bytes": 0,
        "mtime_ns": 0,
        "mtime_iso": "",
        "ext": "",
        "is_hidden": False,
        "link_target": "",
        "is_reparse": False,
        "kind": "other",
    }
    try:
        st = os.lstat(p)
        out["size_bytes"] = int(st.st_size)
        out["mtime_ns"] = int(st.st_mtime_ns) if hasattr(st, "st_mtime_ns") else int(st.st_mtime * 1e9)
        out["mtime_iso"] = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        pass

    kind, is_reparse, link_target = kind_of(p)
    out["kind"] = kind
    out["is_reparse"] = is_reparse
    out["link_target"] = link_target

    name = p.name
    out["is_hidden"] = name.startswith(".")

    if "." in name:
        out["ext"] = name.rsplit(".", 1)[-1].lower()
    else:
        out["ext"] = ""

    return out


def should_hash(meta: dict) -> bool:
    if meta["kind"] != "file":
        return False
    if meta["is_reparse"]:
        return False
    if meta["size_bytes"] <= 0:
        return False
    if meta["size_bytes"] > 20 * 1024 * 1024:
        # 20MB ceiling for hash work; we still record size+mtime
        return False
    ext = "." + meta["ext"] if meta["ext"] else ""
    return ext in HASHABLE_EXT


def stream_sha256(path: Path, *, chunk: int = 65536) -> tuple[str, int]:
    """Return (sha256_hex, bytes_hashed). Up to 20MB is read."""
    h = hashlib.sha256()
    total = 0
    with open(path, "rb") as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
            total += len(buf)
            if total >= 20 * 1024 * 1024:
                break
    return h.hexdigest(), total


# --------------------------------------------------------------------------- #
# Scanner
# --------------------------------------------------------------------------- #

class Scanner:
    def __init__(self, root: Path, out_dir: Path):
        self.root = root.resolve()
        self.out_dir = out_dir.resolve()
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.csv_path = out_dir / "FILE_INVENTORY.csv"
        self.ckpt_path = out_dir / "SCAN_CHECKPOINT.json"
        self.err_path = out_dir / "SCAN_ERRORS.txt"
        # Roots whose contents we DO NOT scan because we are writing our own
        # outputs there. Recorded in checkpoint as self_excluded_roots so the
        # report can prove the omission. Computed below.
        self._self_excluded_roots = []
        self._csv_fh = None
        self._csv_w = None
        self._counter = 0
        self._top_dirs = []  # list of dict, one per top-level entry completed
        self._current_top = None  # dict
        self._top_started_at = None

    # ---- I/O ---- #
    def open(self):
        # append mode if previous run left a partial file
        new_file = not self.csv_path.exists() or self.csv_path.stat().st_size == 0
        self._csv_fh = open(self.csv_path, "a", encoding="utf-8", newline="")
        self._csv_w = csv.writer(self._csv_fh)
        if new_file:
            self._csv_w.writerow(CSV_HEADER)
            self._csv_fh.flush()

    def compute_self_excluded_roots(self):
        """Identify subtrees under self.root whose contents are THIS scanner's
        own outputs (governance tools + this audit's report dir). They must NOT
        be scanned because their bytes would otherwise inflate total_bytes and
        create a self-reference loop. R011-R281.2: only TWO precise paths —
        do NOT exclude the entire _agent-hub/v2/reports subtree, because that
        subtree contains the formal reports (IMPLEMENTATION_REPORT.md,
        health.json, test_run.json, status.json, test-output.txt) which MUST
        appear in inventory."""
        candidates = []
        # 1) D:\AIOS\_agent-hub\v2\governance  (治理工具/R281治理资产)
        gov = (self.root / "_agent-hub" / "v2" / "governance").resolve()
        if gov.exists():
            candidates.append(gov)
        # 2) D:\AIOS\_agent-hub\v2\reports\system-audit-20260929  (本轮自增长输出)
        # The out_dir passed to Scanner is the current audit report dir. We
        # exclude ONLY this specific report dir, not the entire reports subtree.
        if self.out_dir is not None:
            try:
                rpt = self.out_dir.resolve()
                candidates.append(rpt)
            except OSError:
                pass
        # Deduplicate (report dir may equal gov in degenerate cases; be safe)
        seen = set()
        result = []
        for c in candidates:
            key = str(c).lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(c)
        self._self_excluded_roots = result
        return result

    def is_self_excluded(self, abs_path: Path) -> bool:
        """True if abs_path is inside any of self_excluded_roots."""
        try:
            ap = abs_path.resolve()
        except OSError:
            return False
        for root in self._self_excluded_roots:
            try:
                ap.relative_to(root)
                return True
            except ValueError:
                continue
        return False

    def close(self):
        if self._csv_fh:
            self._csv_fh.flush()
            self._csv_fh.close()
        self.write_checkpoint()

    def write_checkpoint(self):
        payload = {
            "schema": 1,
            "root": str(self.root),
            "out_dir": str(self.out_dir),
            "csv_path": str(self.csv_path),
            "updated_at": now_iso(),
            "rows_written": self._counter,
            "self_excluded_roots": [str(p) for p in self._self_excluded_roots],
            "top_dirs": self._top_dirs,
        }
        tmp = self.ckpt_path.with_suffix(".json.tmp")
        data = json.dumps(payload, ensure_ascii=False, indent=2)
        for attempt in range(5):
            try:
                with open(tmp, "w", encoding="utf-8") as f:
                    f.write(data)
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except OSError:
                        pass
                # retry-friendly replace
                try:
                    os.replace(tmp, self.ckpt_path)
                except PermissionError:
                    # target locked — try delete-then-rename
                    try:
                        os.remove(self.ckpt_path)
                    except OSError:
                        pass
                    os.replace(tmp, self.ckpt_path)
                return
            except PermissionError as e:
                time.sleep(0.2 * (attempt + 1))
                continue
            except OSError as e:
                self.log_error(f"checkpoint write OSError: {e}")
                return
        self.log_error("checkpoint write failed after 5 attempts")

    def log_error(self, msg: str):
        try:
            with open(self.err_path, "a", encoding="utf-8") as f:
                f.write(f"[{now_iso()}] {msg}\n")
        except Exception:
            pass

    def flush(self):
        if self._csv_fh:
            self._csv_fh.flush()

    # ---- Per-top-dir accumulator ---- #
    def begin_top(self, top_rel: str, abs_path: Path):
        self._current_top = {
            "rel": top_rel,
            "abs": str(abs_path),
            "started_at": now_iso(),
            "ended_at": None,
            "duration_s": None,
            "status": "in_progress",
            "file_count": 0,
            "dir_count": 0,
            "symlink_count": 0,
            "junction_count": 0,
            "reparse_count": 0,
            "hidden_count": 0,
            "total_bytes": 0,
            "hashed_count": 0,
            "skipped_subdirs": [],
            "errors": [],
            "ext_breakdown": {},
            "size_buckets": {  # bytes
                "<1KB": 0, "1KB-100KB": 0, "100KB-1MB": 0,
                "1MB-10MB": 0, "10MB-100MB": 0, ">100MB": 0,
            },
        }
        self._top_started_at = time.time()
        self.write_checkpoint()

    def end_top(self, status: str = "complete"):
        if not self._current_top:
            return
        t = self._current_top
        t["ended_at"] = now_iso()
        if self._top_started_at:
            t["duration_s"] = round(time.time() - self._top_started_at, 3)
        if status == "partial":
            t["status"] = "partial"
        elif status == "skipped":
            t["status"] = "skipped"
        else:
            t["status"] = "complete"
        self._top_dirs.append(t)
        self._current_top = None
        self.write_checkpoint()
        self.flush()

    def record_row_meta(self, meta: dict, top_rel: str):
        if not self._current_top:
            return
        t = self._current_top
        if meta["kind"] == "file":
            t["file_count"] += 1
            t["total_bytes"] += meta["size_bytes"]
            ext = meta["ext"] or "(no_ext)"
            t["ext_breakdown"][ext] = t["ext_breakdown"].get(ext, 0) + 1
            sb = meta["size_bytes"]
            if sb < 1024:
                t["size_buckets"]["<1KB"] += 1
            elif sb < 100 * 1024:
                t["size_buckets"]["1KB-100KB"] += 1
            elif sb < 1024 * 1024:
                t["size_buckets"]["100KB-1MB"] += 1
            elif sb < 10 * 1024 * 1024:
                t["size_buckets"]["1MB-10MB"] += 1
            elif sb < 100 * 1024 * 1024:
                t["size_buckets"]["10MB-100MB"] += 1
            else:
                t["size_buckets"][">100MB"] += 1
        elif meta["kind"] == "dir":
            t["dir_count"] += 1
        elif meta["kind"] == "symlink":
            t["symlink_count"] += 1
            t["reparse_count"] += 1
        elif meta["kind"] == "junction":
            t["junction_count"] += 1
            t["reparse_count"] += 1
        if meta["is_hidden"]:
            t["hidden_count"] += 1

    # ---- Row writer ---- #
    def write_row(self, abs_path: Path, top_rel: str, meta: dict, hashed: bool,
                  sha256_hex: str, hash_size: int):
        try:
            rel = abs_path.relative_to(self.root).as_posix()
        except ValueError:
            rel = abs_path.as_posix()
        parent_rel = str(Path(rel).parent.as_posix()) if rel else ""
        name = abs_path.name
        # scan_id: deterministic over (root, rel, mtime_ns, size) — does NOT include content hash
        scan_id_src = f"{self.root}|{rel}|{meta['mtime_ns']}|{meta['size_bytes']}"
        scan_id = hashlib.sha256(scan_id_src.encode("utf-8")).hexdigest()
        row = [
            scan_id,
            str(self.root).replace("\\", "/"),
            rel,
            str(abs_path),
            parent_rel,
            top_rel,
            name,
            meta["kind"],
            meta["size_bytes"],
            meta["mtime_iso"],
            meta["mtime_ns"],
            meta["ext"],
            "1" if meta["is_hidden"] else "0",
            "1" if meta["is_reparse"] else "0",
            meta["link_target"],
            "1" if hashed else "0",
            sha256_hex,
            hash_size,
            now_iso(),
        ]
        self._csv_w.writerow(row)
        self._counter += 1
        self.record_row_meta(meta, top_rel)
        if self._counter % 10000 == 0:
            self.flush()

    # ---- Walk one top-level entry ---- #
    def scan_top(self, top_abs: Path):
        top_rel = top_abs.relative_to(self.root).as_posix()
        # Skip if this top-level entry is inside any self_excluded_roots.
        if self.is_self_excluded(top_abs):
            self.begin_top(top_rel, top_abs)
            if self._current_top is not None:
                self._current_top["status"] = "self_excluded"
                self._current_top["skipped_subdirs"] = [str(top_abs)]
                self._current_top["errors"] = [
                    "skipped: scanner self-excluded root (this scanner writes here)"
                ]
            self.end_top("self_excluded")
            return
        self.begin_top(top_rel, top_abs)
        try:
            # Try as a directory first
            try:
                st = os.lstat(top_abs)
            except OSError as e:
                self._current_top["errors"].append(f"lstat-failed:{e.errno or e}")
                self.end_top("partial")
                return

            if stat.S_ISLNK(st.st_mode):
                # top-level is itself a symlink
                meta = safe_metadata(top_abs)
                self.write_row(top_abs, top_rel, meta, False, "", 0)
                self.end_top("complete")
                return

            if not stat.S_ISDIR(st.st_mode):
                # top-level file
                meta = safe_metadata(top_abs)
                hashed = False
                sha = ""
                hs = 0
                if should_hash(meta):
                    try:
                        sha, hs = stream_sha256(top_abs)
                        hashed = True
                    except OSError as e:
                        self._current_top["errors"].append(f"hash:{top_abs}:{e}")
                self.write_row(top_abs, top_rel, meta, hashed, sha, hs)
                self.end_top("complete")
                return

            # It's a directory — walk it
            self._walk_dir(top_abs, top_rel)
            # Final partial check
            if self._current_top["duration_s"] is None and self._top_started_at is not None:
                dur = time.time() - self._top_started_at
                if dur > PARTIAL_DIR_SECONDS:
                    self._current_top["status"] = "partial"
                    self._current_top["errors"].append(f"exceeded {PARTIAL_DIR_SECONDS}s threshold")
            self.end_top(self._current_top["status"])
        except Exception as e:
            self.log_error(f"scan_top({top_abs}): {e}\n{traceback.format_exc()}")
            if self._current_top:
                self._current_top["errors"].append(str(e))
                self.end_top("partial")

    def _walk_dir(self, dir_abs: Path, top_rel: str):
        """Bounded walk of a directory. Marks partial if exceeds threshold."""
        # If this directory itself is inside a self-excluded root, record once
        # and stop descending.
        if self.is_self_excluded(dir_abs):
            meta = safe_metadata(dir_abs)
            self.write_row(dir_abs, top_rel, meta, False, "", 0)
            if self._current_top is not None:
                self._current_top["skipped_subdirs"].append(
                    str(dir_abs.relative_to(self.root).as_posix())
                )
            return
        # record the dir itself
        meta = safe_metadata(dir_abs)
        self.write_row(dir_abs, top_rel, meta, False, "", 0)

        # iterative walk with timeout guard
        stack = [dir_abs]
        while stack:
            if self._top_started_at is not None and (time.time() - self._top_started_at) > PARTIAL_DIR_SECONDS:
                if self._current_top:
                    self._current_top["status"] = "partial"
                    self._current_top["errors"].append(
                        f"partial: exceeded {PARTIAL_DIR_SECONDS}s"
                    )
                # bail out of this dir
                return
            cur = stack.pop()
            try:
                with os.scandir(cur) as it:
                    for entry in it:
                        try:
                            name = entry.name
                            full = Path(entry.path)
                            # Honor self-excluded roots at any depth: record
                            # the dir/file entry once, then skip — do NOT
                            # descend into it and do NOT hash any file inside.
                            if self.is_self_excluded(full):
                                m = safe_metadata(full)
                                self.write_row(full, top_rel, m, False, "", 0)
                                if self._current_top is not None:
                                    self._current_top["skipped_subdirs"].append(
                                        str(full.relative_to(self.root).as_posix())
                                    )
                                continue
                            # skip hidden caches at any depth
                            if name in SKIP_RECURSE_NAMES:
                                # still record the dir entry but don't recurse
                                m = safe_metadata(full)
                                self.write_row(full, top_rel, m, False, "", 0)
                                if self._current_top is not None:
                                    self._current_top["skipped_subdirs"].append(
                                        str(full.relative_to(self.root).as_posix())
                                    )
                                continue

                            # lstat for kind
                            try:
                                lst = entry.stat(follow_symlinks=False)
                            except OSError as e:
                                self._current_top["errors"].append(f"stat:{full}:{e}")
                                continue

                            mode = lst.st_mode
                            # symlink? record only (don't follow)
                            if stat.S_ISLNK(mode):
                                m = safe_metadata(full)
                                self.write_row(full, top_rel, m, False, "", 0)
                                continue

                            # Windows reparse (junction) detection
                            if os.name == "nt":
                                try:
                                    fa = lst.st_file_attributes  # type: ignore[attr-defined]
                                except AttributeError:
                                    fa = 0
                                if fa & 0x400:  # FILE_ATTRIBUTE_REPARSE_POINT
                                    m = safe_metadata(full)
                                    self.write_row(full, top_rel, m, False, "", 0)
                                    continue

                            if stat.S_ISDIR(mode):
                                m = safe_metadata(full)
                                self.write_row(full, top_rel, m, False, "", 0)
                                stack.append(full)
                                continue

                            if stat.S_ISREG(mode):
                                m = safe_metadata(full)
                                hashed = False
                                sha = ""
                                hs = 0
                                if should_hash(m):
                                    try:
                                        sha, hs = stream_sha256(full)
                                        hashed = True
                                    except OSError as e:
                                        if self._current_top is not None:
                                            self._current_top["errors"].append(f"hash:{full}:{e}")
                                self.write_row(full, top_rel, m, hashed, sha, hs)
                                continue

                            # other (fifo, socket, block, char): just record
                            m = safe_metadata(full)
                            self.write_row(full, top_rel, m, False, "", 0)
                        except Exception as e:
                            self.log_error(f"entry:{entry}:{e}")
                            continue
            except OSError as e:
                if self._current_top is not None:
                    self._current_top["errors"].append(f"scandir:{cur}:{e}")
                continue

    # ---- Top-level ---- #
    def run(self):
        self.open()
        try:
            # Compute self-excluded roots BEFORE any enumeration so the first
            # checkpoint write records them.
            excluded = self.compute_self_excluded_roots()
            print(f"[self-exclude] {len(excluded)} roots: "
                  f"{[str(p) for p in excluded]}", file=sys.stderr)

            # Load existing checkpoint for resume
            already_done = set()
            if self.ckpt_path.exists():
                try:
                    with open(self.ckpt_path, "r", encoding="utf-8") as f:
                        prev = json.load(f)
                    already_done = {t["rel"] for t in prev.get("top_dirs", [])}
                    # Restore counter (so total is accurate)
                    self._counter = int(prev.get("rows_written", 0))
                except (OSError, ValueError, KeyError) as e:
                    self.log_error(f"resume-load-failed: {e}")
            if already_done:
                print(f"[resume] skipping {len(already_done)} already-scanned top-levels",
                      file=sys.stderr)

            # enumerate top-level entries
            try:
                with os.scandir(self.root) as it:
                    top_entries = []
                    for entry in it:
                        top_entries.append(Path(entry.path))
            except OSError as e:
                self.log_error(f"scandir root: {e}")
                return

            # stable order
            top_entries.sort(key=lambda p: p.name.lower())
            for p in top_entries:
                top_rel = p.relative_to(self.root).as_posix()
                if top_rel in already_done:
                    continue
                # Top-level symlink/junction: record only, do not walk
                try:
                    st = os.lstat(p)
                except OSError:
                    st = None
                if st is not None and stat.S_ISLNK(st.st_mode):
                    # record and skip
                    self.begin_top(top_rel, p)
                    meta = safe_metadata(p)
                    self.write_row(p, top_rel, meta, False, "", 0)
                    self.end_top("complete")
                    continue
                if st is not None and os.name == "nt":
                    try:
                        fa = st.st_file_attributes  # type: ignore[attr-defined]
                        if fa & 0x400:
                            self.begin_top(top_rel, p)
                            meta = safe_metadata(p)
                            self.write_row(p, top_rel, meta, False, "", 0)
                            self.end_top("complete")
                            continue
                    except AttributeError:
                        pass
                self.scan_top(p)
        finally:
            self.close()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="D:/AIOS")
    ap.add_argument("--out", default="D:/AIOS/_agent-hub/v2/reports/system-audit-20260929")
    args = ap.parse_args()
    root = Path(args.root)
    out = Path(args.out)
    if not root.exists():
        print(f"root does not exist: {root}", file=sys.stderr)
        sys.exit(2)
    sc = Scanner(root, out)
    sc.run()
    print(json.dumps({
        "ok": True,
        "root": str(root),
        "out": str(out),
        "csv": str(sc.csv_path),
        "rows": sc._counter,
        "tops": len(sc._top_dirs),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
