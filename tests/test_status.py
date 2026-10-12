"""Status tolerates a partial final event and reads durable run state."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from support import setup_workspace

STATUS = Path(__file__).resolve().parents[1] / "skills" / "murmur" / "scripts" / "status"


def test_partial_jsonl_and_durable_state(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    state = {
        "version": 1,
        "state": "succeeded",
        "attempt_id": "abc",
        "attempts": [],
        "protocol": {"complete": True, "head": "abc123"},
    }
    (workspace / "logs" / "state.json").write_text(json.dumps(state) + "\n")
    (workspace / "logs" / "session.jsonl").write_text('{"type":"event_msg"}\n')
    rollout = workspace / "codex-home" / "sessions" / "2026" / "rollout.jsonl"
    rollout.parent.mkdir(parents=True)
    rollout.write_text(
        '{"type":"event_msg","timestamp":"2026-01-01T00:00:00Z","payload":{"type":"token_count","info":{"total_token_usage":{"total_tokens":3}}}}\n'
        '{"type":"event_msg","payload":{"type":"brok'
    )
    result = subprocess.run(
        [sys.executable, str(STATUS), str(workspace)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert "succeeded" in result.stdout
    assert "RUNNING" not in result.stdout
    assert "JSONDecodeError" not in result.stderr
    assert "protocol: complete abc123" in result.stdout
