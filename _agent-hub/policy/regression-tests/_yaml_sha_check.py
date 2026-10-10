#!/usr/bin/env python3
import sys, os, hashlib
hub_root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
yaml_p = os.path.join(hub_root, "policy", "model-policy.v1.yaml")
sha_p = os.path.join(hub_root, "policy", "model-policy.v1.sha256")
if not os.path.exists(yaml_p) or not os.path.exists(sha_p):
    print("yaml or sha missing", file=sys.stderr); sys.exit(1)
actual = hashlib.sha256(open(yaml_p, "rb").read()).hexdigest().upper()
expected = None
for line in open(sha_p, encoding="utf-8"):
    if line.startswith("sha256:"):
        expected = line.split(":", 1)[1].strip().upper()
        break
if expected is None:
    print("no sha256 in manifest", file=sys.stderr); sys.exit(2)
if actual != expected:
    print(f"MISMATCH yaml={actual[:16]}.. manifest={expected[:16]}..", file=sys.stderr); sys.exit(3)
print("yaml sha matches manifest")
