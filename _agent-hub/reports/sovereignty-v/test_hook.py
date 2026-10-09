import json, sys
cases = [
    ('{"tool":"write","file_path":"D:\\test.py","content":"import openai\\nmodel=gpt-4"}', "prohibited"),
    ('{"tool":"write","file_path":"D:\\test.py","content":"import minimax\\nmodel=MiniMax-M3"}', "minimax ok"),
    ('{"tool":"write","file_path":"D:\\backups\\test.py","content":"import openai"}', "exempt"),
    ('{"tool":"bash","command":"ls"}', "non-write"),
    ('{"tool":"Write","file_path":"D:\\code.py","content":"openai_client"}', "prohibited upper"),
    ('{"tool":"write","file_path":"D:\\src\\cloudtech\\live_migration\\provider_router.py","content":"import openai"}', "router exempt"),
]
for raw, label in cases:
    request = json.loads(raw)
    print(f"  [{label}] tool={request.get('tool')!r:>20}  content={request.get('content', '')[:30]!r}")