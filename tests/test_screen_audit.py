"""The screen exporter must not turn missing or stale telemetry into measurements."""
from __future__ import annotations

import json
from pathlib import Path
import runpy


audit = runpy.run_path(str(Path(__file__).resolve().parents[1] / 'scripts/audit_screen.py'))['audit']


def fixture(ws, *, stored_tokens=None):
    (ws / 'logs').mkdir(parents=True)
    (ws / 'murmur.json').write_text(json.dumps({'peers': 2, 'base': 'before', 'cap': '25m'}))
    (ws / 'logs/run.json').write_text(json.dumps({
        'seconds': 1.2, 'exit_code': 4, 'codex_exit_code': 0,
        'usage': {'tokens': stored_tokens}, 'result': {'head': 'after'},
        'review': {'complete': False, 'missing': ['one']},
    }))


def test_missing_usage_remains_unknown_even_for_declared_fixture(tmp_path):
    fixture(tmp_path)
    report = audit(tmp_path, kind='fixture', sections=['review'])
    assert report['usage']['tokens'] is None
    assert report['usage']['status'] == 'unavailable'
    assert report['kind_verified'] is False
    assert report['exit_code'] == 4 and report['codex_exit_code'] == 0
    assert report['mechanism_evidence']['review']['complete'] is False
    assert report['delivered_head'] == 'after'
    assert report['errors'] == []
    assert len(report['source_sha256']['logs/run.json']) == 64


def test_usage_recomputed_and_stale_record_detected(tmp_path):
    fixture(tmp_path)
    sessions = tmp_path / 'codex-home/sessions'
    sessions.mkdir(parents=True)
    usage = {'input_tokens': 20, 'cached_input_tokens': 5,
             'output_tokens': 3, 'reasoning_output_tokens': 1}
    row = {'type': 'token_usage_record', 'payload': {
        'thread_id': 'one', 'response_id': 'response', 'usage': usage}}
    (sessions / 'one.jsonl').write_text(json.dumps(row) + '\n' + json.dumps(row) + '\n')
    report = audit(tmp_path, kind='live', sections=[])
    assert report['usage']['tokens']['total_tokens'] == 23
    assert report['usage']['tokens']['uncached_input_tokens'] == 15
    assert report['usage']['duplicate_records'] == 1
    assert report['usage_matches_run_record'] is False
    assert 'differs' in report['errors'][0]


def test_missing_or_malformed_report_is_an_incomplete_screen(tmp_path):
    fixture(tmp_path)
    (tmp_path / 'logs/run.json').write_text('{')
    report = audit(tmp_path, kind='live', sections=['missing'])
    assert report['recorded_elapsed_seconds'] is None and report['exit_code'] is None
    assert len(report['errors']) == 2
    assert report['mechanism_evidence']['missing'] is None


def test_elapsed_and_timestamp_span_are_not_conflated(tmp_path):
    fixture(tmp_path)
    path = tmp_path / 'logs/run.json'
    record = json.loads(path.read_text())
    record.update(started_at='2026-10-16T03:45:32+00:00', ended_at='2026-10-16T03:50:17+00:00', seconds=155.5)
    path.write_text(json.dumps(record))
    report = audit(tmp_path, kind='live', sections=[])
    assert report['recorded_elapsed_seconds'] == 155.5
    assert report['timestamp_span_seconds'] == 285
    assert report['errors'] == []
