import os, hashlib, re, subprocess
CWD = r"D:\AIOS"
def run(cmd): return subprocess.run(cmd, cwd=CWD, capture_output=True, text=True, shell=False)

p = r"D:\AIOS\_agent-hub\policy\model-policy.v1.yaml"
content = open(p, "rb").read().replace(bytes([13,10]), bytes([10]))
text_norm = content.decode("utf-8")

def find_ex_blocks(text):
    blocks = {}
    lines = text.splitlines()
    current = None
    start = None
    for i, line in enumerate(lines):
        m = re.match(r"^\s*- id: (EX-\d+)", line)
        if m:
            if current:
                blocks[current] = chr(10).join(lines[start:i])
            current = m.group(1)
            start = i
        elif current and line.strip() == "":
            blocks[current] = chr(10).join(lines[start:i])
            current = None
    if current:
        blocks[current] = chr(10).join(lines[start:])
    return blocks

wt_blocks = find_ex_blocks(text_norm)
print("WT EX blocks:", len(wt_blocks))
for k in wt_blocks:
    print("  " + k + ": " + str(len(wt_blocks[k])) + "B")

r = run(["git", "show", "HEAD:_agent-hub/policy/model-policy.v1.yaml"])
head_blocks = find_ex_blocks(r.stdout)
print("HEAD EX blocks:", len(head_blocks))
for k in head_blocks:
    same = wt_blocks.get(k) == head_blocks[k]
    status = "IDENTICAL" if same else "DIFFERS"
    print("  " + k + ": " + status + " (" + str(len(head_blocks[k])) + "B)")

import yaml
try:
    pol = yaml.safe_load(text_norm)
    print("Parse OK")
    print("  Version:", pol.get("policy_version"))
    print("  Status:", pol.get("verification_status"))
    print("  EX rules:", len(pol.get("model_policy", {}).get("exception_rules", [])))
    print("  Last modified:", pol.get("last_modified"))
except Exception as e:
    print("PARSE FAIL:", e)

print("YAML sha256:", hashlib.sha256(open(p, "rb").read()).hexdigest().upper())
