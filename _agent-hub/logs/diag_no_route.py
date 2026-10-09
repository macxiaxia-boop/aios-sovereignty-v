import sys, os, tempfile, json
from pathlib import Path

# Add paths
sys.path.insert(0, r'D:\AIOS\_agent-hub')
sys.path.insert(0, r'D:\AIOS\_agent-hub\v2\src')

# Set up tmp v2 root BEFORE importing v2_consumer
tmpdir = Path(tempfile.mkdtemp(prefix='r4_diag_'))
os.environ['AIOS_V2_ROOT'] = str(tmpdir)
print('tmpdir=', tmpdir)

import v2_consumer
from v2_consumer import CAPABILITIES, route_capability, enqueue, dispatch_envelope

# Save and pop
saved = CAPABILITIES['codex'].copy()
CAPABILITIES['codex'].pop('message', None)
try:
    rc = route_capability('codex', 'message')
    print('route_capability after pop:', rc)
    
    from src.envelope import build_envelope
    env = build_envelope('a', 'codex', 'message', {'__r286_no_route__': True})
    
    res = enqueue(env)
    print('enqueue result:', res)
    
    target = tmpdir / 'messages' / 'inbox' / 'codex' / Path(res['file']).name
    print('target exists:', target.exists())
    
    out = dispatch_envelope(target, env)
    print('out ok:', out.get('ok'))
    for s in out.get('steps', []):
        print('  step:', s)
finally:
    CAPABILITIES['codex'].update(saved)
