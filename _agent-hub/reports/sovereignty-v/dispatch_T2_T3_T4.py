import sys, os
sys.path.insert(0, r'D:\AIOS\_agent-hub\v2')
from src.envelope import build_envelope, envelope_to_json

ENGINEERING_TID = '01a11c33-c813-7752-9e53-b7c332d00445'
PARENT_TID      = '01a11c23-ab7f-7253-9059-7aa7fc204c02'
SUPER_TID       = '01a11c30-6f6c-76c0-8c60-a55f3a43ff63'
AUTHORIZER      = 'user-2026-10-08T23:55'
AUDIT_DIR       = r'D:\AIOS\_agent-hub\reports\sovereignty-v\audit'
TASKS_DIR       = r'D:\AIOS\_agent-hub\reports\sovereignty-v\tasks'
INBOX           = r'D:\AIOS\_agent-hub\v2\messages\inbox'

TASKS = [
    {
        'task_card': 'T2',
        'title': 'cc-switch state + backup + startup hook scan',
        'artifacts': ['W3'],
        'output_path': f'{AUDIT_DIR}\\03-cc-switch-report.md',
        'T_done': f'{TASKS_DIR}\\T2.done',
        'powershell_commands': [
            'Get-Command cc-switch, ccswitch -ErrorAction SilentlyContinue | Select Name, Source, Version',
            'Get-ChildItem $env:USERPROFILE\\.cc-switch -Recurse -ErrorAction SilentlyContinue | Select FullName, Length, LastWriteTime | Select-Object -First 60',
            'Get-ChildItem $env:LOCALAPPDATA\\cc-switch,$env:APPDATA\\cc-switch -Recurse -ErrorAction SilentlyContinue | Select FullName, Length | Select-Object -First 60',
            'Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object { $_.TaskName -match "cc-switch|switch|provider" } | Select TaskName, State, TaskPath',
            'Get-ItemProperty "HKCU:\\Software\\cc-switch","HKLM:\\Software\\cc-switch" -ErrorAction SilentlyContinue',
        ],
    },
    {
        'task_card': 'T3',
        'title': 'OpenClaw agents/cron/gateway model field scan',
        'artifacts': ['W4'],
        'output_path': f'{AUDIT_DIR}\\04-openclaw-models.yaml',
        'T_done': f'{TASKS_DIR}\\T3.done',
        'powershell_commands': [
            'Get-Command openclaw -ErrorAction SilentlyContinue | Select Name, Source, Version',
            'Get-ChildItem "D:\\AIOS\\openclaw","D:\\AIOS\\_agent-hub\\openclaw","$env:USERPROFILE\\.openclaw" -Recurse -Include agents*.yaml,cron*.yaml,gateway*.yaml,config*.yaml -ErrorAction SilentlyContinue | Select FullName, Length | Select-Object -First 60',
            'Select-String -Path "D:\\AIOS\\openclaw\\**\\*.yaml","D:\\AIOS\\_agent-hub\\openclaw\\**\\*.yaml","$env:USERPROFILE\\.openclaw\\**\\*.yaml" -Pattern "model|provider|fallback|alias" -ErrorAction SilentlyContinue | Select-Object -First 100',
        ],
    },
    {
        'task_card': 'T4',
        'title': 'Hermes + other agents + Windows autorun chain scan',
        'artifacts': ['W5','W6'],
        'output_path': f'{AUDIT_DIR}\\05-hermes-others.md',
        'T_done': f'{TASKS_DIR}\\T4.done',
        'W6_output': f'{AUDIT_DIR}\\06-windows-autorun.md',
        'powershell_commands': [
            'Get-Command hermes -ErrorAction SilentlyContinue | Select Name, Source, Version',
            'Get-ChildItem "D:\\AIOS\\hermes","D:\\AIOS\\_agent-hub\\hermes","$env:USERPROFILE\\.hermes" -Recurse -Include *.yaml,*.toml,*.json -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "node_modules|__pycache__" } | Select FullName, Length | Select-Object -First 60',
            'Select-String -Path "D:\\AIOS\\hermes\\**\\*.yaml","D:\\AIOS\\_agent-hub\\hermes\\**\\*.yaml" -Pattern "model|provider|api" -ErrorAction SilentlyContinue | Select-Object -First 80',
            'Get-ScheduledTask | Where-Object { $_.TaskName -match "AIOS|Hermes|OpenClaw|Claude|Codex|hermes|openclaw|claude" } | Select TaskName, State, TaskPath',
            'Get-ChildItem $env:APPDATA\\Microsoft\\Windows\\Start Menu\\Programs\\Startup -ErrorAction SilentlyContinue | Select Name, Length, LastWriteTime',
            'Get-ItemProperty "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" -ErrorAction SilentlyContinue',
            'Get-ChildItem "D:\\AIOS\\_scheduled","D:\\AIOS\\_autostart" -ErrorAction SilentlyContinue | Select FullName, Length | Select-Object -First 30',
        ],
    },
]

results = []
for t in TASKS:
    payload = {
        'task_id': f'sovereignty-v:{t["task_card"]}',
        'engineering_thread_id': ENGINEERING_TID,
        'parent_thread_id': PARENT_TID,
        'supervisor_thread_id': SUPER_TID,
        'phase': 'SOVEREIGNTY-V',
        'mode': 'READ_ONLY_AUDIT',
        'task_card': t['task_card'],
        'title': t['title'],
        'artifacts': t['artifacts'],
        'output_paths': {
            **{f'{a}_output': t['output_path'] for a in t['artifacts'][:1]},
            **{f'W{i+5}_output': p for i, p in enumerate([t.get('W6_output', t['output_path'])])},
            'T_done': t['T_done'],
        },
        'powershell_commands': t['powershell_commands'],
        'red_lines': ['NO_MODIFY_ANY_FILE','NO_API_CALL','NO_SSH_READ','NO_DELETE','NO_REGISTRY_WRITE','NO_TASK_DELETE'],
        'authorizer': AUTHORIZER,
        'expected_runtime_seconds': 180,
    }
    # Fix output_paths mapping
    if t['task_card'] == 'T4':
        payload['output_paths'] = {
            'W5_output': f'{AUDIT_DIR}\\05-hermes-others.md',
            'W6_output': f'{AUDIT_DIR}\\06-windows-autorun.md',
            'T_done': t['T_done'],
        }
    else:
        payload['output_paths'] = {
            f'{t["artifacts"][0]}_output': t['output_path'],
            'T_done': t['T_done'],
        }
    env = build_envelope(
        sender='codex',
        recipient='claudecode',
        message_type='task',
        payload=payload,
        artifact_refs=t['artifacts'],
        ttl_ms=600000,
    )
    fname = f"{env['id']}__codex__claudecode__task.json"
    path = os.path.join(INBOX, fname)
    with open(path,'w',encoding='utf-8') as f:
        f.write(envelope_to_json(env))
    results.append((t['task_card'], path, env['id'], env['idempotency_key']))

for r in results:
    print('DISPATCH', r[0], '->', r[1])
print('TOTAL_DISPATCHED', len(results))