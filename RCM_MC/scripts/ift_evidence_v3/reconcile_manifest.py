"""Heal the pull manifest after concurrent pull processes.

Multiple pull scripts ran in parallel during the v3.4 pass; record() does a
read-modify-write on manifest.json, so a race can drop entries whose cached
artifact still exists on disk. This scan re-registers any orphaned artifact
(re-hashing the canonical payload) and reports what it repaired so the fix
itself is auditable on the Run_Log.
"""
import hashlib
import json
import os
import sys

SCRATCH = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(SCRATCH, 'ift_v3_cache')


def main():
    man_path = os.path.join(CACHE, 'manifest.json')
    man = json.load(open(man_path))
    repaired = []
    for fn in sorted(os.listdir(CACHE)):
        if not fn.endswith('.json') or fn == 'manifest.json':
            continue
        key = fn[:-5]
        if key in man:
            continue
        payload = open(os.path.join(CACHE, fn), 'rb').read()
        try:
            rows = json.loads(payload)
        except json.JSONDecodeError:
            continue
        man[key] = {
            'dataset': '(re-registered by reconcile_manifest after a '
                       'concurrent-write race; original pull meta lost, '
                       'payload hash is of the surviving canonical file)',
            'endpoint': '(see the pull script named by the key prefix)',
            'rows': len(rows) if isinstance(rows, list) else 1,
            'sha256_16': hashlib.sha256(payload).hexdigest()[:16],
            'reconciled': True,
        }
        repaired.append(key)
    if repaired:
        json.dump(man, open(man_path, 'w'), indent=1)
    print(f'manifest entries: {len(man)}; repaired: {len(repaired)}')
    for k in repaired:
        print('  re-registered:', k)
    return len(repaired)


if __name__ == '__main__':
    sys.exit(0 if main() >= 0 else 1)
