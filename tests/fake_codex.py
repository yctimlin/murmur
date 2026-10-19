#!/usr/bin/env python3
"""Deterministic stand-in for the Codex CLI. No network and no model calls.

Modes (MURMUR_FAKE_CODEX_MODE):
  ok               exit 0
  fail             exit MURMUR_FAKE_CODEX_EXIT (default 23) after a stderr line
  fail-with-commit push one commit, then exit as fail
  commit           push one commit, then exit 0
  hang             sleep until SIGTERM/SIGINT (records it in MURMUR_FAKE_CODEX_SIGNAL_FILE)
  resistant        exit 0 after forking a SIGTERM-ignoring child
  429-first        emit a transient 429 once, then commit successfully
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    args = sys.argv[1:]
    if args[:2] == ["debug", "models"]:
        json.dump(_catalog(), sys.stdout)
        sys.stdout.write("\n")
        return 0
    if "exec" not in args:
        print(f"fake codex: unexpected args {args}", file=sys.stderr)
        return 2
    mode = os.environ.get("MURMUR_FAKE_CODEX_MODE", "ok")
    _write_final(args, None if mode == "hang" else "done\n")
    if mode == "hang":
        return _hang()
    if mode == "resistant":
        return _resistant()
    if mode == "429-first":
        if not sys.stdin.read().strip():
            print("fake codex: empty prompt on stdin", file=sys.stderr, flush=True)
            return 3
        marker = Path(os.environ.get("MURMUR_FAKE_CODEX_429_MARKER", ".fake-429-seen"))
        if not marker.exists():
            marker.write_text("seen\n")
            print("HTTP 429: simulated transient rate limit", file=sys.stderr, flush=True)
            return 1
        _commit_and_push(args)
        print(json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}}), flush=True)
        return 0
    if mode == "fail":
        return _fail()
    if mode == "fail-with-commit":
        _commit_and_push(args)
        return _fail()
    if mode == "commit":
        _commit_and_push(args)
        print(json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}}), flush=True)
        return 0
    print(json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}}), flush=True)
    return 0


def _catalog() -> dict:
    return {
        "models": [
            {
                "slug": "gpt-6-astra",
                "multi_agent_reasoning_effort": "xhigh",
                "multi_agent_version": "v2",
            }
        ]
    }


def _write_final(args: list[str], text: str | None) -> None:
    if text is None or "-o" not in args:
        return
    Path(args[args.index("-o") + 1]).write_text(text)


def _workspace(args: list[str]) -> Path:
    if "-C" not in args:
        raise SystemExit("fake codex: missing -C")
    return Path(args[args.index("-C") + 1]).resolve().parent


def _fail() -> int:
    print("codex failed: simulated", file=sys.stderr)
    return int(os.environ.get("MURMUR_FAKE_CODEX_EXIT", "23"))


def _hang() -> int:
    def _stop(signum, frame) -> None:
        record = os.environ.get("MURMUR_FAKE_CODEX_SIGNAL_FILE")
        if record:
            Path(record).write_text(signal.Signals(signum).name + "\n")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    time.sleep(3600)
    return 0


def _resistant() -> int:
    marker = Path(os.environ["MURMUR_FAKE_CODEX_PIDFILE"])
    child = os.fork()
    if child == 0:
        signal.signal(signal.SIGHUP, signal.SIG_IGN)
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        def on_term(signum, frame) -> None:
            with marker.open("a", encoding="utf-8") as handle:
                handle.write(" TERM\n")
                handle.flush()

        signal.signal(signal.SIGTERM, on_term)
        marker.write_text(f"{os.getpid()} START\n")
        while True:
            time.sleep(0.2)
    for _ in range(100):
        if marker.exists():
            break
        time.sleep(0.02)
    return 0


def _commit_and_push(args: list[str]) -> None:
    ws = _workspace(args)
    meta = json.loads((ws / "murmur.json").read_text())
    clone = Path(meta["agents"][0]["clone"])
    _git(["git", "commit", "--allow-empty", "-m", "work"], clone)
    _git(["git", "push", "origin", "HEAD:main"], clone)


def _git(args: list[str], cwd: Path) -> None:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        raise SystemExit(result.returncode or 1)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
