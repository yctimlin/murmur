#!/usr/bin/env python3
"""Disk housekeeping (supervisor directive 10-21 14:00).

For runs that are finished (result.json) AND fully judged (score.json with 2 judgments),
delete only bulky scratch: codex-home/.tmp, peers/*/.work, node_modules, venvs, caches.
Keeps codex sessions, sqlite state (message board), logs, git repos (origin.git + peer .git),
and source trees, so forensics and reported numbers stay reproducible.
Usage: cleanup_ws.py [--dry]
"""
import json, os, shutil, subprocess, sys
from pathlib import Path

R4 = Path('/workspace/r4')
WS = R4 / 'lab/ws'
RES = R4 / 'lab/results'
JUD = R4 / 'judge'
BULK = {'node_modules', '.venv', 'venv', '.cache', 'target', '.pytest_cache', '.mypy_cache', '.work'}

dry = '--dry' in sys.argv


def judged(rid):
    f = JUD / rid.split('-')[0] / f'{rid}.score.json'
    if not f.exists():
        return False
    try:
        return len(json.loads(f.read_text()).get('judgments', [])) >= 2
    except Exception:
        return False


def size(p):
    out = subprocess.run(['du', '-sb', str(p)], capture_output=True, text=True).stdout
    return int(out.split()[0]) if out else 0


total = 0
for ws in sorted(WS.iterdir()):
    rid = ws.name
    if not (RES / rid / 'result.json').exists() or not judged(rid):
        continue
    targets = []
    if (ws / 'codex-home/.tmp').exists():
        targets.append(ws / 'codex-home/.tmp')
    peers = ws / 'work/peers'
    roots = [p for p in peers.iterdir()] if peers.exists() else []
    if (ws / 'work/solo').exists():
        roots.append(ws / 'work/solo')
    roots.append(ws / 'work')
    for root in roots:
        for dp, dns, _ in os.walk(root):
            for d in list(dns):
                if d in BULK:
                    targets.append(Path(dp) / d)
                    dns.remove(d)
                elif d in ('.git', 'origin.git', 'peers'):
                    dns.remove(d)
    seen = set()
    for t in targets:
        if t in seen or not t.exists():
            continue
        seen.add(t)
        s = size(t)
        total += s
        print(f'{rid}: {t.relative_to(ws)} {s/1e6:.0f} MB')
        if not dry:
            shutil.rmtree(t, ignore_errors=True)
print(f'{"would free" if dry else "freed"} {total/1e9:.2f} GB')
