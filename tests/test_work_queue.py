"""Actual concurrent claims, recovery fencing, dependencies and setup/run boundaries."""
from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import sys

import pytest

from murmur import work_queue as q
from support import run_cli, setup_workspace


@pytest.fixture
def queue(tmp_path):
    path = tmp_path / 'queue.sqlite3'
    q.initialize(path, [{'id': f'a{i}', 'clone': str(tmp_path / f'a{i}')} for i in range(1, 4)])
    return path


def test_atomic_claims_and_idempotent_retry(queue):
    q.add(queue, 'a1', 'unit', 'Small unit', 'Do a bounded thing')
    with ThreadPoolExecutor(max_workers=3) as pool:
        results = list(pool.map(lambda a: q.claim(queue, a), ['a1', 'a2', 'a3']))
    winners = [r['task'] for r in results if r['task']]
    assert len(winners) == 1
    winner = winners[0]
    retry = q.claim(queue, winner['owner'])
    assert retry['existing_claim'] and retry['task']['token'] == winner['token']
    assert retry['task']['expires'] == winner['expires']
    assert q.inspect(queue)['events']['claimed'] == 1


def test_expired_claim_is_recoverable_and_old_owner_is_fenced(queue, monkeypatch):
    q.add(queue, 'a1', 'unit', 'Small unit', 'A result')
    old = q.claim(queue, 'a1', lease_seconds=1)['task']
    monkeypatch.setattr(q.time, 'time', lambda: old['expires'] + 1)
    new = q.claim(queue, 'a2')['task']
    assert new['previous_owner'] == 'a1'
    assert new['token'] != old['token']
    with pytest.raises(q.QueueError, match='superseded'):
        q.update(queue, 'a1', 'unit', old['token'], 'finish', 'late old result')
    q.update(queue, 'a2', 'unit', new['token'], 'finish', 'recovered')
    assert q.inspect(queue)['status'] == 'complete'
    assert q.inspect(queue)['events']['expired'] == 1


def test_dependency_readiness_and_release_handoff(queue):
    q.add(queue, 'a1', 'first', 'First', 'First task')
    q.add(queue, 'a1', 'second', 'Second', 'Second task', ['first'])
    assert q.inspect(queue)['waiting'] == 1
    claimed = q.claim(queue, 'a1')['task']
    assert q.claim(queue, 'a2')['task'] is None
    q.update(queue, 'a1', 'first', claimed['token'], 'release', 'work is on branch draft/a1')
    other = q.claim(queue, 'a2')['task']
    assert other['result'] == 'work is on branch draft/a1'
    with pytest.raises(q.QueueError):
        q.update(queue, 'a1', 'first', claimed['token'], 'finish', 'wrong owner')
    q.update(queue, 'a2', 'first', other['token'], 'finish', 'landed')
    second = q.claim(queue, 'a3')['task']
    assert second['id'] == 'second'


def test_renew_requires_current_fencing_token(queue):
    q.add(queue, 'a1', 'one', 'One', 'Detail')
    task = q.claim(queue, 'a1', lease_seconds=1)['task']
    q.update(queue, 'a1', task['id'], task['token'], 'renew')
    assert q.claim(queue, 'a1')['task']['expires'] > task['expires']
    with pytest.raises(q.QueueError):
        q.update(queue, 'a2', task['id'], task['token'], 'renew')


def test_bounded_status_and_closed_dependencies(queue):
    with pytest.raises(q.QueueError, match='dependency'):
        q.add(queue, 'a1', 'one', 'One', 'Detail', ['future'])
    for i in range(25):
        q.add(queue, 'a1', str(i), 'Title', 'Detail')
    assert not q.add(queue, 'a1', '0', 'Title', 'Detail')['created']
    with pytest.raises(q.QueueError, match='already exists'):
        q.add(queue, 'a2', '0', 'Title', 'Detail')
    q.claim(queue, 'a1')
    status = q.inspect(queue)
    assert len(status['tasks']) == 20 and status['next_offset'] == 20
    assert len(q.inspect(queue, offset=20)['tasks']) == 5
    assert all('token' not in t for t in status['tasks'])


def enabled_workspace(tmp_path):
    config = tmp_path / 'queue.toml'
    config.write_text('work_stealing = true\n')
    return setup_workspace(tmp_path, '--config', str(config))


def helper(ws, peer, *args):
    return subprocess.run([sys.executable, str(ws / 'work/.murmur/work_queue.py'), *args],
                          cwd=ws / 'work/peers' / peer, text=True, capture_output=True)


def test_standalone_helper_and_success_gate(tmp_path):
    ws = enabled_workspace(tmp_path)
    root_prompt = (ws / 'prompts/root.md').read_text()
    assert 'work_queue' not in root_prompt
    assert helper(ws, 'a1', 'add', 'one', 'Title', 'Detail').returncode == 0
    claimed = json.loads(helper(ws, 'a2', 'next').stdout)['task']
    result = helper(ws, 'a2', 'finish', 'one', claimed['token'], 'commit evidence')
    assert result.returncode == 0, result.stdout
    run = run_cli('run', str(ws))
    assert run.returncode == 0, run.stderr
    record = json.loads((ws / 'logs/run.json').read_text())
    assert record['work_queue']['status'] == 'complete'
    assert record['work_queue']['events']['claimed'] == 1


@pytest.mark.parametrize('state', ['unused', 'unfinished', 'missing'])
def test_unfinished_or_missing_queue_cannot_report_success(tmp_path, state):
    ws = enabled_workspace(tmp_path)
    path = ws / 'work/.murmur/work_queue.sqlite3'
    if state == 'unfinished':
        q.add(path, 'a1', 'one', 'Title', 'Detail')
    elif state == 'missing':
        path.unlink()
    run = run_cli('run', str(ws))
    assert run.returncode == 1
    record = json.loads((ws / 'logs/run.json').read_text())
    assert record['codex_exit_code'] == 0
    assert record['exit_code'] == 1
    assert 'work queue' in run.stderr
    assert '(exit 0)' not in run.stdout


def test_base_has_no_helper_or_gate(tmp_path):
    ws = setup_workspace(tmp_path)
    assert not (ws / 'work/.murmur/work_queue.py').exists()
    assert run_cli('run', str(ws)).returncode == 0
    assert 'work_queue' not in json.loads((ws / 'logs/run.json').read_text())
