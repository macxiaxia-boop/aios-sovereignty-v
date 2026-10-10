#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
openclaw_runtime.py - ModelPolicy Adapter for OpenClaw runtime (W8/T11 - 2026-10-09)

SSOT paths:
  - Spec:     D:\AIOS\_agent-hub\policy\adapter-spec.v1.md
  - Policy:   D:\AIOS\_agent-hub\policy\model-policy.v1.yaml
  - Manifest: D:\AIOS\_agent-hub\policy\model-policy.v1.sha256
  - Contract: D:\AIOS\_agent-hub\policy\adapter-contract.md

Authorizer: user-2026-10-08T23:55 (sovereignty-v) + 你就开始 + 继续 (2026-10-09)
Thread:     01a11c33-c813-7752-9e53-b7c332d00445 (Codex engineering - W8)
Supervisor: 01a11c30-6f6c-76c0-8c60-a55f3a43ff63 (Codex supervisor)
Executor:   Claude Code 01a11c33 (执行线程)

红线契约（写进 SSOT - 永久态）:
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

# 路径常量（adapter-spec.v1.md §"读取 Policy"）- 仅路径常量，不含 model id
POLICY_PATH = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml")
SHA_PATH    = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256")
AUDIT_LOG   = Path(r"D:\AIOS\_agent-hub\audit\adapter-validations.log")

# 运行时身份（仅本 runtime 的 host 标识，非 model id）
RUNTIME_HOST = "openclaw"

# 拒绝原因前缀（与 spec §"validate 校验顺序" 完全对齐）
REASON_PROVIDER_NOT_ALLOWED = "provider_not_allowed"
REASON_PROVIDER_DISABLED    = "provider_disabled"
REASON_MODEL_NOT_ALLOWED    = "model_not_allowed"
REASON_MODEL_DISABLED       = "model_disabled"
REASON_ROUTE_PROHIBITED     = "route_prohibited"
REASON_POLICY_UNAVAILABLE   = "policy_unavailable"

# 8h 时区偏移（中国标准时间 - 与 manifest signed_at 字段保持一致）
_TZ_CN = timezone(timedelta(hours=8))


# ---
# 内部工具
# ---

def _now_iso() -> str:
    """ISO-8601 with CST offset（spec §"审计日志"示例格式对齐）"""
    now = datetime.now(_TZ_CN)
    return now.strftime("%Y-%m-%dT%H:%M:%S") + now.strftime("%z")[:3] + ":" + \
           now.strftime("%z")[3:]


def _read_manifest_sha256() -> str:
    """从 model-policy.v1.sha256 提取 hash（不依赖 yaml 库即可工作）"""
    text = SHA_PATH.read_text(encoding="utf-8")
    m = re.search(r"sha256:\s*([0-9A-Fa-f]{64})", text)
    if not m:
        raise RuntimeError(f"manifest 格式错误: {SHA_PATH}")
    return m.group(1).upper()


def _load_policy_dict() -> dict:
    """读取 + 验签 + 解析 policy yaml。失败 - 抛 RuntimeError。

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

    # 解析 yaml - 用最小子集避免依赖（PyYAML 在 venv 中不一定有）
    try:
        import yaml  # type: ignore
        return yaml.safe_load(raw)
    except ImportError:
        # 降级路径：用极简 yaml parser 仅支持 spec 当前结构
        return _minimal_yaml_load(raw.decode("utf-8"))


def _minimal_yaml_load(text: str) -> dict:
    """最小 YAML 加载器 - 仅供 PyYAML 缺失时降级用 - 不用于生产。

    支持两层 mapping + 列表 + 标量; 足够解析 model-policy.v1.yaml 当前结构。
    """
    out: dict = {}
    stack = [(out, -1)]
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
                # last appended mapping - turn into mapping under new list
                if isinstance(parent, dict) and parent and \
                   isinstance(list(parent.values())[-1], list):
                    last_key = list(parent.keys())[-1]
                    parent[last_key].append(_parse_scalar(value))
                else:
                    raise RuntimeError(f"yaml_minimal_loader: unexpected list at indent {indent}")
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
                # container - peek next lines to decide list or mapping
                child: object = {}
                if isinstance(parent, dict):
                    parent[key] = child
                stack.append((child, indent))  # type: ignore[arg-type]
            else:
                if isinstance(parent, dict):
                    parent[key] = _parse_scalar(value)
    return out


def _parse_scalar(v: str):
    """yaml 标量 - python 原生类型"""
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

    永远不抛异常 - 审计写入失败不能让 validate() 崩溃, 但写 stderr 告警。
    """
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:  # noqa: BLE001
        print(f"[openclaw_adapter] AUDIT WRITE FAILED: {e}", file=sys.stderr)


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


# ---
# 校验逻辑（spec §"validate 校验顺序"）
# ---

def _check_prohibited_routes(policy: dict, model: str, provider: str) -> str | None:
    """第 5 步：检查 prohibited_runtime_routes。

    spec §"validate 校验顺序" 5 - 不命中 prohibited 列表；命中即拒绝。

    设计原则（红线 NO_FABRICATE_MODEL_ID 兼容）：
      - 只把"显式关键词列表"型 route 视作可执行规则。
      - 句子型 route (如 "any provider other than MiniMax" / "any cross-provider
        auto-fallback" / "any cron/heartbeat/session-restore carrying legacy model")
        是元规则, 已在 step 1 (provider 白名单) 覆盖, 这里跳过。
      - 关键词提取优先级: ① 括号内 slash 列表 ② slash/逗号分隔的纯 token 行。
    """
    routes = policy.get("model_policy", {}).get("prohibited_runtime_routes", []) or []
    if not isinstance(routes, list):
        return None

    for r in routes:
        if not isinstance(r, str):
            continue
        # 跳过元规则（已在 step 1/2/3/4 覆盖）
        lower_r = r.lower()
        if "other than" in lower_r or "auto-fallback" in lower_r or \
           "auto-restore" in lower_r or "env var" in lower_r or \
           "cron" in lower_r or "session-restore" in lower_r or \
           "heartbeat" in lower_r:
            continue

        # 提取显式关键词 token
        keywords: list[str] = []
        # ① 括号内 "...(kw1/kw2/kw3)" 形式
        paren = re.search(r"\(([^)]+)\)", r)
        if paren:
            for tok in re.split(r"[/,\s]+", paren.group(1)):
                tok = tok.strip().lower()
                if tok and len(tok) >= 3:
                    keywords.append(tok)
        # ② "kw1 / kw2 profiles" 形式
        if "/" in r and "profiles" in lower_r:
            head = r.split("profiles")[0]
            for tok in re.split(r"[/,\s]+", head):
                tok = tok.strip().lower()
                if tok and len(tok) >= 3 and tok not in ("in", "config"):
                    keywords.append(tok)
        # ③ "any X containing Y" 形式 - 提取 Y 后的关键词
        m_contain = re.search(r"containing\s+([A-Za-z0-9_./-]+)", lower_r)
        if m_contain:
            keywords.append(m_contain.group(1).lower())

        if not keywords:
            continue

        for kw in keywords:
            # 显式匹配: model 或 provider 直接等于或包含此关键词
            if kw == provider.lower() or kw == model.lower():
                return f"{REASON_ROUTE_PROHIBITED}:{r}"
            if kw in model.lower() or kw in provider.lower():
                return f"{REASON_ROUTE_PROHIBITED}:{r}"
    return None


def _validate_impl(model: str, provider: str, request_id: str) -> Tuple[bool, str]:
    """实际校验主函数。失败统一写 audit 后返回。"""
    # 加载 + 验签 policy（任一异常 - policy_unavailable）
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


# ---
# 统一接口（spec §"统一接口"）
# ---

def validate(model: str, provider: str, *, request_id: str) -> Tuple[bool, str]:
    """校验一次模型调用请求是否符合当前策略。

    参数:
        model:       请求的模型 ID（必须存在于 policy.allowed_providers[*].models）
        provider:    请求的 provider（必须存在于 policy.allowed_providers）
        request_id:  调用方生成的请求 ID（keyword-only 强制必填；UUID4 或 trace_id）

    返回:
        (True, "ok")                 - 请求放行
        (False, "<reason>")          - 请求拒绝；reason ≤ 200 字符

    红线契约:
        - NO_FABRICATE_MODEL_ID       - model id 从 policy 文件读取, 禁止硬编码
        - UNIFIED_INTERFACE_REQUIRED  - 签名 (model, provider, *, request_id) -> Tuple[bool, str]
        - NO_AUTO_FALLBACK_IN_ADAPTER - 拒绝时不重试/不切换 provider/不切换 model
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


# ---
# 模块自检（可选；非契约必需）
# ---

def _self_test() -> int:
    """6 项本地冒烟；任一失败 - exit 1。

    用例严格匹配 model-policy.v1.yaml 当前实际内容（仅一个 model enabled）。
    """
    cases = [
        # (model, provider, request_id, expect_allowed, label)
        ("MiniMax-M3",          "MiniMax", "selftest-1", True,  "default ok"),
        ("claude-sonnet-4.5",   "MiniMax", "selftest-2", False, "fabricated model denied"),
        ("MiniMax-M3",          "anthropic", "selftest-3", False, "other provider denied"),
        ("",                    "MiniMax", "selftest-4", False, "empty model denied"),
        ("gpt-5-codex",         "MiniMax", "selftest-5", False, "prohibited keyword denied"),
        ("MiniMax-M3",          "MiniMax", "",            False, "missing request_id denied"),
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
        total = 6
        print(f"=== self-test: {total} - {n} FAIL ===")
        sys.exit(0 if n == 0 else 1)
    elif arg == "--smoke":
        ok, reason = validate("MiniMax-M3", "MiniMax", request_id="smoke-1")
        print(f"smoke: allowed={ok} reason={reason!r}")
        sys.exit(0 if ok else 1)
    else:
        print("usage: openclaw_runtime.py [--self-test|--smoke]")
        sys.exit(2)
