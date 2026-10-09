#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
openclaw_cron_validate.py — OpenClaw cron payload validate() 集成 (Phase I.3 / T24 · 2026-10-09)

SSOT 路径
  - Spec:     D:\AIOS\_agent-hub\policy\adapter-spec.v1.md
  - Policy:   D:\AIOS\_agent-hub\policy\model-policy.v1.yaml
  - Manifest: D:\AIOS\_agent-hub\policy\model-policy.v1.sha256
  - Contract: D:\AIOS\_agent-hub\policy\adapter-contract.md
  - Adapter:  D:\AIOS\_agent-hub\policy\adapters\openclaw_runtime.py

线程 / 授权
  - Thread:    01a11c33-c813-7752-9e53-b7c332d00445 (Phase I.3)
  - Supervisor: 01a11c30-6f6c-76c0-8c60-a55f3a43ff63
  - Authorizer: user-2026-10-08T23:55 (sovereignty-v) + 你就开始 + 继续 (2026-10-09)

红线契约
  - NO_FABRICATE_MODEL_ID        : 仅从 yaml payload 读 model/provider, 不在本文件硬编码 id
  - UNIFIED_INTERFACE_REQUIRED   : 必须调 openclaw_runtime.validate(model, provider, *, request_id)
  - NO_AUTO_FALLBACK_IN_ADAPTER  : 拒绝路径仅记录 + 退出, 不切换 / 不重试 / 不回填默认

工作流
  1. 扫 D:\AIOS\openclaw\cron\*.yaml
  2. 用极简 yaml parser 抽 (model, provider, request_id, name)
  3. 调 openclaw_runtime.validate()
  4. 写入 audit log: D:\AIOS\_agent-hub\audit\cron-validations.log
  5. 退出码: 0=全过; 1=有拒绝; 2=扫不到 yaml
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Tuple

# 路径常量
CRON_DIR    = Path(r"D:\AIOS\openclaw\cron")
ADAPTER_DIR = Path(r"D:\AIOS\_agent-hub\policy\adapters")
AUDIT_LOG   = Path(r"D:\AIOS\_agent-hub\audit\cron-validations.log")

# 8h CST
_TZ_CN = timezone(timedelta(hours=8))


def _now_iso() -> str:
    now = datetime.now(_TZ_CN)
    return now.strftime("%Y-%m-%dT%H:%M:%S") + now.strftime("%z")[:3] + ":" + now.strftime("%z")[3:]


# ─────────────────────────────────────────────────────────────────────────────
# 极简 yaml 解析 (复用 codex_runtime._minimal_yaml_load 风格, 自包含避免跨模块依赖)
# 仅支持 spec 当前结构: top-level scalar + 一个 inline payload 块 (key: value)
# ─────────────────────────────────────────────────────────────────────────────

def _minimal_top_load(text: str) -> dict:
    """只解析顶层 scalar (key: value), 忽略嵌套 block / list / 注释."""
    out: dict = {}
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent != 0:
            continue  # 只取顶层 scalar
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        key = key.strip()
        value = value.strip()
        # 去掉两侧引号
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1]
        out[key] = value
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Audit log
# ─────────────────────────────────────────────────────────────────────────────

def _append_audit(record: dict) -> None:
    """追加 JSONL · 失败只 stderr 不抛 (红线 #22: 不向 redo stack 灌错)."""
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001
        print(f"[openclaw_cron_validate] AUDIT WRITE FAILED: {e}", file=sys.stderr)


# ─────────────────────────────────────────────────────────────────────────────
# Adapter import (deferred, 让 --help 不依赖 adapter)
# ─────────────────────────────────────────────────────────────────────────────

def _import_adapter():
    """动态导入 openclaw_runtime.validate()."""
    sys.path.insert(0, str(ADAPTER_DIR))
    try:
        import openclaw_runtime  # type: ignore
        return openclaw_runtime
    except Exception as e:  # noqa: BLE001
        print(f"[openclaw_cron_validate] ADAPTER IMPORT FAILED: {type(e).__name__}:{e}", file=sys.stderr)
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 核心: 扫 cron 目录 + 逐个 validate
# ─────────────────────────────────────────────────────────────────────────────

def _scan_cron_dir() -> list[Path]:
    if not CRON_DIR.exists():
        return []
    return sorted(CRON_DIR.glob("*.yaml"))


def _extract_payload(yaml_path: Path) -> dict:
    """从 yaml 顶层抽 (model, provider, request_id, name)."""
    try:
        text = yaml_path.read_text(encoding="utf-8")
        top = _minimal_top_load(text)
    except Exception as e:  # noqa: BLE001
        return {"_error": f"yaml_parse_failed:{type(e).__name__}:{e}"}
    return {
        "name":       top.get("name", yaml_path.stem),
        "provider":   top.get("provider", ""),
        "model":      top.get("model", ""),
        "request_id": top.get("request_id", f"cron-{yaml_path.stem}"),
    }


def _validate_one(adapter, yaml_path: Path, *, dry_run: bool) -> Tuple[bool, str, dict]:
    """对一个 cron yaml 跑 validate. 返回 (allowed, reason, payload_dict)."""
    payload = _extract_payload(yaml_path)
    if "_error" in payload:
        return False, payload["_error"], payload
    if not payload.get("model") or not payload.get("provider"):
        return False, "missing_required_fields:model_or_provider", payload

    if dry_run:
        # dry-run 模式: 不真调 validate(), 仅报告将调什么
        return True, "dry_run:skipped", payload

    assert adapter is not None
    try:
        ok, reason = adapter.validate(
            payload["model"],
            payload["provider"],
            request_id=payload["request_id"],
        )
        return ok, reason, payload
    except Exception as e:  # noqa: BLE001
        return False, f"adapter_exc:{type(e).__name__}:{e}", payload


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="OpenClaw cron payload validate() integrator (Phase I.3 / T24)")
    ap.add_argument("--cron-dir", default=str(CRON_DIR), help="cron yaml 目录")
    ap.add_argument("--dry-run", action="store_true", help="dry-run: 不真调 validate, 仅报告")
    ap.add_argument("--verbose", action="store_true", help="verbose: 每条都打")
    ap.add_argument("--strict", action="store_true", help="strict: 任何 DENY 即 exit 1 (默认 exit 1 同语义)")
    args = ap.parse_args(argv)

    cron_dir = Path(args.cron_dir)
    yamls = sorted(cron_dir.glob("*.yaml")) if cron_dir.exists() else []
    if not yamls:
        print(f"[openclaw_cron_validate] NO CRON YAML FOUND in {cron_dir}", file=sys.stderr)
        print(f"[openclaw_cron_validate] tip: 至少放 1 个 *.yaml 到该目录才能验证集成", file=sys.stderr)
        return 2

    adapter = None if args.dry_run else _import_adapter()
    if not args.dry_run and adapter is None:
        print(f"[openclaw_cron_validate] ABORT: cannot import openclaw_runtime", file=sys.stderr)
        return 3

    allowed_count = 0
    denied_count  = 0
    denied_msgs:  list[str] = []

    print(f"[openclaw_cron_validate] mode={'dry-run' if args.dry_run else 'live'} dir={cron_dir} count={len(yamls)}")
    for yp in yamls:
        ok, reason, payload = _validate_one(adapter, yp, dry_run=args.dry_run)
        if args.verbose or not ok:
            status = "ALLOW" if ok else "DENY"
            print(f"  [{status}] {yp.name:42s} name={payload.get('name','?'):24s} "
                  f"model={payload.get('model','?'):16s} provider={payload.get('provider','?'):10s} "
                  f"reason={reason!r}")
        _append_audit({
            "ts":          _now_iso(),
            "cron_yaml":   str(yp),
            "name":        payload.get("name"),
            "provider":    payload.get("provider"),
            "model":       payload.get("model"),
            "request_id":  payload.get("request_id"),
            "dry_run":     args.dry_run,
            "allowed":     ok,
            "reason":      reason,
        })
        if ok:
            allowed_count += 1
        else:
            denied_count += 1
            denied_msgs.append(f"{yp.name}: {reason}")

    print(f"[openclaw_cron_validate] SUMMARY allowed={allowed_count} denied={denied_count} total={len(yamls)}")
    if denied_msgs:
        for m in denied_msgs:
            print(f"  - DENY: {m}")
    return 0 if denied_count == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))