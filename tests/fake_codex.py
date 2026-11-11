#!/usr/bin/env python3
"""Deterministic stand-in for the Codex CLI. No network and no model calls.

Modes (MURMUR_FAKE_CODEX_MODE):
  ok               exit 0
  fail             exit MURMUR_FAKE_CODEX_EXIT (default 23) after a stderr line
  fail-with-commit push one commit, then exit as fail
  commit           push one commit to main, then exit 0
  draft-only       push one commit to draft/a1 (not main), then exit 0
  receipts         every agent commits a file and pushes it to main, logged the way Codex
                   0.163 logs a command (see _work); a swarm also gets a message board
  hang             sleep until SIGTERM or SIGINT; with MURMUR_FAKE_CODEX_SIGNAL_FILE, write
                   "ready" there once the handlers are installed and the signal name on exit
  resistant        exit 0 after forking a SIGTERM-ignoring child

Every exec writes Codex-style rollouts with token counts under $CODEX_HOME/sessions: one
for a solo run, or one for the root plus one per peer (see TOKENS). Set
MURMUR_FAKE_CODEX_ROLLOUTS=none to write none, or =partial to end each with a half-written
line.

The root of a swarm calls `spawn_agent` once per peer, the way Codex 0.163 handles it:
  - The stand-in model sets `fork_turns` to "none" only if the prompt on stdin asks for it.
    MURMUR_FAKE_CODEX_FORK_TURNS=omit makes it leave the argument out whatever the prompt
    says, and =all makes it send "all".
  - Before the call runs, every approved `PreToolUse` hook in $CODEX_HOME/config.toml whose
    matcher fits the tool name gets the call on stdin and may replace its arguments. A hook
    without a matching `trusted_hash` in `hooks.state` is skipped.
  - Unless the arguments that ran have `fork_turns` "none", the peer's rollout starts with a
    copy of the root's conversation and names the root in `forked_from_id`.
$CODEX_HOME/fake_spawns.jsonl records the arguments each call was sent with and ran with.

`--version` prints MURMUR_FAKE_CODEX_VERSION (default 0.163.0); `features list` prints
the swarm features unless MURMUR_FAKE_CODEX_NO_FEATURES is set.
MURMUR_FAKE_CODEX_MODELS=fail makes `codex debug models` exit 5.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import time
import tomllib
from datetime import datetime, timezone
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
    _write_rollouts(args, _work(args) if mode == "receipts" else {})
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


def _event(kind: str, payload: dict, at: float | None = None) -> str:
    stamp = "2026-11-10T00:00:00.000Z" if at is None else (
        datetime.fromtimestamp(at, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"))
    return json.dumps({"timestamp": stamp, "type": kind, "payload": payload})


def _token_count(tokens: tuple[int, int, int], fraction: float) -> str:
    inp, cached, out = (int(value * fraction) for value in tokens)
    usage = {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out,
             "reasoning_output_tokens": 0, "total_tokens": inp + out}
    return _event("event_msg", {"type": "token_count",
                                "info": {"total_token_usage": usage, "last_token_usage": usage}})


def _call(name: str, arguments: str) -> str:
    return _event("response_item", {"type": "function_call", "name": name, "arguments": arguments})


def _user_message(text: str) -> str:
    return _event("response_item", {"type": "message", "role": "user",
                                    "content": [{"type": "input_text", "text": text}]})


def _command(script: str, cwd: Path, exit_code: int, output: str) -> str:
    """A finished shell command, as Codex 0.163 records it in a rollout."""
    item = {"type": "CommandExecution", "command": ["/bin/bash", "-lc", script], "cwd": f"file://{cwd}",
            "status": "completed" if exit_code == 0 else "failed", "aggregated_output": output,
            "exit_code": exit_code}
    return _event("event_msg", {"type": "item_completed", "item": item}, at=time.time())


def _say(text: str) -> str:
    message = {"type": "message", "role": "assistant", "phase": "commentary",
               "content": [{"type": "output_text", "text": text}]}
    return _event("response_item", message, at=time.time())


def _work(args: list[str]) -> dict[str, list[str]]:
    """Each agent adds `<id>.txt` on main; returns the rollout lines that record it, by agent.

    The first agent runs the tests before it commits. The second only says it verified its
    change, in the `Verified:` line of its commit message, and any others say `not run`. In
    a swarm the first agent also posts a claim and a `DONE` that names its commit.
    """
    ws = _workspace(args)
    meta = json.loads((ws / "murmur.json").read_text())
    lines: dict[str, list[str]] = {}
    posts = []
    for number, agent in enumerate(meta["agents"]):
        name, clone = agent["id"], Path(agent["clone"])
        verified = ("python3 -m unittest -q (2 tests)", "read the diff", "not run")[min(number, 2)]
        own = lines[name] = [_say(f"I will add {name}.txt.")]
        posts.append((name, f"{name} claims {name}.txt", time.time()))
        if number == 0:
            own.append(_command("python3 -m unittest -q", clone, 0, "Ran 2 tests in 0.001s\n\nOK\n"))
        _git(["git", "pull", "-q", "--rebase", "origin", "main"], clone)
        (clone / f"{name}.txt").write_text(f"{name}\n")
        _git(["git", "add", f"{name}.txt"], clone)
        message = f"Add {name}.txt\n\nOne file per agent.\n\nVerified: {verified}"
        script = f"git add {name}.txt && git commit -m 'Add {name}.txt' && git push origin HEAD:main"
        output = _git(["git", "commit", "-m", message], clone) + _git(["git", "push", "origin", "HEAD:main"], clone)
        own.append(_command(script, clone, 0, output))
        if number == 0:
            sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=clone, capture_output=True,
                                 text=True, check=True).stdout.strip()
            posts.append((name, f"DONE {name}.txt is on origin/main at {sha}; tests pass", time.time()))
    if meta["mode"] != "solo":
        _write_board(Path(os.environ["CODEX_HOME"]), posts)
    return lines


def _write_board(home: Path, posts: list[tuple[str, str, float]]) -> None:
    """Codex's message board: the columns of its `posts` table that murmur reads."""
    db = sqlite3.connect(home / "agent_message_board_1.sqlite")
    db.execute("CREATE TABLE posts (seq INTEGER PRIMARY KEY AUTOINCREMENT, board TEXT NOT NULL, "
               "id TEXT NOT NULL, channel TEXT NOT NULL, root TEXT NOT NULL, author TEXT NOT NULL, "
               "timestamp INTEGER NOT NULL, body_search TEXT NOT NULL, payload TEXT NOT NULL)")
    for number, (agent, text, at) in enumerate(posts):
        db.execute("INSERT INTO posts (board, id, channel, root, author, timestamp, body_search, payload) "
                   "VALUES ('board', ?, 'tasks', ?, ?, ?, ?, ?)",
                   (f"post-{number}", f"post-{number}", f"/root/{agent}", int(at * 1e6),
                    text.lower(), json.dumps({"metadata": {"author": f"/root/{agent}"}, "text": text})))
    db.commit()
    db.close()


def _write_rollouts(args: list[str], work: dict[str, list[str]]) -> None:
    style = os.environ.get("MURMUR_FAKE_CODEX_ROLLOUTS", "full")
    if style == "none":
        return
    ws = _workspace(args)
    meta = json.loads((ws / "murmur.json").read_text())
    home = Path(os.environ["CODEX_HOME"])
    sessions = home / "sessions" / "2026" / "11" / "10"
    sessions.mkdir(parents=True, exist_ok=True)
    prompt = sys.stdin.read() if args[-1] == "-" else ""
    rollouts = []
    if meta["mode"] == "solo":
        head = [_event("session_meta", {"id": "solo"})]
        calls = [_call("exec_command", '{"cmd": "git status"}'), *work.get("solo", [])]
        rollouts.append(("solo", head, calls, PEER_TOKENS))
    else:
        root_head = [_event("session_meta", {"id": "root", "forked_from_id": None, "source": "exec"}),
                     _user_message(prompt)]
        spawns, peers = [], []
        for number, agent in enumerate(meta["agents"], start=1):
            sent = {"task_name": agent["id"], "message": f"prompts/{agent['id']}.md"}
            if fork_turns := _model_fork_turns(prompt):
                sent["fork_turns"] = fork_turns
            ran = _pre_tool_use(home, "collaborationspawn_agent", sent)
            with (home / "fake_spawns.jsonl").open("a") as record:
                record.write(json.dumps({"sent": sent, "ran": ran}) + "\n")
            spawns.append(_call("spawn_agent", json.dumps(sent)))
            forked = ran.get("fork_turns", "all") != "none"
            source = {"subagent": {"thread_spawn": {"parent_thread_id": "root", "depth": 1,
                                                    "agent_path": f"/root/{agent['id']}"}}}
            head = [_event("session_meta", {"id": agent["id"], "source": source,
                                            "forked_from_id": "root" if forked else None})]
            if forked:
                head += root_head
            read = _call("exec_command", json.dumps({"cmd": f"cat {ws}/prompts/{agent['id']}.md"}))
            calls = [read, *work.get(agent["id"], [])]
            peers.append((agent["id"], head, calls, tuple(n * number for n in PEER_TOKENS)))
        rollouts += [("root", root_head, spawns, ROOT_TOKENS), *peers]
    for name, head, calls, tokens in rollouts:
        lines = [*head, _token_count(tokens, 0.5), *calls, _token_count(tokens, 1.0)]
        text = "\n".join(lines) + "\n"
        if style == "partial":
            text += _token_count(tokens, 2.0)[:40]
        (sessions / f"rollout-2026-11-10T00-00-00-{name}.jsonl").write_text(text)


def _model_fork_turns(prompt: str) -> str | None:
    """The `fork_turns` the stand-in model sends: what the prompt asks for, unless overridden."""
    override = os.environ.get("MURMUR_FAKE_CODEX_FORK_TURNS")
    if override:
        return None if override == "omit" else override
    asked = re.search(r'`fork_turns` set to `"(\w+)"`', prompt)
    return asked[1] if asked else None


def _matches(matcher: str | None, tool_name: str) -> bool:
    """Codex's hook matcher: empty or `*` is all, plain names are exact, the rest is a regex."""
    if not matcher or matcher == "*":
        return True
    if all(ch.isascii() and (ch.isalnum() or ch in "_|") for ch in matcher):
        return tool_name in matcher.split("|")
    return re.search(matcher, tool_name) is not None


def _trusted_hash(matcher: str | None, hook: dict) -> str:
    """Codex's `hook_hash` for a PreToolUse command hook (hooks/src/engine/discovery.rs)."""
    handler = {"type": "command", "command": hook["command"], "timeout": hook.get("timeout", 600),
               "async": hook.get("async", False)}
    if hook.get("statusMessage") is not None:
        handler["statusMessage"] = hook["statusMessage"]
    identity = {"event_name": "pre_tool_use", "hooks": [handler]}
    if matcher is not None:
        identity["matcher"] = matcher
    canonical = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()}"


def _pre_tool_use(home: Path, tool_name: str, tool_input: dict) -> dict:
    """The arguments a tool call runs with once the approved PreToolUse hooks have seen it."""
    config_file = home / "config.toml"
    hooks = tomllib.loads(config_file.read_text()).get("hooks", {})
    states = hooks.get("state", {})
    for group_index, group in enumerate(hooks.get("PreToolUse", [])):
        if not _matches(group.get("matcher"), tool_name):
            continue
        for hook_index, hook in enumerate(group.get("hooks", [])):
            state = states.get(f"{config_file}:pre_tool_use:{group_index}:{hook_index}", {})
            approved = state.get("trusted_hash") == _trusted_hash(group.get("matcher"), hook)
            if hook.get("type") != "command" or state.get("enabled") is False or not approved:
                continue
            event = {"session_id": "root", "turn_id": "turn-1", "transcript_path": None,
                     "cwd": os.getcwd(), "hook_event_name": "PreToolUse", "model": "gpt-6-astra",
                     "permission_mode": "bypassPermissions", "tool_name": tool_name,
                     "tool_input": tool_input, "tool_use_id": f"call_{tool_input.get('task_name')}"}
            done = subprocess.run(hook["command"], shell=True, input=json.dumps(event),
                                  capture_output=True, text=True, timeout=hook.get("timeout", 600))
            if done.returncode != 0 or not done.stdout.strip():
                continue
            answer = json.loads(done.stdout).get("hookSpecificOutput", {})
            if answer.get("permissionDecision") == "allow" and "updatedInput" in answer:
                tool_input = answer["updatedInput"]
    return tool_input


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


def _git(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.stderr.write(result.stderr or result.stdout)
        raise SystemExit(result.returncode or 1)
    return result.stdout + result.stderr


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        raise SystemExit(0)
