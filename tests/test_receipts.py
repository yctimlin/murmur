"""Change receipts: who made each commit of a run, why, and how it was verified."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

from murmur import receipts
from support import run_cli, setup_workspace

T0 = 1_800_000_000  # a fixed clock, so commits and log events line up the same way every time
_opened: list[str] = []
_watching = False


def _audit(event: str, args: tuple) -> None:
    if _watching and event in ("open", "sqlite3.connect"):
        _opened.append(str(args[0]))


sys.addaudithook(_audit)


def _stamp(at: float) -> str:
    return datetime.fromtimestamp(at, timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


class Run:
    """A set-up workspace plus what a run would have left in it: commits, rollouts and a board."""

    def __init__(self, tmp_path: Path, *setup: str) -> None:
        self.ws = setup_workspace(tmp_path, *(setup or ("--peers", "2")))
        self.meta = json.loads((self.ws / "murmur.json").read_text())
        self.origin = self.ws / "work" / "origin.git"
        self.clock = float(T0)
        self.lines: dict[str, list[str]] = {}
        self.posts: list[tuple] = []

    def tick(self, seconds: float = 10) -> float:
        self.clock += seconds
        return self.clock

    def clone(self, agent: str) -> Path:
        return Path(next(item["clone"] for item in self.meta["agents"] if item["id"] == agent))

    def git(self, agent: str, *args: str, check: bool = True) -> str:
        date = f"{int(self.clock)} +0000"
        env = {**os.environ, "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
        done = subprocess.run(["git", *args], cwd=self.clone(agent), env=env, capture_output=True, text=True)
        assert done.returncode == 0 or not check, done.stderr
        return done.stdout + done.stderr

    def _event(self, agent: str, kind: str, payload: dict) -> None:
        line = json.dumps({"timestamp": _stamp(self.tick(1)), "type": kind, "payload": payload})
        self.lines.setdefault(agent, []).append(line)

    def command(self, agent: str, script: str, exit_code: int | None = 0, output: str = "") -> None:
        item = {"type": "CommandExecution", "command": ["/bin/bash", "-lc", script],
                "cwd": f"file://{self.clone(agent)}", "aggregated_output": output, "exit_code": exit_code}
        self._event(agent, "event_msg", {"type": "item_completed", "item": item})

    def say(self, agent: str, text: str) -> None:
        self._event(agent, "response_item", {"type": "message", "role": "assistant", "phase": "commentary",
                                             "content": [{"type": "output_text", "text": text}]})

    def commit(self, agent: str, message: str = "Add a file", *, branch: str = "main", name: str | None = None,
               logged: bool = True, push: bool = True) -> str:
        """Commit a new file in the agent's clone and push it, logging the command like Codex does."""
        self.tick()
        name = name or f"{agent}-{int(self.clock)}.txt"
        (self.clone(agent) / name).write_text(f"{name}\n")
        self.git(agent, "add", name)
        output = self.git(agent, "commit", "-m", message)
        if push:
            output += self.git(agent, "push", "origin", f"HEAD:{branch}")
        if logged:
            self.command(agent, f"git add {name} && git commit -m ... && git push origin HEAD:{branch}", 0, output)
        return self.git(agent, "rev-parse", "HEAD").strip()

    def post(self, agent: str, text: str, channel: str = "tasks") -> None:
        self.posts.append((channel, f"/root/{agent}", int(self.tick(1) * 1e6), json.dumps({"text": text})))

    def write(self, *, sessions: bool = True, board: bool = True, wal: bool = False):
        """Write the rollouts and the board. With `wal`, returns the open connection that keeps
        the posts in the `-wal` file, the way a stopped Codex leaves them."""
        home = self.ws / "codex-home"
        folder = home / "sessions" / "2027" / "01" / "15"
        folder.mkdir(parents=True, exist_ok=True)
        for agent, lines in (self.lines.items() if sessions else ()):
            source = "exec" if agent in ("solo", "root") else {
                "subagent": {"thread_spawn": {"depth": 1, "agent_path": f"/root/{agent}"}}}
            meta = {"timestamp": _stamp(T0), "type": "session_meta", "payload": {"id": agent, "source": source}}
            (folder / f"rollout-{agent}.jsonl").write_text("\n".join([json.dumps(meta), *lines]) + "\n")
        if not (board and self.posts):
            return None
        db = sqlite3.connect(home / receipts.BOARD_DB)
        if wal:
            db.execute("PRAGMA journal_mode=WAL")
        db.execute("CREATE TABLE posts (seq INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT, author TEXT, "
                   "timestamp INTEGER, payload TEXT)")
        db.executemany("INSERT INTO posts (channel, author, timestamp, payload) VALUES (?, ?, ?, ?)", self.posts)
        db.commit()
        if wal:
            return db
        db.close()
        return None

    def collect(self) -> dict:
        return receipts.collect(self.ws)

    def receipt(self, sha: str) -> dict:
        return next(item for item in self.collect()["receipts"] if item["sha"] == sha)


# --- which commands count as checks, and when their exit status can be trusted ----------


@pytest.mark.parametrize("script, kind, at_zero, at_one", [
    ("python3 -m unittest -q", "test", "passed", "failed"),
    ("pytest -q > out.txt 2>&1", "test", "passed", "failed"),
    ("cd pkg && pytest -q", "test", "passed", "failed"),
    ("(cd pkg && pytest)", "test", "passed", "failed"),
    # A later command in the chain may be the one that failed (a rejected push, say).
    ("pytest -q && git commit -m x && git push origin HEAD:main", "test", "passed", "unclear"),
    ("(cd pkg && pytest) && echo ok", "test", "passed", "unclear"),
    ("set -euo pipefail\npytest -q | tail -3\ngit status", "test", "passed", "unclear"),
    ("set -o pipefail; pytest -q | tail -3", "test", "passed", "failed"),
    ("set -eo pipefail; pytest -q | tail -3", "test", "passed", "failed"),
    # The exit status belongs to another command, or a failure is swallowed.
    ("pytest -q | tail -5", "test", "unclear", "unclear"),
    ("pytest -q; git status --short", "test", "unclear", "unclear"),
    ("pytest -q || true", "test", "unclear", "unclear"),
    ("git status || pytest -q", "test", "unclear", "failed"),
    ("if go test ./...; then echo ok; fi", "test", "unclear", "unclear"),
    ("PYTHONPATH=src .venv/bin/python -m pytest tests/", "test", "passed", "failed"),
    ("uv run pytest", "test", "passed", "failed"),
    ("timeout 60 npm run test", "test", "passed", "failed"),
    ("npx --yes vitest run", "test", "passed", "failed"),
    ("make -C build test", "test", "passed", "failed"),
    ("ruff check .", "lint", "passed", "failed"),
    ("pnpm typecheck", "lint", "passed", "failed"),
    ("python -m py_compile wordstats.py", "lint", "passed", "failed"),
    ("npm run build", "build", "passed", "failed"),
    ("cargo build --release", "build", "passed", "failed"),
])
def test_checks_are_recognised(script: str, kind: str, at_zero: str, at_one: str):
    for exit_code, result in ((0, at_zero), (1, at_one), (None, "unknown")):
        found = receipts.checks_in(script, exit_code)
        assert [(kind_, result_) for kind_, _command, result_, _checkout in found] == [(kind, result)], exit_code


@pytest.mark.parametrize("script", [
    "cat test_wordstats.py",
    "grep -rn unittest .",
    "git commit -m 'run pytest && npm test'",
    'echo "pytest -q; npm test"',
    "cat > PR.md <<'EOF'\nVerify with:\npytest -q\nnpm test\nEOF",
    "python3 - <<PY\nprint('ok')\nPY\ngit status",
    "python3 wordstats.py --top 3 notes.txt",
    "git push origin HEAD:main",
    "",
])
def test_text_that_only_mentions_a_check_is_not_one(script: str):
    assert receipts.checks_in(script, 0) == []


def test_a_script_can_hold_several_checks():
    assert receipts.checks_in("ruff check . && python -m pytest -q && npm run build", 0) == [
        ("lint", "ruff check .", "passed", None), ("test", "python -m pytest -q", "passed", None),
        ("build", "npm run build", "passed", None)]
    assert receipts.checks_in("cat > notes.md <<EOF\nnpm test\nEOF\nnpm test", 1) == [
        ("test", "npm test", "failed", None)]


@pytest.mark.parametrize("script, checkout", [
    ("git fetch origin && git switch --detach origin/draft/a2 && pytest -q", "git switch --detach origin/draft/a2"),
    ("git checkout -q draft/a1\npytest -q\ngit checkout -q main", "git checkout -q draft/a1"),
    ("git -C ../a2 checkout abc1234 && pytest -q", "git -C ../a2 checkout abc1234"),
    ("pytest -q && git checkout main", None),
    ("git checkout -b feature && pytest -q", None),
    ("git switch -c feature && pytest -q", None),
    ("git checkout -- README.md && pytest -q", None),
    ("git status && pytest -q", None),
])
def test_a_checkout_before_a_check_is_noted(script: str, checkout: str | None):
    assert [found[3] for found in receipts.checks_in(script, 0)] == [checkout]


# --- redaction ---------------------------------------------------------------------------


def test_redaction_masks_credentials_and_personal_paths(tmp_path: Path):
    ws = tmp_path / "runs" / "r1"
    redact = receipts.Redactor(ws)
    home = str(Path.home())
    text = redact(
        f"cd {ws}/work/peers/a1 && cat {home}/notes.txt /Users/alice/x /home/bob/y\n"
        "OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz012345 curl -H 'Authorization: Bearer abcdefghijklmnop1234'\n"
        'export GITHUB_TOKEN=ghp_abcdefghijklmnopqrstuvwxyz0123456789 {"password": "hunter2hunter2"}\n'
        "aws AKIAABCDEFGHIJKLMNOP eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.c2lnbmF0dXJl sk-b6f01***c2ef6\n"
    )
    assert "<workspace>/work/peers/a1" in text and "~/notes.txt" in text
    for secret in ("sk-proj", "abcdefghijklmnop1234", "ghp_", "hunter2", "AKIA", "eyJ", "c2ef6",
                   home, "alice", "bob", str(tmp_path)):
        assert secret not in text, secret
    assert "OPENAI_API_KEY=[redacted]" in text and "Bearer [redacted]" in text


def test_redaction_drops_terminal_control_sequences(tmp_path: Path):
    redact = receipts.Redactor(tmp_path)
    assert redact("\x1b[32m3 passed\x1b[0m in 0.1s\x07\x1b]0;title\x1b\\") == "3 passed in 0.1s0;title"
    assert redact("10%\r50%\r100%\r\ndone\tok") == "10%\n50%\n100%\ndone\tok"


def test_redaction_leaves_ordinary_text_alone(tmp_path: Path):
    redact = receipts.Redactor(tmp_path)
    for text in ("Ran 4 tests in 0.001s", "max_output_tokens: 12000", "risk-based task-list for a1",
                 "281c672..f4a3599  HEAD -> main", "token = 5", "tokenizer: implemented for unicode",
                 "tokens: 935,222 input (857,728 cached)", "see https://example.com/home/page",
                 "Secrets: redaction of credential-like strings"):
        assert redact(text) == text


def test_long_output_keeps_its_end_and_long_text_is_cut(tmp_path: Path):
    redact = receipts.Redactor(tmp_path)
    output = "\n".join(f"line {number}" for number in range(500)) + "\nRan 3 tests\nOK\n"
    excerpt = redact.excerpt(output, whole=True)
    assert excerpt.startswith("[...]\n") and excerpt.endswith("Ran 3 tests\nOK")
    assert len(excerpt.splitlines()) == receipts.MAX_OUTPUT_LINES + 1
    assert len(redact.excerpt("x" * 100_000, whole=True)) <= receipts.MAX_OUTPUT
    clipped = redact.clip("word " * 1000)
    assert len(clipped) < receipts.MAX_TEXT + 40 and clipped.endswith("more chars]")


def test_excerpt_prefers_the_runners_verdict_when_other_commands_follow(tmp_path: Path):
    output = "Ran 2 tests in 0.000s\n\nOK\n" + "\n".join(f"+ diff line {n}" for n in range(40))
    assert receipts.Redactor(tmp_path).excerpt(output, whole=False) == "[...]\nRan 2 tests in 0.000s\nOK"


# --- reading session logs ----------------------------------------------------------------


def _write_rollout(ws: Path, name: str, lines: list) -> Path:
    folder = ws / "codex-home" / "sessions"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text("".join(line if isinstance(line, str) else json.dumps(line) + "\n" for line in lines))
    return path


def _item(script: str, exit_code=0, output: str = "", at: float = T0) -> dict:
    item = {"type": "CommandExecution", "command": ["/bin/bash", "-lc", script], "cwd": "file:///ws/work",
            "aggregated_output": output, "exit_code": exit_code}
    return {"timestamp": _stamp(at), "type": "event_msg", "payload": {"type": "item_completed", "item": item}}


def test_session_reader_skips_what_it_cannot_use(tmp_path: Path):
    path = _write_rollout(tmp_path, "r.jsonl", [
        {"type": "session_meta", "payload": {"id": "x", "agent_path": "/root/a2"}},
        {"type": "session_meta", "payload": {"id": "parent", "source": "exec"}},  # a fork's copy of its parent
        "not json at all\n",
        "[1, 2, 3]\n",
        {"type": "event_msg", "payload": "a string"},
        {"timestamp": _stamp(T0), "type": "a_new_event_type", "payload": {"type": "surprise", "item": 7}},
        {"type": "event_msg", "payload": {"type": "item_completed", "item": {"type": "FileChange"}}},
        _item("pytest -q", 1, "1 failed", at=T0 + 5),
        {"type": "response_item", "payload": {"type": "message", "role": "user",
                                              "content": [{"type": "input_text", "text": "the brief"}]}},
        {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": "odd"}},
        {"timestamp": "yesterday", "type": "response_item",
         "payload": {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "hi"}]}},
        {"type": "event_msg", "payload": {"type": "task_complete", "last_agent_message": "all done"}},
        '{"timestamp": "2027-01-15T08:0',  # the run was stopped mid-write
    ])
    session = receipts.read_session(path, tmp_path)
    assert session["agent"] == "a2" and session["final"] == "all done"
    assert [(event["kind"], event["line"]) for event in session["events"]] == [("command", 8), ("say", 11)]
    command, said = session["events"]
    assert (command["script"], command["exit_code"], command["cwd"]) == ("pytest -q", 1, "/ws/work")
    assert said["text"] == "hi" and said["at"] == command["at"] == T0 + 5  # a bad stamp keeps the last good one


def test_a_forked_session_does_not_repeat_its_parents_commands(tmp_path: Path):
    own = {"type": "session_meta", "payload": {"id": "child", "forked_from_id": "parent", "agent_path": "/root/a1"}}
    parent = {"type": "session_meta", "payload": {"id": "parent", "source": "exec"}}
    settings = {"type": "event_msg", "payload": {"type": "thread_settings_applied", "thread_id": "child"}}
    lines = [own, parent, _item("pytest -q", 1), settings, _item("npm test", 0), settings, _item("ruff check .", 0)]
    session = receipts.read_session(_write_rollout(tmp_path, "forked.jsonl", lines), tmp_path)
    assert [event["script"] for event in session["events"]] == ["npm test", "ruff check ."]
    own["payload"]["forked_from_id"] = None
    fresh = receipts.read_session(_write_rollout(tmp_path, "fresh.jsonl", lines), tmp_path)
    assert [event["script"] for event in fresh["events"]] == ["pytest -q", "npm test", "ruff check ."]


def test_session_reader_falls_back_to_plain_tool_calls(tmp_path: Path):
    def call(call_id: str, arguments: dict) -> dict:
        return {"timestamp": _stamp(T0), "type": "response_item",
                "payload": {"type": "function_call", "name": "exec_command", "call_id": call_id,
                            "arguments": json.dumps(arguments)}}

    def output(call_id: str, value) -> dict:
        return {"timestamp": _stamp(T0 + 3), "type": "response_item",
                "payload": {"type": "function_call_output", "call_id": call_id, "output": value}}

    lines = [
        call("c1", {"cmd": "pytest -q", "workdir": "/ws/work/repo"}),
        output("c1", json.dumps({"output": "2 passed", "metadata": {"exit_code": 0}})),
        call("c2", {"command": ["bash", "-lc", "npm test"]}),
        output("c2", "plain text with no status"),
        call("c3", {"cmd": "ruff check ."}),  # never answered
        {"type": "response_item", "payload": {"type": "function_call", "name": "spawn_agent", "arguments": "{}"}},
    ]
    session = receipts.read_session(_write_rollout(tmp_path, "calls.jsonl", lines), tmp_path)
    assert [(e["script"], e["exit_code"], e["output"]) for e in session["events"]] == [
        ("pytest -q", 0, "2 passed"), ("npm test", None, "plain text with no status"), ("ruff check .", None, "")]
    assert session["events"][0]["cwd"] == "/ws/work/repo" and session["agent"] == "root"
    # Next to Codex's own record of the commands, the calls would count each one twice.
    both = receipts.read_session(_write_rollout(tmp_path, "both.jsonl", [*lines, _item("pytest -q")]), tmp_path)
    assert [event["script"] for event in both["events"]] == ["pytest -q"]


# --- receipts from a workspace -----------------------------------------------------------


def test_observed_check_is_tied_to_the_commit_by_its_sha(tmp_path: Path):
    run = Run(tmp_path)
    run.say("a1", "I will add the parser and test it.")
    run.command("a1", "python3 -m unittest -q", 0, "Ran 4 tests in 0.001s\n\nOK\n")
    sha = run.commit(
        "a1", "Add the parser\n\nIt reads flags in any order.\n\nVerified: python3 -m unittest -q (4 tests)")
    run.write()
    document = run.collect()
    receipt = document["receipts"][0]
    assert (receipt["sha"], receipt["short"], receipt["subject"]) == (sha, sha[:7], "Add the parser")
    assert receipt["base_sha"] == run.meta["base"] and receipt["parents"] == [run.meta["base"]]
    assert receipt["who"] == {"agent": "a1", "author": "a1 <a1@murmur.local>", "committer": None,
                              "integrated_by": None}
    assert receipt["on_main"] and receipt["branches"] == ["main"]
    assert receipt["when"]["authored_at"] == receipt["when"]["committed_at"]
    assert receipt["when"]["pushed"]["main"].endswith("Z")
    change = receipt["change"]
    assert (change["files"], change["insertions"], change["deletions"], change["paths_omitted"]) == (1, 1, 0, 0)
    assert change["paths"][0]["path"].startswith("a1-") and change["paths"][0]["insertions"] == 1
    why = receipt["why"]
    assert "It reads flags in any order." in why["message"]
    assert why["intent"]["text"] == "I will add the parser and test it."
    assert why["intent"]["source"] == {"rollout": "codex-home/sessions/2027/01/15/rollout-a1.jsonl", "line": 2}
    verified = receipt["verification"]
    assert (verified["status"], verified["linked_by"], verified["certainty"]) == (
        "observed-pass", "commit-output", "observed")
    assert verified["commit_source"]["line"] == 4
    [check] = verified["checks"]
    assert check == {
        "kind": "test", "command": "python3 -m unittest -q", "exit_code": 0, "result": "passed", "when": "before",
        "checkout": None,
        "at": check["at"], "cwd": "work/peers/a1", "output_excerpt": "Ran 4 tests in 0.001s\nOK",
        "source": {"rollout": "codex-home/sessions/2027/01/15/rollout-a1.jsonl", "line": 3},
    }
    assert verified["claims"] == [
        {"source": "commit-message", "text": "Verified: python3 -m unittest -q (4 tests)", "not_run": False,
         "agent": "a1", "at": receipt["when"]["authored_at"], "seq": None}]
    run_facts = document["run"]
    assert (run_facts["mode"], run_facts["base"], run_facts["head"]) == ("swarm", run.meta["base"], sha)
    assert (run_facts["commits_on_main"], run_facts["commits_off_main"], run_facts["finished"]) == (1, 0, False)
    assert document["schema"] == receipts.SCHEMA
    assert json.loads(receipts.to_json(document)) == document


def test_claimed_is_not_observed_and_not_run_is_not_a_claim(tmp_path: Path):
    run = Run(tmp_path, "--peers", "3")
    claimed = run.commit("a1", "Add a\n\nVerified: ran the unit tests, all green")
    run.git("a2", "pull", "-q", "--rebase", "origin", "main")
    stated = run.commit("a2", "Add b\n\nVerified: not run")
    run.git("a3", "pull", "-q", "--rebase", "origin", "main")
    silent = run.commit("a3", "Add c")
    run.write()
    assert run.receipt(claimed)["verification"]["status"] == "claimed"
    assert run.receipt(claimed)["verification"]["summary"] == (
        "an agent says this was verified, but no test, lint or build command in a1's session log before this commit")
    assert run.receipt(stated)["verification"]["status"] == "none"
    assert run.receipt(stated)["verification"]["claims"][0]["not_run"] is True
    assert "stated that no check was run" in run.receipt(stated)["verification"]["summary"]
    assert run.receipt(silent)["verification"] == {
        "status": "none", "summary": "no test, lint or build command in a3's session log before this commit",
        "checks": [], "claims": [], "linked_by": "commit-output", "certainty": "observed",
        "commit_source": {"rollout": "codex-home/sessions/2027/01/15/rollout-a3.jsonl", "line": 2}}
    text = receipts.render_text(run.collect())
    assert "verified: CLAIMED only" in text and text.count("verified: NOT OBSERVED") == 2
    assert 'claim (commit message): "Verified: ran the unit tests, all green"' in text


def test_a_failing_last_run_is_reported_as_failed(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q", 0, "3 passed")
    run.command("a1", "pytest -q", 1, "1 failed, 2 passed")
    run.command("a1", "ruff check .", 0, "All checks passed!")
    sha = run.commit("a1", "Ship it\n\nVerified: pytest -q (3 passed)")
    run.write()
    verified = run.receipt(sha)["verification"]
    assert verified["status"] == "observed-fail" and verified["summary"] == (
        "the last test run with an exit status of its own in a1's session log exited non-zero")
    assert [(check["kind"], check["result"]) for check in verified["checks"]] == [
        ("test", "passed"), ("test", "failed"), ("lint", "passed")]
    text = receipts.render_text(run.collect())
    assert "verified: OBSERVED, FAILED" in text and "FAIL exit 1  pytest -q" in text
    assert 'claim (commit message): "Verified: pytest -q (3 passed)"' in text  # shown next to what was seen


def test_a_failed_push_is_not_a_failed_test(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q && git push origin HEAD:main", 1, "3 passed\n ! [rejected] HEAD -> main (fetch first)")
    sha = run.commit("a1")
    run.write()
    verified = run.receipt(sha)["verification"]
    assert verified["status"] == "observed-unclear" and verified["checks"][0]["result"] == "unclear"
    assert verified["checks"][0]["output_excerpt"] == "[...]\n3 passed"


def test_a_fixed_failure_counts_as_passed(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q", 1, "1 failed")
    run.command("a1", "pytest -q", 0, "3 passed")
    sha = run.commit("a1")
    run.write()
    assert run.receipt(sha)["verification"]["status"] == "observed-pass"


def test_a_later_unclear_run_does_not_undo_a_clear_one(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q", 0, "3 passed")
    run.command("a1", "pytest -q; git status --short", 0, "3 passed")
    run.command("a1", "ruff check . | tail -2", 0, "")
    passed = run.commit("a1", "First")
    run.command("a1", "pytest -q", 1, "1 failed")
    run.command("a1", "pytest -q | tail -1", 0, "1 failed")
    failed = run.commit("a1", "Second")
    run.write()
    verified = run.receipt(passed)["verification"]
    assert verified["status"] == "observed-pass" and verified["summary"] == (
        "the last test run with an exit status of its own in a1's session log exited 0; "
        "a later test and lint run has no exit status of its own")
    assert [check["result"] for check in verified["checks"]] == ["passed", "unclear", "unclear"]
    assert run.receipt(failed)["verification"]["status"] == "observed-fail"


def test_a_masked_exit_status_is_unclear(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q | tail -3", 0, "3 passed")
    run.command("a1", "npm test", None, "")
    sha = run.commit("a1")
    run.write()
    verified = run.receipt(sha)["verification"]
    assert verified["status"] == "observed-unclear"
    assert [check["result"] for check in verified["checks"]] == ["unclear", "unknown"]
    assert "verified: OBSERVED, result unclear" in receipts.render_text(run.collect())


def test_checks_go_to_the_commit_they_came_before(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q", 0, "1 passed")
    first = run.commit("a1", "First")
    second = run.commit("a1", "Second")
    run.command("a1", "npm run build", 0, "built")
    run.command("a1", "pytest -q && git commit -q -m Third && git push -q origin HEAD:main", 0, "")  # not this run's
    third = run.commit("a1", "Third")
    run.command("a1", "pytest -q", 1, "1 failed")
    run.write()
    checks = {sha: [(c["command"], c["when"]) for c in run.receipt(sha)["verification"]["checks"]]
              for sha in (first, second, third)}
    assert checks[first] == [("pytest -q", "before")]
    assert checks[second] == []
    assert checks[third] == [("npm run build", "before"), ("pytest -q", "before"), ("pytest -q", "after")]
    assert run.receipt(second)["verification"]["status"] == "none"
    # What ran after the last commit is listed, but it may be about another tree: it is not graded.
    assert run.receipt(third)["verification"]["status"] == "observed-pass"
    assert "FAIL exit 1  pytest -q\n                 test, after the commit (not counted)" in (
        receipts.render_text(run.collect()))
    a1 = next(agent for agent in run.collect()["agents"] if agent["id"] == "a1")
    assert (a1["commits"], a1["checks"], a1["checks_without_commit"]) == (3, 4, [])


def test_checks_after_the_last_commit_or_on_another_checkout_do_not_grade(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "git switch -q --detach origin/draft/a2 && python3 -m unittest -q", 1, "FAILED (failures=1)")
    sha = run.commit("a1", "Commit first\n\nVerified: python3 -m unittest -q")
    run.command("a1", "python3 -m unittest -q", 0, "OK")
    run.write()
    verified = run.receipt(sha)["verification"]
    assert verified["status"] == "claimed" and verified["summary"] == (
        "an agent says this was verified, but no test, lint or build command in a1's session log "
        "before this commit (2 listed but not counted: run after the commit or on another checkout)")
    assert [(check["when"], check["result"], check["checkout"]) for check in verified["checks"]] == [
        ("before", "failed", "git switch -q --detach origin/draft/a2"), ("after", "passed", None)]
    text = receipts.render_text(run.collect())
    assert ("run after `git switch -q --detach origin/draft/a2` in the same command line: "
            "another checkout (not counted)") in text


def test_a_check_in_the_commit_command_is_marked(tmp_path: Path):
    run = Run(tmp_path)
    run.tick()
    (run.clone("a1") / "x.txt").write_text("x\n")
    run.git("a1", "add", "x.txt")
    output = run.git("a1", "commit", "-m", "Add x") + run.git("a1", "push", "origin", "HEAD:main")
    run.command("a1", "pytest -q && git add x.txt && git commit -m 'Add x' && git push origin HEAD:main", 0, output)
    run.write()
    [receipt] = run.collect()["receipts"]
    assert [(c["when"], c["result"]) for c in receipt["verification"]["checks"]] == [("with", "passed")]
    assert "in the commit command" in receipts.render_text(run.collect())


def test_a_rebased_commit_is_tied_by_author_time_and_marked_inferred(tmp_path: Path):
    run = Run(tmp_path)
    run.commit("a2", "Other work")
    run.command("a1", "pytest -q", 0, "2 passed")
    old = run.commit("a1", "Mine", push=False)  # the log names the SHA from before the rebase
    run.tick(30)
    run.git("a1", "pull", "-q", "--rebase", "origin", "main")
    run.git("a1", "push", "-q", "origin", "HEAD:main")
    new = run.git("a1", "rev-parse", "HEAD").strip()
    assert new != old
    run.write()
    receipt = run.receipt(new)
    verified = receipt["verification"]
    assert (verified["linked_by"], verified["certainty"], verified["status"]) == (
        "author-time", "inferred", "observed-pass")
    assert receipt["when"]["authored_at"] < receipt["when"]["committed_at"]
    assert "tied to this commit by its author time" in receipts.render_text(run.collect())


def test_an_unlogged_commit_is_placed_by_time_alone(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q", 0, "2 passed")
    first = run.commit("a1", "First", logged=False)
    run.command("a1", "pytest -q", 1, "1 failed")
    second = run.commit("a1", "Second", logged=False)
    run.write()
    assert [c["result"] for c in run.receipt(first)["verification"]["checks"]] == ["passed"]
    assert run.receipt(first)["verification"]["linked_by"] == "author-time"
    assert run.receipt(second)["verification"]["status"] == "observed-fail"
    assert run.receipt(second)["verification"]["commit_source"] is None


def test_a_draft_and_its_rebased_copy_share_their_evidence(tmp_path: Path):
    run = Run(tmp_path)
    run.commit("a2", "Other work")
    run.command("a1", "pytest -q", 0, "2 passed")
    draft = run.commit("a1", "Draft\n\nVerified: pytest -q", branch="draft/a1")
    run.tick(30)
    run.git("a1", "pull", "-q", "--rebase", "origin", "main")
    run.git("a1", "push", "-q", "origin", "HEAD:main")
    landed = run.git("a1", "rev-parse", "HEAD").strip()
    run.write()
    document = run.collect()
    assert [receipt["sha"] for receipt in document["receipts"]][-1] == draft  # off main comes last
    on_draft, on_main = run.receipt(draft), run.receipt(landed)
    assert (on_draft["on_main"], on_draft["branches"]) == (False, ["draft/a1"])
    assert (on_main["on_main"], on_main["branches"]) == (True, ["main"])
    assert "draft/a1" in on_draft["when"]["pushed"] and "main" in on_main["when"]["pushed"]
    for receipt in (on_draft, on_main):
        assert [c["result"] for c in receipt["verification"]["checks"]] == ["passed"]
    assert (document["run"]["commits_on_main"], document["run"]["commits_off_main"]) == (2, 1)
    text = receipts.render_text(document)
    assert "not on main:" in text and "on draft/a1, pushed to draft/a1" in text


def test_a_reviewers_checks_stay_with_the_reviewer(tmp_path: Path):
    run = Run(tmp_path, "--peers", "3")
    sha = run.commit("a1")
    run.command("a2", "git pull -q origin main && pytest -q", 0, "9 passed")
    run.write()
    document = run.collect()
    assert run.receipt(sha)["verification"]["status"] == "none"  # a1 itself ran nothing
    agents = {agent["id"]: agent for agent in document["agents"]}
    assert {name: agent["checks"] for name, agent in agents.items()} == {"root": 0, "a1": 0, "a2": 1, "a3": 0}
    [review] = agents["a2"]["checks_without_commit"]
    assert (review["command"], review["result"], review["when"]) == ("pytest -q", "passed", "no-commit")
    text = receipts.render_text(document)
    assert "a2 made no commits; checks in its session log (1):\n  ok   exit 0  pytest -q" in text
    assert "a3 made no commits and ran no checks" in text and "root made" not in text
    markdown = receipts.render_markdown(document)
    assert "## Agents without commits" in markdown and "ok   exit 0  pytest -q" in markdown


def test_a_commit_applied_by_another_agent_names_both(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q", 0, "2 passed")
    draft = run.commit("a1", "Draft", branch="draft/a1")
    run.tick(60)
    run.git("a2", "fetch", "-q", "origin", "draft/a1")
    output = run.git("a2", "cherry-pick", "FETCH_HEAD")
    run.git("a2", "push", "-q", "origin", "HEAD:main")
    run.command("a2", "git cherry-pick FETCH_HEAD && git push origin HEAD:main", 0, output)
    picked = run.git("a2", "rev-parse", "HEAD").strip()
    run.write()
    receipt = run.receipt(picked)
    assert receipt["who"] == {"agent": "a1", "author": "a1 <a1@murmur.local>",
                              "committer": "a2 <a2@murmur.local>", "integrated_by": "a2"}
    assert receipt["verification"]["status"] == "observed-pass"  # the author's own test run
    assert run.receipt(draft)["who"]["committer"] is None
    assert "committed by a2 <a2@murmur.local>" in receipts.render_text(run.collect())


def test_board_posts_are_linked_by_sha_or_by_time(tmp_path: Path):
    run = Run(tmp_path)
    run.post("a2", "a2 claims the docs")
    run.post("a1", "a1 claims the parser")
    sha = run.commit("a1", "Add the parser")
    run.post("a1", f"DONE parser on origin/main at {sha[:7]}; verified with the unit tests")
    run.post("a2", f"FACT reviewed {sha[:10]}: flags work in any order")
    run.post("a2", "RANKING: nothing to do with deadbeef1234")
    run.post("a1", "moving on to the README")
    later = run.commit("a1", "Add the README")
    run.write()
    board = run.receipt(sha)["why"]["board"]
    assert [(post["agent"], post["link"], post["certainty"]) for post in board] == [
        ("a1", "before-commit", "inferred"), ("a1", "names-commit", "observed"), ("a2", "names-commit", "observed")]
    assert board[0]["text"] == "a1 claims the parser" and board[0]["channel"] == "tasks"
    # The DONE post is from before the second commit too, but it names the first: it stays there.
    assert [post["text"] for post in run.receipt(later)["why"]["board"]] == ["moving on to the README"]
    verified = run.receipt(sha)["verification"]
    assert verified["status"] == "claimed"
    [claim] = verified["claims"]
    assert (claim["source"], claim["agent"], claim["seq"], claim["at"]) == ("board", "a1", 3, board[1]["at"])
    text = receipts.render_text(run.collect())
    assert "(names this commit)" in text and "(before the commit, linked by time)" in text
    assert f"claim (board post by a1 at {board[1]['at'][11:]}, quoted above)" in text


def test_board_posts_are_capped_per_receipt(tmp_path: Path):
    run = Run(tmp_path)
    for number in range(10):
        run.post("a1", f"note {number}")
    sha = run.commit("a1")
    for number in range(3):
        run.post("a2", f"review {number} of {sha[:8]}")
    run.write()
    texts = [post["text"] for post in run.receipt(sha)["why"]["board"]]
    assert texts == ["note 9", *(f"review {number} of {sha[:8]}" for number in range(3))]


def test_merge_rename_and_binary_changes(tmp_path: Path):
    run = Run(tmp_path, "--solo")
    run.tick()
    clone = run.clone("solo")
    run.git("solo", "checkout", "-q", "-b", "side")
    (clone / "side.txt").write_text("one\ntwo\n")
    run.git("solo", "add", "side.txt")
    run.git("solo", "commit", "-q", "-m", "Side work")
    run.git("solo", "checkout", "-q", "main")
    run.git("solo", "mv", "README.md", "README.txt")
    (clone / "blob.bin").write_bytes(bytes(range(256)) * 4)
    run.git("solo", "add", "blob.bin")
    run.git("solo", "commit", "-q", "-m", "Rename and add a binary")
    run.tick()
    run.git("solo", "merge", "-q", "--no-ff", "-m", "Merge side", "side")
    run.git("solo", "push", "-q", "origin", "HEAD:main")
    run.write()
    by_subject = {receipt["subject"]: receipt for receipt in run.collect()["receipts"]}
    assert set(by_subject) == {"Side work", "Rename and add a binary", "Merge side"}
    renamed = {path["path"]: path for path in by_subject["Rename and add a binary"]["change"]["paths"]}
    assert renamed["README.md => README.txt"]["insertions"] == 0
    assert renamed["blob.bin"] == {"path": "blob.bin", "insertions": None, "deletions": None}
    merge = by_subject["Merge side"]
    assert len(merge["parents"]) == 2 and merge["base_sha"] == by_subject["Rename and add a binary"]["sha"]
    assert [(p["path"], p["insertions"]) for p in merge["change"]["paths"]] == [("side.txt", 2)]
    assert all(receipt["who"]["agent"] == "solo" and receipt["on_main"] for receipt in by_subject.values())


def test_a_commit_under_another_identity_has_no_agent(tmp_path: Path):
    run = Run(tmp_path)
    run.git("a1", "config", "user.email", "someone@example.com")
    run.git("a1", "config", "user.name", "Someone")
    sha = run.commit("a1", "Odd author")
    run.write()
    receipt = run.receipt(sha)
    assert receipt["who"]["agent"] is None and receipt["who"]["author"] == "Someone <someone@example.com>"
    assert receipt["verification"]["status"] == "none" and receipt["verification"]["certainty"] == "unknown"
    assert f"{sha[:7]}  unknown agent  Odd author" in receipts.render_text(run.collect())
    assert receipts.for_agent(run.collect(), "a1")["receipts"] == []


def test_solo_run(tmp_path: Path):
    run = Run(tmp_path, "--solo")
    run.command("solo", "python3 -m unittest -q", 0, "OK")
    sha = run.commit("solo", "Solo work")
    run.write()
    document = run.collect()
    assert [(agent["id"], agent["role"], agent["commits"]) for agent in document["agents"]] == [("solo", "solo", 1)]
    assert run.receipt(sha)["verification"]["status"] == "observed-pass"
    assert run.receipt(sha)["verification"]["checks"][0]["cwd"] == "work/repo"
    assert receipts.render_text(document).startswith("change receipts for run1 (solo, gpt-6-astra/high)\n")


# --- gaps in what the run recorded ----------------------------------------------------------


def test_missing_sessions_board_and_reflog_leave_named_gaps(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q", 0, "1 passed")
    sha = run.commit("a1", "Add a\n\nVerified: pytest -q")
    run.post("a1", "posted")
    run.write(sessions=False, board=False)
    shutil.rmtree(run.origin / "logs")
    document = run.collect()
    receipt = document["receipts"][0]
    assert receipt["sha"] == sha and receipt["when"]["pushed"] == {} and receipt["why"]["board"] == []
    verified = receipt["verification"]
    assert (verified["status"], verified["linked_by"], verified["certainty"]) == ("claimed", None, "unknown")
    assert "there is no session log for a1" in verified["summary"]
    assert document["warnings"] == [
        "no reflog for main: push times are unknown there",
        "no Codex session logs found; nothing about verification could be observed"]
    text = receipts.render_text(document)
    assert "note: no reflog for main" in text and "pushed to" not in text


def test_no_origin_and_no_commits(tmp_path: Path):
    run = Run(tmp_path)
    run.write()
    empty = run.collect()
    assert empty["receipts"] == [] and "no commits to describe" in receipts.render_text(empty)
    assert empty["run"]["head"] == run.meta["base"]
    shutil.rmtree(run.origin)
    gone = run.collect()
    assert gone["receipts"] == [] and gone["run"]["head"] is None
    assert gone["warnings"][0] == "work/origin.git is missing; there are no commits to describe"


def test_unusable_board_and_base_are_warnings(tmp_path: Path):
    run = Run(tmp_path)
    sha = run.commit("a1")
    run.write()
    (run.ws / "codex-home" / receipts.BOARD_DB).write_text("this is not a database")
    assert run.receipt(sha)["why"]["board"] == []
    assert "cannot read the message board" in run.collect()["warnings"][0]
    meta = run.meta | {"base": "0" * 40}
    (run.ws / "murmur.json").write_text(json.dumps(meta))
    broken = run.collect()
    assert broken["receipts"] == [] and "cannot list the run's commits" in broken["warnings"][0]
    for unusable in ("", "--all", None):
        (run.ws / "murmur.json").write_text(json.dumps(run.meta | {"base": unusable}))
        document = run.collect()
        assert document["receipts"] == [] and document["run"]["head"] == sha
        assert document["warnings"][0].startswith("murmur.json names no base commit")


def test_board_rows_that_are_not_posts_are_skipped(tmp_path: Path):
    run = Run(tmp_path)
    run.posts += [("tasks", "/root/a1", int(run.tick() * 1e6), "not json"),
                  ("tasks", "/root/a1", int(run.tick() * 1e6), json.dumps({"text": ""})),
                  ("tasks", "/root/a1", int(run.tick() * 1e6), json.dumps(["a", "list"])),
                  ("tasks", "/root/a1", "soon", json.dumps({"text": "a post without a usable time"}))]
    run.post("a1", "a real post")
    run.write()
    posts, warnings = receipts.read_board(run.ws)
    assert [(post["text"], post["agent"]) for post in posts] == [
        ("a post without a usable time", "a1"), ("a real post", "a1")]
    assert posts[0]["at"] is None and posts[1]["at"] == pytest.approx(run.clock) and warnings == []


def test_not_a_workspace(tmp_path: Path):
    with pytest.raises(receipts.ReceiptsError, match="no workspace at"):
        receipts.collect(tmp_path / "nope")
    (tmp_path / "murmur.json").write_text("{ not json")
    with pytest.raises(receipts.ReceiptsError, match="unreadable"):
        receipts.collect(tmp_path)
    (tmp_path / "murmur.json").write_text("[]")
    with pytest.raises(receipts.ReceiptsError, match="not a murmur workspace file"):
        receipts.collect(tmp_path)


# --- safety --------------------------------------------------------------------------------


def _fingerprint(root: Path) -> dict[str, tuple]:
    found = {}
    for path in sorted(root.rglob("*")):
        if path.is_file() and not path.is_symlink():
            found[str(path.relative_to(root))] = (path.stat().st_mtime_ns,
                                                 hashlib.sha256(path.read_bytes()).hexdigest())
    return found


def test_collecting_changes_nothing_in_the_run_and_never_opens_auth(tmp_path: Path):
    global _watching
    run = Run(tmp_path)
    run.command("a1", "pytest -q", 0, "1 passed")
    sha = run.commit("a1")
    run.post("a1", f"DONE {sha[:7]}")
    board = run.write(wal=True)
    try:
        home = run.ws / "codex-home"
        assert (home / f"{receipts.BOARD_DB}-wal").stat().st_size > 0  # the posts are only in the WAL
        auth = home / "auth.json"
        auth.unlink()
        auth.write_text('{"OPENAI_API_KEY": "sk-live-do-not-read-this-0123456789"}\n')
        before = _fingerprint(run.ws)
        _opened.clear()
        _watching = True
        try:
            document = run.collect()
            text = receipts.render_text(document) + receipts.render_markdown(document) + receipts.to_json(document)
        finally:
            _watching = False
        assert _fingerprint(run.ws) == before
        assert [post["link"] for post in document["receipts"][0]["why"]["board"]] == ["names-commit"]
        assert _opened and not [path for path in _opened if "auth" in Path(path).name]
        assert "do-not-read" not in text
    finally:
        board.close()


def test_secrets_and_paths_in_logs_do_not_reach_a_receipt(tmp_path: Path):
    run = Run(tmp_path)
    key = "sk-proj-abcdefghijklmnopqrstuvwxyz012345"
    run.say("a1", f"I will call the API with {key} from {Path.home()}/.config/app")
    run.command("a1", f"OPENAI_API_KEY={key} pytest -q {run.ws}/work/peers/a1/tests", 0,
                f"reading {Path.home()}/.netrc\npassword=correcthorsebattery\n1 passed\n")
    sha = run.commit("a1", f"Add a\n\nUses {key}.\n\nVerified: pytest with token=abcdef0123456789")
    run.post("a1", f"DONE {sha[:7]} deployed with Bearer abcdefghijklmnopqrstuvwx")
    run.write()
    document = run.collect()
    text = receipts.to_json(document) + receipts.render_text(document) + receipts.render_markdown(document)
    for secret in (key, "sk-proj", "correcthorse", "abcdef0123456789", "abcdefghijklmnopqrstuvwx",
                   str(Path.home()), str(tmp_path)):
        assert secret not in text, secret
    check = document["receipts"][0]["verification"]["checks"][0]
    assert check["command"] == "OPENAI_API_KEY=[redacted] pytest -q <workspace>/work/peers/a1/tests"
    assert check["output_excerpt"] == "reading ~/.netrc\npassword=[redacted]\n1 passed"


def test_markdown_fences_survive_backticks_in_the_log(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q", 0, "````\n3 passed")
    run.commit("a1", "Add `a`")
    run.write()
    markdown = receipts.render_markdown(run.collect())
    assert markdown.startswith("# Change receipts for run1 (swarm, 2 peers, gpt-6-astra/high)\n")
    assert "\n`````text\n" in markdown and markdown.count("`````") == 2
    assert "## " in markdown and "by a1" in markdown


# --- the command, and the files `murmur run` writes -----------------------------------------


def test_receipts_command(tmp_path: Path):
    run = Run(tmp_path)
    run.command("a1", "pytest -q", 0, "1 passed")
    first = run.commit("a1", "From a1")
    run.git("a2", "pull", "-q", "--rebase", "origin", "main")
    second = run.commit("a2", "From a2")
    run.write()
    shown = run_cli("receipts", str(run.ws))
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout == receipts.render_text(run.collect()) and shown.stderr == ""
    assert f"{first[:7]}  a1  From a1" in shown.stdout and f"{second[:7]}  a2  From a2" in shown.stdout
    assert not (run.ws / "logs" / "receipts.json").exists()  # showing them writes nothing

    only = run_cli("receipts", str(run.ws), "--agent", "a2", "--json")
    document = json.loads(only.stdout)
    assert [receipt["sha"] for receipt in document["receipts"]] == [second]
    assert [agent["id"] for agent in document["agents"]] == ["a2"]

    written = run_cli("receipts", str(run.ws), "--write", "--agent", "a1")
    assert written.returncode == 0 and f"{second[:7]}  a2" not in written.stdout
    assert "wrote" in written.stderr and "receipts.md" in written.stderr
    saved = json.loads((run.ws / "logs" / "receipts.json").read_text())
    assert [receipt["sha"] for receipt in saved["receipts"]] == [first, second]  # the files hold every agent
    assert f"## {second[:7]} by a2" in (run.ws / "logs" / "receipts.md").read_text()
    assert not list((run.ws / "logs").glob("*.partial"))


def test_receipts_command_errors(tmp_path: Path):
    missing = run_cli("receipts", str(tmp_path / "nope"))
    assert missing.returncode == 3 and missing.stdout == ""
    assert missing.stderr.strip() == f"murmur: no workspace at {tmp_path / 'nope'}"
    run = Run(tmp_path)
    unknown = run_cli("receipts", str(run.ws), "--agent", "a9")
    assert unknown.returncode == 3
    assert unknown.stderr.strip() == "murmur: no agent 'a9' in run1 (agents: root, a1, a2)"
    assert run_cli("receipts").returncode == 2


@pytest.mark.parametrize("mode", ["--solo", "--peers=3"])
def test_run_writes_receipts(tmp_path: Path, mode: str):
    workspace = setup_workspace(tmp_path, mode)
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "receipts"})
    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert f"receipts: {workspace / 'logs' / 'receipts.md'}" in lines
    assert lines[-1].startswith("review it: ")  # the fetch command stays last
    document = json.loads((workspace / "logs" / "receipts.json").read_text())
    assert document["run"]["finished"] is True and document["run"]["exit_code"] == 0
    assert document["warnings"] == []
    statuses = {receipt["who"]["agent"]: receipt["verification"]["status"] for receipt in document["receipts"]}
    markdown = (workspace / "logs" / "receipts.md").read_text()
    if mode == "--solo":
        assert statuses == {"solo": "observed-pass"}
        assert document["receipts"][0]["why"]["board"] == []
    else:
        assert statuses == {"a1": "observed-pass", "a2": "claimed", "a3": "none"}
        first = document["receipts"][0]
        assert [post["link"] for post in first["why"]["board"]] == ["before-commit", "names-commit"]
        assert [claim["source"] for claim in first["verification"]["claims"]] == ["commit-message", "board"]
        assert "CLAIMED only" in markdown and "NOT OBSERVED" in markdown
    for receipt in document["receipts"]:
        assert receipt["verification"]["linked_by"] == "commit-output"
        assert receipt["why"]["intent"]["text"] == f"I will add {receipt['who']['agent']}.txt."
        assert receipt["why"]["message"].startswith("One file per agent.")
        assert receipt["when"]["pushed"]["main"]
    assert "OBSERVED, passed" in markdown
    assert run_cli("receipts", str(workspace)).stdout == receipts.render_text(document)


def test_run_survives_a_receipts_failure(tmp_path: Path):
    workspace = setup_workspace(tmp_path, "--solo")
    (workspace / "logs" / "receipts.json").mkdir()  # the file cannot be put in place
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "commit"})
    assert result.returncode == 0, result.stderr
    assert "murmur: could not write the change receipts:" in result.stderr
    assert f"murmur: to try again: murmur receipts {workspace} --write" in result.stderr
    assert "receipts:" not in result.stdout and "review it:" in result.stdout
    assert json.loads((workspace / "logs" / "run.json").read_text())["exit_code"] == 0


@pytest.mark.parametrize("mode, code", [("ok", 4), ("fail", 1), ("draft-only", 4)])
def test_run_writes_receipts_whatever_the_outcome(tmp_path: Path, mode: str, code: int):
    workspace = setup_workspace(tmp_path, "--peers", "2")
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": mode})
    assert result.returncode == code
    document = json.loads((workspace / "logs" / "receipts.json").read_text())
    assert document["run"]["exit_code"] == code and document["run"]["commits_on_main"] == 0
    drafts = [receipt for receipt in document["receipts"] if not receipt["on_main"]]
    assert len(drafts) == (1 if mode == "draft-only" else 0)
    if drafts:
        assert drafts[0]["branches"] == ["draft/a1"] and drafts[0]["who"]["agent"] == "a1"
