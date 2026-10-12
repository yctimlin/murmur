"""Exit statuses, interruption, the cap, and exclusive runs."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from murmur.errors import (
    EXIT_CAPPED,
    EXIT_CODEX_FAILED,
    EXIT_INCOMPLETE,
    EXIT_INTERRUPTED,
    EXIT_LAUNCHER,
    EXIT_OK,
)
from murmur.procutil import pid_alive

from support import init_repo, run_cli, setup_workspace


def _state(workspace: Path) -> dict:
    return json.loads((workspace / "logs" / "state.json").read_text())


def test_solo_success_is_zero_and_prints_fetch(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "ok"})
    assert result.returncode == EXIT_OK, result.stderr
    assert "succeeded" in result.stdout
    assert "review it:" in result.stdout
    assert _state(workspace)["state"] == "succeeded"
    assert (workspace / "logs" / "attempts").exists()
    assert "not a completed run" not in result.stderr


def test_codex_failure_prints_diagnostic_log_and_fetch(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    result = run_cli(
        "run", str(workspace),
        extra_env={"MURMUR_FAKE_CODEX_MODE": "fail-with-commit", "MURMUR_FAKE_CODEX_EXIT": "23"},
    )
    assert result.returncode == EXIT_CODEX_FAILED, result.stderr
    assert "codex exited 23" in result.stderr
    assert "codex failed: simulated" in result.stderr
    assert "partial result, not a completed run" in result.stderr
    assert "log:" in result.stderr
    log_path = Path(result.stderr.split("log:", 1)[1].strip().splitlines()[0].strip())
    assert log_path.is_file()
    assert "review it:" in result.stdout
    assert "1 new commit" in result.stdout
    state = _state(workspace)
    assert state["state"] == "failed"
    assert state["reason"] == "codex-exit"
    assert state["codex_exit_code"] == 23
    assert state["version"] == 1


def test_timeout_exits_capped(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo", "--cap", "1s")
    result = run_cli(
        "run", str(workspace),
        extra_env={"MURMUR_FAKE_CODEX_MODE": "hang"},
        timeout=15,
    )
    assert result.returncode == EXIT_CAPPED, result.stderr
    assert "reached the time cap" in result.stderr
    assert "review it:" in result.stdout
    assert _state(workspace)["state"] == "capped"


def test_interruption_exits_130_and_stops_codex(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo", "--cap", "30s")
    pidfile = tmp_path / "codex.pid"
    env = os.environ.copy()
    env["MURMUR_FAKE_CODEX_MODE"] = "hang"
    env["MURMUR_FAKE_CODEX_PIDFILE"] = str(pidfile)
    proc = subprocess.Popen(
        [sys.executable, "-m", "murmur", "run", str(workspace)],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,
    )
    deadline = time.monotonic() + 10
    while not pidfile.exists():
        assert proc.poll() is None, proc.stderr.read() if proc.stderr else ""
        assert time.monotonic() < deadline
        time.sleep(0.05)
    os.kill(proc.pid, signal.SIGINT)
    stdout, stderr = proc.communicate(timeout=10)
    assert proc.returncode == EXIT_INTERRUPTED, stderr
    assert "interrupted" in stderr
    assert "review it:" in stdout
    assert not pid_alive(int(pidfile.read_text().strip()))
    assert _state(workspace)["state"] == "interrupted"


def test_missing_workspace_is_a_launcher_error(tmp_path: Path):
    result = run_cli("run", str(tmp_path / "missing"))
    assert result.returncode == EXIT_LAUNCHER
    assert "no workspace" in result.stderr


def test_swarm_without_attestations_is_incomplete(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--peers", "2")
    result = run_cli(
        "run", str(workspace), "--protocol-retries", "0",
        extra_env={"MURMUR_FAKE_CODEX_MODE": "ok"},
    )
    assert result.returncode == EXIT_INCOMPLETE, result.stderr
    assert "a1 spawn-failed" in result.stderr
    assert "a2 spawn-failed" in result.stderr
    assert "review it:" in result.stdout
    assert _state(workspace)["reason"] == "incomplete"


def test_swarm_protocol_success(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--peers", "2")
    result = run_cli(
        "run", str(workspace),
        extra_env={"MURMUR_FAKE_CODEX_MODE": "protocol-ok"},
    )
    assert result.returncode == EXIT_OK, result.stderr
    assert "protocol: complete" in result.stderr
    assert "1 new commit" in result.stdout
    protocol = _state(workspace)["protocol"]
    assert protocol["complete"] is True
    assert set(protocol["outcomes"]) == {"a1", "a2"}


def test_protocol_retry_then_success(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--peers", "2")
    count = tmp_path / "count"
    result = run_cli(
        "run", str(workspace), "--protocol-retries", "1",
        extra_env={
            "MURMUR_FAKE_CODEX_MODE": "protocol-on-second",
            "MURMUR_FAKE_CODEX_COUNT": str(count),
        },
    )
    assert result.returncode == EXIT_OK, result.stderr
    assert count.read_text() == "2"


def test_concurrent_run_is_rejected(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo", "--cap", "30s")
    pidfile = tmp_path / "codex.pid"
    env = os.environ.copy()
    env["MURMUR_FAKE_CODEX_MODE"] = "hang"
    env["MURMUR_FAKE_CODEX_PIDFILE"] = str(pidfile)
    first = subprocess.Popen(
        [sys.executable, "-m", "murmur", "run", str(workspace)],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + 10
        while True:
            state_path = workspace / "logs" / "state.json"
            if state_path.exists():
                state = json.loads(state_path.read_text())
                if state.get("state") == "running" and state.get("codex_pid"):
                    break
            assert first.poll() is None
            assert time.monotonic() < deadline
            time.sleep(0.05)
        second = run_cli("run", str(workspace), timeout=10)
        assert second.returncode == EXIT_LAUNCHER
        assert "in use" in second.stderr
        assert _state(workspace)["state"] == "running"
    finally:
        os.kill(first.pid, signal.SIGTERM)
        first.wait(timeout=10)


def test_stale_run_is_recovered_without_losing_evidence(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo", "--cap", "30s")
    pidfile = tmp_path / "codex.pid"
    env = os.environ.copy()
    env["MURMUR_FAKE_CODEX_MODE"] = "hang"
    env["MURMUR_FAKE_CODEX_PIDFILE"] = str(pidfile)
    first = subprocess.Popen(
        [sys.executable, "-m", "murmur", "run", str(workspace)],
        env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,
    )
    deadline = time.monotonic() + 10
    codex_pid = None
    while codex_pid is None:
        assert first.poll() is None
        assert time.monotonic() < deadline
        state_path = workspace / "logs" / "state.json"
        if state_path.exists():
            state = json.loads(state_path.read_text())
            codex_pid = state.get("codex_pid")
        time.sleep(0.05)
    os.kill(first.pid, signal.SIGKILL)
    first.wait(timeout=5)
    assert pid_alive(int(codex_pid))
    refused = run_cli("run", str(workspace), timeout=10)
    assert refused.returncode == EXIT_LAUNCHER
    assert "--recover" in refused.stderr
    assert pid_alive(int(codex_pid))
    first_log = (workspace / "logs" / "attempts").glob("*/session.jsonl")
    preserved = next(first_log).read_text()
    assert "hang-marker" in preserved
    recovered = run_cli(
        "run", "--recover", str(workspace),
        extra_env={"MURMUR_FAKE_CODEX_MODE": "ok"},
    )
    assert recovered.returncode == EXIT_OK, recovered.stderr
    assert not pid_alive(int(codex_pid))
    state = _state(workspace)
    assert state["state"] == "succeeded"
    assert len(state["attempts"]) == 2
    assert state["attempts"][0]["reason"] == "stale"
    stale_log = workspace / state["attempts"][0]["dir"] / "session.jsonl"
    assert stale_log.read_text() == preserved


def test_normal_exit_kills_resistant_descendant(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    pidfile = tmp_path / "child"
    result = run_cli(
        "run", str(workspace),
        extra_env={"MURMUR_FAKE_CODEX_MODE": "resistant", "MURMUR_FAKE_CODEX_PIDFILE": str(pidfile)},
    )
    assert result.returncode == EXIT_OK, result.stderr
    text = pidfile.read_text()
    pid = int(text.split()[0])
    assert "TERM" in text
    assert not pid_alive(pid)


def test_retry_keeps_the_previous_attempt(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    first = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "fail"})
    assert first.returncode == EXIT_CODEX_FAILED
    again = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "ok"})
    assert again.returncode == EXIT_LAUNCHER
    assert "--retry" in again.stderr
    second = run_cli("run", "--retry", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "ok"})
    assert second.returncode == EXIT_OK, second.stderr
    state = json.loads((workspace / "logs" / "state.json").read_text())
    attempts = state["attempts"]
    assert [item["state"] for item in attempts] == ["failed", "succeeded"]
    first = workspace / attempts[0]["dir"]
    second = workspace / attempts[1]["dir"]
    assert first != second
    assert "codex failed: simulated" in (first / "session.err").read_text()
    assert (second / "session.jsonl").is_file()


def test_setup_failure_removes_the_workspace(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    result = run_cli(
        "setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"),
        "--id", "run1", "--solo", "--setup", "exit 7",
    )
    assert result.returncode == EXIT_LAUNCHER
    assert "setup command failed" in result.stderr
    assert not (tmp_path / "runs" / "run1").exists()


def test_interrupted_setup_removes_the_workspace(tmp_path: Path):
    repo, brief = init_repo(tmp_path / "src")
    workspace = tmp_path / "runs" / "run1"
    marker = tmp_path / "asleep"
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "murmur", "setup", str(brief),
            "--repo", str(repo), "--into", str(tmp_path / "runs"),
            "--id", "run1", "--solo", "--setup", f"touch {tmp_path / 'asleep'} && sleep 30",
        ],
        env=os.environ.copy(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        start_new_session=True,
    )
    deadline = time.monotonic() + 10
    while not marker.exists():
        assert proc.poll() is None, "setup exited before the command started"
        assert time.monotonic() < deadline
        time.sleep(0.05)
    os.kill(proc.pid, signal.SIGINT)
    stdout, stderr = proc.communicate(timeout=10)
    assert proc.returncode == EXIT_INTERRUPTED, stderr
    assert "setup interrupted" in stderr
    assert not workspace.exists()
    assert stdout.strip() == ""
