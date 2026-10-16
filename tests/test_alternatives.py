from __future__ import annotations

import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from murmur import alternatives as alt
from support import git, run_cli, setup_workspace


def fixture(tmp_path):
    ws = setup_workspace(tmp_path, extra_env={'MURMUR_ALTERNATIVES': '1'})
    return ws, ws / 'work' / 'origin.git', ws / 'work' / 'alternatives' / 'trials.sqlite3'


def candidate(ws, peer, value, *, message='candidate'):
    clone = ws / 'work' / 'peers' / peer
    (clone / 'value.txt').write_text(value)
    git(clone, 'add', 'value.txt')
    git(clone, 'commit', '-q', '-m', message)
    git(clone, 'push', '-q', 'origin', f'HEAD:refs/heads/draft/{peer}')
    return git(clone, 'rev-parse', 'HEAD')


def checks():
    return [[sys.executable, '-c', "from pathlib import Path; assert Path('value.txt').read_text() == 'good'"]]


def ready(tmp_path, command=None, timeout=5):
    ws, origin, state = fixture(tmp_path)
    opened = alt.open_trial(state, origin, 'unit', command or checks(), timeout)
    bad = candidate(ws, 'a1', 'bad')
    good = candidate(ws, 'a2', 'good')
    alt.submit(state, origin, 'unit', 'a1', bad)
    alt.submit(state, origin, 'unit', 'a2', good)
    return ws, origin, state, opened['base'], bad, good


def test_only_passing_candidate_is_promoted_and_logged(tmp_path):
    ws, origin, state, base, bad, good = ready(tmp_path)
    result = alt.evaluate(state, origin, 'unit')
    assert result['status'] == 'promoted' and result['winner'] == good
    assert git(origin, 'rev-parse', 'main') == good
    assert [r['passed'] for r in result['results']] == [False, True]
    assert alt.inspect(state)['complete']
    with sqlite3.connect(state) as db:
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='candidate_checked'").fetchone()[0] == 2
    result = run_cli('run', str(ws))
    assert result.returncode == 0, result.stderr
    record = json.loads((ws / 'logs' / 'run.json').read_text())
    assert record['alternatives']['trials'][0]['winner'] == good


def test_shared_head_change_cannot_be_overwritten(tmp_path):
    ws, origin, state, base, bad, good = ready(tmp_path)
    clone = ws / 'work' / 'peers' / 'a1'
    git(clone, 'push', '-q', 'origin', 'HEAD:main')
    result = alt.evaluate(state, origin, 'unit')
    assert result['status'] == 'stale'
    assert git(origin, 'rev-parse', 'main') == bad


def test_distinct_peers_and_two_slots_are_enforced(tmp_path):
    ws, origin, state = fixture(tmp_path)
    alt.open_trial(state, origin, 'unit', checks(), 5)
    first = candidate(ws, 'a1', 'first')
    second = candidate(ws, 'a2', 'second')
    alt.submit(state, origin, 'unit', 'a1', first)
    with pytest.raises(sqlite3.IntegrityError):
        alt.submit(state, origin, 'unit', 'a1', second)
    with pytest.raises(ValueError, match='two distinct'):
        alt.evaluate(state, origin, 'unit')
    alt.submit(state, origin, 'unit', 'a2', second)
    with pytest.raises(ValueError, match='slots'):
        alt.submit(state, origin, 'unit', 'a3', first)
    result = alt.evaluate(state, origin, 'unit')
    assert result['status'] == 'rejected'


def test_timeout_and_mutating_checks_never_promote(tmp_path):
    commands = [[sys.executable, '-c', 'import time; time.sleep(5)'],
                [sys.executable, '-c', "from pathlib import Path; Path('README.md').write_text('changed')"]]
    ws, origin, state, base, bad, good = ready(tmp_path, commands, .05)
    result = alt.evaluate(state, origin, 'unit')
    assert result['status'] == 'rejected'
    assert git(origin, 'rev-parse', 'main') == base
    assert all(r['checks'][0]['timed_out'] and not r['tracked_clean'] for r in result['results'])
    assert not list(state.parent.glob('candidate-*'))


def test_helper_and_run_completion_gate(tmp_path):
    ws, origin, state = fixture(tmp_path)
    helper = ws / 'work' / 'peers' / 'a1' / '.murmur' / 'alternatives'
    result = subprocess.run([str(helper), 'open', 'unit', '--checks', json.dumps(checks())],
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    result = run_cli('run', str(ws))
    assert result.returncode == 1
    record = json.loads((ws / 'logs' / 'run.json').read_text())
    assert record['alternatives']['complete'] is False
    assert 'unresolved' in result.stderr


def test_disabled_and_solo_runs_have_no_helper(tmp_path):
    ws = setup_workspace(tmp_path, '--solo', extra_env={'MURMUR_ALTERNATIVES': '1'})
    assert not (ws / 'work' / 'alternatives').exists()
    assert json.loads((ws / 'murmur.json').read_text())['alternatives'] is False


def test_check_diagnostics_are_bounded(tmp_path):
    commands = [[sys.executable, '-c', "print('x' * 20000)"]]
    ws, origin, state, base, bad, good = ready(tmp_path, commands)
    result = alt.evaluate(state, origin, 'unit')
    assert result['winner'] == bad  # both pass: first registered wins, not quality ranking
    assert all(r['checks'][0]['output_truncated'] for r in result['results'])
    assert all(len(r['checks'][0]['output_tail']) <= 4000 for r in result['results'])


def test_failed_trial_has_one_audited_retry_with_frozen_checks(tmp_path):
    ws, origin, state = fixture(tmp_path)
    alt.open_trial(state, origin, 'unit', checks(), 5)
    first = candidate(ws, 'a1', 'bad-first')
    second = candidate(ws, 'a2', 'bad-second')
    alt.submit(state, origin, 'unit', 'a1', first)
    alt.submit(state, origin, 'unit', 'a2', second)
    assert alt.evaluate(state, origin, 'unit')['status'] == 'rejected'
    assert not alt.inspect(state)['complete']
    with sqlite3.connect(state) as db:
        frozen = db.execute('SELECT checks,timeout FROM trials').fetchone()
    retried = alt.retry(state, origin, 'unit')
    assert retried['attempt'] == 2
    good = candidate(ws, 'a1', 'good', message='corrected')
    alt.submit(state, origin, 'unit', 'a1', good)
    alt.submit(state, origin, 'unit', 'a2', second)
    assert alt.evaluate(state, origin, 'unit')['status'] == 'promoted'
    assert alt.inspect(state)['complete']
    with sqlite3.connect(state) as db:
        assert db.execute('SELECT checks,timeout FROM trials').fetchone() == frozen
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='candidate_checked'").fetchone()[0] == 4
        assert db.execute("SELECT COUNT(*) FROM events WHERE kind='retried'").fetchone()[0] == 1
        db.execute("UPDATE trials SET status='rejected'")
    with pytest.raises(ValueError, match='one retry'):
        alt.retry(state, origin, 'unit')
