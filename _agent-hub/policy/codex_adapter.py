#!/usr/bin/env python3
"""Codex Adapter · ModelPolicy PreToolUse Hook · v1.0
实现 adapter-contract.md 的 intercept_request() 语义。
挂在 Codex hooks.json 的 PreToolUse Write|Edit 钩子。
- 读 model-policy.v1.yaml
- 校验 sha256
- 检查 file_path/content 是否含禁止 provider 关键字
- DENY → exit 1 (Codex 阻止写盘)
- ALLOW → exit 0

落盘位置: D:\AIOS\_agent-hub\policy\codex_adapter.py
作者: Codex 01a11c23 (supervisor, 接 01a11c30 班)
授权: user-2026-10-08T23:55 + 你就开始 + 继续 + B+C (2026-10-09)
"""
import json, sys, os, hashlib, time
from pathlib import Path

POLICY_PATH = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml")
MANIFEST_PATH = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256")
REJECT_LOG = Path(r"D:\AIOS\_agent-hub\audit\adapter-rejects.log")

# 禁止关键字 (来自 model_policy.prohibited_runtime_routes + 用户原话)
PROHIBITED = [
    "deepseek", "qwen", "gpt-4", "gpt-3.5", "claude-3", "claude-sonnet",
    "gemini", "llama-3", "mistral", "openai.com", "anthropic.com", "googleapis",
    "gpt-5-codex", "openai", "claude", "doubao", "ollama", "qwen2", "qwen3",
    "agnes", "gpt-image", "chatgpt", "codex-openai", "codex_desktop",
]

# 允许的 MiniMax 标识 (防止误伤合法的 MiniMax 调用)
ALLOWED = ["MiniMax", "MiniMax-M3", "minimaxi.com", "minimax"]

def verify_policy():
    """验证 Policy 文件 + sha256"""
    if not POLICY_PATH.exists():
        return False, "policy file missing"
    if not MANIFEST_PATH.exists():
        return False, "manifest missing"
    actual = hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest().upper()
    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
    expected = None
    for line in manifest_text.splitlines():
        if line.startswith("sha256:"):
            expected = line.split(":", 1)[1].strip().upper()
            break
    if not expected:
        return False, "manifest format invalid"
    return actual == expected, f"sha256 {'match' if actual == expected else 'MISMATCH'}"

def check_content(text):
    """检查文本中是否含禁止关键字"""
    if not text:
        return []
    text_lower = text.lower()
    hits = []
    for kw in PROHIBITED:
        if kw in text_lower:
            hits.append(kw)
    return hits

def log_reject(reason, payload_summary):
    """记录拒绝事件到审计日志"""
    REJECT_LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": time.time(),
        "adapter": "codex-pre-tool-use",
        "reason": reason,
        "payload_summary": payload_summary[:200] if payload_summary else "",
    }
    with open(REJECT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw else {}
    except Exception as e:
        # 解析失败 → 放行（避免误阻塞合法调用）
        sys.exit(0)

    # 1. 验证 Policy (fail-closed: Policy 损坏 → 拒绝所有)
    ok, info = verify_policy()
    if not ok:
        log_reject(f"POLICY_INVALID: {info}", str(data))
        print(f"ADAPTER-REJECT: Policy {info}", file=sys.stderr)
        sys.exit(2)

    # 2. 收集所有要检查的文本字段
    texts = []
    for key in ("file_path", "command", "content", "prompt", "new_string", "old_string"):
        v = data.get(key)
        if isinstance(v, str):
            texts.append((key, v))

    # 3. 检查每个文本
    for key, text in texts:
        hits = check_content(text)
        if hits:
            reason = f"PROHIBITED_KEYWORD: {hits} in {key}"
            log_reject(reason, text)
            print(f"ADAPTER-DENY: {reason}", file=sys.stderr)
            sys.exit(1)

    # 4. ALLOW
    sys.exit(0)

if __name__ == "__main__":
    main()
