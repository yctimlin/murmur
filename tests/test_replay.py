"""Replay: what each agent did over time, and two runs of one task side by side."""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from murmur import receipts, replay, tokens
from support import init_repo, run_cli
from test_receipts import T0, Run, _stamp

_opened: list[str] = []
_watching = False


def _audit(event: str, args: tuple) -> None:
    if _watching and event in ("open", "sqlite3.connect"):
        _opened.append(str(args[0]))


sys.addaudithook(_audit)


class Replayed(Run):
    """A workspace with what a run leaves for a replay: turns, token counts, tool calls and a run record."""

    version = "0.163.0"  # Codex stamps its version on a session; None leaves it out, as test logs do

    def __init__(self, tmp_path: Path, *setup: str, ws: Path | None = None) -> None:
        if ws is None:
            super().__init__(tmp_path, *setup)
            return
        self.ws = ws
        self.meta = json.loads((ws / "murmur.json").read_text())
        self.origin = ws / "work" / "origin.git"
        self.clock = float(T0)
        self.lines, self.posts = {}, []

    def turn(self, agent: str, end: str | None = None) -> None:
        payload = {"type": "task_started"} if end is None else {"type": "task_complete", "last_agent_message": end}
        self._event(agent, "event_msg", payload)

    def tokens(self, agent: str, used: int, cached: int, out: int) -> None:
        usage = {"input_tokens": used, "cached_input_tokens": cached, "output_tokens": out,
                 "total_tokens": used + out}
        self._event(agent, "event_msg", {"type": "token_count", "info": {"total_token_usage": usage}})

    def call(self, agent: str, name: str, arguments: dict, took: float = 0, answered: bool = True) -> None:
        """A plain function call (`spawn_agent`, `wait_agent`) and its output `took` seconds later."""
        call_id = f"call-{agent}-{len(self.lines.get(agent, []))}"
        self._event(agent, "response_item", {"type": "function_call", "name": name, "call_id": call_id,
                                             "arguments": json.dumps(arguments)})
        self.tick(took)
        if answered:
            self._event(agent, "response_item", {"type": "function_call_output", "call_id": call_id,
                                                 "output": "{}"})

    def exec(self, agent: str, script: str, commands=(), patches=(), took: float = 0) -> None:
        """A code-mode `exec` call: its JavaScript, then what Codex logged as run, then its output."""
        call_id = f"call-{agent}-{len(self.lines.get(agent, []))}"
        self._event(agent, "response_item", {"type": "custom_tool_call", "name": "exec", "call_id": call_id,
                                             "input": script})
        for command, code, output in commands:
            began = self.clock + 1
            self.tick(took)
            item = {"type": "CommandExecution", "command": ["/bin/bash", "-lc", command],
                    "cwd": f"file://{self.clone(agent) if agent != 'root' else self.ws}",
                    "aggregated_output": output, "exit_code": code}
            self._event(agent, "event_msg", {"type": "item_completed", "item": item,
                                             "started_at_ms": int(began * 1000),
                                             "completed_at_ms": int((self.clock + 1) * 1000)})
        for paths in patches:
            item = {"type": "FileChange", "changes": {path: {"type": "update"} for path in paths}}
            self._event(agent, "event_msg", {"type": "item_completed", "item": item,
                                             "started_at_ms": int((self.clock + 1) * 1000),
                                             "completed_at_ms": int((self.clock + 1) * 1000)})
        self._event(agent, "response_item", {"type": "custom_tool_call_output", "call_id": call_id,
                                             "output": [{"type": "input_text", "text": "Script completed"}]})

    def write(self, **options):
        board = super().write(**options)
        if self.version:
            for rollout in (self.ws / "codex-home" / "sessions").rglob("*.jsonl"):
                head, _, rest = rollout.read_text().partition("\n")
                meta = json.loads(head)
                meta["payload"]["cli_version"] = self.version
                rollout.write_text(json.dumps(meta) + "\n" + rest)
        return board

    def finish(self, exit_code: int = 0, **record) -> None:
        """The record `murmur run` leaves in logs/run.json."""
        elapsed = self.clock - T0
        (self.ws / "logs" / "run.json").write_text(json.dumps({
            "seconds": elapsed, "active_seconds": elapsed, "stalled_seconds": 0.0, "exit_code": exit_code,
            "delivered": exit_code == 0, "capped": False, "interrupted": False, "diagnostic": f"exit {exit_code}",
            **record}))

    def replay(self) -> dict:
        return replay.collect_run(self.ws)


def _pair(tmp_path: Path, *swarm_options: str, solo_options: tuple = ()) -> tuple[Replayed, Replayed]:
    """A swarm and a solo workspace set up from the same repository and brief."""
    repo, brief = init_repo(tmp_path / "src")
    found = []
    for run_id, options in (("swarm1", ("--peers", "2", *swarm_options)), ("solo1", ("--solo", *solo_options))):
        done = run_cli("setup", str(brief), "--repo", str(repo), "--into", str(tmp_path / "runs"), "--id", run_id,
                       "--cap", "30s", *options)
        assert done.returncode == 0, done.stderr
        found.append(Replayed(tmp_path, ws=tmp_path / "runs" / run_id))
    return found[0], found[1]


def _swarm(run: Replayed) -> dict:
    """Two peers: a1 tests and lands a commit, a2 drafts, reviews a1 and posts. Returns the SHAs."""
    run.turn("root")
    run.call("root", "spawn_agent", {"task_name": "a1", "message": "gAAAAAB" + "x" * 40})
    run.call("root", "spawn_agent", {"task_name": "a2", "message": "gAAAAAB" + "y" * 40})
    run.tokens("root", 1000, 400, 50)
    for agent in ("a1", "a2"):
        run.turn(agent)
        run.exec(agent, f'text(await tools.exec_command({{cmd:"cat {run.ws}/prompts/{agent}.md"}}));',
                 [(f"cat {run.ws}/prompts/{agent}.md", 0, "the brief")])
        run.tokens(agent, 5000, 1000, 100)
    run.say("a1", "I will add the feature and test it.")
    run.exec("a1", 'text(await tools.collaboration__post({channel_name:"tasks",text:"CLAIM a1"}));\n'
                   'text(await tools.apply_patch("*** Begin Patch"));\n'
                   'text(await tools.exec_command({cmd:"python3 -m unittest -q"}));',
             [("python3 -m unittest -q", 0, "Ran 2 tests\n\nOK\n")],
             patches=[[f"{run.clone('a1')}/feature.py"]], took=4)
    run.post("a1", "CLAIM a1 takes the feature")
    main = run.commit("a1", "Add the feature\n\nVerified: python3 -m unittest -q")
    run.tokens("a1", 20000, 12000, 700)
    run.git("a2", "checkout", "-q", "-b", "draft/a2")
    draft = run.commit("a2", "Draft another way", branch="draft/a2")
    run.exec("a2", 'text(await tools.exec_command({cmd:"git fetch origin && pytest -q | tail -3"}));',
             [("git fetch origin && pytest -q | tail -3", 0, "2 passed")], took=2)
    run.post("a2", f"REVIEW a2: {main[:7]} looks right, tests pass", channel="findings")
    run.tokens("a2", 30000, 21000, 900)
    run.turn("a1", end="Implemented and pushed.")
    run.turn("a2", end="Reviewed a1's change.")
    run.call("root", "wait_agent", {"timeout_ms": 3600000}, took=3)
    run.tokens("root", 3000, 1500, 80)
    run.turn("root", end="done")
    run.write()
    run.finish()
    return {"main": main, "draft": draft}


def _solo(run: Replayed) -> str:
    run.turn("solo")
    run.exec("solo", 'text(await tools.exec_command({cmd:"cat README.md"}));', [("cat README.md", 0, "hello")])
    run.exec("solo", 'text(await tools.exec_command({cmd:"python3 -m unittest -q"}));',
             [("python3 -m unittest -q", 0, "OK")], took=2)
    sha = run.commit("solo", "Add the feature alone")
    run.tokens("solo", 9000, 6000, 400)
    run.turn("solo", end="Done alone.")
    run.write()
    run.finish()
    return sha


def _events(run: dict, agent: str | None = None, kind: str | None = None) -> list[dict]:
    return [event for event in run["events"]
            if agent in (None, event["agent"]) and kind in (None, event["kind"])]


# --- sorting tool calls into kinds ----------------------------------------------------------


@pytest.mark.parametrize("script, kind", [
    ("cat wordstats.py", "read"),
    ("pwd && ls -la && rg --files", "read"),
    ("cd pkg && sed -n '1,40p' main.py", "read"),
    ("git status --short && git log -3 --oneline", "read"),
    ("git -C repo diff --stat", "read"),
    ("pwd; if [ -f AGENTS.md ]; then cat AGENTS.md; fi", "read"),
    ("ls 2>&1 > /dev/null", "read"),
    ("cat > notes.md <<'EOF'\npytest -q\nEOF", "edit"),
    ("echo done >> log.txt", "edit"),
    ("sed -i 's/a/b/' main.py", "edit"),
    ("cp a.py b.py", "edit"),
    ("python3 -m unittest -q", "test"),
    ("ruff check . && git add -A && git commit -m x && git push origin HEAD:main", "test"),
    ("cat > t.py <<'EOF'\nx\nEOF\npytest -q", "test"),
    ("git add -A && git commit -m 'run pytest'", "git"),
    ("rm -r __pycache__\ngit add a.py\ngit commit -m x", "git"),
    ("git push origin HEAD:draft/a1", "git"),
    ("git switch -c draft/a1", "git"),
    ("python3 wordstats.py --top 3 notes.txt", "run"),
    ("mkdir -p .work && python3 capture.py > .work/out.txt", "run"),
    ("npm ci", "run"),
    ("python3 - <<'PY'\nprint('pytest')\nPY", "run"),
    ("cd repo", "run"),
    ("", "run"),
])
def test_commands_are_sorted_into_kinds(script: str, kind: str):
    assert replay.classify(script) == kind


def test_a_code_mode_call_is_read_for_its_tools_and_commands():
    script = ('text(await tools.collaboration__post({channel_name:"tasks",text:"cmd: \\"not a command\\""}));\n'
              'text(await tools.exec_command({cmd:"git fetch origin && python3 -m unittest -q",workdir:"/w"}));\n'
              "text(await tools.exec_command({cmd:'cat \"a b.txt\"'}));\n"
              'text(await tools.apply_patch("*** Begin Patch"));\ntext(await tools.view_image({path:"a.png"}));')
    assert replay.call_actions("exec", script) == (
        ["collaboration__post", "exec_command", "apply_patch", "view_image"],
        ["git fetch origin && python3 -m unittest -q", 'cat "a b.txt"'])
    assert [(event["kind"], event["text"]) for event in replay.call_events("a1", "exec", script)] == [
        ("test", "git fetch origin && python3 -m unittest -q"), ("read", 'cat "a b.txt"'),
        ("coord", "post"), ("edit", "apply_patch"), ("run", "view_image")]


def test_a_plain_call_and_text_that_was_cut_short():
    assert replay.call_events("solo", "exec_command", json.dumps({"cmd": "pytest -q", "workdir": "/w"})) == [
        {"agent": "solo", "kind": "test", "text": "pytest -q", "exit": None, "check": None, "script": "pytest -q"}]
    assert replay.call_events("solo", "shell", json.dumps({"command": ["bash", "-lc", "ls"]}))[0]["kind"] == "read"
    cut = replay.call_events("solo", "exec_command", '{"cmd":"cat > a.py <<\'EOF\'\\nimport os\\nprint(')
    assert [(event["kind"], event["text"]) for event in cut] == [("edit", "cat > a.py <<'EOF'")]
    code = replay.call_events("a2", "exec", 'text(await tools.exec_command({cmd:"python3 - <<\'PY\'\\nfrom pathlib')
    assert [(event["kind"], event["text"]) for event in code] == [("run", "python3 - <<'PY'")]
    spawn = replay.call_events("root", "spawn_agent", '{"task_name":"a1","message":"gAAAAABq1kz_RJfWabwIvX4E5')
    assert spawn == [{"agent": "root", "kind": "coord", "exit": None, "check": None, "text": "spawn_agent a1"}]
    assert replay.call_events("root", "wait_agent", "{}")[0]["text"] == "wait_agent"
    assert replay.call_events("a1", "exec", "not javascript at all") == []


# --- one run ---------------------------------------------------------------------------------


def test_a_swarm_run_becomes_lanes_of_timed_events(tmp_path: Path):
    run = Replayed(tmp_path)
    shas = _swarm(run)
    found = run.replay()
    assert [agent["id"] for agent in found["agents"]] == ["root", "a1", "a2"]
    assert [agent["role"] for agent in found["agents"]] == ["root", "peer", "peer"]
    assert found["example"] is None and found["codex_versions"] == ["0.163.0"]
    assert (found["mode"], found["peers"], found["model"], found["effort"], found["cap"]) == (
        "swarm", 2, "gpt-6-astra", "high", "30s")
    assert found["clock"]["kind"] == "wall" and found["clock"]["start"] == _stamp(T0)[:19] + "Z"

    # Every event sits where the log put it: seconds since the first log entry, in order.
    times = [event["t"] for event in found["events"]]
    assert times == sorted(times) and times[0] >= 0 and times[-1] <= found["duration_s"]
    assert found["duration_s"] == run.clock - T0
    assert [(event["kind"], event["text"]) for event in _events(found, "root")] == [
        ("turn_start", ""), ("coord", "spawn_agent a1"), ("coord", "spawn_agent a2"), ("coord", "wait_agent"),
        ("turn_end", "done")]
    wait = _events(found, "root", "coord")[-1]
    assert wait["end"] - wait["t"] == 4  # from the call to its output: the 3 s wait and the next log line

    kinds = [(event["kind"], re.sub(r"a1-\d+\.txt", "FILE", event["text"])) for event in _events(found, "a1")]
    assert kinds == [
        ("turn_start", ""),
        ("read", "cat <workspace>/prompts/a1.md"),
        ("say", "I will add the feature and test it."),
        ("coord", "post"),
        ("test", "python3 -m unittest -q"),
        ("edit", "apply_patch feature.py"),
        ("post", "#tasks CLAIM a1 takes the feature"),
        ("main", f"{shas['main'][:7]} Add the feature (+1 -0)"),
        ("git", "git add FILE && git commit -m ... && git push origin HEAD:main"),
        ("turn_end", "Implemented and pushed."),
    ]
    test = _events(found, "a1", "test")[0]
    assert (test["exit"], test["check"], test["end"] - test["t"]) == (0, "passed", 4)  # times as Codex recorded
    landed = _events(found, kind="main")
    assert [event["sha"] for event in landed] == [shas["main"][:7]]
    drafted = _events(found, "a2", "draft")
    assert [(event["sha"], event["text"]) for event in drafted] == [
        (shas["draft"][:7], f"draft/a2: {shas['draft'][:7]} Draft another way (+1 -0)")]
    assert [event["text"] for event in _events(found, "a2", "post")] == [
        f"#findings REVIEW a2: {shas['main'][:7]} looks right, tests pass"]

    by_id = {agent["id"]: agent for agent in found["agents"]}
    assert by_id["a1"]["calls"] == {"test": 1, "edit": 1, "git": 1, "coord": 1, "read": 1}
    assert by_id["a2"]["calls"] == {"test": 1, "git": 1, "read": 1}
    assert (by_id["a1"]["posts"], by_id["a1"]["changes_on_main"], by_id["a2"]["changes_on_main"]) == (1, 1, 0)
    for agent in found["agents"]:
        (start, end), = agent["turns"]
        assert 0 <= start < end <= found["duration_s"]
    assert found["main"] == {"commits": 1, "files": 1, "insertions": 1, "deletions": 0,
                             "last_change_s": landed[0]["t"]}
    assert found["drafts"] == ["draft/a2"]
    assert found["outcome"] == {"finished": True, "exit_code": 0, "delivered": True, "capped": False,
                                "interrupted": False, "diagnostic": "exit 0"}
    assert found["launcher"] == {"seconds": run.clock - T0, "active_seconds": run.clock - T0,
                                 "stalled_seconds": 0.0}
    assert found["score"] is None and found["warnings"] == []


def test_tokens_are_the_last_running_total_of_each_session_summed(tmp_path: Path):
    run = Replayed(tmp_path)
    _swarm(run)
    found = run.replay()
    usage = tokens.run_usage(run.ws, order=["a1", "a2"])  # what `murmur run` reports
    assert found["tokens"]["agents"] == usage["agents"]
    assert found["tokens"]["total"] == usage["total"] == {
        "input_tokens": 53000, "cached_input_tokens": 34500, "output_tokens": 1680, "total_tokens": 54680}
    series = found["token_series"]
    assert [point[1:] for point in series["a1"]] == [[5000, 1000, 100], [20000, 12000, 700]]
    assert [point[1:] for point in series["root"]] == [[1000, 400, 50], [3000, 1500, 80]]
    for name, points in series.items():
        assert [point[0] for point in points] == sorted(point[0] for point in points)
        last = usage["agents"][name]
        assert points[-1][1:] == [last["input_tokens"], last["cached_input_tokens"], last["output_tokens"]]


def test_an_agent_with_two_sessions_has_one_running_total(tmp_path: Path):
    run = Replayed(tmp_path)
    run.turn("a1")
    run.tokens("a1", 100, 10, 1)  # two seconds in
    run.tokens("a1", 300, 30, 3)
    run.write()
    second = run.ws / "codex-home" / "sessions" / "2027" / "01" / "15" / "rollout-a1-again.jsonl"
    usage = {"input_tokens": 50, "cached_input_tokens": 5, "output_tokens": 2}
    second.write_text("\n".join(json.dumps(line) for line in (
        {"timestamp": _stamp(T0 + 1.5), "type": "session_meta", "payload": {"id": "again", "agent_path": "/root/a1"}},
        {"timestamp": _stamp(T0 + 1.5), "type": "event_msg",
         "payload": {"type": "token_count", "info": {"total_token_usage": usage}}})) + "\n")
    found = run.replay()
    assert [point[1:] for point in found["token_series"]["a1"]] == [[50, 5, 2], [150, 15, 3], [350, 35, 5]]
    assert found["tokens"]["agents"]["a1"]["input_tokens"] == 350


def test_a_long_token_series_is_thinned_but_keeps_its_end():
    points = [[index, index, 0, 0] for index in range(5000)]
    thinned = replay._thin(points, replay.MAX_SERIES)
    assert len(thinned) <= replay.MAX_SERIES + 1 and thinned[0] == points[0] and thinned[-1] == points[-1]
    assert replay._thin(points[:10], replay.MAX_SERIES) == points[:10]


def test_commands_come_from_what_was_logged_as_run_not_from_the_call_text(tmp_path: Path):
    run = Replayed(tmp_path)
    run.turn("a1")
    # The script fails on its first tool, so the command after it never runs and Codex logs none.
    run.exec("a1", 'text(await tools.collaboration__post({new_channel_name:"tasks",text:"x"}));\n'
                   'text(await tools.exec_command({cmd:"git switch -c draft/a1"}));')
    run.write()
    assert [(event["kind"], event["text"]) for event in _events(run.replay(), "a1")] == [
        ("turn_start", ""), ("coord", "post")]


def test_plain_tool_calls_and_an_unanswered_one(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    run.turn("solo")
    run.call("solo", "exec_command", {"cmd": "pytest -q"}, took=5)
    run.call("solo", "exec_command", {"cmd": "git status"}, answered=False)
    run.write()
    found = run.replay()
    first, second = _events(found, "solo", "test")[0], _events(found, "solo", "read")[0]
    assert (first["text"], first["end"] - first["t"], first["exit"]) == ("pytest -q", 6, None)
    assert (second["text"], second["end"]) == ("git status", None)
    # The turn never ended: the lane runs to the end of the log, and the run is not finished.
    assert found["agents"][0]["turns"] == [[1.0, found["duration_s"]]]
    assert found["outcome"]["finished"] is False and found["launcher"] is None
    assert any("no logs/run.json" in warning for warning in found["warnings"])


def test_calls_made_in_parallel_each_keep_their_own_command(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    run.turn("solo")
    for call_id, command in (("c1", "pytest -q"), ("c2", "git status"), ("c3", "cat a.py")):
        run._event("solo", "response_item", {"type": "function_call", "name": "exec_command", "call_id": call_id,
                                             "arguments": json.dumps({"cmd": command})})
    for call_id in ("c2", "c1", "c3"):
        run.tick(5)
        output = json.dumps({"output": "", "metadata": {"exit_code": 0}})
        run._event("solo", "response_item", {"type": "function_call_output", "call_id": call_id, "output": output})
    run.write()
    found = [(event["text"], event["t"], event["end"]) for event in run.replay()["events"]
             if event["kind"] in replay.TOOL_KINDS]
    assert found == [("pytest -q", 2.0, 16.0), ("git status", 3.0, 10.0), ("cat a.py", 4.0, 22.0)]


def test_a_forked_session_does_not_repeat_its_parents_work(tmp_path: Path):
    run = Replayed(tmp_path)
    run.turn("a1")
    run.exec("a1", 'tools.exec_command({cmd:"npm test"})', [("npm test", 0, "ok")])
    run.tokens("a1", 700, 0, 7)
    run.write()
    rollout = next((run.ws / "codex-home" / "sessions").rglob("rollout-a1.jsonl"))
    own = rollout.read_text().splitlines()
    meta = json.loads(own[0])
    meta["payload"]["forked_from_id"] = "root"
    parent = [json.dumps({"timestamp": _stamp(T0), "type": "event_msg", "payload": payload}) for payload in (
        {"type": "task_started"},
        {"type": "item_completed", "item": {"type": "CommandExecution", "command": "pytest -q", "exit_code": 1}},
        {"type": "token_count", "info": {"total_token_usage": {"input_tokens": 99999}}},
        {"type": "thread_settings_applied"})]
    rollout.write_text("\n".join([json.dumps(meta), *parent, *own[1:]]) + "\n")
    found = run.replay()
    assert [(event["kind"], event["text"]) for event in _events(found, "a1")] == [
        ("turn_start", ""), ("test", "npm test")]
    assert [point[1] for point in found["token_series"]["a1"]] == [700]


def test_a_solo_run(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    sha = _solo(run)
    found = run.replay()
    assert [(agent["id"], agent["role"]) for agent in found["agents"]] == [("solo", "solo")]
    assert (found["mode"], found["peers"], found["drafts"]) == ("solo", 1, [])
    assert [event["kind"] for event in found["events"]] == [
        "turn_start", "read", "test", "main", "git", "turn_end"]
    assert found["receipts"][0]["sha"] == sha[:7] and found["receipts"][0]["status"] == "observed-pass"
    assert found["source"]["files"] == ["murmur.json", "logs/run.json", "codex-home/sessions (1 rollout)",
                                        "work/origin.git"]


def test_receipts_are_the_ones_murmur_receipts_gives(tmp_path: Path):
    run = Replayed(tmp_path)
    shas = _swarm(run)
    found = run.replay()
    document = receipts.collect(run.ws)
    assert [entry["sha"] for entry in found["receipts"]] == [receipt["short"] for receipt in document["receipts"]]
    main, draft = found["receipts"]
    assert (main["sha"], main["agent"], main["on_main"], main["placed_by"]) == (shas["main"][:7], "a1", True, "push")
    assert (main["status"], main["status_label"]) == ("observed-pass", "OBSERVED, passed")
    assert main["lines"] == receipts.receipt_lines(document["receipts"][0])
    assert main["t"] == _events(found, kind="main")[0]["t"]
    assert (draft["agent"], draft["on_main"], draft["branches"], draft["status"]) == (
        "a2", False, ["draft/a2"], "none")
    assert found["receipts_note"] is None


def test_a_commit_without_a_reflog_is_placed_by_its_author_time_and_says_so(tmp_path: Path):
    run = Replayed(tmp_path)
    run.turn("a1")
    sha = run.commit("a1")
    run.write()
    shutil.rmtree(run.origin / "logs")
    found = run.replay()
    event, = _events(found, kind="commit")
    assert event["sha"] == sha[:7] and "placed by its author time" in event["text"] and "on main" in event["text"]
    assert _events(found, kind="main") == [] and found["main"]["last_change_s"] is None
    assert found["receipts"][0]["placed_by"] == "author time"
    assert any("no reflog" in warning for warning in found["warnings"])


def test_a_run_without_logs_or_commits(tmp_path: Path):
    run = Replayed(tmp_path)
    found = run.replay()
    assert found["events"] == [] and found["tokens"] is None and found["duration_s"] == 0
    assert found["receipts"] == [] and found["receipts_note"] == "the run made no commits"
    assert found["example"] is None  # nothing to judge the logs by
    text = replay.render_text(replay.build([found]))
    assert "tokens: no Codex session logs found" in text and "not finished" in text


def test_stalled_time_is_a_separate_fact_and_the_timeline_is_not_shortened(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    run.turn("solo")
    run.tick(600)  # the machine was frozen here; the log's stamps simply jump
    run.turn("solo", end="done")
    run.write()
    run.finish(4, seconds=602.0, active_seconds=100.0, stalled_seconds=502.0, delivered=False)
    found = run.replay()
    assert found["duration_s"] == 602 and found["launcher"]["stalled_seconds"] == 502.0
    assert any("counted 502 s as stalled" in warning for warning in found["warnings"])
    text = replay.render_text(replay.build([found]))
    assert "finished after (wall clock)  10:02" in text
    assert "launcher clock               602 s = 100 active + 502 stalled" in text
    assert "exit                         4, nothing delivered" in text


def test_logs_without_a_codex_version_are_labelled_as_example_data(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    run.version = None
    _solo(run)
    document = replay.build([run.replay()])
    assert "look like test or example data" in document["example"]
    assert "EXAMPLE DATA: " in replay.render_text(document)
    assert "EXAMPLE DATA: " in "\n".join(replay.summary_lines(document))
    assert json.loads(_embedded(replay.render_html(document)))["example"] == document["example"]


# --- two runs side by side ---------------------------------------------------------------------


def test_a_matched_pair_shows_wins_and_losses(tmp_path: Path):
    swarm, solo = _pair(tmp_path)
    _swarm(swarm)
    solo.tick(60)  # the solo run takes longer here
    _solo(solo)
    document = replay.build([swarm.replay(), solo.replay()])
    assert document["title"] == "swarm1 vs solo1" and [run["label"] for run in document["runs"]] == ["A", "B"]
    assert document["compatibility"] == []
    assert document["runs"][0]["brief"] == document["runs"][1]["brief"]
    assert document["runs"][0]["brief"]["source"] == "murmur.json"
    rows = {row["key"]: row for row in document["comparison"]}
    assert rows["time"]["label"] == "finished after (wall clock)"
    assert rows["time"]["note"].startswith("B took ") and rows["time"]["note"].endswith("x as long")
    assert rows["input"]["values"] == ["53,000", "9,000"] and rows["input"]["note"] == "A used 5.9x as many"
    assert rows["cached"]["values"] == ["34,500", "6,000"] and rows["uncached"]["values"] == ["18,500", "3,000"]
    assert rows["output"]["values"] == ["1,680", "400"] and rows["commits"]["values"] == ["1", "1"]
    assert rows["drafts"]["values"] == ["draft/a2", "none"]
    assert rows["exit"]["values"] == ["0, delivered", "0, delivered"]
    assert rows["score"]["values"] == [replay.NO_SCORE, replay.NO_SCORE] and rows["score"]["note"] == ""
    ahead = document["ahead"]
    assert len(ahead["A"]) == 1 and ahead["A"][0].startswith("finished sooner (")
    assert ahead["B"] == ["used fewer input tokens (9,000 against 53,000)",
                          "used fewer output tokens (400 against 1,680)"]
    assert ahead["not_compared"] == ["quality: no quality score supplied for both runs"]
    assert any("one run with one run" in note for note in document["notes"])
    text = replay.render_text(document)
    assert "same task and settings: brief sha256 " in text and "NOT A LIKE-FOR-LIKE PAIR" not in text
    assert "where each run comes out ahead" in text and replay.NO_SCORE in text


def test_a_pair_that_differs_gets_compatibility_warnings(tmp_path: Path):
    swarm, solo = _pair(tmp_path, "--effort", "low", "--cap", "5m", solo_options=("--model", "gpt-6-astra"))
    _swarm(swarm)
    _solo(solo)
    meta = json.loads((solo.ws / "murmur.json").read_text())
    meta |= {"brief_sha256": hashlib.sha256(b"another task").hexdigest(), "base": "f" * 40, "model": "other-model"}
    (solo.ws / "murmur.json").write_text(json.dumps(meta))
    solo.version = "0.170.0"
    solo.write()
    document = replay.build([swarm.replay(), solo.replay()])
    found = document["compatibility"]
    assert len(found) == 6
    assert found[0].startswith("the briefs differ (sha256 ") and "did not get the same task" in found[0]
    assert found[1:] == ["the model differs: A gpt-6-astra, B other-model",
                         "the reasoning effort differs: A low, B high",
                         "the base commit differs: A " + swarm.meta["base"][:10] + ", B ffffffffff",
                         "the time cap differs: A 5m, B 30s",
                         "the Codex CLI version differs: A 0.163.0, B 0.170.0"]
    text = replay.render_text(document)
    assert "NOT A LIKE-FOR-LIKE PAIR:" in text and "same task and settings" not in text


def test_the_brief_hash_of_an_older_workspace_comes_from_the_brief_file(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    meta = json.loads((run.ws / "murmur.json").read_text())
    brief = Path(meta["brief"])
    recorded = meta.pop("brief_sha256")
    assert recorded == hashlib.sha256(brief.read_text().strip().encode()).hexdigest()  # what setup writes
    (run.ws / "murmur.json").write_text(json.dumps(meta))
    found = run.replay()["brief"]
    assert found["sha256"] == recorded and "still matches the prompt" in found["source"]
    brief.write_text("A different task now.\n")
    assert run.replay()["brief"] == {
        "sha256": None, "source": "not recorded in murmur.json, and the brief file has changed since"}
    brief.unlink()
    other = Replayed(tmp_path / "other", "--solo")
    document = replay.build([run.replay(), other.replay()])
    assert document["compatibility"][0] == ("the brief of A has no recorded hash, so it is not confirmed that both "
                                            "runs got the same task")


def test_a_run_that_did_not_deliver_is_not_called_faster_or_cheaper(tmp_path: Path):
    swarm, solo = _pair(tmp_path)
    swarm.turn("root")
    swarm.tokens("root", 10, 0, 1)
    swarm.turn("root", end="done")
    swarm.write()
    swarm.finish(4, delivered=False)
    _solo(solo)
    document = replay.build([swarm.replay(), solo.replay()])
    assert document["ahead"]["A"] == []
    assert document["ahead"]["B"] == ["delivered a result; the other run did not"]
    assert document["ahead"]["not_compared"][0] == (
        "time and tokens: A (4, nothing delivered) did not finish with a delivered result, so being sooner or "
        "cheaper says nothing")
    rows = {row["key"]: row for row in document["comparison"]}
    assert rows["time"]["note"] and rows["input"]["note"]  # the numbers are still shown
    assert rows["last_main"]["values"][0] == "none" and rows["commits"]["values"] == ["0", "1"]


def test_a_small_difference_is_not_rounded_to_none():
    runs = [{"label": "A"}, {"label": "B"}]
    assert replay._lower(runs, [486, 490], "finished sooner", "took {} as long", replay.clock) == (
        "B took 1.01x as long", "finished sooner (8:06 against 8:10)", 0)
    assert replay._lower(runs, [300, 100], "x", "used {} as many", str)[0] == "A used 3.0x as many"
    assert replay._lower(runs, [0, 5], "x", "used {} as many", str)[0] == "A had none"
    assert replay._lower(runs, [7, 7], "x", "{}", str) == ("equal", "", None)
    assert replay._lower(runs, [None, 7], "x", "{}", str) == ("", "", None)


def test_a_score_is_shown_only_when_supplied_and_never_counts_as_a_win(tmp_path: Path):
    swarm, solo = _pair(tmp_path)
    _swarm(swarm)
    _solo(solo)
    runs = [swarm.replay(), solo.replay()]
    one = replay.build(runs, {"swarm1": replay.score(7.5, "supplied with --score-a")})
    rows = {row["key"]: row for row in one["comparison"]}
    assert rows["score"]["values"] == ["7.5", replay.NO_SCORE] and rows["score"]["note"] == ""
    assert "quality: no quality score supplied for one run" in one["ahead"]["not_compared"]

    both = replay.build(runs, {"swarm1": replay.score(7.5, "a"), "solo1": replay.score(8, "b"),
                               "elsewhere": replay.score(1, "c")})
    rows = {row["key"]: row for row in both["comparison"]}
    assert rows["score"]["values"] == ["7.5", "8"] and rows["score"]["note"] == "B is higher by 0.5"
    assert not any("score" in won or "quality" in won for label in "AB" for won in both["ahead"][label])
    assert both["ahead"]["not_compared"] == [
        "quality: the scores supplied are 7.5 for A and 8 for B; murmur did not assess quality and cannot tell "
        "whether a difference between two scores means anything"]
    assert "scores were supplied for elsewhere, which is not a run shown here" in both["notes"]
    text = replay.render_text(both)
    assert "score of A: 7.5, a; murmur did not assess quality" in text
    same = replay.build(runs, {"swarm1": replay.score(8, "a"), "solo1": replay.score(8.0, "b")})
    assert {row["key"]: row for row in same["comparison"]}["score"]["note"] == "equal"
    assert runs[0]["score"] is None  # building a document leaves the runs as they were


def test_scores_from_a_file(tmp_path: Path):
    path = tmp_path / "scores.json"
    path.write_text(json.dumps({"swarm1": 7, "solo1": {"score": 8.25, "source": "two blind judges"}}))
    assert replay.read_scores(path) == {
        "swarm1": {"value": 7, "source": "supplied in scores.json"},
        "solo1": {"value": 8.25, "source": "two blind judges (scores.json)"}}
    for bad, message in (('{"a": "high"}', "the score of 'a' in"), ('{"a": true}', "must be a number"),
                         ('{"a": {"source": "x"}}', "must be a number"), ("[1]", "must be a JSON object"),
                         ("{", "is not JSON"), ('{"a": NaN}', "must be a number")):
        path.write_text(bad)
        with pytest.raises(replay.ReplayError, match=re.escape(message)):
            replay.read_scores(path)
    with pytest.raises(replay.ReplayError, match="cannot read"):
        replay.read_scores(tmp_path / "missing.json")


def test_only_one_or_two_runs(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    _solo(run)
    found = run.replay()
    with pytest.raises(replay.ReplayError, match="one run, or two side by side"):
        replay.build([found, found, found])
    single = replay.build([found])
    assert single["ahead"] is None and single["compatibility"] == [] and single["notes"] == []
    assert "where each run comes out ahead" not in replay.render_text(single)


# --- the text view and the playback ---------------------------------------------------------------


def test_text_view(tmp_path: Path):
    swarm, solo = _pair(tmp_path)
    shas = _swarm(swarm)
    _solo(solo)
    document = replay.build([swarm.replay(), solo.replay()])
    text = replay.render_text(document)
    lines = text.splitlines()
    assert lines[0] == "murmur replay: swarm1 vs solo1"
    assert lines[3].startswith("clock: wall-clock time since each run's first session-log entry")
    assert "Nothing is" in text and "stretched, compressed or aligned" in " ".join(lines[3:6])
    lane = {line.split("|")[0].strip(): line.split("|", 1)[1] for line in lines if re.match(r"  \w+ +\|", line)}
    assert set(lane) == {"root", "a1", "a2", "solo"}
    assert lane["root"].startswith("[c") and lane["root"].rstrip().endswith("]")
    assert {"M", "t", "p"} <= set(lane["a1"]) and "D" in lane["a2"] and "M" in lane["solo"]
    assert max(map(len, lane.values())) <= replay.LANE_WIDTH
    assert ("  A a1    5 tool calls (1 test, 1 edit, 1 git, 1 coord, 1 read); 1 post; 1 commit on main; 20,000\n"
            "          input (12,000 cached), 700 output\n") in text
    assert "key events (turns, posts, commits, checks; --all lists every tool call)" in text
    assert "A a1   on main    " + shas["main"][:7] in text and "A a2   draft      draft/a2: " in text
    assert "cat <workspace>" not in text  # reads are not key events
    assert f"A {shas['main'][:7]}  a1  Add the feature  [main, 1 file(s) +1 -0]" in text
    assert "verified: OBSERVED, passed: " in text
    assert all(len(line) <= 160 for line in lines)

    every = replay.render_text(document, every=True)
    assert "\nevents\n" in every and "A a1   read       cat <workspace>/prompts/a1.md" in every
    assert "A a1   say        I will add the feature and test it." in every
    assert "A a1   test       python3 -m unittest -q (check passed, exit 0)" in every
    # `pytest | tail`: the status is the pipe's, so the replay does not call the check passed.
    assert "git fetch origin && pytest -q | tail -3 (exit 0, not the check's own)" in every


def test_the_key_event_list_is_capped_and_says_so(tmp_path: Path):
    run = Replayed(tmp_path)
    run.turn("a1")
    for number in range(replay.KEY_EVENT_LIMIT + 5):
        run.post("a1", f"note {number}")
    run.write()
    text = replay.render_text(replay.build([run.replay()]))
    assert "  ... 6 more: --all prints them, and --html has them all" in text
    assert f"note {replay.KEY_EVENT_LIMIT + 4}" in replay.render_text(replay.build([run.replay()]), every=True)


def test_a_failed_command_shows_its_exit_status(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    run.turn("solo")
    run.exec("solo", 'tools.exec_command({cmd:"ls nope"})', [("ls nope", 2, "No such file")])
    run.exec("solo", 'tools.exec_command({cmd:"pytest -q"})', [("pytest -q", 1, "1 failed")])
    run.write()
    text = replay.render_text(replay.build([run.replay()]), every=True)
    assert "read       ls nope (exit 2)" in text and "test       pytest -q (check FAILED, exit 1)" in text
    assert [event["check"] for event in run.replay()["events"]] == [None, None, "failed"]


def test_playback_prints_every_event_in_clock_order_without_waiting_off_a_terminal(tmp_path: Path):
    swarm, solo = _pair(tmp_path)
    _swarm(swarm)
    _solo(solo)
    document = replay.build([swarm.replay(), solo.replay()])
    out, naps = io.StringIO(), []
    replay.play(document, out, speed=10, animate=False, sleep=naps.append)
    text = out.getvalue()
    assert naps == []
    assert text.startswith("murmur replay: swarm1 vs solo1, played without delays, because this is not a terminal\n")
    played = [line for line in text.split("\n\n")[1].splitlines()]
    assert len(played) == sum(len(run["events"]) for run in document["runs"]) + 2
    stamps = [line[:8].strip() for line in played]
    seconds = [int(stamp.split(":")[0]) * 60 + int(stamp.split(":")[1]) for stamp in stamps]
    assert seconds == sorted(seconds)
    finishes = [line for line in played if " FINISH " in line]
    assert [line.split(" FINISH ")[1].split(":")[0] for line in finishes] == ["solo1", "swarm1"]
    assert "exit 0, delivered; 53,000 input (34,500 cached), 1,680 output" in finishes[1]
    assert "[20,000 in]" not in text and "[26,000 in]" in text  # the run's running total, not one agent's
    assert text.rstrip().endswith("not compared: quality: no quality score supplied for both runs")


def test_animated_playback_waits_in_proportion_and_does_not_skip_quiet_time(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    run.turn("solo")
    run.tick(300)
    run.turn("solo", end="done")
    run.write()
    run.finish()
    document = replay.build([run.replay()])
    out, naps = io.StringIO(), []
    replay.play(document, out, speed=60, animate=True, sleep=naps.append)
    assert naps == [pytest.approx(1 / 60), pytest.approx(301 / 60)]
    assert sum(naps) == pytest.approx(document["runs"][0]["duration_s"] / 60)
    assert "played at 60x: one second here is 60 s of the run, quiet stretches included" in out.getvalue()


# --- the HTML page ---------------------------------------------------------------------------------


def _embedded(html: str) -> str:
    start = html.index("const DATA = ") + len("const DATA = ")
    return html[start:html.index(";\n(function () {", start)]


def _page_script(html: str) -> str:
    return html[html.index("<script>") + len("<script>"):html.rindex("</script>")]


def test_html_is_one_self_contained_file(tmp_path: Path):
    swarm, solo = _pair(tmp_path)
    _swarm(swarm)
    _solo(solo)
    document = replay.build([swarm.replay(), solo.replay()])
    html = replay.render_html(document)
    assert html.startswith("<!doctype html>") and html.rstrip().endswith("</html>")
    assert json.loads(_embedded(html)) == document
    # Nothing is fetched: no URL, no linked file, and a policy that forbids loading any.
    assert not re.search(r"https?://|//[a-z]|\bsrc\s*=|<link\b|@import|url\(", html)
    assert "default-src 'none'" in html
    assert html.count("<script>") == 1 and html.count("</script>") == 1
    for control in ('id="play"', 'id="speed"', 'id="scrub"', 'id="lanes"', 'id="meters"', 'id="receipts"',
                    'id="cards"', 'id="log"', 'id="compat"'):
        assert control in html
    # The page builds itself from the data with text nodes only.
    script = _page_script(html)
    assert not re.search(r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|\beval\(|new Function", script)


def test_log_text_cannot_become_markup(tmp_path: Path):
    run = Replayed(tmp_path)
    attack = "</script>\u2028<script>alert(1)</script><img src=x onerror=alert(2)>"
    run.turn("a1")
    run.say("a1", f"said {attack} and <!-- a comment")
    run.exec("a1", "tools.exec_command({})", [(f"echo '{attack}'", 0, attack)])
    run.post("a1", f"post {attack}")
    run.commit("a1", f"Subject {attack}\n\nBody {attack}")
    run.turn("a1", end=attack)
    run.write()
    document = replay.build([run.replay()])
    assert sum(attack in event["text"] for event in document["runs"][0]["events"]) >= 4  # it is in the data
    html = replay.render_html(document)
    assert html.count("</script>") == 1 and "<img" not in html and "<!-- a" not in html
    assert "\u2028" not in html and "alert(1)" in html  # kept, as escaped text inside the JSON
    data = _embedded(html)
    assert "<" not in data and ">" not in data and "&" not in data
    assert json.loads(data) == document


def test_the_page_script_runs_and_plays(tmp_path: Path):
    """Run the page's script in Node against a stand-in DOM: it must build the page and move the clock."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    swarm, solo = _pair(tmp_path)
    shas = _swarm(swarm)
    _solo(solo)
    document = replay.build([swarm.replay(), solo.replay()], {"swarm1": replay.score(7, "<b>a judge</b>")})
    html = replay.render_html(document)
    ids = re.findall(r'id="(\w+)"', html)
    harness = tmp_path / "page.js"
    harness.write_text(_DOM + f"\nconst IDS = {json.dumps(ids)};\n" + _page_script(html) + _CHECKS)
    done = subprocess.run([node, str(harness)], capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    seen = json.loads(done.stdout)
    assert seen["title"] == "murmur replay: swarm1 vs solo1"
    assert seen["markup"] == []  # no element was ever given markup to parse
    longest = max(run["duration_s"] for run in document["runs"])
    assert seen["end"]["now"] == longest and seen["end"]["shown"] == seen["end"]["total"] > 20
    assert seen["start"] == {"now": 0, "shown": seen["start"]["shown"], "total": seen["end"]["total"],
                             "playing": False}
    assert 0 <= seen["start"]["shown"] < seen["middle"]["shown"] < seen["end"]["shown"]
    assert seen["played"]["now"] == longest and seen["played"]["playing"] is False
    text = "\n".join(seen["text"])
    for expected in ("no quality score supplied", "<b>a judge</b>", "Same task and settings: brief sha256",
                     shas["main"][:7], "OBSERVED, passed", "53,000 input (34,500 cached)", "finish ",
                     "Clock: wall-clock time", "murmur did not assess quality"):
        assert expected in text, expected
    # Tokens tick with the clock: nothing at the start, a part in the middle, the totals at the end.
    assert seen["meters"][0].startswith("0 input") and seen["meters"][2].startswith("53,000 input")
    middle = int(seen["meters"][1].split(" input")[0].replace(",", ""))
    assert 0 < middle < 53000


# A stand-in for the browser's DOM: enough for the page to build itself, and it records every
# text it is given and any attempt to set markup.
_DOM = r"""
const texts = [], markup = [], frames = [];
function node(tag) {
  const classes = new Set();
  const self = {
    tagName: String(tag).toUpperCase(), children: [], style: {}, listeners: {}, hidden: false, open: false,
    classList: { add: (c) => classes.add(c), remove: (c) => classes.delete(c), contains: (c) => classes.has(c),
                 toggle: (c, on) => (on === undefined ? !classes.has(c) : on) ? classes.add(c) : classes.delete(c) },
    appendChild(child) { self.children.push(child); return child; },
    addEventListener(kind, run) { self.listeners[kind] = run; },
    click() { if (self.listeners.click) self.listeners.click({ target: self }); },
    scrollIntoView() {}, setAttribute() {},
  };
  let text = "";
  Object.defineProperty(self, "textContent", { get: () => text,
    set: (value) => { text = String(value); texts.push(text); } });
  Object.defineProperty(self, "className", { get: () => [...classes].join(" "),
    set: (value) => { classes.clear(); String(value).split(/\s+/).filter(Boolean).forEach((c) => classes.add(c)); } });
  for (const name of ["innerHTML", "outerHTML"]) {
    Object.defineProperty(self, name, { set: (value) => markup.push(value), get: () => "" });
  }
  self.insertAdjacentHTML = (where, value) => markup.push(value);
  return self;
}
const byId = {};
const document = {
  title: "", activeElement: { tagName: "BODY" },
  createElement: node,
  getElementById: (id) => byId[id] || (IDS.includes(id) || id.startsWith("rc-") ? (byId[id] = node("div")) : null),
  querySelectorAll: () => [], querySelector: () => null,
  addEventListener() {}, write: (value) => markup.push(value),
};
const window = globalThis;
let clockMs = 0;
globalThis.performance = { now: () => clockMs };
globalThis.requestAnimationFrame = (run) => { frames.push(run); };
"""

_CHECKS = r"""
const api = window.murmurReplay, seen = { title: document.title, markup };
const meter = () => byId.meters.children[0].children[1].children[1].textContent;
seen.end = api.state();
seen.meters = [];
api.draw(0); seen.start = api.state(); seen.meters.push(meter());
api.draw(seen.end.now / 2); seen.middle = api.state(); seen.meters.push(meter());
api.draw(seen.end.now); seen.meters.push(meter());
byId.play.click();   // from the end, Play starts over
for (let step = 0; step < 100000 && frames.length; step++) { clockMs += 1000; frames.shift()(clockMs); }
seen.played = api.state();
seen.text = texts;
console.log(JSON.stringify(seen));
"""


# --- nothing leaks, nothing changes ------------------------------------------------------------------


def _fingerprint(root: Path) -> dict[str, tuple]:
    return {str(path.relative_to(root)): (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
            for path in sorted(root.rglob("*")) if path.is_file() and not path.is_symlink()}


def test_a_replay_changes_nothing_in_the_run_and_never_opens_auth(tmp_path: Path):
    global _watching
    run = Replayed(tmp_path)
    run.turn("a1")
    run.exec("a1", "tools.exec_command({})", [("pytest -q", 0, "1 passed")])
    sha = run.commit("a1")
    run.post("a1", f"DONE {sha[:7]}")
    run.tokens("a1", 10, 1, 1)
    board = run.write(wal=True)
    try:
        run.finish()
        auth = run.ws / "codex-home" / "auth.json"
        auth.unlink()
        auth.write_text('{"OPENAI_API_KEY": "sk-live-do-not-read-this-0123456789"}\n')
        before = _fingerprint(run.ws)
        _opened.clear()
        _watching = True
        try:
            document = replay.build([run.replay()])
            out = io.StringIO()
            replay.play(document, out)
            shown = replay.render_text(document, every=True) + replay.render_html(document) + out.getvalue()
        finally:
            _watching = False
        assert _fingerprint(run.ws) == before
        assert _opened and not [path for path in _opened if "auth" in Path(path).name]
        assert "do-not-read" not in shown
        assert [event["text"] for event in _events(document["runs"][0], kind="post")] == [f"#tasks DONE {sha[:7]}"]
    finally:
        board.close()


def test_secrets_long_text_and_personal_paths_do_not_reach_a_replay(tmp_path: Path):
    run = Replayed(tmp_path)
    key = "sk-proj-abcdefghijklmnopqrstuvwxyz0123456789"
    home = str(Path.home())
    run.turn("a1")
    run.say("a1", f"Using OPENAI_API_KEY={key} from {home}/.config and /home/somebody/notes " + "x" * 2000)
    run.exec("a1", "tools.exec_command({})",
             [(f"curl -H 'Authorization: Bearer {key}' https://example.com > {run.ws}/out.json", 0, key)])
    run.post("a1", f"token: ghp_{'a' * 36} in {run.ws}/work")
    run.turn("a1", end=f"wrote {home}/result with {key}")
    run.write()
    document = replay.build([run.replay()])
    shown = replay.render_text(document, every=True) + replay.render_html(document) + replay.to_json(document)
    assert key not in shown and "ghp_" not in shown and "abcdefghij" not in shown
    assert home not in shown and "/home/somebody" not in shown and str(run.ws) not in shown
    assert "[redacted]" in shown and "<workspace>/out.json" in shown
    said = _events(document["runs"][0], "a1", "say")[0]["text"]
    assert len(said) < replay.MAX_EVENT_TEXT + 40 and said.endswith("more chars]")
    # An encrypted payload (what `spawn_agent` is sent) is named, not copied.
    run.call("root", "spawn_agent", {"task_name": "a1", "message": "gAAAAAB" + "Zz9_-" * 30})
    assert "Zz9_-" not in replay.to_json(replay.build([run.replay()]))


# --- the command -----------------------------------------------------------------------------------


def test_replay_command(tmp_path: Path):
    swarm, solo = _pair(tmp_path)
    _swarm(swarm)
    _solo(solo)
    one = run_cli("replay", str(swarm.ws))
    assert one.returncode == 0 and one.stderr == ""
    assert one.stdout == replay.render_text(replay.build([swarm.replay()]))  # the text has no "made at" line
    assert one.stdout.startswith("murmur replay: swarm1\n")

    two = run_cli("replay", str(swarm.ws), str(solo.ws), "--score-a", "7", "--score-b", "7.5")
    assert two.returncode == 0, two.stderr
    assert two.stdout.startswith("murmur replay: swarm1 vs solo1\n")
    assert "score of A: 7, supplied with --score-a; murmur did not assess quality" in two.stdout
    assert "B is higher by 0.5" in two.stdout

    every = run_cli("replay", str(swarm.ws), "--all")
    assert "cat <workspace>/prompts/a1.md" in every.stdout and "cat <workspace>" not in one.stdout

    played = run_cli("replay", str(swarm.ws), str(solo.ws), "--play", "--speed", "100")
    assert played.returncode == 0 and "played without delays, because this is not a terminal" in played.stdout
    assert " FINISH solo1: exit 0, delivered" in played.stdout

    scores = tmp_path / "scores.json"
    scores.write_text('{"solo1": {"score": 6, "source": "my own reading"}}')
    out = tmp_path / "race.html"
    page = run_cli("replay", str(swarm.ws), str(solo.ws), "--html", str(out), "--score", str(scores), "--speed", "5")
    assert page.returncode == 0, page.stderr
    assert page.stderr.strip() == f"murmur: wrote {out}"
    assert page.stdout.startswith("murmur replay: swarm1 vs solo1\n") and "lanes (" not in page.stdout
    data = json.loads(_embedded(out.read_text()))
    assert data["speed"] == 5 and [run["score"] for run in data["runs"]] == [
        None, {"value": 6, "source": "my own reading (scores.json)"}]
    assert not list(tmp_path.glob(".race.html*"))

    saved = tmp_path / "saved.json"
    printed = run_cli("replay", str(swarm.ws), str(solo.ws), "--json")
    saved.write_text(printed.stdout)
    again = run_cli("replay", str(saved))
    assert again.returncode == 0, again.stderr
    assert again.stdout == run_cli("replay", str(swarm.ws), str(solo.ws)).stdout  # a saved replay shows the same


def test_score_flags_go_by_position_even_when_two_runs_share_an_id(tmp_path: Path):
    first, second = Replayed(tmp_path / "x", "--solo"), Replayed(tmp_path / "y", "--solo")
    _solo(first)
    _solo(second)
    scores = tmp_path / "scores.json"
    scores.write_text('{"run1": 1}')
    shown = run_cli("replay", str(first.ws), str(second.ws), "--score-a", "6", "--score-b", "9", "--json")
    assert [run["score"]["value"] for run in json.loads(shown.stdout)["runs"]] == [6, 9]
    mixed = run_cli("replay", str(first.ws), str(second.ws), "--score", str(scores), "--score-b", "9", "--json")
    assert [run["score"] and run["score"]["value"] for run in json.loads(mixed.stdout)["runs"]] == [None, 9]
    filed = run_cli("replay", str(first.ws), "--score", str(scores), "--json")
    assert json.loads(filed.stdout)["runs"][0]["score"] == {"value": 1, "source": "supplied in scores.json"}


def test_replay_command_errors(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    _solo(run)
    ws = str(run.ws)

    def failed(*args: str) -> str:
        done = run_cli("replay", *args)
        assert done.returncode == 3 and done.stdout == "", done
        return done.stderr.strip()

    assert failed(str(tmp_path / "nope")) == f"murmur: cannot read {tmp_path / 'nope'}: No such file or directory"
    assert failed(str(tmp_path)) == f"murmur: no workspace at {tmp_path}"
    assert failed(ws, ws, ws) == "murmur: replay takes one run, or two to show side by side"
    assert failed(ws, "--score-b", "5") == "murmur: --score-b needs a second run"
    for speed in ("0", "-2", "nan", "inf"):
        assert failed(ws, "--speed", speed) == "murmur: --speed must be a number greater than 0"
    assert failed(ws, "--score-a", "nan") == "murmur: a score must be a number"
    assert failed(ws, "--score", str(tmp_path / "none.json")).startswith("murmur: cannot read ")
    text = tmp_path / "notes.txt"
    text.write_text("hello\n")
    assert failed(str(text)) == f"murmur: {text} is neither a workspace nor a replay saved with --json"
    for content, message in (('{"kind": "murmur-replay", "schema": 99, "runs": []}', "is a replay of schema 99"),
                             ('{"kind": "murmur-replay", "schema": 1, "runs": []}', "holds no complete run"),
                             ('{"kind": "murmur-replay", "schema": 1, "runs": [{"id": "x"}]}',
                              "holds no complete run"),
                             ('{"kind": "something else"}', "is neither a workspace nor a replay")):
        text.write_text(content)
        assert message in failed(str(text))
    assert failed(ws, "--html", str(tmp_path / "no" / "such" / "dir.html")).startswith("murmur: ")
    assert run_cli("replay").returncode == 2


def test_a_saved_replay_with_a_damaged_run_is_refused(tmp_path: Path):
    run = Replayed(tmp_path, "--solo")
    _solo(run)
    document = replay.build([run.replay()])
    path = tmp_path / "saved.json"
    for damage in (lambda run: run["events"][0].pop("t"), lambda run: run["events"].append("text"),
                   lambda run: run.update(duration_s="long"), lambda run: run["outcome"].pop("exit_code"),
                   lambda run: run["clock"].pop("label"), lambda run: run.update(agents=[{"role": "peer"}])):
        broken = json.loads(replay.to_json(document))
        damage(broken["runs"][0])
        path.write_text(json.dumps(broken))
        with pytest.raises(replay.ReplayError, match="holds no complete run"):
            replay.load(path)
    path.write_text(replay.to_json(document))
    assert replay.build(replay.load(path))["comparison"] == document["comparison"]


@pytest.mark.parametrize("mode", ["--solo", "--peers=2"])
def test_replay_of_a_run_made_by_murmur_run(tmp_path: Path, mode: str):
    """End to end with the stand-in Codex: its logs have no Codex version, so the replay says so."""
    from support import setup_workspace
    workspace = setup_workspace(tmp_path, mode)
    assert re.fullmatch(r"[0-9a-f]{64}", json.loads((workspace / "murmur.json").read_text())["brief_sha256"])
    result = run_cli("run", str(workspace), extra_env={"MURMUR_FAKE_CODEX_MODE": "receipts"})
    assert result.returncode == 0, result.stderr
    shown = run_cli("replay", str(workspace), "--all")
    assert shown.returncode == 0, shown.stderr
    assert "EXAMPLE DATA: the session logs carry no Codex CLI version" in shown.stdout
    assert "exit                         0, delivered" in shown.stdout
    agents = ["solo"] if mode == "--solo" else ["a1", "a2"]
    for agent in agents:
        assert re.search(rf"A {agent} +on main +[0-9a-f]{{7}} Add {agent}.txt", shown.stdout)
    assert "launcher clock" in shown.stdout and "verified: OBSERVED, passed" in shown.stdout
    out = tmp_path / "run.html"
    assert run_cli("replay", str(workspace), "--html", str(out)).returncode == 0
    assert json.loads(_embedded(out.read_text()))["runs"][0]["main"]["commits"] == len(agents)


def test_the_page_template_ships_with_the_package():
    from importlib.resources import files
    template = files("murmur").joinpath("replay.html").read_text(encoding="utf-8")
    assert template.count(replay._DATA_MARK) == 1
