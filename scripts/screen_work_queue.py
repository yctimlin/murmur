#!/usr/bin/env python3
"""Deterministic end-to-end queue screen; fake Codex, real helper/Git/task handoff.

Run from this checkout: python scripts/screen_work_queue.py .work/queue-fixture
Does not claim live agent adoption or performance. Emits evidence.json and a normal run.json.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def run(argv, *, cwd=None, env=None):
    p = subprocess.run([str(v) for v in argv], cwd=cwd, env=env, capture_output=True, text=True, check=True)
    return p.stdout.strip()


def screen(output: Path):
    started = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    fakebin = output / 'bin'
    fakebin.mkdir()
    (fakebin / 'codex').symlink_to(ROOT / 'tests/fake_codex.py')
    env = {**os.environ, 'PATH': str(fakebin) + os.pathsep + os.environ['PATH'],
           'PYTHONPATH': str(ROOT / 'src')}
    source = output / 'input'
    source.mkdir()
    (source / 'README.md').write_text('Invented scripted task: publish a text file and its byte manifest.\n')
    run(['git', 'init', '-q', '-b', 'main', source])
    run(['git', 'add', '.'], cwd=source)
    run(['git', '-c', 'user.name=screen', '-c', 'user.email=screen@example.com',
         'commit', '-qm', 'screen seed'], cwd=source)
    brief = output / 'brief.md'
    brief.write_text('Create payload.txt and a manifest containing its byte count.\n')
    config = output / 'screen.toml'
    config.write_text('work_stealing = true\n')
    ws = Path(run([sys.executable, '-m', 'murmur', 'setup', brief, '--repo', source,
                   '--config', config, '--peers', '2', '--cap', '25m', '--into', output / 'runs',
                   '--id', 'scripted'], env=env).splitlines()[-1])
    queue = ws / 'work/.murmur/work_queue.py'

    def helper(peer, *args):
        return json.loads(run([sys.executable, queue, *args], cwd=ws / 'work/peers' / peer, env=env))

    helper('a1', 'add', 'payload', 'Write text payload', 'Write payload.txt with a short ASCII message')
    helper('a1', 'add', 'manifest', 'Write byte manifest', 'Write manifest.txt containing payload byte count', '--after', 'payload')
    first = helper('a1', 'next')['task']
    helper('a1', 'release', 'payload', first['token'], 'No code yet; another peer can implement this unit')
    stolen = helper('a2', 'next')['task']
    assert stolen['owner'] == 'a2' and stolen['previous_owner'] == 'a1'
    stale = subprocess.run([sys.executable, str(queue), 'finish', 'payload', first['token'], 'stale owner'],
                           cwd=ws / 'work/peers/a1', env=env, capture_output=True, text=True)
    assert stale.returncode == 1
    second_clone = ws / 'work/peers/a2'
    (second_clone / 'payload.txt').write_text('hello from a reclaimed task\n')
    run(['git', 'add', 'payload.txt'], cwd=second_clone)
    run(['git', 'commit', '-qm', 'Publish recovered payload'], cwd=second_clone)
    run(['git', 'push', 'origin', 'HEAD:main'], cwd=second_clone)
    revision = run(['git', 'rev-parse', 'HEAD'], cwd=second_clone)
    helper('a2', 'finish', 'payload', stolen['token'], 'Delivered ' + revision)
    next_task = helper('a1', 'next')['task']
    assert next_task['id'] == 'manifest'
    first_clone = ws / 'work/peers/a1'
    run(['git', 'pull', '--rebase', 'origin', 'main'], cwd=first_clone)
    count = len((first_clone / 'payload.txt').read_bytes())
    (first_clone / 'manifest.txt').write_text(str(count) + '\n')
    assert int((first_clone / 'manifest.txt').read_text()) == count
    run(['git', 'add', 'manifest.txt'], cwd=first_clone)
    run(['git', 'commit', '-qm', 'Integrate payload manifest'], cwd=first_clone)
    run(['git', 'push', 'origin', 'HEAD:main'], cwd=first_clone)
    revision = run(['git', 'rev-parse', 'HEAD'], cwd=first_clone)
    helper('a1', 'finish', 'manifest', next_task['token'], 'Byte assertion passed; delivered ' + revision)
    run([sys.executable, '-m', 'murmur', 'run', ws], env=env)
    record = json.loads((ws / 'logs/run.json').read_text())
    with sqlite3.connect(ws / 'work/.murmur/work_queue.sqlite3') as db:
        events = [{'actor': a, 'kind': k, 'task': t, 'data': json.loads(d)}
                  for a, k, t, d in db.execute('SELECT actor, kind, task, data FROM events ORDER BY seq')]
    result = {'mode': 'scripted-fake-codex', 'model_calls': 0, 'model_tokens': 0,
              'elapsed_seconds': round(time.monotonic() - started, 3), 'run_seconds': record['seconds'],
              'queue': record['work_queue'], 'events': events, 'stale_owner_rejected': True,
              'manifest_assertion': True, 'exit_code': record['exit_code'],
              'observed_usage': record['usage'],
              'limits': 'Scripted peers prove mechanics, not live model adoption or task quality gains.'}
    (output / 'evidence.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    screen(Path(sys.argv[1]).resolve())
