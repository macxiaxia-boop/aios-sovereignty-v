#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
codex_runtime.py — ModelPolicy Adapter for Codex runtime (W8/T9 · 2026-10-09)

SSOT paths:
  - Spec:     D:\AIOS\_agent-hub\policy\adapter-spec.v1.md
  - Policy:   D:\AIOS\_agent-hub\policy\model-policy.v1.yaml
  - Manifest: D:\AIOS\_agent-hub\policy\model-policy.v1.sha256
  - Contract: D:\AIOS\_agent-hub\policy\adapter-contract.md

Authorizer: user-2026-10-08T23:55 (sovereignty-v) + 你就开始 + 继续 (2026-10-09)
Thread:     01a11c33-c813-7752-9e53-b7c332d00445 (Codex engineering · W8)
Supervisor: 01a11c30-6f6c-76c0-8c60-a55f3a43ff63 (Codex supervisor)

红线契约（写进 SSOT · 永久态）:
  - NO_FABRICATE_MODEL_ID        : 所有 model id 仅从 policy yaml 读取；本文件内禁止字面量 id
  - UNIFIED_INTERFACE_REQUIRED   : validate 签名必须为 (model, provider, *, request_id) -> Tuple[bool, str]
  - NO_AUTO_FALLBACK_IN_ADAPTER  : 拒绝路径绝不重试 / 切换 provider / 切换 model
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Tuple

# 路径常量（adapter-spec.v1.md §"读取 Policy"）── 仅路径常量，不含 model id
POLICY_PATH = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml")
SHA_PATH    = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256")
AUDIT_LOG   = Path(r"D:\AIOS\_agent-hub\audit\adapter-validations.log")

# 运行时身份（仅本 runtime 的 host 标识，非 model id）
RUNTIME_HOST = "codex"

# 拒绝原因前缀（与 spec §"validate 校验顺序" 完全对齐）
REASON_PROVIDER_NOT_ALLOWED = "provider_not_allowed"
REASON_PROVIDER_DISABLED    = "provider_disabled"
REASON_MODEL_NOT_ALLOWED    = "model_not_allowed"
REASON_MODEL_DISABLED       = "model_disabled"
REASON_ROUTE_PROHIBITED     = "route_prohibited"
REASON_POLICY_UNAVAILABLE   = "policy_unavailable"

# 8h 时区偏移（中国标准时间 · 与 manifest signed_at 字段保持一致）
_TZ_CN = timezone(timedelta(hours=8))


# ─────────────────────────────────────────────────────────────────────────────
# 内部工具
# ─────────────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    """ISO-8601 with CST offset（spec §"审计日志"示例格式对齐）"""
    return datetime.now(_TZ_CN).strftime("%Y-%m-%dT%H:%M:%S%z")[:-2] + ":" + \
           datetime.now(_TZ_CN).strftime("%z")[-2:]


def _read_manifest_sha256() -> str:
    """从 model-policy.v1.sha256 提取 hash（不依赖 yaml 库即可工作）"""
    text = SHA_PATH.read_text(encoding="utf-8")
    m = re.search(r"sha256:\s*([0-9A-Fa-f]{64})", text)
    if not m:
        raise RuntimeError(f"manifest 格式错误: {SHA_PATH}")
    return m.group(1).upper()


def _load_policy_dict() -> dict:
    """读取 + 验签 + 解析 policy yaml。失败 → 抛 RuntimeError。

    红线 #NO_FABRICATE_MODEL_ID: 此函数只把 policy 当作黑箱字典吐出，调用方按 key 读取。
    """
    if not POLICY_PATH.exists():
        raise RuntimeError(f"policy file missing: {POLICY_PATH}")
    if not SHA_PATH.exists():
        raise RuntimeError(f"sha256 manifest missing: {SHA_PATH}")

    raw = POLICY_PATH.read_bytes()
    expected = _read_manifest_sha256()
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != expected:
        raise RuntimeError(
            f"policy sha256 mismatch: actual={actual} expected={expected}"
        )

    # 解析 yaml —— 用最小子集避免依赖（PyYAML 在 venv 中不一定有）
    try:
        import yaml  # type: ignore
        return yaml.safe_load(raw)
    except ImportError:
        # 降级路径：用极简 yaml parser 仅支持 spec 当前结构
        return _minimal_yaml_load(raw.decode("utf-8"))


def _minimal_yaml_load(text: str) -> dict:
    """最小 YAML 加载器 · 仅供 PyYAML 缺失时降级用 · 不用于生产。

    支持两层 mapping + 列表 + 标量; 足够解析 model-policy.v1.yaml 当前结构。
    """
    import ast
    out: dict = {}
    stack = [(out, -1)]
    current_indent = -1
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        # list item
        if stripped.startswith("- "):
            value = stripped[2:].strip()
            # pop stack to find list parent
            while stack and stack[-1][1] >= indent:
                stack.pop()
            parent, _ = stack[-1]
            if not isinstance(parent, list):
                # last appended mapping → turn into mapping under new list
                if isinstance(parent, dict) and parent and \
                   isinstance(list(parent.values())[-1], list):
                    last_key = list(parent.keys())[-1]
                    parent[last_key].append(_parse_scalar(value))
                else:
                    raise RuntimeError(f"yaml fallback: unexpected list at indent {indent}")
            continue
        # key: value
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            # adjust stack
            while stack and stack[-1][1] >= indent:
                stack.pop()
            parent, _ = stack[-1]
            if value == "":
                # container — peek next lines to decide list or mapping
                child: object = {}
                if isinstance(parent, dict):
                    parent[key] = child
                stack.append((child, indent))  # type: ignore[arg-type]
            else:
                if isinstance(parent, dict):
                    parent[key] = _parse_scalar(value)
    return out


def _parse_scalar(v: str):
    """yaml 标量 → python 原生类型"""
    if v.lower() in ("true", "yes"):
        return True
    if v.lower() in ("false", "no"):
        return False
    if v in ("null", "~", ""):
        return None
    if (v.startswith('"') and v.endswith('"')) or \
       (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    # number
    try:
        if "." in v:
            return float(v)
        return int(v)
    except ValueError:
        return v


def _append_audit(record: dict) -> None:
    """追加一行 JSONL 到 audit 日志（spec §"审计日志"）。

    永远不抛异常 —— 审计写入失败不能让 validate() 崩溃, 但写 stderr 告警。
    """
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001
        print(f"[codex_adapter] AUDIT WRITE FAILED: {e}", file=sys.stderr)


def _audit_and_return(allowed: bool, model: str, provider: str,
                      request_id: str, reason: str) -> Tuple[bool, str]:
    """统一收口: 写审计 + 返回结果"""
    _append_audit({
        "ts": _now_iso(),
        "runtime": RUNTIME_HOST,
        "model": model,
        "provider": provider,
        "request_id": request_id,
        "allowed": allowed,
        "reason": reason,
    })
    return (allowed, reason)


# ─────────────────────────────────────────────────────────────────────────────
# 校验逻辑（spec §"validate 校验顺序"）
# ─────────────────────────────────────────────────────────────────────────────

def _check_prohibited_routes(policy: dict, model: str, provider: str) -> str | None:
    """第 5 步：检查 prohibited_runtime_routes。

    spec §"validate 校验顺序" 5 — 不命中 prohibited 列表；命中即拒绝。
    返回命中原因字符串 / None。
    """
    routes = policy.get("model_policy", {}).get("prohibited_runtime_routes", []) or []
    if not isinstance(routes, list):
        return None
    # 简化匹配: 任一 route 关键词在 model/provider 串中 → 拒绝
    composite = f"{provider}::{model}".lower()
    for r in routes:
        if not isinstance(r, str):
            continue
        kw = r.lower()
        # 取 route 字符串里"具区分度"的 token 匹配
        for token in re.findall(r"[A-Za-z0-9_./:-]+", kw):
            if len(token) < 3:
                continue
            if token in composite or token in kw:
                # 任何 prohibited 路由的具体 token 命中 → 拒绝
                if token in composite:
                    return f"{REASON_ROUTE_PROHIBITED}:{r}"
    return None


def _validate_impl(model: str, provider: str, request_id: str) -> Tuple[bool, str]:
    """实际校验主函数。失败统一写 audit 后返回。"""
    # 加载 + 验签 policy（任一异常 → policy_unavailable）
    try:
        policy = _load_policy_dict()
    except Exception as e:  # noqa: BLE001
        return _audit_and_return(
            False, model, provider, request_id,
            f"{REASON_POLICY_UNAVAILABLE}:{type(e).__name__}",
        )

    mp = policy.get("model_policy", {}) or {}
    providers = mp.get("allowed_providers", []) or []

    # 1) provider 白名单
    provider_entry = None
    for p in providers:
        if isinstance(p, dict) and p.get("id") == provider:
            provider_entry = p
            break
    if provider_entry is None:
        return _audit_and_return(
            False, model, provider, request_id,
            f"{REASON_PROVIDER_NOT_ALLOWED}:{provider}",
        )

    # 2) provider enabled
    if provider_entry.get("enabled") is not True:
        return _audit_and_return(
            False, model, provider, request_id,
            f"{REASON_PROVIDER_DISABLED}:{provider}",
        )

    # 3) model 白名单
    models = provider_entry.get("models", []) or []
    model_entry = None
    for m in models:
        if isinstance(m, dict) and m.get("id") == model:
            model_entry = m
            break
    if model_entry is None:
        return _audit_and_return(
            False, model, provider, request_id,
            f"{REASON_MODEL_NOT_ALLOWED}:{model}",
        )

    # 4) model enabled
    if model_entry.get("enabled") is not True:
        return _audit_and_return(
            False, model, provider, request_id,
            f"{REASON_MODEL_DISABLED}:{model}",
        )

    # 5) prohibited routes
    route_reason = _check_prohibited_routes(policy, model, provider)
    if route_reason:
        return _audit_and_return(
            False, model, provider, request_id, route_reason,
        )

    # 6) 全过
    return _audit_and_return(True, model, provider, request_id, "ok")


# ─────────────────────────────────────────────────────────────────────────────
# 统一接口（spec §"统一接口"）
# ─────────────────────────────────────────────────────────────────────────────

def validate(model: str, provider: str, *, request_id: str) -> Tuple[bool, str]:
    """校验一次模型调用请求是否符合当前策略。

    参数:
        model:       请求的模型 ID（必须存在于 policy.allowed_providers[*].models）
        provider:    请求的 provider（必须存在于 policy.allowed_providers）
        request_id:  调用方生成的请求 ID（keyword-only 强制必填；UUID4 或 trace_id）

    返回:
        (True, "ok")                 — 请求放行
        (False, "<reason>")          — 请求拒绝；reason ≤ 200 字符

    红线契约:
        - NO_FABRICATE_MODEL_ID       — model id 从 policy 文件读取, 禁止硬编码
        - UNIFIED_INTERFACE_REQUIRED  — 签名 (model, provider, *, request_id) -> Tuple[bool, str]
        - NO_AUTO_FALLBACK_IN_ADAPTER — 拒绝时不重试/不切换 provider/不切换 model
    """
    # request_id 必填 + 类型检查（防御性；keyword-only 已强制）
    if not isinstance(request_id, str) or not request_id:
        return _audit_and_return(
            False, str(model), str(provider), "<missing>",
            f"{REASON_POLICY_UNAVAILABLE}:request_id_required",
        )
    # 截断 reason 长度（spec §"返回" ≤ 200 字符）
    allowed, reason = _validate_impl(model, provider, request_id)
    if len(reason) > 200:
        reason = reason[:197] + "..."
    return (allowed, reason)


# ─────────────────────────────────────────────────────────────────────────────
# 模块自检（可选；非契约必需）
# ─────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    """5 项本地冒烟；任一失败 → exit 1。"""
    cases = [
        # (model, provider, request_id, expect_allowed, label)
        ("MiniMax-M3",          "MiniMax", "selftest-1", True,  "default ok"),
        ("MiniMax-M2.7",        "MiniMax", "selftest-2", True,  "alt model ok"),
        ("MiniMax-M2.7-highspeed", "MiniMax", "selftest-3", True, "highspeed ok"),
        ("claude-sonnet-4.5",   "MiniMax", "selftest-4", False, "fabricated model denied"),
        ("MiniMax-M3",          "anthropic", "selftest-5", False, "other provider denied"),
        ("",                    "MiniMax", "selftest-6", False, "empty model denied"),
    ]
    fail = 0
    for model, provider, rid, expect_ok, label in cases:
        try:
            ok, reason = validate(model, provider, request_id=rid)
            actual_ok = ok
        except Exception as e:  # noqa: BLE001
            actual_ok = False
            reason = f"EXC:{type(e).__name__}:{e}"
        if actual_ok != expect_ok:
            print(f"  FAIL  {label}: expected allowed={expect_ok} got={actual_ok} reason={reason!r}")
            fail += 1
        else:
            print(f"  PASS  {label}: allowed={actual_ok} reason={reason!r}")
    return fail


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "--self-test":
        n = _self_test()
        print(f"=== self-test: {len([c for c in [
            ('MiniMax-M3','MiniMax','selftest-1',True,'default ok'),
            ('MiniMax-M2.7','MiniMax','selftest-2',True,'alt model ok'),
            ('MiniMax-M2.7-highspeed','MiniMax','selftest-3',True,'highspeed ok'),
            ('claude-sonnet-4.5','MiniMax','selftest-4',False,'fabricated model denied'),
            ('MiniMax-M3','anthropic','selftest-5',False,'other provider denied'),
            ('','MiniMax','selftest-6',False,'empty model denied'),
        ])} - {n} FAIL ===")
        sys.exit(0 if n == 0 else 1)
    elif arg == "--smoke":
        ok, reason = validate("MiniMax-M3", "MiniMax", request_id="smoke-1")
        print(f"smoke: allowed={ok} reason={reason!r}")
        sys.exit(0 if ok else 1)
    else:
        print("usage: codex_runtime.py [--self-test|--smoke]")
        sys.exit(2)
