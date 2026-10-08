import sys
sys.path.insert(0, r'D:\AIOS\_agent-hub\v2')
from src.envelope import build_envelope, envelope_to_json

env = build_envelope(
    sender='codex',
    recipient='claudecode',
    message_type='task',
    payload={
        'task_id': 'sovereignty-v:T1',
        'engineering_thread_id': '01a11c33-c813-7752-9e53-b7c332d00445',
        'parent_thread_id': '01a11c23-ab7f-7253-9059-7aa7fc204c02',
        'supervisor_thread_id': '01a11c30-6f6c-76c0-8c60-a55f3a43ff63',
        'phase': 'SOVEREIGNTY-V',
        'mode': 'READ_ONLY_AUDIT',
        'task_card': 'T1',
        'title': 'Codex/Claude Code config + env var scan',
        'artifacts': ['W1','W2'],
        'output_paths': {
            'W1_config_snapshot': r'D:\AIOS\_agent-hub\reports\sovereignty-v\audit\01-config-snapshot.json',
            'W2_env_snapshot':    r'D:\AIOS\_agent-hub\reports\sovereignty-v\audit\02-env-snapshot.txt',
            'T1_done':            r'D:\AIOS\_agent-hub\reports\sovereignty-v\tasks\T1.done',
        },
        'powershell_commands': [
            'Get-ChildItem $env:USERPROFILE\\.codex -Recurse -Include *.toml,*.json -ErrorAction SilentlyContinue | Select FullName, Length, LastWriteTime',
            'Get-ChildItem $env:USERPROFILE\\.claude -Recurse -Include *.toml,*.json,*.yaml -ErrorAction SilentlyContinue | Select FullName, Length, LastWriteTime',
            'Get-ChildItem env: | Where-Object { $_.Name -match "OPENAI|ANTHROPIC|MiniMax|MODEL|API" } | Select Name, Value',
            'Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match "codex|claude" } | Select Id, ProcessName, Path',
            'Get-ChildItem "D:\\AIOS" -Recurse -Depth 2 -Include *.toml,settings*.json -ErrorAction SilentlyContinue | Where-Object { $_.FullName -notmatch "_archived|_backup|_patches|_backups|node_modules" } | Select FullName, Length | Select-Object -First 80',
        ],
        'red_lines': ['NO_MODIFY_ANY_FILE','NO_API_CALL','NO_SSH_READ','NO_DELETE'],
        'authorizer': 'user-2026-10-08T23:55',
        'expected_runtime_seconds': 120,
    },
    artifact_refs=['W1','W2'],
    ttl_ms=600000,
)
fname = f"{env['id']}__codex__claudecode__task.json"
path = rf'D:\AIOS\_agent-hub\v2\messages\inbox\{fname}'
with open(path,'w',encoding='utf-8') as f:
    f.write(envelope_to_json(env))
print('WROTE', path)
print('id=', env['id'])
print('idem=', env['idempotency_key'])