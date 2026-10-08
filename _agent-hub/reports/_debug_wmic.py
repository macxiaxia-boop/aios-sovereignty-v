import subprocess, re
out_bytes = subprocess.check_output(
    ['wmic', 'process', 'where', "name='python.exe'", 'get', 'ProcessId,CommandLine', '/FORMAT:CSV'],
)
# wmic default encoding is CP1252 (or system locale); try utf-8 with replace
text = out_bytes.decode('utf-8', errors='replace')
print('=== last 800 chars ===')
print(repr(text[-800:]))
print()
print('=== per line ===')
for i, line in enumerate(text.splitlines()):
    print(i, repr(line))

print()
print('=== try find start_consumer_real ===')
pids = []
# unwrap continuation lines ending with " -"
raw = text.splitlines()
buf = ""
joined = []
for line in raw:
    if line.rstrip().endswith(' -'):
        buf += line.rstrip()[:-2]
    else:
        buf += line
        if buf.strip():
            joined.append(buf)
        buf = ""
for line in joined:
    print('JOINED:', repr(line[-120:]))
    if 'start_consumer_real' in line:
        m = re.search(r',(\d+)\s*$', line.strip())
        if m:
            pids.append(int(m.group(1)))
print('PIDS:', pids)