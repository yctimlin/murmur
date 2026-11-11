"""Peers start without the launcher's conversation: the prompt asks, and a Codex hook enforces it."""

from __future__ import annotations

import json
import shlex
import subprocess
import tomllib
from importlib.resources import files
from pathlib import Path

import pytest

import fake_codex
from murmur.cli import SPAWN_HOOK_MATCHER, SPAWN_HOOK_TIMEOUT_S, hook_trust_hash
from murmur.spawn_hook import rewrite
from murmur.tokens import forked_peers

from support import run_cli, setup_workspace

LAUNCHER = "You are the launcher for"
ENCRYPTED = "gAAAAABq8-opaque"

# Hashes that Codex 0.163.0 itself reported (`hooks/list` on its app server, `currentHash`)
# for these hooks, with `trustStatus` "trusted" once config.toml held the same value.
CODEX_HASHES = [
    ("spawn_agent$", "/tmp/venv-fork/bin/python3 /tmp/fork-exp/runs/fix1/hooks/spawn_hook.py",
     "sha256:198cf954c3ae915118cbff4a3c8e7ad8bf2df1b674a26683da5fbd7d2c83da34"),
    ("spawn_agent", "/tmp/venv-fork/bin/python /tmp/fork-exp/runs/hook1/hooks/spawn.py",
     "sha256:78605444d6ec9771199dd9725bad53ace16e1398461c726154fa72f731d04125"),
    ("spawn_agent$", """'/opt/my tools/pythön3' '/tmp/it'"'"'s a "run"/back\\slash/hook.py'""",
     "sha256:876fded2669cd823d145d952bfb177a7d7922e4b8911cc0d30071d91d03c6c3a"),
]


def _event(tool_input, tool_name: str = "collaborationspawn_agent", **extra) -> dict:
    """A PreToolUse event the way Codex 0.163 writes it to a hook's stdin."""
    return {"session_id": "s1", "turn_id": "t1", "transcript_path": None, "cwd": "/w",
            "hook_event_name": "PreToolUse", "model": "gpt-6-astra",
            "permission_mode": "bypassPermissions", "tool_name": tool_name,
            "tool_input": tool_input, "tool_use_id": "call_1", **extra}


def _config(ws: Path) -> dict:
    return tomllib.loads((ws / "codex-home" / "config.toml").read_text())


def _rollout(ws: Path, name: str) -> str:
    sessions = ws / "codex-home" / "sessions"
    return next(sessions.rglob(f"rollout-*-{name}.jsonl")).read_text()


def _spawns(ws: Path) -> list[dict]:
    lines = (ws / "codex-home" / "fake_spawns.jsonl").read_text().splitlines()
    return [json.loads(line) for line in lines]


def _drop_hook(ws: Path) -> None:
    config = ws / "codex-home" / "config.toml"
    text = config.read_text()
    config.write_text(text[:text.index("[[hooks.PreToolUse]]")])


def _drop_approval(ws: Path) -> None:
    config = ws / "codex-home" / "config.toml"
    text = config.read_text()
    config.write_text(text[:text.index("[hooks.state.")])


@pytest.mark.parametrize("sent", [{}, {"fork_turns": "all"}, {"fork_turns": "3"}, {"fork_turns": None}])
def test_hook_makes_the_launchers_spawn_fresh_and_keeps_its_other_arguments(sent: dict):
    arguments = {"task_name": "a1", "message": ENCRYPTED, **sent}
    for tool_name in ("collaborationspawn_agent", "spawn_agent"):
        assert rewrite(_event(arguments, tool_name)) == {"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {"task_name": "a1", "message": ENCRYPTED, "fork_turns": "none"},
        }}


@pytest.mark.parametrize("event", [
    _event({"task_name": "a1", "message": ENCRYPTED, "fork_turns": "none"}),  # nothing to change
    _event({"task_name": "h1", "message": ENCRYPTED}, agent_id="peer-thread", agent_type="default"),
    _event({"timeout_ms": 1000}, "collaborationwait_agent"),
    _event({"command": "spawn_agent --help"}, "Bash"),
    _event("not an object"),
    {"hook_event_name": "PreToolUse"},
    ["not", "an", "event"],
    None,
])
def test_hook_leaves_every_other_call_alone(event):
    assert rewrite(event) is None


def test_swarm_setup_registers_the_hook_and_records_its_approval(tmp_path: Path):
    ws = setup_workspace(tmp_path, "--peers", "2")
    config_file = ws / "codex-home" / "config.toml"
    hooks = _config(ws)["hooks"]
    script = ws / "hooks" / "spawn_hook.py"
    assert script.read_text() == files("murmur").joinpath("spawn_hook.py").read_text()
    [group] = hooks["PreToolUse"]
    [hook] = group["hooks"]
    assert group["matcher"] == SPAWN_HOOK_MATCHER == "spawn_agent$"
    assert hook["type"] == "command" and hook["timeout"] == SPAWN_HOOK_TIMEOUT_S
    assert shlex.split(hook["command"])[1:] == [str(script)]
    # Only murmur's own hook is approved, under the key and hash Codex looks up.
    assert hooks["state"] == {f"{config_file}:pre_tool_use:0:0": {"trusted_hash": hook_trust_hash(
        "pre_tool_use", SPAWN_HOOK_MATCHER, hook["command"], SPAWN_HOOK_TIMEOUT_S)}}
    assert set(hooks) == {"PreToolUse", "state"}


def test_solo_setup_has_no_hook(tmp_path: Path):
    ws = setup_workspace(tmp_path, "--solo")
    assert "hooks" not in _config(ws)
    assert not (ws / "hooks").exists()


@pytest.mark.parametrize("matcher, command, expected", CODEX_HASHES)
def test_approval_hash_is_the_one_codex_computes(matcher: str, command: str, expected: str):
    assert hook_trust_hash("pre_tool_use", matcher, command, 30) == expected
    # The stand-in Codex in these tests approves hooks by the same rule.
    assert fake_codex._trusted_hash(matcher, {"type": "command", "command": command, "timeout": 30}) == expected


def test_installed_hook_command_answers_codex(tmp_path: Path):
    ws = setup_workspace(tmp_path, "--peers", "2")
    command = _config(ws)["hooks"]["PreToolUse"][0]["hooks"][0]["command"]

    def answer(stdin: str) -> subprocess.CompletedProcess:
        return subprocess.run(command, shell=True, input=stdin, capture_output=True, text=True, timeout=30)

    done = answer(json.dumps(_event({"task_name": "a1", "message": ENCRYPTED})))
    assert done.returncode == 0 and done.stderr == ""
    assert json.loads(done.stdout)["hookSpecificOutput"]["updatedInput"] == {
        "task_name": "a1", "message": ENCRYPTED, "fork_turns": "none"}
    # Anything else gets no answer and exit 0: Codex then runs the call as it is.
    for stdin in (json.dumps(_event({"timeout_ms": 5}, "collaborationwait_agent")), "not json", ""):
        done = answer(stdin)
        assert (done.returncode, done.stdout, done.stderr) == (0, "", "")


def _assert_fresh(ws: Path, result: subprocess.CompletedProcess) -> None:
    assert LAUNCHER in _rollout(ws, "root")
    for peer in ("a1", "a2"):
        rollout = _rollout(ws, peer)
        assert LAUNCHER not in rollout and "fork_turns" not in rollout
        assert json.loads(rollout.splitlines()[0])["payload"]["forked_from_id"] is None
    assert [spawn["ran"]["fork_turns"] for spawn in _spawns(ws)] == ["none", "none"]
    assert forked_peers(ws) == 0
    assert json.loads((ws / "logs" / "run.json").read_text())["forked_peers"] == 0
    assert "launcher's conversation" not in result.stderr


def test_model_that_follows_the_prompt_spawns_fresh_peers(tmp_path: Path):
    ws = setup_workspace(tmp_path, "--peers", "2")
    result = run_cli("run", str(ws), extra_env={"MURMUR_FAKE_CODEX_MODE": "commit"})
    assert result.returncode == 0, result.stderr
    assert [spawn["sent"] for spawn in _spawns(ws)] == [
        {"task_name": "a1", "message": "prompts/a1.md", "fork_turns": "none"},
        {"task_name": "a2", "message": "prompts/a2.md", "fork_turns": "none"},
    ]
    _assert_fresh(ws, result)


def test_prompt_alone_spawns_fresh_peers(tmp_path: Path):
    """A Codex that does not run the hook still gets `fork_turns` from the launcher's prompt."""
    ws = setup_workspace(tmp_path, "--peers", "2")
    _drop_hook(ws)
    result = run_cli("run", str(ws), extra_env={"MURMUR_FAKE_CODEX_MODE": "commit"})
    assert result.returncode == 0, result.stderr
    _assert_fresh(ws, result)


@pytest.mark.parametrize("model", ["omit", "all"])
def test_hook_alone_spawns_fresh_peers(tmp_path: Path, model: str):
    """A model that ignores the prompt cannot fork the launcher: the hook rewrites its calls."""
    ws = setup_workspace(tmp_path, "--peers", "2")
    result = run_cli("run", str(ws), extra_env={"MURMUR_FAKE_CODEX_MODE": "commit",
                                                "MURMUR_FAKE_CODEX_FORK_TURNS": model})
    assert result.returncode == 0, result.stderr
    assert [spawn["sent"].get("fork_turns") for spawn in _spawns(ws)] == [
        None if model == "omit" else model] * 2
    _assert_fresh(ws, result)


@pytest.mark.parametrize("disable", [_drop_hook, _drop_approval])
def test_forked_peers_are_reported(tmp_path: Path, disable):
    """Without the hook (or its approval) and with a model that ignores the prompt, Codex copies
    the launcher's conversation into each peer. The run says so."""
    ws = setup_workspace(tmp_path, "--peers", "2")
    disable(ws)
    result = run_cli("run", str(ws), extra_env={"MURMUR_FAKE_CODEX_MODE": "commit",
                                                "MURMUR_FAKE_CODEX_FORK_TURNS": "omit"})
    assert result.returncode == 0, result.stderr
    for peer in ("a1", "a2"):
        rollout = _rollout(ws, peer)
        assert LAUNCHER in rollout
        assert json.loads(rollout.splitlines()[0])["payload"]["forked_from_id"] == "root"
    assert forked_peers(ws) == 2
    assert json.loads((ws / "logs" / "run.json").read_text())["forked_peers"] == 2
    assert "murmur: 2 peer(s) started with a copy of the launcher's conversation" in result.stderr


def test_only_the_launchers_own_forked_peers_count(tmp_path: Path):
    sessions = tmp_path / "codex-home" / "sessions"
    sessions.mkdir(parents=True)

    def rollout(name: str, meta: dict | None, tail: str = "") -> None:
        first = json.dumps({"type": "session_meta", "payload": meta}) + "\n" if meta else ""
        (sessions / f"{name}.jsonl").write_text(first + tail)

    def spawned(depth: int) -> dict:
        return {"subagent": {"thread_spawn": {"parent_thread_id": "p", "depth": depth}}}

    rollout("root", {"id": "r", "forked_from_id": None, "source": "exec"})
    rollout("fresh", {"id": "a1", "forked_from_id": None, "source": spawned(1)})
    rollout("forked", {"id": "a2", "forked_from_id": "r", "source": spawned(1)})
    rollout("helper", {"id": "h", "forked_from_id": "a1", "source": spawned(2)})  # a peer's own fork
    rollout("review", {"id": "v", "forked_from_id": "r", "source": {"subagent": "review"}})
    rollout("resumed", {"id": "u", "forked_from_id": "r", "source": "exec"})
    rollout("old", {"id": "o"})
    rollout("empty", None)
    rollout("cut", None, '{"type": "session_meta", "payl')
    assert forked_peers(tmp_path) == 1
    assert forked_peers(tmp_path / "nowhere") == 0
