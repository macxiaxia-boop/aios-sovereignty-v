"""Patch adapter: combine EncodedCommand + -args properly"""
import sys
fp = r"D:\AIOS\_agent-hub\v2\src\claude_adapter.py"
with open(fp, "r", encoding="utf-8") as f:
    src = f.read()

old = '''    ps_cmd = (
        f"& 'D:\\\\npm-global\\\\claude.ps1' -p $args[0] --add-dir '{workdir}'"
    )
    encoded = base64.b64encode(ps_cmd.encode("utf-16le")).decode("ascii")
    start = time.time()
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-EncodedCommand", encoded, "-args", prompt],
            capture_output=True, timeout=300,
        )'''
new = '''    # Build PS script that includes both the invocation AND the prompt as a
    # single script block, so -EncodedCommand does not collide with -args.
    ps_script = (
        "& 'D:\\\\npm-global\\\\claude.ps1' -p "
        + "'" + prompt.replace("'", "''") + "'"
        + " --add-dir '" + workdir + "'"
    )
    encoded = base64.b64encode(ps_script.encode("utf-16le")).decode("ascii")
    start = time.time()
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-EncodedCommand", encoded],
            capture_output=True, timeout=300,
        )'''
if old in src:
    src = src.replace(old, new)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK patched claude_adapter.py")
else:
    print("FAIL: pattern not found")
    sys.exit(1)