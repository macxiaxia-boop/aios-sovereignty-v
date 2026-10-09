#!/usr/bin/env python3
"""ModelPolicy Reconciler · Mode A + L1 Auto-Rollback · v2.0
原 v1 由 codex 01a11c30 写 (检测+报告) · v2 加 L1 自动回滚 runtime config
- 不变量: NEVER auto-modify policy file
- 不变量: NEVER auto-modify model-policy.v1.yaml / .sha256
- 允许: L1 drift 自动回滚 runtime config (e.g. 删除新加的非 MiniMax profile 文件)
- 允许: 写 DriftEvent 到 audit/drift-events.log (含 auto_rollback action)

落盘位置: D:\AIOS\_agent-hub\policy\reconciler\reconciler.py (覆盖原 v1)
作者: Codex 01a11c23 (supervisor, 接 01a11c30 班)
授权: user-2026-10-08T23:55 + 你就开始 + 继续 + B+C (2026-10-09)
"""
import argparse, json, time, subprocess, hashlib, sys, os
from pathlib import Path

POLICY_PATH_DEFAULT = r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml"
SHA256_PATH_DEFAULT = r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256"
DRIFT_LOG           = r"D:\AIOS\_agent-hub\audit\drift-events.log"
ALERT_LOG           = r"D:\AIOS\_agent-hub\policy\reconciler\alerts.jsonl"

# Codex config 目录 (L1 runtime config 自动回滚目标)
CODEX_HOME = Path(os.environ.get("USERPROFILE", "")) / ".codex"

PROHIBITED_KEYWORDS = [
    "deepseek", "qwen", "gpt-4", "gpt-3.5", "claude-3", "claude-sonnet",
    "gemini", "llama-3", "mistral", "openai.com", "anthropic.com", "googleapis",
    "gpt-5-codex", "doubao", "ollama", "agnes", "gpt-image", "chatgpt",
]

# L1 自动回滚: 删除非 MiniMax 的 profile 文件
L1_AUTO_DELETE_PATTERNS = [
    "codex-openai.config.toml",
    "codex-claude.config.toml",
    "codex-deepseek.config.toml",
    "ollama.config.toml",
    "codex-switch.bat",
    "codex-switch.py",
]

def load_yaml(path):
    try:
        import yaml
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        print(f"FATAL load_yaml: {e}", file=sys.stderr)
        return None

def verify_sha256(policy_path, sha_path):
    if not os.path.exists(sha_path):
        return False, "manifest missing"
    manifest_hash = None
    for line in open(sha_path, "r", encoding="utf-8"):
        if line.startswith("sha256:"):
            manifest_hash = line.split(":", 1)[1].strip()
            break
    if not manifest_hash:
        return False, "manifest format wrong"
    actual = hashlib.sha256(open(policy_path, "rb").read()).hexdigest().upper()
    return actual == manifest_hash.upper(), f"expected={manifest_hash[:16]}.. actual={actual[:16]}.."

def scan_processes():
    out_list = []
    try:
        r = subprocess.run(["wmic", "process", "get", "Name,ProcessId,CommandLine", "/FORMAT:CSV"],
                           capture_output=True, text=True, timeout=15)
        for line in r.stdout.splitlines()[1:]:
            parts = line.split(",", 2)
            if len(parts) >= 3:
                out_list.append({"name": parts[0], "pid": parts[1], "cmd": parts[2]})
    except Exception as e:
        out_list.append({"error": str(e)})
    return out_list

def scan_env():
    out = []
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-ChildItem env: | Where-Object { $_.Name -match 'OPENAI|ANTHROPIC|MiniMax|MODEL|API' } | ConvertTo-Json -Compress"],
                           capture_output=True, text=True, timeout=15)
        if r.stdout.strip():
            out = json.loads(r.stdout)
    except Exception as e:
        out = [{"error": str(e)}]
    return out

def scan_codex_profiles():
    """扫描 ~/.codex/ 下所有 profile 文件"""
    profiles = []
    if not CODEX_HOME.exists():
        return profiles
    for f in CODEX_HOME.iterdir():
        if f.is_file() and f.suffix in (".toml", ".bat", ".ps1", ".py"):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore").lower()
                hits = [kw for kw in PROHIBITED_KEYWORDS if kw in text]
                if hits:
                    profiles.append({"path": str(f), "name": f.name, "hits": hits, "size": f.stat().st_size})
            except Exception:
                pass
    return profiles

def auto_rollback_l1(drift_items):
    """L1 自动回滚: 删除 ~/.codex/ 下含禁止关键字的 profile 文件
    不变量: NEVER modify policy files
    """
    actions = []
    profiles = scan_codex_profiles()
    for p in profiles:
        name = p["name"].lower()
        # 仅回滚明确已知的"非 MiniMax profile" 模式
        if any(pattern.lower() in name for pattern in L1_AUTO_DELETE_PATTERNS):
            try:
                target = Path(p["path"])
                if target.exists():
                    target.unlink()
                    actions.append({
                        "type": "auto_rollback_l1",
                        "action": "delete",
                        "path": p["path"],
                        "reason": f"L1 drift: contains prohibited keywords {p['hits']}",
                    })
            except Exception as e:
                actions.append({
                    "type": "auto_rollback_l1_failed",
                    "path": p["path"],
                    "error": str(e),
                })
    return actions

def check_compliance(policy, procs, envs):
    drift = []
    for p in procs:
        cmd = (p.get("cmd") or "").lower()
        name = (p.get("name") or "").lower()
        if not any(t in name for t in ("codex", "claude", "openclaw", "hermes", "node", "python")):
            continue
        for kw in PROHIBITED_KEYWORDS:
            if kw in cmd:
                drift.append({"type": "L2", "source": "proc", "pid": p.get("pid"),
                              "name": name, "reason": f"prohibited_keyword:{kw}",
                              "cmd": cmd[:200]})
                break
    for e in envs:
        name = (e.get("Name") or "").upper()
        val = (e.get("Value") or "")
        if "MINIMAX" in val.upper() or "MiniMax" in val:
            continue
        if any(kw in val.lower() for kw in PROHIBITED_KEYWORDS):
            drift.append({"type": "L1", "source": "env", "name": name,
                          "reason": "non_MiniMax_endpoint", "value_prefix": val[:80]})
    # L1 profile drift
    profiles = scan_codex_profiles()
    for prof in profiles:
        drift.append({"type": "L1", "source": "profile", "path": prof["path"],
                      "reason": f"prohibited_profile:{prof['hits']}"})
    return drift

def append_jsonl(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=POLICY_PATH_DEFAULT)
    ap.add_argument("--sha256-manifest", default=SHA256_PATH_DEFAULT)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--auto-rollback", action="store_true", default=True,
                    help="Auto rollback L1 drift (default: True)")
    args = ap.parse_args()

    policy = load_yaml(args.policy)
    if not policy:
        print("FATAL: cannot load policy", file=sys.stderr)
        sys.exit(2)

    ok, info = verify_sha256(args.policy, args.sha256_manifest)
    if not ok:
        print(f"FATAL: sha256 mismatch ({info})", file=sys.stderr)
        sys.exit(3)

    procs = scan_processes()
    envs = scan_env()
    drift = check_compliance(policy, procs, envs)

    # L1 自动回滚
    rollback_actions = []
    l1_drift = [d for d in drift if d.get("type") == "L1"]
    if l1_drift and args.auto_rollback:
        rollback_actions = auto_rollback_l1(l1_drift)

    event = {
        "ts": time.time(),
        "policy_id": policy.get("policy_id"),
        "policy_version": policy.get("policy_version"),
        "proc_count": len(procs),
        "env_count": len(envs),
        "drift_count": len(drift),
        "drift": drift,
        "rollback_actions": rollback_actions,
    }
    append_jsonl(DRIFT_LOG, event)

    # 漂移仍存在 (L2 或 L1 回滚失败) → 告警
    residual_drift = [d for d in drift if d.get("type") == "L2"]
    failed_rollbacks = [a for a in rollback_actions if "failed" in a.get("type", "")]
    if residual_drift or failed_rollbacks:
        append_jsonl(ALERT_LOG, event)
        print(f"ALERT: residual={len(residual_drift)} rollback_fail={len(failed_rollbacks)}", file=sys.stderr)
        sys.exit(1)

    if rollback_actions:
        print(f"OK+ROLLBACK: procs={len(procs)} env={len(envs)} drift={len(drift)} actions={len(rollback_actions)}")
        sys.exit(0)

    print(f"OK: procs={len(procs)} env={len(envs)} drift=0")
    sys.exit(0)

if __name__ == "__main__":
    main()
