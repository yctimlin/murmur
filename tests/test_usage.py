"""Observed usage must not double count history or turn cumulative counters."""
from __future__ import annotations

import json
from pathlib import Path

from murmur.usage import summarize_usage
from support import run_cli, setup_workspace


def record(thread="root", response="r1", n=100, **changes):
    payload = {"thread_id": thread, "response_id": response,
               "usage": {"input_tokens": n, "cached_input_tokens": n // 2,
                         "output_tokens": 10, "reasoning_output_tokens": 5},
               "thread_token_usage": {"input_tokens": 999999}}
    payload.update(changes)
    return {"type": "token_usage_record", "payload": payload}


def write(home, name, events):
    path = home / "sessions" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(event) for event in events) + "\n")
    return path


def test_response_usage_sums_root_and_peers_without_inherited_or_replayed_duplicates(tmp_path):
    root = record()
    write(tmp_path, "root.jsonl", [root, record(response="r2", n=200)])
    write(tmp_path, "peer.jsonl", [
        {"type": "session_meta", "payload": {"id": "peer", "agent_path": "/root/a1", "parent_thread_id": "root"}},
        root, record(thread="peer", response="p1", n=300),
    ])
    result = summarize_usage(tmp_path)
    assert result["status"] == "observed"
    assert result["observed_responses"] == 3
    assert result["duplicate_records"] == 1
    assert result["tokens"] == {"input_tokens": 600, "cached_input_tokens": 300,
                                 "uncached_input_tokens": 300, "output_tokens": 30,
                                 "reasoning_output_tokens": 15, "total_tokens": 630}
    assert result["threads"][0]["agent_path"] == "/root/a1"


def test_missing_usage_is_unknown_not_free(tmp_path):
    assert summarize_usage(tmp_path)["tokens"] is None
    write(tmp_path, "empty.jsonl", [{"type": "session_meta", "payload": {"id": "peer"}}])
    result = summarize_usage(tmp_path)
    assert result["status"] == "partial"
    assert result["threads_without_usage"] == ["peer"]
    assert result["tokens"] is None


def test_truncated_and_invalid_usage_preserve_valid_observations(tmp_path):
    path = write(tmp_path, "partial.jsonl", [record(), record(response="bad", usage={"input_tokens": True})])
    with path.open("a") as f:
        f.write('{"type":')
    result = summarize_usage(tmp_path)
    assert result["status"] == "partial"
    assert result["observed_responses"] == 1
    assert result["unreadable_records_or_files"] == 2
    assert result["tokens"]["input_tokens"] == 100


def test_archive_duplicate_and_conflicting_record_are_detected(tmp_path):
    write(tmp_path, "one.jsonl", [record()])
    archived = tmp_path / "archived_sessions"
    archived.mkdir()
    (archived / "one.jsonl").write_text(json.dumps(record(n=999)) + "\n")
    result = summarize_usage(tmp_path)
    assert result["status"] == "partial"
    assert result["duplicate_records"] == 1
    assert result["unreadable_records_or_files"] == 1
    assert result["tokens"]["input_tokens"] == 100


def test_usage_is_recorded_on_failed_run(tmp_path):
    ws = setup_workspace(tmp_path, "--solo")
    write(ws / "codex-home", "one.jsonl", [record()])
    result = run_cli("run", str(ws), extra_env={"MURMUR_FAKE_CODEX_MODE": "fail"})
    assert result.returncode == 1
    assert "100 input (50 uncached), 10 output" in result.stdout
    saved = json.loads((ws / "logs" / "run.json").read_text())
    assert saved["usage"]["tokens"]["input_tokens"] == 100
