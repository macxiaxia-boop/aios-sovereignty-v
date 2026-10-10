import os, hashlib, subprocess, sys

SCRIPTS_DIR = r"D:\AIOS\_agent-hub\scripts"
KNOWLEDGE_DIR = r"D:\AIOS\_agent-hub\knowledge"

# Run discover_cloudtech to produce the JSON
r = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "discover_cloudtech.py")], capture_output=True, text=True, shell=False)
print("discover_cloudtech stdout:")
print(r.stdout)
print("stderr:", r.stderr[:200])
print("rc:", r.returncode)
if r.returncode == 0 and r.stdout:
    cloudtech_json_path = os.path.join(KNOWLEDGE_DIR, "cloudtech_paths.json")
    with open(cloudtech_json_path, "w", encoding="utf-8") as f:
        f.write(r.stdout)
    h = hashlib.sha256(open(cloudtech_json_path, "rb").read()).hexdigest().upper()
    print(f"wrote cloudtech_paths.json  {os.path.getsize(cloudtech_json_path)}B  sha256={h}")

# Run verify_ext_d
print()
print("=== verify_ext_d.py ===")
r = subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "verify_ext_d.py")], capture_output=True, text=True, shell=False)
print(r.stdout)
print("rc:", r.returncode)
if r.returncode != 0:
    print("stderr:", r.stderr[:500])

# Also confirm 4 adapter runtimes load correctly
print()
print("=== adapter runtime smokes ===")
for host in ["codex", "claude_code", "hermes", "openclaw"]:
    py = os.path.join(SCRIPTS_DIR, "_check.py")
    code = (
        "import sys, json" + chr(10)
        + "sys.path.insert(0, r\"D:\\AIOS\\_agent-hub\\policy\")" + chr(10)
        + "sys.path.insert(0, r\"D:\\AIOS\\_agent-hub\\policy\\adapters\")" + chr(10)
        + "import importlib.util" + chr(10)
        + "spec = importlib.util.spec_from_file_location(\"rt\", r\"D:\\AIOS\\_agent-hub\\policy\\adapters\\" + host + "_runtime.py\")" + chr(10)
        + "m = importlib.util.module_from_spec(spec)" + chr(10)
        + "spec.loader.exec_module(m)" + chr(10)
        + "print(json.dumps(m.healthz(), indent=2, default=str))" + chr(10)
    )
    with open(py, "w", encoding="utf-8") as f:
        f.write(code)
    r = subprocess.run([sys.executable, py], capture_output=True, text=True, shell=False)
    print(f"{host}: rc={r.returncode}  output={r.stdout.strip()[:80]}")
    if r.returncode != 0:
        print("  stderr:", r.stderr.strip()[:200])
os.unlink(py)
