"""scripts/timeline_to_replay.py: published research timelines as replays.

The timelines here are made up for the tests, in the format of the round-4 forensics files.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from murmur import replay
from support import run_cli

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "timeline_to_replay.py"
spec = importlib.util.spec_from_file_location("timeline_to_replay", SCRIPT)
importer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(importer)

SWARM = """\
# Timeline X1-T9-swarm-r1

result.json: {"run_exit": 0, "wall_min": 1445.0, "active_min": 6.5, "input": 900000, "commits": 2, "delivered": true, "murmur_sha": "abc123", "capped": null}
score overall 6.5
- judge: {"coverage": 7, "overall": 6.0, "guess": "team"}
- judge: {"coverage": 7, "overall": 7.0, "guess": "team"}
judge evidence (full text): /lab/judge/X1-T9-swarm-r1.j1.md
git refs at end (/lab/ws/X1-T9-swarm-r1/work/origin.git):
```
draft/a1 1111111
main 2222222
```

## Per-agent summary (A = active min)
- a1: calls 3, first A0.2, last A4.0
- run span: active 4.2 min, wall 1445.0 min

## Event stream (A active-min | W Taipei | who | kind | content)
A   0.0 | 23:58:00 | murmur | COMMIT    | 0000000 [] Snapshot of /lab/tasks/T9/input (3 files changed, 9 insertions(+))
A   0.0 | 23:58:01 | root  | TURN_START | exec
A   0.1 | 23:58:06 | root  | FCALL     | spawn_agent {"task_name":"a1","message":"gAAAAABq1kzRJfWabwIvX4E5hc1g3IFPiAyLZ0BF5PKtvEc …[+900]
A   0.2 | 23:58:12 | a1    | TURN_START | exec
A   0.2 | 23:58:12 | a1    | TURN_START | exec
A   0.2 | 23:58:12 | a1    | MAIL      | /root->/root/a1: Message Type: NEW_TASK
A   0.4 | 23:58:24 | a1    | THINK     | **Planning the draft**
A   0.5 | 23:58:30 | a1    | CALL      | text(await tools.exec_command({cmd:"cat /lab/ws/prompts/a1.md"})); text(await tools.collaboration__post({channel_name:"tasks",text:"CLAIM a1 | all of it"}));
A   0.5 | 23:58:31 | a1    | OUT       | Script completed Wall time 0.3 seconds Output: {"chunk_id":"b5","exit_code":0,"output":"the brief"}
A   0.5 | 23:58:31 | a1    | POST#tasks | CLAIM a1 | all of it
A   2.0 | 00:00:00 | a1    | CALL      | text(await tools.exec_command({cmd:"cat > app.py <<'EOF'\\nimport os\\nprint('a long file …[+5000]
A   2.1 | 00:00:06 | a1    | OUT       | Script completed
A   2.5 | 00:00:30 | a1    | COMMIT    | 1111111 [draft/a1] Draft the app (1 file changed, 40 insertions(+))
A   3.0 | 00:01:00 | a1    | CALL      | text(await tools.exec_command({cmd:"python3 -m unittest -q && git push origin HEAD:main"}));
A   3.5 | 00:01:30 | a1    | OUT       | Script completed Output: {"exit_code":1,"output":"FAILED (failures=1)"}
A   3.9 | 23:59:54 | a1    | COMMIT    | 2222222 [HEAD -> main] Finish the app (2 files changed, 12 insertions(+), 3 deletions(-))
A   4.0 | 00:00:00 | a1    | SAY       | Pushed to main.
A   4.0 | 00:00:00 | a1    | TURN_END  | Pushed to main.
A   4.2 | 00:00:12 | root  | TURN_END  | done
"""

SOLO = """\
# Timeline X1-T9-solo-r1

result.json: {"run_exit": 0, "wall_min": 9.0, "active_min": 8.5, "input": 200000, "commits": 1, "delivered": true, "murmur_sha": null, "capped": null}
score overall 6.75
- judge: {"overall": 6.5, "guess": "single"}
- judge: {"overall": 7.0, "guess": "single"}
git refs at end (/lab/ws/X1-T9-solo-r1/repo/.git):
```
main 3333333
```

## Per-agent summary (A = active min)
- run span: active 6.0 min, wall 9.0 min

## Event stream (A active-min | W Taipei | who | kind | content)
A   0.0 | 12:00:00 | op    | COMMIT    | 9999999 [] Initial import (4 files changed, 10 insertions(+))
A   0.1 | 12:00:06 | root  | TURN_START | exec
A   0.3 | 12:00:18 | root  | FCALL     | exec_command {"cmd":"pwd && ls -la && rg --files -g AGENTS.md","max_output_tokens":4000}
A   0.3 | 12:00:19 | root  | OUT       | Chunk ID: 4c Wall time: 0.0 seconds Process exited with code 1 Original token count: 215 Output: /lab
A   5.5 | 12:08:30 | Codex | COMMIT    | 3333333 [HEAD -> main] Build it alone (5 files changed, 300 insertions(+))
A   5.5 | 12:08:30 | root  | FCALL     | exec_command {"cmd":"git -c user.name=Codex commit -m \\"Build it alone\\"\\ngit status --short","workdir":"/lab"}
A   5.5 | 12:08:31 | root  | OUT       | Chunk ID: 2b Process exited with code 0 Output: [main 3333333] Build it alone 5 files changed
A   5.8 | 12:08:48 | root  | ERROR     | {"type": "stream_error", "message": "retrying"}
A   6.0 | 12:09:00 | root  | TURN_END  | Committed to main.
"""

RESULTS = {"exp": "X1", "rows": [
    {"run": "X1-T9-swarm-r1", "task": "T9", "arm": "swarm", "overall": 6.5, "active_nf": 4.1, "active_raw": 6.5,
     "runner_active": 6.5, "wall_min": 1445.0, "input": 900000, "uncached": 30000, "output": 7000,
     "guesses": ["team", "team"], "unmerged_branches": 1, "main_added_lines": 52},
    {"run": "X1-T9-solo-r1", "task": "T9", "arm": "solo", "overall": 6.75, "active_nf": 7.0, "active_raw": 8.5,
     "input": 200000, "uncached": 9000, "output": 3000, "guesses": ["single", "single"]},
]}


@pytest.fixture
def files(tmp_path: Path) -> dict[str, Path]:
    timelines = tmp_path / "research-r4" / "analysis" / "forensics" / "timelines"
    timelines.mkdir(parents=True)
    results = tmp_path / "research-r4" / "results" / "E1.json"
    results.parent.mkdir()
    results.write_text(json.dumps(RESULTS))
    (timelines / "X1-T9-swarm-r1.md").write_text(SWARM)
    (timelines / "X1-T9-solo-r1.md").write_text(SOLO)
    return {"swarm": timelines / "X1-T9-swarm-r1.md", "solo": timelines / "X1-T9-solo-r1.md", "results": results}


def _shown(run: dict) -> list[tuple]:
    return [(event["t"], event["agent"], event["kind"], event["text"]) for event in run["events"]]


def test_a_timeline_becomes_a_run_on_its_active_clock(files):
    run = importer.to_run(files["swarm"])
    cited = "research-r4/analysis/forensics/timelines/X1-T9-swarm-r1.md"
    assert run["id"] == "X1-T9-swarm-r1" and (run["mode"], run["peers"]) == ("swarm", 1)
    assert run["source"]["kind"] == "timeline" and run["source"]["files"] == [cited]
    assert "not read from a run's workspace" in run["source"]["description"]
    assert run["clock"]["kind"] == "active" and "an estimate" in run["clock"]["note"]
    assert run["duration_s"] == 252.0  # 4.2 active minutes: nothing is added to it
    assert _shown(run) == [
        (0.0, "root", "turn_start", ""),
        (6.0, "root", "coord", "spawn_agent a1 [cut short in the timeline]"),
        (12.0, "a1", "turn_start", ""),
        (30.0, "a1", "read", "cat /lab/ws/prompts/a1.md"),
        (30.0, "a1", "coord", "post"),
        (30.0, "a1", "post", "#tasks CLAIM a1 | all of it"),
        (120.0, "a1", "edit", "cat > app.py <<'EOF' [cut short in the timeline]"),
        (150.0, "a1", "commit", "1111111 [draft/a1] Draft the app (1 file changed, 40 insertions(+))"),
        (180.0, "a1", "test", "python3 -m unittest -q && git push origin HEAD:main"),
        (234.0, "a1", "commit", "2222222 [HEAD -> main] Finish the app (2 files changed, 12 insertions(+), "
                                "3 deletions(-))"),
        (240.0, "a1", "say", "Pushed to main."),
        (240.0, "a1", "turn_end", "Pushed to main."),
        (252.0, "root", "turn_end", "done"),
    ]
    by_kind = {event["kind"]: event for event in run["events"]}
    assert (by_kind["read"]["end"], by_kind["read"]["exit"]) == (30.0, 0)  # the one command of its call
    assert (by_kind["edit"]["end"], by_kind["edit"]["exit"]) == (126.0, None)  # its output line gives no status
    assert (by_kind["test"]["end"], by_kind["test"]["exit"]) == (210.0, 1)
    assert by_kind["test"]["check"] == "unclear"  # the push after `&&` may be what failed
    assert all("script" not in event for event in run["events"])
    assert run["events"][1]["end"] is None  # no output line followed the spawn
    assert [event["sha"] for event in run["events"] if event["kind"] == "commit"] == ["1111111", "2222222"]
    assert run["base"] == "0000000"  # the snapshot is where the run started, not an agent's work
    assert [(agent["id"], agent["role"], agent["turns"]) for agent in run["agents"]] == [
        ("root", "root", [[0.0, 252.0]]), ("a1", "peer", [[12.0, 240.0]])]
    assert run["agents"][1]["calls"] == {"test": 1, "edit": 1, "coord": 1, "read": 1}
    assert run["outcome"] == {"finished": True, "exit_code": 0, "delivered": True, "capped": None,
                              "interrupted": None, "diagnostic": None}
    assert run["tokens"]["total"] == {"input_tokens": 900000, "cached_input_tokens": None,
                                      "uncached_input_tokens": None, "output_tokens": None}
    assert run["main"] == {"commits": 2, "files": None, "insertions": None, "deletions": None,
                           "last_change_s": None}
    assert run["drafts"] == ["draft/a1"] and run["task"] is None
    assert run["score"] == {"value": 6.5, "source": f"'score overall' in {cited}; its judge lines give 6 and 7"}
    assert run["receipts"] == [] and "not available" in run["receipts_note"]
    facts = {fact["label"]: fact for fact in run["facts"]}
    assert facts["result.json active_min"] == {"label": "result.json active_min", "value": "6.5", "source": cited}
    assert facts["timeline run span"]["value"] == "active 4.2 min, wall 1445 min"
    assert facts["started from"]["value"].startswith("0000000 [] Snapshot of")
    assert json.loads(facts["judge 2"]["value"])["overall"] == 7.0
    assert all(fact["source"] == cited for fact in run["facts"])
    assert run["warnings"][0] == ("left out of the timeline: 1 MAIL line (deliveries of messages to an agent), "
                                  "1 THINK line (reasoning summaries), 1 repeated TURN_START line")
    assert "not whether each command ran" in run["warnings"][1]
    assert run["warnings"][2].startswith("commits (2) are placed by their author time")


def test_the_wall_clock_is_the_time_of_day_column_across_midnight(files):
    run = importer.to_run(files["swarm"], clock="wall")
    assert run["clock"]["kind"] == "wall" and "frozen" in run["clock"]["note"]
    times = {event["kind"]: event["t"] for event in run["events"]}
    assert times["read"] == 30 and times["test"] == 180  # 23:58:30 and, past midnight, 00:01:00
    # The file is in time order but its clock column is a time of day: a second midnight is a second day.
    assert times["say"] == 120 + 86400 and run["duration_s"] == 132 + 86400
    assert [event["t"] for event in run["events"]] == sorted(event["t"] for event in run["events"])
    assert run["warnings"][0].startswith("the event stream ends at 1442.2 min on this clock, but the timeline's "
                                         "own summary says 1445")


def test_a_solo_timeline_and_the_results_file(files):
    run = importer.to_run(files["solo"], files["results"])
    assert (run["mode"], run["peers"], run["task"], run["base"]) == ("solo", 1, "T9", "9999999")
    assert [(agent["id"], agent["role"]) for agent in run["agents"]] == [("root", "solo")]
    listing, commit, committing, error, end = run["events"][1:]
    assert (listing["kind"], listing["text"], listing["exit"]) == (
        "read", "pwd && ls -la && rg --files -g AGENTS.md", 1)
    # Git names "Codex" as the author; the agent whose command printed the SHA made the commit.
    assert (commit["agent"], commit["kind"], commit["sha"]) == ("root", "commit", "3333333")
    assert commit["text"].endswith("(git author Codex)")
    assert (committing["kind"], committing["exit"]) == ("git", 0) and "⏎ git status --short" in committing["text"]
    assert (error["kind"], end["kind"]) == ("error", "turn_end")
    assert run["tokens"]["total"] == {"input_tokens": 200000, "cached_input_tokens": None,
                                      "uncached_input_tokens": 9000, "output_tokens": 3000}
    assert "research-r4/results/E1.json" in run["tokens"]["source"]
    assert run["source"]["files"][1] == "research-r4/results/E1.json"
    facts = {fact["label"]: fact for fact in run["facts"]}
    assert facts["E1.json active_nf"] == {"label": "E1.json active_nf", "value": "7.0",
                                         "source": "research-r4/results/E1.json"}
    assert "E1.json main_added_lines" not in facts  # the file has none for this run, so none is shown
    assert not any(warning.startswith("left out") for warning in run["warnings"])


def test_a_pair_of_timelines_says_what_the_files_do_not_record(files):
    runs = [importer.to_run(files[name], files["results"]) for name in ("swarm", "solo")]
    document = replay.build(runs)
    assert document["example"] is None
    assert document["compatibility"] == [
        "the brief of A and B has no recorded hash, so it is not confirmed that both runs got the same task; "
        "both are labelled task T9 in their source",
        "the model of A and B is not recorded",
        "the reasoning effort of A and B is not recorded",
        "the base commit differs: A 0000000, B 9999999",
        "the time cap of A and B is not recorded"]
    rows = {row["key"]: row for row in document["comparison"]}
    assert rows["time"]["label"] == "finished after (active minutes, the timeline's estimate)"
    assert rows["time"]["values"] == ["4:12", "6:00"] and rows["time"]["note"] == "B took 1.4x as long"
    assert rows["input"]["values"] == ["900,000", "200,000"]
    assert rows["cached"]["values"] == ["not recorded", "not recorded"]
    assert rows["uncached"]["values"] == ["30,000", "9,000"] and rows["output"]["values"] == ["7,000", "3,000"]
    assert rows["lines"]["values"] == ["+52", "not recorded"] and rows["model"]["values"] == ["not recorded"] * 2
    assert rows["last_main"]["values"] == ["not recorded"] * 2 and "launcher" not in rows
    assert rows["score"]["values"] == ["6.5", "6.75"] and rows["score"]["note"] == "B is higher by 0.25"
    assert document["ahead"]["A"] == ["finished sooner (4:12 against 6:00)"]
    assert document["ahead"]["B"] == ["used fewer input tokens (200,000 against 900,000)",
                                      "used fewer output tokens (3,000 against 7,000)"]
    text = replay.render_text(document)
    assert "other figures in the source files:" in text
    assert "A E1.json active_nf: 4.1 [research-r4/results/E1.json]" in text
    assert "B tokens per agent: not in the source" in text
    assert "A X1-T9-swarm-r1: not available: change receipts are made from" in text
    html = replay.render_html(document)
    assert "research-r4/analysis/forensics/timelines/X1-T9-solo-r1.md" in html
    one_wall = importer.to_run(files["solo"], clock="wall")
    mixed = replay.build([runs[0], one_wall])
    assert "the runs are on different clocks, so their times do not compare" in mixed["compatibility"]
    assert not any("sooner" in won for label in "AB" for won in mixed["ahead"][label])


def test_a_call_without_a_shell_command_takes_no_exit_status(files):
    lines = SOLO.splitlines()
    at = next(index for index, line in enumerate(lines) if "| ERROR" in line)
    lines[at:at] = [
        'A   5.6 | 12:08:36 | root  | CALL      | text(await tools.apply_patch("*** Begin Patch")); '
        'text(await tools.view_image({path:"a.png"}));',
        'A   5.6 | 12:08:37 | root  | OUT       | Script completed Output: {"exit_code":0}',
        'A   5.7 | 12:08:42 | root  | NEWKIND   | something this importer has never seen']
    files["solo"].write_text("\n".join(lines) + "\n")
    run = importer.to_run(files["solo"])
    patched, viewed = [event for event in run["events"] if event["t"] == 336.0]
    assert (patched["kind"], patched["text"], patched["exit"], patched["end"]) == ("edit", "apply_patch", None, 336.0)
    assert (viewed["kind"], viewed["text"], viewed["check"]) == ("run", "view_image", None)
    assert run["warnings"][0] == "left out of the timeline: 1 NEWKIND line"


def test_files_that_are_not_timelines(files, tmp_path: Path):
    other = tmp_path / "notes.md"
    other.write_text("# Notes\n\nnothing here\n")
    with pytest.raises(importer.TimelineError, match="is not a forensics timeline"):
        importer.parse(other)
    with pytest.raises(importer.TimelineError, match="cannot read"):
        importer.parse(tmp_path / "missing.md")
    (tmp_path / "empty.json").write_text('{"rows": []}')
    with pytest.raises(importer.TimelineError, match="has no row for X1-T9-solo-r1"):
        importer.to_run(files["solo"], tmp_path / "empty.json")
    (tmp_path / "empty.json").write_text("[]")
    with pytest.raises(importer.TimelineError, match="cannot read"):
        importer.to_run(files["solo"], tmp_path / "empty.json")


def test_the_script(files, tmp_path: Path):
    def script(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True, timeout=60)

    both = [str(files["swarm"]), str(files["solo"]), "--results", str(files["results"])]
    shown = script(*both)
    assert shown.returncode == 0, shown.stderr
    assert shown.stdout.startswith("murmur replay: X1-T9-swarm-r1 vs X1-T9-solo-r1\n")
    assert "lanes (one column is" in shown.stdout and "NOT A LIKE-FOR-LIKE PAIR:" in shown.stdout

    saved, page = tmp_path / "pair.json", tmp_path / "pair.html"
    written = script(*both, "--json", str(saved), "--html", str(page), "--clock", "wall")
    assert written.returncode == 0, written.stderr
    assert written.stderr.splitlines() == [f"wrote {page}", f"wrote {saved}"]
    assert "lanes (" not in written.stdout and "finished after (wall clock)" in written.stdout
    assert page.read_text().startswith("<!doctype html>")
    # `murmur replay` shows a saved replay like any other, and a score can still be overridden.
    again = run_cli("replay", str(saved), "--score-a", "9")
    assert again.returncode == 0, again.stderr
    assert "finished after (wall clock)" in again.stdout and "supplied with --score-a" in again.stdout
    assert "score of B: 6.75, 'score overall' in research-r4/" in again.stdout

    bad = script(str(tmp_path / "pair.json"))
    assert bad.returncode == 1 and "is not a forensics timeline" in bad.stderr and bad.stdout == ""
    assert script(*both[:2], str(files["solo"])).returncode == 2
