fp = r"D:\AIOS\_agent-hub\v2\src\claude_adapter.py"
with open(fp, "r", encoding="utf-8") as f:
    src = f.read()
old = 'r = subprocess.run(\n            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",\n             "-EncodedCommand", encoded, "-args", prompt],\n            capture_output=True, timeout=300, text=True,\n        )'
new = 'r = subprocess.run(\n            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",\n             "-EncodedCommand", encoded, "-args", prompt],\n            capture_output=True, timeout=300,\n        )\n        try:\n            sout = r.stdout.decode("utf-8", errors="replace") if r.stdout else ""\n            serr = r.stderr.decode("utf-8", errors="replace") if r.stderr else ""\n            # PowerShell often emits GBK on Windows-cn hosts; try GBK if UTF-8 decode produced too many replacements\n            if r.stdout and sout.count("\ufffd") > 4:\n                try: sout = r.stdout.decode("gbk", errors="replace")\n                except Exception: pass\n        except Exception:\n            sout = ""; serr = ""'
if old in src:
    src = src.replace(old, new)
    with open(fp, "w", encoding="utf-8") as f:
        f.write(src)
    print("claude_adapter.py patched OK")
else:
    print("FAIL: pattern not found in adapter")
    # Show first 80 lines of adapter
    print(src[:2000])
