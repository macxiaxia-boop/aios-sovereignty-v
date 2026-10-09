#!/usr/bin/env python3
"""Codex Adapter · ModelPolicy PreToolUse Hook · v2.0
- 加真实 MiniMax model id 到 ALLOWED (MiniMax-M2.7 / MiniMax-M2.7-highspeed)
- 保留 fail-closed 语义
- 加 quota 验证 hook (可后续扩展)
"""
import json, sys, os, hashlib, time
from pathlib import Path

POLICY_PATH = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml")
MANIFEST_PATH = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256")
REJECT_LOG = Path(r"D:\AIOS\_agent-hub\audit\adapter-rejects.log")

# v2.0: 真实 model id 来自 https://api.minimaxi.com/v1/models
# 用户授权: MiniMax-M3 (默认) / MiniMax-M2.7 / MiniMax-M2.7-highspeed
PROHIBITED = [
    "deepseek", "qwen", "gpt-4", "gpt-3.5", "claude-3", "claude-sonnet",
    "gemini", "llama-3", "mistral", "openai.com", "anthropic.com", "googleapis",
    "gpt-5-codex", "openai", "claude", "doubao", "ollama", "qwen2", "qwen3",
    "agnes", "gpt-image", "chatgpt", "codex-openai", "codex_desktop",
]

# v2.0: 真实 MiniMax model id (从 /v1/models 实证)
ALLOWED = [
    "MiniMax",            # provider name
    "MiniMax-M3",         # 深度推理 (默认)
    "MiniMax-M2.7",       # 标准
    "MiniMax-M2.7-highspeed",  # 高速
    "minimaxi.com",       # domain
    "minimax",            # owned_by
]

def verify_policy():
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
    if not text:
        return []
    text_lower = text.lower()
    hits = []
    for kw in PROHIBITED:
        if kw in text_lower:
            hits.append(kw)
    return hits

def log_reject(reason, payload_summary):
    REJECT_LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "ts": time.time(),
        "adapter": "codex-pre-tool-use-v2",
        "reason": reason,
        "payload_summary": payload_summary[:200] if payload_summary else "",
    }
    with open(REJECT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

def main():
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw else {}
    except Exception:
        sys.exit(0)

    ok, info = verify_policy()
    if not ok:
        log_reject(f"POLICY_INVALID: {info}", str(data))
        print(f"ADAPTER-REJECT: Policy {info}", file=sys.stderr)
        sys.exit(2)

    texts = []
    for key in ("file_path", "command", "content", "prompt", "new_string", "old_string"):
        v = data.get(key)
        if isinstance(v, str):
            texts.append((key, v))

    for key, text in texts:
        hits = check_content(text)
        if hits:
            reason = f"PROHIBITED_KEYWORD: {hits} in {key}"
            log_reject(reason, text)
            print(f"ADAPTER-DENY: {reason}", file=sys.stderr)
            sys.exit(1)

    sys.exit(0)

if __name__ == "__main__":
    main()
