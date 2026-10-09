#!/usr/bin/env python3
"""
CloudTech PreToolUse Hook — ModelPolicy v1 enforcement
- stdin JSON parse → 关键字检查 → exit 1 deny / exit 0 allow
- v2 修: BOM (\ufeff) strip · 兼容 PowerShell pipe
"""
import json, sys, hashlib, time
from pathlib import Path

POLICY_PATH = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml")
SHA_PATH = Path(r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256")
REJECT_LOG = Path(r"D:\AIOS\_agent-hub\audit\cloudtech-adapter-rejects.log")

PROHIBITED = [
    "deepseek", "qwen", "gpt-4", "gpt-3.5", "claude-3", "claude-sonnet",
    "gemini", "llama-3", "mistral", "openai.com", "anthropic.com", "googleapis",
    "gpt-5-codex", "doubao", "agnes", "gpt-image", "codex-openai", "codex_desktop",
    "dashscope",
]

EXCEPT_PATH_PATTERNS = [
    r".*backups.*\.py$",
    r".*_backups.*\.py$",
    r".*legacy.*\.py$",
    r".*provider_router\.py$",
]
ALLOWED_MINIMAX_TOKENS = [
    "minimax", "MiniMax", "MINIMAX", "minimax-m3", "minimax-m2.7",
    "MiniMax-M3", "MiniMax-M2.7", "MiniMax-M2.7-highspeed",
    "https://api.minimaxi.com", "https://api.minimaxi.com/v1", "https://api.minimaxi.com/anthropic",
    "api.minimax", "api.minimaxi.com",
]

def verify_policy():
    if not POLICY_PATH.exists() or not SHA_PATH.exists():
        return False, "policy or manifest missing"
    actual = hashlib.sha256(POLICY_PATH.read_bytes()).hexdigest().upper()
    expected = None
    for line in SHA_PATH.read_text(encoding="utf-8").splitlines():
        if line.startswith("sha256:"):
            expected = line.split(":", 1)[1].strip().upper()
            break
    if not expected:
        return False, "manifest format invalid"
    return actual == expected, f"sha256 {'match' if actual == expected else 'MISMATCH'}"

def is_exempt_path(file_path):
    import re
    for pat in EXCEPT_PATH_PATTERNS:
        if re.match(pat, file_path):
            return True
    return False

def check_content(text):
    text_lower = text.lower()
    for tok in ALLOWED_MINIMAX_TOKENS:
        if tok.lower() in text_lower:
            return None
    for kw in PROHIBITED:
        if kw in text_lower:
            return f"prohibited_keyword:{kw}"
    return None

def main():
    ok, info = verify_policy()
    if not ok:
        print(json.dumps({"decision": "deny", "reason": f"policy_{info}"}))
        sys.exit(1)

    try:
        raw = sys.stdin.read()
        # BOM strip (兼容 PowerShell pipe)
        if raw.startswith("\ufeff"):
            raw = raw[1:]
        request = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        request = {}

    tool = request.get("tool", "")
    file_path = request.get("file_path", "") or request.get("path", "")
    content = request.get("content", "") or request.get("text", "")

    if tool not in ("write", "edit", "Write", "Edit", "create_file", "apply_patch", "multi_edit"):
        print(json.dumps({"decision": "allow", "reason": "non-write tool"}))
        sys.exit(0)

    if file_path and is_exempt_path(file_path):
        print(json.dumps({"decision": "allow", "reason": "exempt_path"}))
        sys.exit(0)

    if content:
        reason = check_content(content)
        if reason:
            entry = {
                "ts": time.time(),
                "runtime": "cloudtech_pretool_use",
                "tool": tool,
                "file_path": file_path,
                "reason": reason,
                "policy": "model-policy.v1",
            }
            try:
                REJECT_LOG.parent.mkdir(parents=True, exist_ok=True)
                with REJECT_LOG.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except Exception:
                pass
            print(json.dumps({"decision": "deny", "reason": reason, "policy_ref": str(POLICY_PATH)}))
            sys.exit(1)

    print(json.dumps({"decision": "allow", "reason": "policy_compliant"}))
    sys.exit(0)

if __name__ == "__main__":
    main()