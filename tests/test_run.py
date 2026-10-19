"""Exit statuses, interruption, the cap, and process cleanup."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from murmur.cli import (
    EXIT_CAPPED,
    EXIT_CODEX_FAILED,
    EXIT_INTERRUPTED,
    EXIT_LAUNCHER,
    EXIT_NO_WORK,
    EXIT_OK,
)
from murmur.procutil import pid_alive

from support import init_repo, run_cli, setup_workspace


def test_solo_success_is_zero_and_prints_fetch(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "commit"})
    assert result.returncode == EXIT_OK, result.stderr
    assert "review it:" in result.stdout
    assert "fetch" in result.stdout
    record = json.loads((workspace / "logs" / "run.json").read_text())
    assert record["commits"] == "1" and record["delivered"] is True
    assert record["diagnostic"] == "exit 0"
    assert not (workspace / "logs" / "state.json").exists()


def test_codex_success_with_main_unchanged_is_no_work(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli("run", str(workspace))
    assert EXIT_NO_WORK == 4
    assert result.returncode == EXIT_NO_WORK, result.stderr
    assert "no work delivered" in result.stderr
    record = json.loads((workspace / "logs" / "run.json").read_text())
    assert record["exit_code"] == EXIT_NO_WORK
    assert record["codex_exit_code"] == 0
    assert record["commits"] == "0" and record["delivered"] is False
    assert record["drafts"] == []


def test_no_work_lists_unmerged_draft_branches(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "draft-only"})
    assert result.returncode == EXIT_NO_WORK, result.stderr
    assert "draft/a1" in result.stderr
    assert "refs/heads/draft/*:refs/heads/murmur/run1/draft/*" in result.stderr
    record = json.loads((workspace / "logs" / "run.json").read_text())
    assert record["drafts"] == ["draft/a1"]
    assert "draft/a1" in record["diagnostic"]


def test_codex_failure_prints_diagnostic_log_and_fetch(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "fail-with-commit"})
    assert result.returncode == EXIT_CODEX_FAILED, result.stderr
    assert "codex exited 23" in result.stderr
    assert "session.err" in result.stderr
    assert "codex failed: simulated" in (workspace / "logs" / "session.err").read_text()
    assert "fetch" in result.stdout
    assert "review it:" in result.stdout


def test_timeout_exits_capped(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo", "--cap", "1s")
    result = run_cli(
        "run", str(workspace),
        extra_env={"MURMUR_FAKE_CODEX_MODE": "hang"},
        timeout=20,
    )
    assert EXIT_CAPPED == 124
    assert result.returncode == 124, result.stderr
    assert "capped" in result.stderr
    assert "session.err" in result.stderr
    assert "fetch" in result.stdout
    record = json.loads((workspace / "logs" / "run.json").read_text())
    assert record["started_at"] < record["ended_at"]


def test_interruption_exits_130_and_stops_codex(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo", "--cap", "30s")
    proc = subprocess.Popen(
        [sys.executable, "-m", "murmur", "run", str(workspace)],
        env={**os.environ, "MURMUR_FAKE_CODEX_MODE": "hang"},
        start_new_session=True,
    )
    deadline = time.monotonic() + 10
    session = workspace / "logs" / "session.jsonl"
    while not session.exists():
        assert time.monotonic() < deadline
        assert proc.poll() is None
        time.sleep(0.05)
    os.killpg(proc.pid, signal.SIGTERM)
    proc.wait(timeout=10)
    assert proc.returncode == EXIT_INTERRUPTED


def test_sigint_to_the_launcher_reaches_codex_as_sigint(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo", "--cap", "30s")
    received = tmp_path / "child-signal"
    proc = subprocess.Popen(
        [sys.executable, "-m", "murmur", "run", str(workspace)],
        env={**os.environ, "MURMUR_FAKE_CODEX_MODE": "hang", "MURMUR_FAKE_CODEX_SIGNAL_FILE": str(received)},
        start_new_session=True,
    )
    deadline = time.monotonic() + 10
    while not (received.exists() and received.read_text() == "ready\n"):
        assert time.monotonic() < deadline
        assert proc.poll() is None
        time.sleep(0.05)
    os.kill(proc.pid, signal.SIGINT)  # the launcher only, not the Codex process group
    proc.wait(timeout=10)
    assert proc.returncode == EXIT_INTERRUPTED
    assert received.read_text().strip() == "SIGINT"


def test_missing_workspace_is_a_launcher_error(tmp_path: Path):
    result = run_cli("run", str(tmp_path / "missing"))
    assert result.returncode == EXIT_LAUNCHER
    assert "no workspace" in result.stderr


def test_second_run_is_rejected(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    first = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "commit"})
    assert first.returncode == EXIT_OK, first.stderr
    again = run_cli("run", str(workspace))
    assert again.returncode == EXIT_LAUNCHER
    assert "already run" in again.stderr


def test_normal_exit_kills_resistant_descendant(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    pidfile = tmp_path / "child"
    result = run_cli(
        "run", str(workspace),
        extra_env={"MURMUR_FAKE_CODEX_MODE": "resistant", "MURMUR_FAKE_CODEX_PIDFILE": str(pidfile)},
    )
    assert result.returncode == EXIT_NO_WORK, result.stderr
    text = pidfile.read_text()
    pid = int(text.split()[0])
    assert "TERM" in text
    assert not pid_alive(pid)


def test_setup_failure_removes_the_workspace(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--solo", "--setup", "exit 7",
    )
    assert result.returncode == EXIT_LAUNCHER
    assert "setup command failed" in result.stderr
    assert not (tmp_path / "runs" / "run1").exists()
