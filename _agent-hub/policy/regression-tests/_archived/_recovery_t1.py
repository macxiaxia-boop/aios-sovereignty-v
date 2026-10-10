import os, hashlib, re, subprocess
CWD = r"D:\AIOS"
def run(cmd): return subprocess.run(cmd, cwd=CWD, capture_output=True, text=True, shell=False)

p = r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml"
sha_p = r"D:\AIOS\_agent-hub\policy\model-policy.v1.sha256"

raw = open(p, "rb").read()
print("input size:", len(raw), "sha:", hashlib.sha256(raw).hexdigest().upper())

# Normalize line endings
content = raw.replace(bytes([13, 10]), bytes([10]))
text = content.decode("utf-8")
lines = text.splitlines()
print("lines:", len(lines))

# Find the actual audit_log line (raw single-backslashes)
audit_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith("audit_log:") and "policy-changes.log" in line:
        audit_idx = i
        print("audit_log at line:", i + 1, ":", repr(line))
        break

if audit_idx is None:
    raise SystemExit("FAIL")

# Build new text: keep lines[0:audit_idx+1] + EX-001 replacement later
# Plan: insert "  exception_rules:" right after audit_log line, then a blank, then keep going
new_lines = []
for i, line in enumerate(lines):
    new_lines.append(line)
    if i == audit_idx:
        # After audit_log, insert exception_rules: and blank
        new_lines.append("")
        new_lines.append("  exception_rules:")
        new_lines.append("")

# Sanity check
print()
print("=== sample after insertion ===")
for i in range(audit_idx, min(len(new_lines), audit_idx + 12)):
    print(i + 1, ":", new_lines[i])

new_text = chr(10).join(new_lines)

# Verify yaml parses now
import yaml
try:
    pol = yaml.safe_load(new_text)
    print()
    print("Parse OK after insertion; EX count:", len(pol.get("model_policy", {}).get("exception_rules", [])))
except Exception as e:
    print("Parse FAIL:", e)
    raise SystemExit("abort")

# Add EX-011 before `adapter:` line
m = re.search(r"^adapter:", new_text, re.MULTILINE)
adapter_idx = m.start() if m else None
print()
print("adapter at:", adapter_idx)

ex_011 = []
ex_011.append("")
ex_011.append("    # EXT-E (R1346) 2026-10-10: dynamic CloudTech prefix discovery")
ex_011.append("    - id: EX-011")
ex_011.append("      type: path_globs")
ex_011.append('      description: "EXT-E dynamically discovered CloudTech installation prefixes"')
ex_011.append("      globs:")
ex_011.append('        - "D:/CloudTech-Portable/*"')
ex_011.append('        - "C:/CloudTech-Portable/*"')
ex_011.append('        - "D:/AIOS/cloudtech-saas/*"')
ex_011.append("      allowed_keywords:")
ex_011.append('        - "*"')
ex_011.append('      rationale: "Auto-discovered via scripts/discover_cloudtech.py. Complements EX-005 hardcoded list."')
ex_011.append('      discovery_source: "D:\\\\AIOS\\\\_agent-hub\\\\knowledge\\\\cloudtech_paths.json"')
ex_011_text = chr(10).join(ex_011) + chr(10)

final_text = new_text[:adapter_idx] + ex_011_text + new_text[adapter_idx:]
pol = yaml.safe_load(final_text)
print("Parse OK after EX-011; EX count:", len(pol.get("model_policy", {}).get("exception_rules", [])))

# Verify EX-001~010 byte-identical vs HEAD
def find_ex_blocks(text):
    blocks = {}
    cur_lines = text.splitlines()
    current = None
    start = None
    for i, line in enumerate(cur_lines):
        m = re.match(r"^\s*- id: (EX-\d+)", line)
        if m:
            if current:
                blocks[current] = chr(10).join(cur_lines[start:i])
            current = m.group(1)
            start = i
        elif current and line.strip() == "":
            blocks[current] = chr(10).join(cur_lines[start:i])
            current = None
    if current:
        blocks[current] = chr(10).join(cur_lines[start:])
    return blocks

wt_blocks = find_ex_blocks(final_text)
r = run(["git", "show", "HEAD:_agent-hub/policy/model-policy.v1.yaml"])
head_blocks = find_ex_blocks(r.stdout)
print()
print("EX byte-verification WT vs HEAD:")
all_ok = True
for k in head_blocks:
    same = wt_blocks.get(k) == head_blocks[k]
    status = "IDENTICAL" if same else "CHANGED"
    print(f"  {k}: {status}")
    if not same:
        all_ok = False
print("RED-LINE OK" if all_ok else "RED-LINE VIOLATED")
print()

# Write new yaml
with open(p, "w", encoding="utf-8") as f:
    f.write(final_text)
content_final = open(p, "rb").read()
new_h = hashlib.sha256(content_final).hexdigest().upper()
print("new yaml size:", len(content_final), "sha:", new_h)

# Rehash manifest additively
sha_text = open(sha_p, encoding="utf-8").read()
new_lines = []
for line in sha_text.splitlines():
    if line.startswith("sha256:"):
        new_lines.append("sha256:" + new_h)
    elif line.startswith("size_bytes:"):
        new_lines.append("size_bytes: " + str(len(content_final)))
    else:
        new_lines.append(line)
new_lines.append("updated_at: 2026-10-10T10:30+08:00")
new_lines.append("updated_reason: T1 yaml recover - exception_rules indent fix + EX-011 + sha sync")
new_lines.append("verification_status: ACTIVE")
new_sha_text = chr(10).join(new_lines) + chr(10)
with open(sha_p, "w", encoding="utf-8") as f:
    f.write(new_sha_text)
print("manifest updated")

# Verify adapters_registry
import sys
sys.path.insert(0, r"D:\AIOS\_agent-hub\policy")
import importlib
if "adapters_registry" in sys.modules:
    importlib.reload(sys.modules["adapters_registry"])
import adapters_registry as ar
print("verify:", ar._verify_sha256())
print("default:", ar.get_default_model())
