"""clear_pycaches.py — recursively remove all __pycache__ directories."""
import shutil
import os

count = 0
for root, dirs, files in os.walk(r'D:\AIOS'):
    # Skip .git and node_modules-like
    dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', '.venv', 'venv', '_backups_relinked_1790674911')]
    for d in list(dirs):
        if d == '__pycache__':
            path = os.path.join(root, d)
            try:
                shutil.rmtree(path)
                count += 1
            except Exception as e:
                print(f'failed: {path}: {e}')
print(f'removed {count} __pycache__ directories')