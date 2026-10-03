# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.abspath('app'))
from tools.approval import _match_user_deny_rule

test_cmds = [
    'rm -rf /',
    'del /f /q C:\\some\\file',
    'Remove-Item -Recurse -Force C:\\test',
    'format C: /fs:NTFS',
    'git clean -fdx',
    'git reset --hard HEAD~1',
    'shred -u secret.txt',
    'drop table users',
    'git status',
    'python main.py',
    'npm run build'
]

print("=" * 70)
print("  VERIFYING HARDLINE DELETION / WIPE PROTECTION IN HERMES")
print("=" * 70)
for cmd in test_cmds:
    matched = _match_user_deny_rule(cmd)
    if matched:
        print(f"  [BLOCKED] \"{cmd}\" -> Rule: \"{matched}\"")
    else:
        print(f"  [ALLOWED] \"{cmd}\"")
print("=" * 70)
