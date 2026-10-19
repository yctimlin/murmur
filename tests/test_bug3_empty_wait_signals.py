from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from murmur.cli import EXIT_INTERRUPTED, ROOT_WAIT_MS, render

from support import run_cli, setup_workspace


def test_root_prompt_handles_empty_wait_result_without_waiting_again():
    prompt = render("root.md", n="1", spawns="-", wait_ms=str(ROOT_WAIT_MS))
    assert "receiver_thread_ids=[]" in prompt
    assert "when no peer" in prompt


def test_sigint_to_launcher_is_forwarded_to_codex_child(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo", "--cap", "30s")
    received = tmp_path / "child-signal"
    proc = subprocess.Popen(
        [sys.executable, "-m", "murmur", "run", str(workspace)],
        env={**os.environ, "MURMUR_FAKE_CODEX_MODE": "hang", "MURMUR_FAKE_CODEX_SIGNAL_FILE": str(received)},
        start_new_session=True,
    )
    session = workspace / "logs" / "session.jsonl"
    deadline = time.monotonic() + 10
    while not session.exists():
        assert time.monotonic() < deadline
        assert proc.poll() is None
        time.sleep(0.05)
    time.sleep(0.5)  # let the fake child install its handlers
    os.kill(proc.pid, signal.SIGINT)  # the launcher only, not its child's group
    proc.wait(timeout=10)
    assert proc.returncode == EXIT_INTERRUPTED
    assert received.read_text().strip() == "SIGINT"
