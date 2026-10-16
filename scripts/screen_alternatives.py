#!/usr/bin/env python3
"""Credential-free mechanism screen with real setup/run, helpers and Git.

Usage: python scripts/screen_alternatives.py OUTPUT_DIRECTORY
Fake Codex drives two deterministic candidates. This is not live adoption evidence.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CHECK = "from spans import compress; assert compress([])==[]; assert compress([3,1,2,2,8,9])==[(1,3),(8,9)]; assert compress([-2,-1,0,5])==[(-2,0),(5,5)]"
GOOD = '''def compress(values):
    result = []
    for value in sorted(set(values)):
        if result and value == result[-1][1] + 1:
            result[-1] = (result[-1][0], value)
        else:
            result.append((value, value))
    return result
'''
BAD = '''def compress(values):
    return [(min(values), max(values))] if values else []
'''


def call(argv, cwd=None, env=None):
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise RuntimeError(f'{argv}: {result.stderr or result.stdout}')
    return result.stdout


def worker(args):
    if args[:2] == ['debug', 'models']:
        return subprocess.call([sys.executable, str(ROOT / 'tests' / 'fake_codex.py'), *args])
    ws = Path(args[args.index('-C') + 1]).parent
    clones = [ws / 'work' / 'peers' / peer for peer in ('a1', 'a2')]
    helper = clones[0] / '.murmur' / 'alternatives'
    call([str(helper), 'open', 'spans', '--checks', json.dumps([[sys.executable, '-c', CHECK]]), '--timeout', '5'])
    for clone, content in zip(clones, (BAD, GOOD)):
        (clone / 'spans.py').write_text(content)
        call(['git', 'add', 'spans.py'], clone)
        call(['git', 'commit', '-qm', 'Independent span candidate'], clone)
        call(['git', 'push', '-q', 'origin', f'HEAD:draft/{clone.name}'], clone)
        call([str(clone / '.murmur' / 'alternatives'), 'submit', 'spans', f'draft/{clone.name}'])
    result = json.loads(call([str(helper), 'evaluate', 'spans']))
    assert result['status'] == 'promoted'
    assert [r['passed'] for r in result['results']] == [False, True]
    (ws / 'logs' / 'fixture-evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    Path(args[args.index('-o') + 1]).write_text('scripted alternatives screen complete\n')
    print(json.dumps({'type': 'event_msg', 'payload': {'type': 'task_complete'}}))
    return 0


def screen(out):
    out = out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='alternatives-input-') as tmp:
        source = Path(tmp) / 'input'
        source.mkdir()
        (source / 'README.md').write_text('Integer-span compression screen.\n')
        brief = out / 'brief.md'
        brief.write_text('Implement maximal contiguous spans of unsorted unique integers, including empty and negative inputs.\n')
        fake_bin = out / 'bin'
        fake_bin.mkdir()
        executable = fake_bin / 'codex'
        executable.write_text('#!/bin/sh\nexec ' + shlex.join([sys.executable, str(Path(__file__).resolve()), '--fixture-worker']) + ' "$@"\n')
        executable.chmod(0o755)
        env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ['PATH'],
                   PYTHONPATH=str(ROOT / 'src'), MURMUR_ALTERNATIVES='1')
        cmd = [sys.executable, '-m', 'murmur']
        call([*cmd, 'setup', str(brief), '--repo', str(source), '--peers', '2', '--cap', '25m',
              '--into', str(out / 'runs'), '--id', 'screen'], env=env)
        ws = out / 'runs' / 'screen'
        call([*cmd, 'run', str(ws)], env=env)
        run = json.loads((ws / 'logs' / 'run.json').read_text())
        evidence = json.loads((ws / 'logs' / 'fixture-evidence.json').read_text())
        state = ws / 'work' / 'alternatives' / 'trials.sqlite3'
        with sqlite3.connect(state) as db:
            events = [{'kind': kind, 'detail': json.loads(detail)} for kind, detail in db.execute('SELECT kind,detail FROM events ORDER BY sequence')]
        record = {'kind': 'scripted-real-git-screen', 'live_model': False, 'model_calls': 0,
                  'model_tokens': 0, 'seconds_including_setup': round(time.monotonic() - started, 4),
                  'workspace': str(ws), 'run': run, 'evidence': evidence, 'events': events}
        (out / 'screen.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps({'screen': str(out / 'screen.json'), 'seconds': record['seconds_including_setup'],
                          'events': len(events), 'exit_code': run['exit_code'], 'winner': evidence['winner']}))


if __name__ == '__main__':
    if sys.argv[1:2] == ['--fixture-worker']:
        raise SystemExit(worker(sys.argv[2:]))
    screen(Path(sys.argv[1]))
