#!/usr/bin/env python3
"""Model Policy Reconciler v7 — W15"""
import argparse, json, time, subprocess, hashlib, sys, os, fnmatch
from pathlib import Path

POLICY_PATH_DEFAULT = r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml"
SHA256_PATH_DEFAULT = r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256"
DRIFT_LOG = r"D:\AIOS\_agent-hub\audit\drift-events.log"
ALERT_LOG = r"D:\AIOS\_agent-hub\policy\reconciler\alerts.jsonl"
LOCK_FILE = r"D:\AIOS\_agent-hub\policy\reconciler\.lock"

PROHIBITED_KEYWORDS_HARDCODED = [
    "deepseek", "gpt-4", "gpt-3.5", "claude-3", "claude-sonnet",
    "gemini", "llama-3", "mistral", "anthropic.com", "googleapis",
    "gpt-5-codex", "doubao", "agnes", "gpt-image", "codex-openai", "codex_desktop",
    "dashscope",
]

SCAN_TARGETS = [
    "~/.codex", "~/.claude", "~/.openclaw", "~/.hermes",
    "D:/AIOS/_agent-hub", "D:/CloudTech-Portable",
]

EXCLUDED_PATH_TAGS = {
    # generic
    "__pycache__", ".git", ".venv", "venv", "node_modules", ".cache",
    ".uv-cache", "uv-cache", ".tox", ".eggs", "dist", "build",
    ".next", ".nuxt", ".output", "coverage", ".nyc_output",
    # CloudTech
    "_backups", "backups", "legacy",
    "dist-v45", "dist-v4", "dist-v3",
    "design", "research", "references",
    "shadcn-ui", "plugins-clone",
    # Codex / Claude / Hermes / OpenClaw user
    "attachments", "computer-use",
    "hermes-agent",  # 1018 FP
    "sessions", "skills",  # .hermes/sessions .claude/skills etc
    "cache", "npm", "projects", "presets", "scripts",  # .openclaw/* .claude/*
    "state", "state-snapshots", "ollama",  # .claude/state etc
    "etc", "logs", "provider_models_cache",  # misc
    "_backup", "_archive",  # all backup/archive patterns
    "embedding", "_scripts",
    # policy 自己
    "model-policy.v1", "codex_adapter.py",
    "cloudtech_pre_tool_use_hook.py", "reconciler.py",
    "adapter-contract.md", "adapter-spec.v1.md",
    "acceptance_phase_i", "audit_gap_check", "W14_", "spec",
}

MAX_FILES_PER_TARGET = 3000

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

def safe_decode(b):
    for enc in ("utf-8", "cp1252", "gbk", "latin-1"):
        try: return b.decode(enc)
        except (UnicodeDecodeError, LookupError): continue
    return b.decode("latin-1", errors="replace")

def scan_processes():
    out_list = []
    try:
        r = subprocess.run(["wmic", "process", "get", "Name,ProcessId,CommandLine", "/FORMAT:CSV"], capture_output=True, timeout=15)
        raw = safe_decode(r.stdout)
        for line in raw.splitlines()[1:]:
            parts = line.split(",", 2)
            if len(parts) >= 3:
                out_list.append({"name": parts[0], "pid": parts[1], "cmd": parts[2]})
    except Exception as e:
        out_list.append({"error": str(e)})
    return out_list

def scan_env():
    out = []
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command", "Get-ChildItem env: | Where-Object { $_.Name -match 'OPENAI|ANTHROPIC|MiniMax|MODEL|API|OLLAMA|DEEPSEEK|QWEN' } | ConvertTo-Json -Compress"], capture_output=True, timeout=15)
        if r.stdout.strip():
            out = json.loads(safe_decode(r.stdout))
    except Exception as e:
        out = [{"error": str(e)}]
    return out

def scan_profile_files():
    candidates = []
    all_keywords = PROHIBITED_KEYWORDS_HARDCODED + ["openai.com", "qwen", "ollama", "chatgpt"]
    include_exts = {".py", ".js", ".ts", ".mjs", ".cjs", ".jsx", ".tsx", ".yaml", ".yml", ".json"}
    for base in SCAN_TARGETS:
        scan_count = 0
        p = Path(os.path.expanduser(base))
        if not p.exists(): continue
        is_cloudtech = "CloudTech" in str(p)
        target_label = "cloudtech" if is_cloudtech else "user"
        for f in p.rglob("*"):
            if scan_count >= MAX_FILES_PER_TARGET: break
            if not f.is_file(): continue
            if f.suffix.lower() not in include_exts: continue
            if any(tag in f.parts for tag in EXCLUDED_PATH_TAGS): continue
            if any(x in f.name for x in [".bak.", ".old", "config.backup.", ".disabled", ".pyc"]): continue
            try:
                if f.stat().st_size > 1_000_000: continue
                scan_count += 1
                txt = safe_decode(f.read_bytes())
                hits = []
                for kw in all_keywords:
                    if kw in txt.lower(): hits.append(kw)
                if hits:
                    candidates.append({"path": str(f), "size": f.stat().st_size, "hits": hits, "target": target_label})
            except Exception: pass
    return candidates

def check_compliance(policy, procs, envs, profile_files, path_globs_with_kw, env_vars):
    drift = []
    for p in procs:
        cmd = (p.get("cmd") or "").lower()
        name = (p.get("name") or "").lower()
        if not any(t in name for t in ("codex", "claude", "openclaw", "hermes", "node", "python")): continue
        for kw in PROHIBITED_KEYWORDS_HARDCODED:
            if kw in cmd:
                drift.append({"type": "L2", "source": "proc", "pid": p.get("pid"), "name": name, "reason": f"prohibited_keyword:{kw}", "cmd": cmd[:200]})
                break
    for e in envs:
        name = (e.get("Name") or "").upper()
        if is_env_exempt(name, env_vars): continue
        val = (e.get("Value") or "")
        all_kw = PROHIBITED_KEYWORDS_HARDCODED + ["openai.com", "qwen", "ollama", "chatgpt"]
        if any(p in val for p in all_kw):
            if "MiniMax" not in val and "minimax" not in val:
                drift.append({"type": "L1", "source": "env", "name": name, "reason": "non_MiniMax_endpoint", "value_prefix": val[:80]})
    for pf in profile_files:
        path = pf["path"]
        for kw in pf["hits"]:
            if is_path_exempt(path, path_globs_with_kw, kw): continue
            drift.append({"type": "L1", "source": "profile", "path": path, "reason": f"prohibited_profile:[{kw}]", "target": pf.get("target", "user")})
    return drift

def append_jsonl(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")

def acquire_lock():
    try:
        if os.path.exists(LOCK_FILE):
            age = time.time() - os.path.getmtime(LOCK_FILE)
            if age < 300: return None
        Path(LOCK_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(LOCK_FILE, "w") as f: f.write(str(os.getpid()))
        return True
    except Exception: return True

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=POLICY_PATH_DEFAULT)
    ap.add_argument("--sha256-manifest", default=SHA256_PATH_DEFAULT)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()
    if acquire_lock() is None:
        print('SKIP: another reconciler instance running', file=sys.stderr); sys.exit(0)
    policy = load_yaml(args.policy)
    if not policy: print("FATAL: cannot load policy", file=sys.stderr); sys.exit(2)
    ok, info = verify_sha256(args.policy, args.sha256_manifest)
    if not ok: print(f"FATAL: sha256 mismatch ({info})", file=sys.stderr); sys.exit(3)
    path_globs, env_vars = parse_exception_rules(policy)
    procs = scan_processes()
    envs = scan_env()
    profiles = scan_profile_files()
    drift = check_compliance(policy, procs, envs, profiles, path_globs, env_vars)
    by_target = {}
    for d in drift:
        t = d.get("target", "user"); by_target[t] = by_target.get(t, 0) + 1
    profile_by_target = {}
    for p in profiles:
        t = p.get("target", "user"); profile_by_target[t] = profile_by_target.get(t, 0) + 1
    event = {"ts": time.time(), "policy_id": policy.get("policy_id"), "policy_version": policy.get("policy_version"),
             "proc_count": len(procs), "env_count": len(envs), "profile_count": len(profiles),
             "profile_by_target": profile_by_target,
             "exception_globs": len(path_globs), "exception_envs": sorted(env_vars),
             "scan_targets": SCAN_TARGETS,
             "drift_count": len(drift), "drift_by_target": by_target, "drift": drift}
    append_jsonl(DRIFT_LOG, event)
    if drift:
        append_jsonl(ALERT_LOG, event)
        print(f"ALERT: {len(drift)} drift(s) found. See {ALERT_LOG}"); sys.exit(1)
    print(f"OK: procs={len(procs)} env={len(envs)} profiles={len(profiles)} drift=0 (targets={len(SCAN_TARGETS)})")
    sys.exit(0)

if __name__ == "__main__":
    main()
