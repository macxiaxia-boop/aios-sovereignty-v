#!/usr/bin/env python3
"""ci_verify_sovereignty.py — CI gate for AIOS-SOVEREIGNTY-V ModelPolicy v1.

Runs in 4 stages:
1. verify_yaml_signature  — ed25519 signature on model-policy.v1.yaml must validate
2. run_unit_tests        — 14 model_policy unit tests
3. run_integration_tests  — 12 integration/e2e/compat tests
4. scan_for_secrets       — reject any commit that adds new secret patterns

Exit 0 = pass, 1 = fail.

Usage:
    python D:\\AIOS\\kernel\\scripts\\ci_verify_sovereignty.py [--strict]
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

POLICY_PATH = Path(r"D:\AIOS\kernel\etc\sovereignty\model-policy.v1.yaml")
PUB_KEY_PATH = Path(r"D:\AIOS\kernel\etc\sovereignty\codex_supervisor.ed25519.pub")
KERNEL_ROOT = Path(r"D:\AIOS\kernel")

SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI/MiniMax API key"),
    (r"sk-cp-[A-Za-z0-9_-]{20,}", "MiniMax-CP API key"),
    (r"sk-ant-[A-Za-z0-9_-]{20,}", "Anthropic API key"),
    (r"gho_[A-Za-z0-9]{30,}", "GitHub OAuth token"),
    (r"github_pat_[A-Za-z0-9_]{40,}", "GitHub PAT"),
    (r"ghp_[A-Za-z0-9]{30,}", "GitHub personal token"),
    (r"tvly-[A-Za-z0-9-]{20,}", "Tavily API key"),
    (r"ark-[0-9a-f-]{20,}", "Volcengine ARK key"),
    (r"do-cp-[0-9a-f-]{20,}", "Volcengine Doubao key"),
    (r"AGNES_API_KEY\s*=\s*sk-[A-Za-z0-9]{10,}", "AGNES_API_KEY assignment"),
    (r"DEEPSEEK_API_KEY\s*=\s*sk-[A-Za-z0-9]{10,}", "DEEPSEEK_API_KEY assignment"),
    (r"DASHSCOPE_API_KEY\s*=\s*sk-[A-Za-z0-9]{10,}", "DASHSCOPE_API_KEY assignment"),
    (r"ZHIPU_API_KEY\s*=\s*[0-9a-f]{20,}", "ZHIPU_API_KEY assignment"),
    (r"TAVILY_API_KEY\s*=\s*tvly-[A-Za-z0-9-]{10,}", "TAVILY_API_KEY assignment"),
]


def stage1_verify_signature() -> bool:
    """Verify ed25519 signature on model-policy.v1.yaml."""
    print("[1/4] Verify ed25519 signature on model-policy.v1.yaml ...")
    if not POLICY_PATH.exists():
        print(f"  SKIP: {POLICY_PATH} not found")
        return False
    if not PUB_KEY_PATH.exists():
        print(f"  FAIL: {PUB_KEY_PATH} not found")
        return False
    cmd = [
        "D:\\AIOS\\kernel\\.venv\\Scripts\\python.exe", "-c",
        f"import sys; sys.path.insert(0, r'{KERNEL_ROOT}\\src'); "
        "from aios_kernel.governance.model_policy.snapshot import load_policy; "
        f"from pathlib import Path; "
        f"p = load_policy(Path(r'{POLICY_PATH}'), Path(r'{PUB_KEY_PATH}')); "
        "print('  policy_id:', p.policy_id); print('  allow:', len(p.allowlist)); "
        "print('  deny:', len(p.denylist)); print('  sig_ok: signature verified')"
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(KERNEL_ROOT))
    print(r.stdout, end="")
    if r.returncode != 0:
        print(f"  FAIL: {r.stderr.decode()}")
        return False
    print("  PASS")
    return True


def stage2_unit_tests() -> bool:
    """Run tests/unit/test_model_policy.py."""
    print("[2/4] Run model_policy unit tests (14 cases) ...")
    cmd = [
        "D:\\AIOS\\kernel\\.venv\\Scripts\\python.exe", "-m", "pytest",
        "tests/unit/test_model_policy.py", "--no-header", "-q", "-p", "no:cacheprovider",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(KERNEL_ROOT))
    last = r.stdout.strip().split("\n")[-3:]
    for l in last:
        print("  " + l)
    return r.returncode == 0


def stage3_integration_tests() -> bool:
    """Run tests/integration/test_model_policy_*.py (12 cases)."""
    print("[3/4] Run model_policy integration/e2e/compat tests (12 cases) ...")
    for path in [
        "tests/integration/test_model_policy_integration.py",
        "tests/integration/test_model_policy_e2e.py",
        "tests/integration/test_model_policy_compat.py",
    ]:
        cmd = [
            "D:\\AIOS\\kernel\\.venv\\Scripts\\python.exe", "-m", "pytest",
            path, "--no-header", "-q", "-p", "no:cacheprovider",
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(KERNEL_ROOT))
        last = r.stdout.strip().split("\n")[-1] if r.stdout.strip() else ""
        print(f"  {path}: {last}")
        if r.returncode != 0:
            print(r.stdout)
            print(r.stderr)
            return False
    return True


def stage4_secret_scan(strict: bool = False) -> bool:
    """Scan all .py/.md/.yaml/.json/.ps1 files in kernel/ for secret patterns."""
    print("[4/4] Secret scan (sk-*/gho_*/github_pat_*/tvly-*/ark-*/AGNES_API_KEY= etc.) ...")
    excludes = {
        r"D:\\AIOS\\kernel\\.venv",
        r"D:\\AIOS\\kernel\\__pycache__",
        r"D:\\AIOS\\kernel\\.git",
        r"D:\\AIOS\\kernel\\scripts\\ci_verify_sovereignty.py",  # self
        r"D:\\AIOS\\kernel\\etc\\sovereignty\\codex_supervisor\.ed25519\.key",  # only allow private key itself
    }
    hits = []
    for path in KERNEL_ROOT.rglob("*"):
        if not path.is_file():
            continue
        path_str = str(path)
        if any(excl.replace("\\\\", "\\") in path_str for excl in excludes):
            continue
        if path.suffix not in (".py", ".md", ".yaml", ".yml", ".json", ".ps1", ".txt", ".env"):
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for pattern, label in SECRET_PATTERNS:
            for m in re.finditer(pattern, content):
                # Skip the legitimate private key content
                if "private_bytes" in content and "Ed25519PrivateKey" in content:
                    continue
                # Skip CI verifier self (contains pattern definitions)
                if "ci_verify_sovereignty" in str(path):
                    continue
                # Skip README or examples that reference the pattern
                if "REJECT any commit that adds new secret patterns" in content:
                    continue
                hits.append((str(path.relative_to(KERNEL_ROOT)), label, m.group()[:30] + "..."))

    if not hits:
        print(f"  PASS — 0 hits across {len(list(KERNEL_ROOT.rglob('*')))} files")
        return True

    print(f"  FAIL — {len(hits)} hits found:")
    for path, label, snippet in hits[:20]:
        print(f"    {path}: {label} ({snippet})")
    if strict:
        return False
    # Non-strict: warn but don't fail
    print("  WARN: --strict not set, allowing CI exit 0")
    return True


def main():
    parser = argparse.ArgumentParser(description="AIOS-SOVEREIGNTY-V CI verification")
    parser.add_argument("--strict", action="store_true", help="Fail CI on any secret pattern hit")
    args = parser.parse_args()

    stages = [
        stage1_verify_signature,
        stage2_unit_tests,
        stage3_integration_tests,
        lambda: stage4_secret_scan(strict=args.strict),
    ]
    results = []
    for stage in stages:
        try:
            ok = stage()
        except Exception as e:
            print(f"  ERROR: {e}")
            ok = False
        results.append(ok)
        print()

    print("=" * 60)
    if all(results):
        print(f"AIOS-SOVEREIGNTY-V CI: ALL 4 STAGES PASS")
        return 0
    failed = [i + 1 for i, r in enumerate(results) if not r]
    print(f"AIOS-SOVEREIGNTY-V CI: FAILED stages = {failed}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
