"""The skill's status script reads a run while Codex is still writing it."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from support import setup_workspace

STATUS = Path(__file__).resolve().parents[1] / "skills" / "murmur" / "scripts" / "status"


def _status(workspace: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(STATUS), str(workspace)],
                          capture_output=True, text=True, timeout=30, check=False)


def test_half_written_last_line_is_skipped(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    (workspace / "logs" / "session.jsonl").write_text("")
    sessions = workspace / "codex-home" / "sessions" / "2026" / "11" / "10"
    sessions.mkdir(parents=True)
    events = [
        {"timestamp": "2026-11-10T00:00:00Z", "type": "response_item",
         "payload": {"type": "function_call", "name": "exec", "arguments": "{}"}},
        {"timestamp": "2026-11-10T00:00:05Z", "type": "event_msg",
         "payload": {"type": "token_count", "info": {"total_token_usage": {"total_tokens": 1234}}}},
    ]
    text = "".join(json.dumps(event) + "\n" for event in events)
    (sessions / "rollout.jsonl").write_text(text + "\n" + '{"timestamp": "2026-11-1')
    result = _status(workspace)
    assert result.returncode == 0, result.stderr
    assert "RUNNING" in result.stdout
    assert "tool calls 1" in result.stdout and "tokens 1,234" in result.stdout


def test_missing_workspace_is_one_line(tmp_path: Path):
    result = _status(tmp_path / "nope")
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "no readable murmur workspace" in result.stderr
