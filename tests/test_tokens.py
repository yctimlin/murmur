"""Token usage per agent, summed from rollouts and reported at the end of `murmur run`."""

from __future__ import annotations

import json
from pathlib import Path

from murmur.cli import EXIT_NO_WORK, EXIT_OK
from murmur.tokens import run_usage, session_usage, summary_lines

from support import run_cli, setup_workspace


def _usage(inp: int, cached: int, out: int) -> dict:
    return {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out,
            "total_tokens": inp + out}


def _rollout(path: Path, *events: dict, tail: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(event) + "\n" for event in events) + tail)
    return path


def _tokens(inp: int, cached: int, out: int) -> dict:
    return {"type": "event_msg", "payload": {"type": "token_count",
                                             "info": {"total_token_usage": _usage(inp, cached, out)}}}


def _call(name: str, arguments: str) -> dict:
    return {"type": "response_item", "payload": {"type": "function_call", "name": name,
                                                 "arguments": arguments}}


def test_session_takes_the_last_running_total_and_names_the_peer(tmp_path: Path):
    rollout = _rollout(
        tmp_path / "r.jsonl",
        {"type": "session_meta", "payload": {"id": "x"}},
        _tokens(10, 5, 1),
        _call("exec_command", '{"cmd": "cat /ws/prompts/a3.md"}'),
        {"type": "event_msg", "payload": {"type": "token_count", "info": None}},
        _tokens(100, 60, 9),
        tail='{"type": "event_msg", "payload": {"type": "token_co',  # half-written last line
    )
    assert session_usage(rollout) == ("a3", _usage(100, 60, 9))


def test_spawning_session_is_the_root_even_if_it_mentions_a_prompt(tmp_path: Path):
    rollout = _rollout(tmp_path / "r.jsonl",
                       _call("spawn_agent", '{"message": "read prompts/a1.md"}'), _tokens(7, 0, 1))
    assert session_usage(rollout) == ("root", _usage(7, 0, 1))


def test_session_without_token_counts_is_zero(tmp_path: Path):
    rollout = _rollout(tmp_path / "r.jsonl", {"type": "session_meta", "payload": {}}, ["odd"])
    assert session_usage(rollout) == ("root?", _usage(0, 0, 0))


def test_run_usage_sums_sessions_per_agent_in_order(tmp_path: Path):
    sessions = tmp_path / "codex-home" / "sessions" / "2026" / "11" / "10"
    _rollout(sessions / "1.jsonl", _call("exec_command", "prompts/a2.md"), _tokens(20, 10, 2))
    _rollout(sessions / "2.jsonl", _call("spawn_agent", "{}"), _tokens(1, 0, 1))
    _rollout(sessions / "3.jsonl", _call("exec_command", "prompts/a1.md"), _tokens(30, 15, 3))
    _rollout(sessions / "4.jsonl", _call("exec_command", "prompts/a2.md"), _tokens(5, 5, 5))
    usage = run_usage(tmp_path, order=["a1", "a2"])
    assert list(usage["agents"]) == ["root", "a1", "a2"]
    assert usage["agents"]["a2"] == _usage(25, 15, 7)
    assert usage["total"] == _usage(56, 30, 11)
    assert summary_lines(usage) == [
        "tokens: 56 input (30 cached), 11 output",
        "  root  1 input (0 cached), 1 output",
        "  a1    30 input (15 cached), 3 output",
        "  a2    25 input (15 cached), 7 output",
    ]


def test_run_usage_without_rollouts_is_none(tmp_path: Path):
    assert run_usage(tmp_path) is None
    assert summary_lines(None) == ["tokens: no Codex session logs found"]


def test_solo_run_prints_and_records_tokens(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "commit"})
    assert result.returncode == EXIT_OK, result.stderr
    assert "tokens: 10,000 input (6,000 cached), 700 output" in result.stdout
    record = json.loads((workspace / "logs" / "run.json").read_text())
    assert record["tokens"] == {"total": _usage(10000, 6000, 700),
                                "agents": {"solo": _usage(10000, 6000, 700)}}


def test_swarm_run_records_tokens_per_agent_and_in_total(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--peers", "2")
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_ROLLOUTS": "partial"})
    assert result.returncode == EXIT_NO_WORK, result.stderr
    record = json.loads((workspace / "logs" / "run.json").read_text())
    assert record["tokens"]["agents"] == {
        "root": _usage(1000, 400, 50),
        "a1": _usage(10000, 6000, 700),
        "a2": _usage(20000, 12000, 1400),
    }
    assert record["tokens"]["total"] == _usage(31000, 18400, 2150)
    lines = result.stdout.splitlines()
    start = lines.index("tokens: 31,000 input (18,400 cached), 2,150 output")
    assert lines[start + 1:start + 4] == [
        "  root  1,000 input (400 cached), 50 output",
        "  a1    10,000 input (6,000 cached), 700 output",
        "  a2    20,000 input (12,000 cached), 1,400 output",
    ]


def test_run_without_rollouts_records_null_tokens(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_ROLLOUTS": "none"})
    assert "tokens: no Codex session logs found" in result.stdout
    assert json.loads((workspace / "logs" / "run.json").read_text())["tokens"] is None
