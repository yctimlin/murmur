"""Regression test for refusing a successful run that leaves main unchanged."""

from __future__ import annotations

import json
from pathlib import Path

from murmur.cli import EXIT_LAUNCHER

from support import run_cli, setup_workspace


def test_run_reports_no_work_delivered_when_main_does_not_advance(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli("run", str(workspace))

    assert result.returncode == EXIT_LAUNCHER
    assert "no work delivered" in result.stderr
    record = json.loads((workspace / "logs" / "run.json").read_text())
    assert record["exit_code"] == EXIT_LAUNCHER
    assert record["commits"] == "0"
    assert record["delivered"] is False
    assert record["diagnostic"] == "no work delivered"
