#!/usr/bin/env python3
"""Deterministic stand-in for the Codex CLI. No network and no model calls.

Modes (MURMUR_FAKE_CODEX_MODE):
  ok               exit 0
  fail             exit MURMUR_FAKE_CODEX_EXIT (default 23) after a stderr line
  fail-with-commit push one commit, then exit as fail
  commit           push one commit to main, then exit 0
  draft-only       push one commit to draft/a1 (not main), then exit 0
  hang             sleep until SIGTERM or SIGINT; with MURMUR_FAKE_CODEX_SIGNAL_FILE, write
                   "ready" there once the handlers are installed and the signal name on exit
  resistant        exit 0 after forking a SIGTERM-ignoring child

Every exec writes Codex-style rollouts with token counts under $CODEX_HOME/sessions: one
for a solo run, or one for the root plus one per peer (see TOKENS). Set
MURMUR_FAKE_CODEX_ROLLOUTS=none to write none, or =partial to end each with a half-written
line. `--version` prints MURMUR_FAKE_CODEX_VERSION (default 0.163.0); `features list` prints
the swarm features unless MURMUR_FAKE_CODEX_NO_FEATURES is set.
MURMUR_FAKE_CODEX_MODELS=fail makes `codex debug models` exit 5.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# (input, cached input, output) per session: the root, then peer number n gets n times PEER.
ROOT_TOKENS = (1000, 400, 50)
PEER_TOKENS = (10000, 6000, 700)


def main() -> int:
    args = sys.argv[1:]
    if args == ["--version"]:
        print(f"codex-cli {os.environ.get('MURMUR_FAKE_CODEX_VERSION', '0.163.0')}")
        return 0
    if args[:2] == ["debug", "models"]:
        if os.environ.get("MURMUR_FAKE_CODEX_MODELS") == "fail":
            print("error: simulated catalog failure", file=sys.stderr)
            return 5
        json.dump(_catalog(), sys.stdout)
        sys.stdout.write("\n")
        return 0
    if args[:2] == ["features", "list"]:
        if not os.environ.get("MURMUR_FAKE_CODEX_NO_FEATURES"):
            print("agent_message_board                      under development  false")
            print("multi_agent_v2                           stable             false")
        print("memories                                 stable             true")
        return 0
    if "exec" not in args:
        print(f"fake codex: unexpected args {args}", file=sys.stderr)
        return 2
    mode = os.environ.get("MURMUR_FAKE_CODEX_MODE", "ok")
    _write_rollouts(args)
    _write_final(args, None if mode == "hang" else "done\n")
    if mode == "hang":
        return _hang()
    if mode == "resistant":
        return _resistant()
    if mode == "fail":
        return _fail()
    if mode == "fail-with-commit":
        _commit_and_push(args)
        return _fail()
    if mode in ("commit", "draft-only"):
        _commit_and_push(args, "draft/a1" if mode == "draft-only" else "main")
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
                "supported_reasoning_levels": [
                    {"effort": effort} for effort in ("low", "medium", "high", "xhigh")
                ],
            }
        ]
    }


def _event(kind: str, payload: dict) -> str:
    return json.dumps({"timestamp": "2026-11-10T00:00:00.000Z", "type": kind, "payload": payload})


def _token_count(tokens: tuple[int, int, int], fraction: float) -> str:
    inp, cached, out = (int(value * fraction) for value in tokens)
    usage = {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out,
             "reasoning_output_tokens": 0, "total_tokens": inp + out}
    return _event("event_msg", {"type": "token_count",
                                "info": {"total_token_usage": usage, "last_token_usage": usage}})


def _call(name: str, arguments: str) -> str:
    return _event("response_item", {"type": "function_call", "name": name, "arguments": arguments})


def _write_rollouts(args: list[str]) -> None:
    style = os.environ.get("MURMUR_FAKE_CODEX_ROLLOUTS", "full")
    if style == "none":
        return
    ws = _workspace(args)
    meta = json.loads((ws / "murmur.json").read_text())
    sessions = Path(os.environ["CODEX_HOME"]) / "sessions" / "2026" / "11" / "10"
    sessions.mkdir(parents=True, exist_ok=True)
    rollouts = []
    if meta["mode"] == "solo":
        rollouts.append(("solo", [_call("exec_command", '{"cmd": "git status"}')], PEER_TOKENS))
    else:
        spawn = _call("spawn_agent", json.dumps({"task_name": "a1", "message": "prompts/a1.md"}))
        rollouts.append(("root", [spawn], ROOT_TOKENS))
        for number, agent in enumerate(meta["agents"], start=1):
            read = _call("exec_command", json.dumps({"cmd": f"cat {ws}/prompts/{agent['id']}.md"}))
            rollouts.append((agent["id"], [read], tuple(n * number for n in PEER_TOKENS)))
    for name, calls, tokens in rollouts:
        lines = [_event("session_meta", {"id": name}), _token_count(tokens, 0.5), *calls,
                 _token_count(tokens, 1.0)]
        text = "\n".join(lines) + "\n"
        if style == "partial":
            text += _token_count(tokens, 2.0)[:40]
        (sessions / f"rollout-2026-11-10T00-00-00-{name}.jsonl").write_text(text)


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
    record = os.environ.get("MURMUR_FAKE_CODEX_SIGNAL_FILE")

    def _stop(signum, frame) -> None:
        if record:
            Path(record).write_text(signal.Signals(signum).name + "\n")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)
    if record:
        Path(record).write_text("ready\n")
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


def _commit_and_push(args: list[str], branch: str = "main") -> None:
    ws = _workspace(args)
    meta = json.loads((ws / "murmur.json").read_text())
    clone = Path(meta["agents"][0]["clone"])
    _git(["git", "commit", "--allow-empty", "-m", "work"], clone)
    _git(["git", "push", "origin", f"HEAD:refs/heads/{branch}"], clone)


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
