#!/usr/bin/env python3
"""
Model Policy Reconciler v3 — 2026-10-09 user directive A+B
- Reads exception_rules from model-policy.v1.yaml
- Skips paths/env_vars listed in exception_rules
- NEVER auto-modify model-policy.v1.yaml
- NEVER auto-modify model-policy.v1.sha256
- Only read + write drift events to audit/drift-events.log
- Single instance enforced via msvcrt file lock
"""
import argparse, json, time, subprocess, hashlib, sys, os
import msvcrt, fnmatch
from pathlib import Path

POLICY_PATH_DEFAULT = r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml"
SHA256_PATH_DEFAULT = r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256"
DRIFT_LOG           = r"D:\AIOS\_agent-hub\audit\drift-events.log"
ALERT_LOG           = r"D:\AIOS\_agent-hub\policy\reconciler\alerts.jsonl"

PROHIBITED_KEYWORDS_HARDCODED = [
    "deepseek", "gpt-4", "gpt-3.5", "claude-3", "claude-sonnet",
    "gemini", "llama-3", "mistral", "anthropic.com", "googleapis",
    "gpt-5-codex", "doubao", "agnes", "gpt-image", "codex-openai", "codex_desktop",
]
# Note: "openai.com", "qwen", "ollama", "chatgpt" now controlled by yaml exception_rules

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

def parse_exception_rules(policy):
    exceptions = policy.get("model_policy", {}).get("exception_rules", []) or []
    path_globs = []
    env_vars = set()
    for rule in exceptions:
        rtype = rule.get("type", "")
        if rtype == "path_globs":
            globs = rule.get("globs", []) or []
            keywords = set(rule.get("allowed_keywords", []) or [])
            for g in globs:
                path_globs.append((g, keywords))
        elif rtype == "env_vars":
            for ev in rule.get("env_vars", []) or []:
                env_vars.add(ev)
    return path_globs, env_vars

def is_path_exempt(file_path, path_globs_with_kw, keyword_hit):
    norm = file_path.replace("\\", "/")
    for glob, kws in path_globs_with_kw:
        expanded = os.path.expanduser(glob).replace("\\", "/")
        if fnmatch.fnmatch(norm, expanded) or fnmatch.fnmatch(norm, glob.replace("\\", "/")):
            if "*" in kws or keyword_hit in kws:
                return True
    return False

def is_env_exempt(env_name, env_vars):
    return env_name in env_vars

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
                            "Get-ChildItem env: | Where-Object { $_.Name -match 'OPENAI|ANTHROPIC|MiniMax|MODEL|API|OLLAMA' } | ConvertTo-Json -Compress"],
                           capture_output=True, text=True, timeout=15)
        if r.stdout.strip():
            out = json.loads(r.stdout)
    except Exception as e:
        out = [{"error": str(e)}]
    return out

def scan_profile_files():
    candidates = []
    all_keywords = PROHIBITED_KEYWORDS_HARDCODED + ["openai.com", "qwen", "ollama", "chatgpt"]
    for base in ["~/.codex", "~/.claude", "~/.openclaw", "~/.hermes", "D:/AIOS/_agent-hub"]:
        p = Path(os.path.expanduser(base))
        if not p.exists():
            continue
        for f in p.rglob("*"):
            if not f.is_file():
                continue
            if any(x in f.name for x in [".bak.", ".old", "config.backup."]):
                continue
            try:
                if f.stat().st_size > 1_000_000:
                    continue
                txt = f.read_text(encoding="utf-8", errors="ignore")
                hits = []
                for kw in all_keywords:
                    if kw in txt.lower():
                        hits.append(kw)
                if hits:
                    candidates.append({"path": str(f), "size": f.stat().st_size, "hits": hits})
            except Exception:
                pass
    return candidates

def check_compliance(policy, procs, envs, profile_files, path_globs_with_kw, env_vars):
    drift = []
    # 1. process cmdlines
    for p in procs:
        cmd = (p.get("cmd") or "").lower()
        name = (p.get("name") or "").lower()
        if not any(t in name for t in ("codex", "claude", "openclaw", "hermes", "node", "python")):
            continue
        for kw in PROHIBITED_KEYWORDS_HARDCODED:
            if kw in cmd:
                drift.append({"type": "L2", "source": "proc", "pid": p.get("pid"),
                              "name": name, "reason": f"prohibited_keyword:{kw}",
                              "cmd": cmd[:200]})
                break
    # 2. env vars (skip exempt)
    for e in envs:
        name = (e.get("Name") or "").upper()
        if is_env_exempt(name, env_vars):
            continue
        val = (e.get("Value") or "")
        all_kw = PROHIBITED_KEYWORDS_HARDCODED + ["openai.com", "qwen", "ollama", "chatgpt"]
        if any(p in val for p in all_kw):
            if "MiniMax" not in val and "minimax" not in val:
                drift.append({"type": "L1", "source": "env", "name": name,
                              "reason": "non_MiniMax_endpoint", "value_prefix": val[:80]})
    # 3. profile files (skip exempt paths)
    for pf in profile_files:
        path = pf["path"]
        for kw in pf["hits"]:
            if is_path_exempt(path, path_globs_with_kw, kw):
                continue
            drift.append({"type": "L1", "source": "profile", "path": path,
                          "reason": f"prohibited_profile:[{kw}]"})
    return drift

def append_jsonl(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def acquire_single_instance_lock():
    """Windows 文件锁 (msvcrt) 强制单实例; 已有实例在跑则本进程退出"""
    lock_path = r"D:\AIOS\_agent-hub\policy\reconciler\.lock"
    Path(lock_path).parent.mkdir(parents=True, exist_ok=True)
    f = open(lock_path, "w")
    try:
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        return f
    except OSError:
        f.close()
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=POLICY_PATH_DEFAULT)
    ap.add_argument("--sha256-manifest", default=SHA256_PATH_DEFAULT)
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--no-scan", action="store_true",
                    help="Skip slow scans (profile files) for fast test/audit mode")
    args = ap.parse_args()
    _lock_f = acquire_single_instance_lock()
    if _lock_f is None:
        print('SKIP: another reconciler instance running', file=sys.stderr)
        sys.exit(0)

    policy = load_yaml(args.policy)
    if not policy:
        print("FATAL: cannot load policy", file=sys.stderr); sys.exit(2)
    ok, info = verify_sha256(args.policy, args.sha256_manifest)
    if not ok:
        print(f"FATAL: sha256 mismatch ({info})", file=sys.stderr); sys.exit(3)

    path_globs, env_vars = parse_exception_rules(policy)
    procs = scan_processes()
    envs = scan_env()
    if args.no_scan:
        profiles = []
    else:
        profiles = scan_profile_files()

    drift = check_compliance(policy, procs, envs, profiles, path_globs, env_vars)
    event = {"ts": time.time(),
             "policy_id": policy.get("policy_id"),
             "policy_version": policy.get("policy_version"),
             "proc_count": len(procs), "env_count": len(envs),
             "profile_count": len(profiles),
             "exception_globs": len(path_globs), "exception_envs": sorted(env_vars),
             "drift_count": len(drift), "drift": drift}
    append_jsonl(DRIFT_LOG, event)
    if drift:
        append_jsonl(ALERT_LOG, event)
        print(f"ALERT: {len(drift)} drift(s) found. See {ALERT_LOG}")
        sys.exit(1)
    print(f"OK: procs={len(procs)} env={len(envs)} profiles={len(profiles)} drift=0")
    sys.exit(0)

if __name__ == "__main__":
    main()
