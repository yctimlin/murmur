"""Regression test for retrying a transient Codex 429."""

from __future__ import annotations

import json
from pathlib import Path

from murmur.cli import EXIT_OK

from support import run_cli, setup_workspace


def test_transient_429_is_retried_and_work_is_delivered(tmp_path: Path) -> None:
    marker = tmp_path / "429-seen"
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli(
        "run",
        str(workspace),
        extra_env={
            "MURMUR_FAKE_CODEX_MODE": "429-first",
            "MURMUR_FAKE_CODEX_429_MARKER": str(marker),
            "MURMUR_RATE_LIMIT_BASE_MS": "1",
        },
    )
    assert result.returncode == EXIT_OK, result.stderr
    record = json.loads((workspace / "logs" / "run.json").read_text())
    assert record["attempts"] == 2
    assert record["delivered"] is True
    assert marker.exists()
