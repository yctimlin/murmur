#!/usr/bin/env python3
"""Capture launcher states using the fake Codex; no credentials or model calls.

Run from a checkout: python scripts/capture_states.py /tmp/murmur-capture
The output directory must not exist. All repositories and logs stay beneath it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from support import init_repo


def capture(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=False)
    bin_dir = destination / "bin"
    bin_dir.mkdir()
    (bin_dir / "codex").symlink_to(ROOT / "tests" / "fake_codex.py")
    empty_home = destination / "codex-config"
    empty_home.mkdir()
    env = {**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
           "PYTHONPATH": str(ROOT / "src"), "CODEX_HOME": str(empty_home),
           "MURMUR_TERM_GRACE": "0.4", "MURMUR_KILL_GRACE": "0.4"}
    rows = []
    for state, mode, expected in [("success", "ok", 0), ("failure", "fail", 1),
                                  ("partial-result", "fail-with-commit", 1),
                                  ("capped", "hang", 124), ("interrupted", "hang", 130),
                                  ("descendant", "resistant", 0)]:
        case = destination / state
        repo, brief = init_repo(case / "source")
        setup = subprocess.run([sys.executable, "-m", "murmur", "setup", str(brief),
                                "--repo", str(repo), "--into", str(case), "--id", "run",
                                "--solo", "--cap", "1s" if state == "capped" else "30s"],
                               env=env, capture_output=True, text=True, timeout=30)
        (case / "setup.txt").write_text(setup.stdout + setup.stderr)
        if setup.returncode:
            raise RuntimeError(f"{state}: setup failed: {setup.stderr}")
        ws = case / "run"
        case_env = {**env, "MURMUR_FAKE_CODEX_MODE": mode,
                    "MURMUR_FAKE_CODEX_PIDFILE": str(case / "child.pid")}
        started = time.monotonic()
        proc = subprocess.Popen([sys.executable, "-m", "murmur", "run", str(ws)], env=case_env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                start_new_session=True)
        if state == "interrupted":
            deadline = time.monotonic() + 10
            while not (ws / "logs" / "session.jsonl").exists():
                if proc.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError("interruption fixture did not start")
                time.sleep(0.02)
            os.killpg(proc.pid, signal.SIGTERM)
        stdout, stderr = proc.communicate(timeout=20)
        (case / "stdout.txt").write_text(stdout)
        (case / "stderr.txt").write_text(stderr)
        rows.append({"state": state, "exit_code": proc.returncode, "expected": expected,
                     "seconds": round(time.monotonic() - started, 3), "model_tokens": 0})
        if proc.returncode != expected:
            raise RuntimeError(f"{state}: exit {proc.returncode}, expected {expected}: {stderr}")
    (destination / "capture.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(destination / "capture.json")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/capture_states.py NEW_OUTPUT_DIRECTORY")
    capture(Path(sys.argv[1]).resolve())
