#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""sync_codex_hook_hash.py — R-Codex-Cure-2026-09-29 自动化工具.

功能:
  1. 读取 ~/.codex/hooks.json
  2. 计算每个 hook 块的 canonical JSON SHA256
  3. 与 config.toml 中 [hooks.state] 段对比
  4. 如不一致, 自动更新 config.toml 并备份原文件

用法:
  python sync_codex_hook_hash.py --check     # 只检，不改
  python sync_codex_hook_hash.py --sync      # 自动同步
  python sync_codex_hook_hash.py --watch     # 文件监控模式 (需 watchdog)
"""
import sys
import os
import re
import json
import hashlib
import shutil
import time
import argparse
from pathlib import Path

HOOKS_JSON = Path(os.path.expanduser(r"~/.codex/hooks.json"))
CONFIG_TOML = Path(os.path.expanduser(r"~/.codex/config.toml"))
EVENT_MAP = {
    "PreToolUse": "pre_tool_use",
    "PostToolUse": "post_tool_use",
    "UserPromptSubmit": "user_prompt_submit",
    "SubagentStop": "subagent_stop",
    "Stop": "stop",
}


def canon(obj) -> str:
    """Canonical JSON for stable hashing (Codex 内部约定)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hashes(hooks_path: Path) -> list:
    """Return [(event_short, m, h, sha256), ...] in canonical order."""
    if not hooks_path.exists():
        raise FileNotFoundError(f"hooks.json not found: {hooks_path}")
    with hooks_path.open("r", encoding="utf-8") as f:
        h = json.load(f)
    rows = []
    for k, short in EVENT_MAP.items():
        arr = h.get("hooks", {}).get(k, [])
        for mi, matcher in enumerate(arr):
            for hi, hook in enumerate(matcher.get("hooks", [])):
                blob = canon(hook)
                sha = hashlib.sha256(blob.encode("utf-8")).hexdigest()
                rows.append((short, mi, hi, sha))
    return rows


def parse_existing_hashes(config_path: Path) -> dict:
    """Parse [hooks.state.<path>:<event>:m:h] = trusted_hash lines from config.toml.
    Note: path can contain backslashes but not single quotes. The path is followed
    by literal `:event:m:h'` suffix."""
    if not config_path.exists():
        return {}
    text = config_path.read_text(encoding="utf-8")
    # 贪婪匹配 path, 然后解析 :event:m:h 后缀 (因为路径可含反斜杠但不含单引号)
    pattern = re.compile(
        r"\[hooks\.state\.'([^']+)'\]\s*\n\s*trusted_hash\s*=\s*\"(sha256:[0-9a-f]+)\""
    )
    out = {}
    for m in pattern.finditer(text):
        full_key = m.group(1)   # e.g. C:\Users\xinzh\.codex\hooks.json:pre_tool_use:0:0
        sha = m.group(2)
        # 拆分最后三段: event:m:h
        parts = full_key.rsplit(":", 2)
        if len(parts) != 3:
            continue
        event_part = parts[0].rsplit(":", 1)[-1]   # 取倒数第 3 个冒号后的 event 名
        try:
            mi = int(parts[1])
            hi = int(parts[2])
        except ValueError:
            continue
        out[(event_part, mi, hi)] = sha
    return out


def replace_hash_in_toml(config_path: Path, event: str, m: int, h: int, new_sha: str) -> bool:
    """Replace the trusted_hash for the given (event,m,h) key in config.toml.
    Returns True if replaced, False if key not found."""
    text = config_path.read_text(encoding="utf-8")
    pattern = re.compile(
        r"(\[hooks\.state\.'[^']+':" + re.escape(event) + r":" + str(m) + r":" + str(h) + r"'\])\s*\n\s*trusted_hash\s*=\s*\"sha256:[0-9a-f]+\""
    )
    new_text, n = pattern.subn(
        lambda mm: f"{mm.group(1)}\ntrusted_hash = \"{new_sha}\"",
        text,
    )
    if n == 0:
        return False
    config_path.write_text(new_text, encoding="utf-8")
    return True


def backup_config(config_path: Path) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    bak = config_path.with_suffix(f".toml.bak-R-Codex-Cure-{ts}")
    shutil.copy2(config_path, bak)
    return bak


def main() -> int:
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--sync", action="store_true")
    ap.add_argument("--watch", action="store_true")
    args = ap.parse_args()

    if not args.check and not args.sync and not args.watch:
        args.check = True  # 默认 --check

    print(f"[sync_codex_hook_hash] hooks.json: {HOOKS_JSON}")
    print(f"[sync_codex_hook_hash] config.toml: {CONFIG_TOML}")

    if args.watch:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            print("ERROR: --watch 需要 watchdog 库 (pip install watchdog)")
            return 2

        class Handler(FileSystemEventHandler):
            def on_modified(self, event):
                if event.src_path.endswith("hooks.json"):
                    print(f"[watch] hooks.json modified -> auto sync")
                    run_sync()

        obs = Observer()
        obs.schedule(Handler(), str(HOOKS_JSON.parent), recursive=False)
        obs.start()
        print("[watch] 监控中, Ctrl+C 停止")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            obs.stop()
        obs.join()
        return 0

    try:
        computed = compute_hashes(HOOKS_JSON)
    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        return 2

    existing = parse_existing_hashes(CONFIG_TOML)

    mismatches = []
    for ev, m, h, sha in computed:
        key = (ev, m, h)
        cur = existing.get(key)
        if cur != f"sha256:{sha}":
            mismatches.append((ev, m, h, sha, cur))

    if not mismatches:
        print(f"✓ hooks hash 全部一致 ({len(computed)}/{len(computed)})")
        return 0

    print(f"✗ hooks hash 不一致 ({len(mismatches)}/{len(computed)})")
    for ev, m, h, sha, cur in mismatches:
        print(f"  {ev}:{m}:{h} -> {sha} (was: {cur or 'MISSING'})")

    if args.check:
        return 1

    if args.sync:
        bak = backup_config(CONFIG_TOML)
        print(f"已备份: {bak}")
        ok_count = 0
        for ev, m, h, sha, cur in mismatches:
            sha_full = f"sha256:{sha}"
            if replace_hash_in_toml(CONFIG_TOML, ev, m, h, sha_full):
                ok_count += 1
                print(f"  ✓ updated {ev}:{m}:{h} -> {sha_full}")
            else:
                print(f"  ✗ key 未找到: {ev}:{m}:{h}")
        print(f"已同步 {ok_count}/{len(mismatches)} 个 hash")
        return 0 if ok_count == len(mismatches) else 1

    return 0


def run_sync():
    computed = compute_hashes(HOOKS_JSON)
    existing = parse_existing_hashes(CONFIG_TOML)
    for ev, m, h, sha in computed:
        if existing.get((ev, m, h)) != f"sha256:{sha}":
            replace_hash_in_toml(CONFIG_TOML, ev, m, h, f"sha256:{sha}")
    print(f"[sync] 完成 ({len(computed)} hooks)")


if __name__ == "__main__":
    sys.exit(main())