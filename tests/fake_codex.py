#!/usr/bin/env python3
"""Deterministic stand-in for the Codex CLI. No network and no model calls.

Modes (MURMUR_FAKE_CODEX_MODE):
  ok                 exit 0
  fail               exit MURMUR_FAKE_CODEX_EXIT (default 23) after a stderr line
  fail-with-commit   push one commit, then exit as fail
  hang               sleep until SIGTERM
  resistant          exit 0 after forking a SIGTERM-ignoring child
  protocol-ok        push one commit and attest every peer, exit 0
  protocol-on-second attest only on the second invocation
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
    _write_final(args, "done\n" if mode != "hang" else None)
    if mode == "hang":
        return _hang()
    if mode == "resistant":
        return _resistant()
    if mode == "fail":
        return _fail()
    if mode == "fail-with-commit":
        _commit_and_push(args)
        return _fail()
    if mode == "protocol-ok":
        sha = _commit_and_push(args)
        _attest_all(args, sha)
        return 0
    if mode == "protocol-on-second":
        count_path = Path(os.environ["MURMUR_FAKE_CODEX_COUNT"])
        count = int(count_path.read_text()) if count_path.exists() else 0
        count += 1
        count_path.write_text(str(count))
        if count >= 2:
            sha = _commit_and_push(args)
            _attest_all(args, sha)
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
            },
            {"slug": "other-model", "multi_agent_version": "v1"},
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
    print(json.dumps({"type": "event_msg", "payload": {"type": "error"}}), flush=True)
    return int(os.environ.get("MURMUR_FAKE_CODEX_EXIT", "23"))


def _hang() -> int:
    pidfile = os.environ.get("MURMUR_FAKE_CODEX_PIDFILE")
    if pidfile:
        Path(pidfile).write_text(str(os.getpid()))
    print(json.dumps({"type": "event_msg", "payload": {"type": "hang-marker"}}), flush=True)

    def _stop(signum, frame) -> None:
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
    print(json.dumps({"type": "event_msg", "payload": {"type": "resistant-parent"}}), flush=True)
    return 0


def _git(args: list[str], cwd: Path) -> None:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        raise SystemExit(result.returncode or 1)


def _commit_and_push(args: list[str]) -> str:
    ws = _workspace(args)
    meta = json.loads((ws / "murmur.json").read_text())
    clone = Path(meta["agents"][0]["clone"])
    _git(["git", "commit", "--allow-empty", "-m", "work"], clone)
    _git(["git", "push", "origin", "HEAD:main"], clone)
    origin = ws / "work" / "origin.git"
    result = subprocess.run(
        ["git", "rev-parse", "main"], cwd=origin, capture_output=True, text=True, check=True
    )
    print(json.dumps({"type": "event_msg", "payload": {"type": "committed"}}), flush=True)
    return result.stdout.strip()


def _attest_all(args: list[str], sha: str) -> None:
    ws = _workspace(args)
    meta = json.loads((ws / "murmur.json").read_text())
    attempt = (ws / "protocol" / "attempt").read_text().strip()
    for agent in meta["agents"]:
        payload = {
            "version": 1,
            "agent": agent["id"],
            "state": "completed",
            "commit": sha,
            "reason": "",
            "checks": [{"name": "acceptance", "result": "pass"}],
            "attempt_id": attempt,
            "updated_at": "1970-01-01T00:00:00+00:00",
        }
        path = ws / "protocol" / f"{agent['id']}.json"
        path.write_text(json.dumps(payload, indent=2) + "\n")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
