import sys, os
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from v2_consumer import CAPABILITIES, dispatch_envelope
from message_queue import enqueue
from envelope import build_envelope
from paths import INBOX
from pathlib import Path
saved = CAPABILITIES['codex'].copy()
CAPABILITIES['codex'].pop('message', None)
try:
    env = build_envelope('a', 'codex', 'message', {'__r286_no_route__': True})
    res = enqueue(env)
    target = INBOX / Path(res['file']).name
    out = dispatch_envelope(target, env)
    print('out ok:', out.get('ok'))
    print('reason for each step:')
    for s in out.get('steps', []):
        print('  step=', s.get('step'), 'reason=', s.get('reason', '')[:200])
finally:
    CAPABILITIES['codex'].update(saved)
