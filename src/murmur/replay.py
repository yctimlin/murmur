"""Replay: what the agents of a run did over time, and how two runs of one task compare.

A replay is put together from what a run already records, the same sources as its change
receipts. Nothing is executed, checked out or written in the run:

  codex-home/sessions/**/*.jsonl           tool calls, turn starts and ends, token counts
  codex-home/agent_message_board_1.sqlite  the board posts (a scratch copy, read-only)
  work/origin.git                          the commits and when each reached a branch
  murmur.json, logs/run.json               the run's settings, exit status and launcher clocks

`collect_run()` turns one workspace into a run: facts, a list of timed events per agent, the
token counts over time and the change receipts. `build()` puts one or two runs into a document
and, for two, says where each comes out ahead and what makes the comparison unfair (another
brief, model, effort or base). `render_text()`, `play()` and `render_html()` show a document.

What a replay does not do:

- It has no opinion on quality. A score is shown only when the user supplies one.
- It does not move time. Events sit where the logs put them, on the clock named in the
  output: wall-clock seconds since the run's first session-log entry. The launcher's active
  and stalled totals are separate facts from logs/run.json.
- Tool calls are sorted into read, edit, test, git, coord and run by the name of the command.
  That is a reading aid, not a measurement.

Text taken from logs is redacted and shortened the way receipts are, and codex-home/auth.json
is never opened.
"""

from __future__ import annotations

import bisect
import hashlib
import json
import math
import re
import textwrap
import time
from datetime import datetime, timezone
from importlib.resources import files
from pathlib import Path

from murmur import receipts, tokens

SCHEMA = 1
KIND = "murmur-replay"
MAX_EVENT_TEXT = 200
MAX_SERIES = 400
LANE_WIDTH = 64
TEXT_WIDTH = 100
KEY_EVENT_LIMIT = 60
DEFAULT_SPEED = 30.0

# Kinds of tool call, in the order that decides the kind of a command line that is several at once.
TOOL_KINDS = ("test", "edit", "git", "coord", "run", "read")
KEY_KINDS = ("turn_start", "turn_end", "post", "main", "draft", "commit", "test", "error")
KIND_NAMES = {"main": "on main", "turn_start": "turn start", "turn_end": "turn end", "run": "command"}
TOKEN_FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens")
NO_SCORE = "no quality score supplied"

WALL_CLOCK = {
    "kind": "wall",
    "label": "wall clock",
    "note": "wall-clock time since each run's first session-log entry, as the logs recorded it. Nothing is "
            "stretched, compressed or aligned, and time the machine was stalled is included; the launcher's "
            "active and stalled totals (logs/run.json) are listed separately.",
}


class ReplayError(Exception):
    """A run cannot be read, or what was asked for cannot be shown."""


# --- sorting tool calls ----------------------------------------------------------------

_READERS = frozenset(
    "cat ls head tail rg grep egrep fgrep find fd wc pwd tree nl less more stat file which type echo printf "
    "date awk cut sort uniq diff cmp jq test [ env basename dirname realpath readlink du df id whoami uname "
    "column xxd od sed perl".split())
_WRITERS = frozenset("apply_patch cp mv tee patch install truncate".split())
# Housekeeping around the command that matters: these do not decide what a command line is.
_NEUTRAL = frozenset(
    "cd pushd popd export set unset true mkdir rm rmdir chmod touch ln sleep wait fi done esac }".split())
_GIT_READS = frozenset(
    "status log diff show ls-files ls-remote ls-tree rev-parse rev-list blame grep describe cat-file "
    "for-each-ref shortlog reflog".split())
_QUOTED = re.compile(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"")
# `> file` and `>> file`, but not `2>&1`, `>&2` or `> /dev/null`.
_REDIRECT = re.compile(r"(?<![&\d>])>>?\s*(?!&|/dev/null\b)[^\s&|;>]")
_IN_PLACE = re.compile(r"\s-[A-Za-z]*i\b")
_COORD_TOOL = re.compile(r"collaboration|(?:spawn|wait|close|resume)_agent$|list_agents$|send_(?:input|message)$")
_TOOL_CALL = re.compile(r"\btools\.(\w+)\s*\(")
# A string literal after `cmd:`; one that the log cut short runs to the end of the text.
_JS_CMD = re.compile(r"\b(?:cmd|command)\s*:\s*(\"(?:[^\"\\]|\\.)*(?:\"|\\?$)|'(?:[^'\\]|\\.)*(?:'|\\?$)"
                     r"|`(?:[^`\\]|\\.)*(?:`|\\?$))")
_JSON_CMD = re.compile(r"\"(?:cmd|command)\"\s*:\s*\"((?:[^\"\\]|\\.)*)")
_TASK_NAME = re.compile(r"\"task_name\"\s*:\s*\"([^\"\\]+)\"")
_ENCRYPTED = re.compile(r"\bgAAAAA[A-Za-z0-9_-]{16,}=*")


def classify(script: str) -> str:
    """The kind of work a shell command line does: test, edit, git, run or read.

    A line that is several at once (`pytest && git push`) gets the first of TOOL_KINDS it holds.
    Output sent to a file counts as an edit only for commands that write text (`cat > f`), not
    for a program whose output is kept (`python3 capture.py > out.txt`).
    """
    found = set()
    for command, _separator in receipts._split(script):
        bare = receipts._bare(command)
        words = bare.split()
        if not words:
            continue
        program, plain = words[0], _QUOTED.sub("''", bare)
        if receipts._kind(command):
            found.add("test")
        elif program in _NEUTRAL:
            continue
        elif program == "git":
            if words[1:2] == ["-C"]:
                del words[1:3]
            verb = next((word for word in words[1:] if not word.startswith("-")), "")
            found.add("read" if verb in _GIT_READS else "git")
        elif program in _WRITERS or program in _READERS and _REDIRECT.search(plain) or (
                program in ("sed", "perl") and _IN_PLACE.search(plain)):
            found.add("edit")
        elif program in _READERS:
            found.add("read")
        else:
            found.add("run")
    return next((kind for kind in TOOL_KINDS if kind in found), "run")


def _unquote(literal: str) -> str:
    """The text of a JavaScript string literal, well enough to read a shell command out of it."""
    if literal.startswith('"'):
        try:
            return json.loads(literal)
        except json.JSONDecodeError:
            pass
    body = literal[1:-1] if len(literal) > 1 and literal[-1] == literal[0] else literal[1:]
    return re.sub(r"\\(.)", lambda match: {"n": "\n", "t": "\t"}.get(match[1], match[1]), body)


def call_actions(name: str, text: str) -> tuple[list[str], list[str]]:
    """(tools, shell scripts) of one logged tool call.

    `text` is a function call's JSON arguments, or the JavaScript of a code-mode `exec` call,
    which names each tool as `tools.<name>(...)`. Text that was cut short still gives the
    tool names and the start of a command.
    """
    if name in receipts._SHELL_TOOLS:
        try:
            arguments = json.loads(text or "{}")
        except json.JSONDecodeError:
            found = _JSON_CMD.search(text)
            return [name], [_unquote(f'"{found[1]}"')] if found else []
        script = receipts._script(arguments.get("cmd") or arguments.get("command")) if isinstance(
            arguments, dict) else ""
        return [name], [script] if script else []
    named = list(dict.fromkeys(_TOOL_CALL.findall(text)))
    if not named:
        return ([name] if name else []), []
    return named, [_unquote(literal) for literal in _JS_CMD.findall(text)]


def _one_line(script: str) -> str:
    """A script on one line, without heredoc bodies; `⏎` marks where a line ended."""
    lines = (" ".join(line.split()) for line in receipts._without_heredocs(script).splitlines())
    return " ⏎ ".join(line for line in lines if line)


def check_of(script: str, exit_code: int | None) -> str | None:
    """What the exit status says about the checks in a command line: passed, failed or unclear.

    The receipts' rule: `unclear` when the status is not the check's own (`pytest | tail`,
    `pytest; git status`, a `pytest && git push` that failed). None without a check or a status.
    """
    results = [result for _kind, _command, result, _checkout in receipts.checks_in(script, exit_code)]
    if not results or exit_code is None:
        return None
    if "failed" in results:
        return "failed"
    return "passed" if all(result == "passed" for result in results) else "unclear"


def script_event(agent: str, script: str, exit_code: int | None) -> dict:
    """A shell command as an event that has no time yet. `script` is for `check_of`, not for show."""
    return {"agent": agent, "kind": classify(script), "text": _one_line(script), "exit": exit_code,
            "check": check_of(script, exit_code), "script": script}


def tool_events(agent: str, tools: list[str], detail: str = "", patched: bool = False) -> list[dict]:
    """Events for the tools of a call that are not shell commands, one per kind.

    Board and agent tools are `coord`, `apply_patch` is an `edit` (left out when the log has
    the file change itself, `patched`), anything else is `run`.
    """
    groups: dict[str, list[str]] = {}
    for tool in tools:
        if tool in receipts._SHELL_TOOLS or tool == "exec":
            continue  # the commands they ran are events of their own
        if tool == "apply_patch":
            if not patched:
                groups.setdefault("edit", []).append(tool)
        elif _COORD_TOOL.search(tool):
            groups.setdefault("coord", []).append(tool.removeprefix("collaboration__"))
        else:
            groups.setdefault("run", []).append(tool)
    return [{"agent": agent, "kind": kind, "exit": None, "check": None,
             "text": ", ".join(names) + (f" {detail}" if detail and kind == "coord" else "")}
            for kind, names in groups.items()]


def call_events(agent: str, name: str, text: str) -> list[dict]:
    """The events of a logged tool call, read from its text alone.

    For sources that have only the call (an imported timeline). The text says what was asked
    for, not whether each command ran.
    """
    tools, scripts = call_actions(name, text)
    return [*(script_event(agent, script, None) for script in scripts),
            *tool_events(agent, tools, _spawned(name, text))]


def _spawned(name: str, text: str) -> str:
    """The peer a `spawn_agent` call names, for the event text."""
    found = _TASK_NAME.search(text) if name.endswith("spawn_agent") else None
    return found[1] if found else ""


# --- one workspace ---------------------------------------------------------------------


def _session_extras(rollout: Path) -> dict:
    """What the receipts' session reader leaves out of a rollout.

    Turn starts and ends, the running token totals, file changes, when each logged command
    started and ended, and the lines each tool call spans, so that the commands the receipts
    reader found can be put under their call. A forked session's copy of its parent's
    conversation is dropped.
    """
    turns, usage, calls, patches = [], [], [], []
    open_calls: dict[str, dict] = {}
    spans: dict[int, tuple[float, float]] = {}
    meta, own, start, last_at = None, False, None, None
    with rollout.open(encoding="utf-8", errors="replace") as handle:
        for number, line in enumerate(handle, start=1):
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            payload = event.get("payload") if isinstance(event, dict) else None
            if not isinstance(payload, dict):
                continue
            last_at = at = receipts._epoch(event.get("timestamp")) or last_at
            start = at if start is None else start
            kind, inner = event.get("type"), payload.get("type")
            if kind == "session_meta":
                meta = meta or payload
            elif kind == "event_msg" and inner == "thread_settings_applied" and not own:
                own = True
                if isinstance(meta, dict) and meta.get("forked_from_id"):
                    for parents in (turns, usage, calls, patches, open_calls, spans):
                        parents.clear()
                    start = at
            elif kind == "event_msg" and inner == "task_started":
                turns.append({"kind": "turn_start", "at": at, "text": ""})
            elif kind == "event_msg" and inner == "task_complete":
                turns.append({"kind": "turn_end", "at": at, "text": str(payload.get("last_agent_message") or "")})
            elif kind == "event_msg" and inner == "token_count":
                info = payload.get("info")
                total = info.get("total_token_usage") if isinstance(info, dict) else None
                if isinstance(total, dict) and at is not None:
                    usage.append((at, [tokens._count(total.get(field)) for field in TOKEN_FIELDS]))
            elif kind == "event_msg" and inner == "item_completed":
                item = payload.get("item")
                began, ended = payload.get("started_at_ms"), payload.get("completed_at_ms")
                if all(isinstance(stamp, (int, float)) and not isinstance(stamp, bool) and stamp > 0
                       for stamp in (began, ended)) and began <= ended:
                    spans[number] = (began / 1000, ended / 1000)
                if isinstance(item, dict) and item.get("type") == "FileChange" and isinstance(
                        item.get("changes"), dict):
                    patches.append({"at": at, "line": number, "paths": [str(path) for path in item["changes"]]})
            elif kind == "response_item" and inner in ("function_call", "custom_tool_call"):
                call = {"at": at, "line": number, "end": None, "end_line": number,
                        "name": str(payload.get("name") or ""),
                        "input": str(payload.get("arguments") or payload.get("input") or "")}
                calls.append(call)
                if isinstance(payload.get("call_id"), str):
                    open_calls[payload["call_id"]] = call
            elif kind == "response_item" and inner in ("function_call_output", "custom_tool_call_output"):
                call_id = payload.get("call_id")
                call = open_calls.pop(call_id, None) if isinstance(call_id, str) else None
                if call:
                    call["end"], call["end_line"] = at, number
    version = meta.get("cli_version") if isinstance(meta, dict) else None
    return {"turns": turns, "usage": usage, "calls": calls, "patches": patches, "spans": spans,
            "start": start, "end": last_at, "cli_version": version if isinstance(version, str) else None}


def _patch_event(agent: str, paths: list[str]) -> dict:
    names = ", ".join(dict.fromkeys(path.rsplit("/", 1)[-1] for path in paths))
    return {"agent": agent, "kind": "edit", "text": f"apply_patch {names}", "exit": None, "check": None}


def _session_events(session: dict, extras: dict) -> list[dict]:
    """The events of one rollout, with `at` and `end` in epoch seconds.

    Every logged command and file change is an event of its own, timed by the start and end
    Codex recorded for it. The other tools of a call (the board, `spawn_agent`, `wait_agent`)
    are one event that lasts from the call to its output.
    """
    agent = session["agent"]
    commands = [event for event in session["events"] if event["kind"] == "command"]
    spans = extras["spans"]
    events, placed = [], set()

    def timed(event: dict, item: dict, call: dict | None) -> dict:
        if call and item["line"] == call["line"]:  # a plain tool call: it is its own record
            return {**event, "at": call["at"], "end": call["end"]}
        began, ended = spans.get(item["line"], (item["at"], None))
        return {**event, "at": began, "end": ended}

    # Each logged command and file change belongs to one call: the last one that was open when
    # it was logged (calls made in parallel overlap).
    lines = [call["line"] for call in extras["calls"]]
    owned: dict[int, list[dict]] = {}
    for item in (*commands, *extras["patches"]):
        index = bisect.bisect_right(lines, item["line"]) - 1
        while index >= 0 and item["line"] > extras["calls"][index]["end_line"]:
            index -= 1
        if index >= 0:
            owned.setdefault(index, []).append(item)
            placed.add(id(item))
    for index, call in enumerate(extras["calls"]):
        items = sorted(owned.get(index, []), key=lambda item: item["line"])
        patched = any("paths" in item for item in items)
        # Commands come from what Codex logged as run, never from the text of the call: a
        # code-mode script that fails on its first tool never reaches the commands after it.
        tools, _scripts = call_actions(call["name"], call["input"])
        events += [timed(_patch_event(agent, item["paths"]) if "paths" in item
                         else script_event(agent, item["script"], item["exit_code"]), item, call)
                   for item in items]
        events += [{**event, "at": call["at"], "end": call["end"]}
                   for event in tool_events(agent, tools, _spawned(call["name"], call["input"]), patched)]
    events += [timed(script_event(agent, command["script"], command["exit_code"]), command, None)
               for command in commands if id(command) not in placed]
    events += [timed(_patch_event(agent, patch["paths"]), patch, None)
               for patch in extras["patches"] if id(patch) not in placed]
    for said in session["events"]:
        if said["kind"] == "say":
            events.append({"agent": agent, "kind": "say", "text": said["text"], "exit": None,
                           "at": said["at"], "end": None})
    for turn in extras["turns"]:
        events.append({"agent": agent, "kind": turn["kind"], "text": turn["text"], "exit": None,
                       "at": turn["at"], "end": None})
    return events


def _thin(points: list, limit: int) -> list:
    """At most about `limit` of the points, evenly picked, always with the last one."""
    if len(points) <= limit:
        return points
    step = math.ceil(len(points) / limit)
    kept = points[::step]
    return kept if kept[-1] is points[-1] else [*kept, points[-1]]


def _series(per_session: list[list], start: float) -> list[list]:
    """An agent's running token totals as [seconds, input, cached, output], across its sessions."""
    points = sorted((at, index, usage) for index, session in enumerate(per_session) for at, usage in session)
    latest: dict[int, list[int]] = {}
    rows: list[list] = []
    for at, index, usage in points:
        latest[index] = usage
        row = [round(max(0.0, at - start), 1), *(sum(column) for column in zip(*latest.values(), strict=True))]
        if rows and rows[-1][0] == row[0]:
            rows[-1] = row
        else:
            rows.append(row)
    return _thin(rows, MAX_SERIES)


def _brief(ws: Path, meta: dict) -> dict:
    """The brief's SHA-256, from murmur.json or from the brief file if it still opens the prompts."""
    recorded = meta.get("brief_sha256")
    if isinstance(recorded, str) and re.fullmatch(r"[0-9a-f]{64}", recorded):
        return {"sha256": recorded, "source": "murmur.json"}
    agents = meta.get("agents") if isinstance(meta.get("agents"), list) else []
    first = agents[0].get("id") if agents and isinstance(agents[0], dict) else None
    try:
        brief = Path(str(meta.get("brief") or "")).read_text().strip()
        prompt = (ws / "prompts" / f"{first}.md").read_text()
    except (OSError, UnicodeDecodeError):
        return {"sha256": None, "source": "not recorded in murmur.json, and the brief file cannot be read"}
    if not brief or not prompt.startswith(brief):
        return {"sha256": None, "source": "not recorded in murmur.json, and the brief file has changed since"}
    return {"sha256": hashlib.sha256(brief.encode()).hexdigest(),
            "source": "the brief file, which still matches the prompt the agents got"}


def _main_change(ws: Path, base: str | None) -> dict:
    """Files and lines that differ between the base commit and main."""
    empty = {"files": None, "insertions": None, "deletions": None}
    if not base or not (ws / "work" / "origin.git").is_dir():
        return empty
    try:
        rows = receipts._git(ws / "work" / "origin.git", "diff", "--numstat", base, "refs/heads/main", "--")
    except receipts.ReceiptsError:
        return empty
    counts = [line.split("\t", 2) for line in rows.splitlines() if line.count("\t") >= 2]
    return {"files": len(counts),
            "insertions": sum(int(added) for added, _removed, _path in counts if added.isdigit()),
            "deletions": sum(int(removed) for _added, removed, _path in counts if removed.isdigit())}


def _git_events(receipt: dict) -> list[dict]:
    """When a commit reached each branch; its author time when the reflog does not say."""
    agent = receipt["who"]["agent"] or receipt["who"]["integrated_by"] or "unknown"
    change = receipt["change"]
    text = f"{receipt['short']} {receipt['subject']} (+{change['insertions']} -{change['deletions']})"
    base = {"agent": agent, "exit": None, "end": None, "sha": receipt["short"]}
    events = [{**base, "kind": "main" if branch == "main" else "draft", "at": receipts._epoch(at),
               "text": text if branch == "main" else f"{branch}: {text}"}
              for branch, at in receipt["when"]["pushed"].items()]
    if not events:
        where = "main" if receipt["on_main"] else ", ".join(receipt["branches"]) or "no branch"
        events.append({**base, "kind": "commit", "at": receipts._epoch(receipt["when"]["authored_at"]),
                       "text": f"{text}, on {where}; placed by its author time, the push time is not recorded"})
    return events


def _receipt_entry(receipt: dict, events: list[dict]) -> dict:
    change, verified = receipt["change"], receipt["verification"]
    landed = next((event for event in events if event["kind"] == ("main" if receipt["on_main"] else "draft")),
                  events[0])
    return {"sha": receipt["short"], "agent": receipt["who"]["agent"], "subject": receipt["subject"],
            "on_main": receipt["on_main"], "branches": receipt["branches"], "at": landed["at"],
            "placed_by": "author time" if landed["kind"] == "commit" else "push",
            "files": change["files"], "insertions": change["insertions"], "deletions": change["deletions"],
            "status": verified["status"], "status_label": receipts.STATUS_LABELS[verified["status"]],
            "summary": verified["summary"], "lines": receipts.receipt_lines(receipt)}


def event_text(redact: receipts.Redactor, text: str) -> str:
    """Log text as an event shows it: redacted, without encrypted payloads, and cut short."""
    return redact.clip(_ENCRYPTED.sub("[encrypted]", text), MAX_EVENT_TEXT)


def collect_run(ws: Path) -> dict:
    """One workspace as a run of the replay document. Raises ReceiptsError when it is not a workspace.

      id, source {kind, description, files}, example, mode, peers, model, effort, base, cap,
      brief {sha256, source}, codex_versions, clock {kind, note, start}, duration_s,
      launcher {seconds, active_seconds, stalled_seconds} or None,
      outcome {finished, exit_code, delivered, capped, interrupted, diagnostic},
      tokens {total, agents {id: usage}, source} or None,
      main {commits, files, insertions, deletions, last_change_s}, drafts, score, facts,
      agents [{id, role, calls {kind: n}, posts, changes_on_main, turns [[start, end]]}],
      events [{t, end, agent, kind, text, exit, check, sha}], token_series {id: [[t, input, cached, output]]},
      receipts [{sha, agent, subject, on_main, branches, t, placed_by, files, insertions, deletions,
                 status, status_label, summary, lines}], receipts_note, warnings

    Times are seconds on the run's clock. `events` are in time order; a tool call has an `end`
    when its output was logged, and `check` when it ran a test, lint or build (see `check_of`).
    """
    ws = Path(ws)
    document = receipts.collect(ws)
    meta = receipts.load_meta(ws)
    record = receipts._run_record(ws)
    redact = receipts.Redactor(ws)
    solo = meta.get("mode") == "solo"
    sessions, _warnings = receipts.read_sessions(ws, solo)
    posts, _warnings = receipts.read_board(ws)
    warnings = list(document["warnings"])

    events, usage, series, versions, edges = [], {}, {}, set(), []
    for session in sessions:
        try:
            extras = _session_extras(ws / session["path"])
            spent = tokens.session_usage(ws / session["path"])[1]
        except OSError:
            continue  # receipts.collect() has already warned about it
        events += _session_events(session, extras)
        into = usage.setdefault(session["agent"], dict.fromkeys(tokens.FIELDS, 0))
        for field in tokens.FIELDS:
            into[field] += spent[field]
        series.setdefault(session["agent"], []).append(extras["usage"])
        versions.update([extras["cli_version"]] if extras["cli_version"] else [])
        edges += [edge for edge in (extras["start"], extras["end"]) if edge is not None]
    events += [{"agent": post["agent"], "kind": "post", "text": f"#{post['channel']} {post['text']}",
                "exit": None, "at": post["at"], "end": None} for post in posts]
    entries = []
    for receipt in document["receipts"]:
        landed = _git_events(receipt)
        events += landed
        entries.append(_receipt_entry(receipt, landed))

    timed = [event for event in events if event["at"] is not None]
    if len(timed) < len(events):
        warnings.append(f"{len(events) - len(timed)} logged event(s) have no time and are left out")
    start = min(edges or [event["at"] for event in timed] or [0.0])
    end = max([*edges, *(event["end"] or event["at"] for event in timed), start])

    def on_clock(at: float | None) -> float | None:
        return None if at is None else round(max(0.0, at - start), 1)

    timed.sort(key=lambda event: event["at"])
    events = [{"t": on_clock(event["at"]), "end": on_clock(event["end"]), "agent": event["agent"],
               "kind": event["kind"], "text": event_text(redact, event["text"]),
               "exit": event["exit"], "check": event.get("check"), "sha": event.get("sha")} for event in timed]
    for entry in entries:
        entry["t"] = on_clock(entry.pop("at"))

    order = [agent["id"] for agent in document["agents"]]
    order += [name for name in dict.fromkeys(event["agent"] for event in events) if name not in order]
    roles = {agent["id"]: agent["role"] for agent in document["agents"]}
    duration = round(end - start, 1)
    total = {field: sum(agent[field] for agent in usage.values()) for field in tokens.FIELDS}
    recorded = record.get("tokens") if isinstance(record.get("tokens"), dict) else None
    if usage and recorded and recorded.get("total") != total:
        warnings.append("logs/run.json records other token totals than the session logs now add up to; "
                        "the session logs are shown")
    stalled = record.get("stalled_seconds")
    if isinstance(stalled, (int, float)) and stalled > 0:
        warnings.append(f"the launcher counted {stalled:g} s as stalled; the timeline includes that time, "
                        "and the logs do not say where in the run it fell")
    if not record:
        warnings.append("no logs/run.json: the run is still going or did not end cleanly, so its numbers "
                        "are those of the logs so far")
    main_events = [event["t"] for event in events if event["kind"] == "main"]
    run = document["run"]
    rollouts = len(sessions)
    return {
        "id": str(run["id"]),
        "source": {
            "kind": "workspace",
            "description": "a murmur workspace: Codex session logs, the message board, origin.git and logs/run.json",
            "files": ["murmur.json", *(["logs/run.json"] if record else []),
                      f"codex-home/sessions ({rollouts} rollout{'' if rollouts == 1 else 's'})",
                      *([f"codex-home/{receipts.BOARD_DB}"] if posts else []), "work/origin.git"],
        },
        # Codex stamps its version on every session; logs without one were not written by it.
        "example": None if versions or not sessions else
        "the session logs carry no Codex CLI version: they look like test or example data, not a real run",
        "mode": run["mode"], "peers": run["peers"], "model": run["model"], "effort": run["effort"],
        "base": run["base"], "cap": meta.get("cap") if isinstance(meta.get("cap"), str) else None,
        "brief": _brief(ws, meta),
        "codex_versions": sorted(versions),
        "clock": {**WALL_CLOCK, "start": receipts._iso(start) if edges else None},
        "duration_s": duration,
        "launcher": {key: record.get(key) for key in ("seconds", "active_seconds", "stalled_seconds")}
        if record else None,
        "outcome": {"finished": bool(record), "exit_code": record.get("exit_code"),
                    "delivered": record.get("delivered"), "capped": record.get("capped"),
                    "interrupted": record.get("interrupted"), "diagnostic": run["diagnostic"]},
        "tokens": {"total": total, "agents": {name: usage[name] for name in order if name in usage},
                   "source": "the last running total in each Codex session log, summed"} if usage else None,
        "main": {"commits": run["commits_on_main"], **_main_change(ws, run["base"]),
                 "last_change_s": max(main_events) if main_events else None},
        "drafts": sorted({branch for entry in entries for branch in entry["branches"] if branch != "main"}),
        "score": None,
        "facts": [],
        "agents": agent_rows(order, roles, events, entries, duration),
        "events": events,
        "token_series": {name: _series(series[name], start) for name in order if name in series},
        "receipts": entries,
        "receipts_note": None if entries else "the run made no commits",
        "warnings": warnings,
    }


def agent_rows(order: list[str], roles: dict, events: list[dict], entries: list[dict],
               duration: float) -> list[dict]:
    """Per agent, in `order`: its tool calls by kind, posts, commits on main and turns, from the events."""
    agents = []
    for name in order:
        own = [event for event in events if event["agent"] == name]
        calls = {kind: sum(1 for event in own if event["kind"] == kind) for kind in TOOL_KINDS}
        turns, opened = [], None
        for event in own:
            if event["kind"] == "turn_start" and opened is None:
                opened = event["t"]
            elif event["kind"] == "turn_end" and opened is not None:
                turns.append([opened, event["t"]])
                opened = None
        if opened is not None:
            turns.append([opened, duration])  # a turn the run was stopped in
        agents.append({
            "id": name, "role": roles.get(name, "peer"),
            "calls": {kind: count for kind, count in calls.items() if count},
            "posts": sum(1 for event in own if event["kind"] == "post"),
            "changes_on_main": sum(1 for entry in entries if entry["agent"] == name and entry["on_main"]),
            "turns": turns,
        })
    return agents


# --- documents -------------------------------------------------------------------------

_RUN_KEYS = ("id", "source", "mode", "clock", "duration_s", "outcome", "main", "agents", "events")
# What a run from another source than a workspace (see scripts/timeline_to_replay.py) may leave out.
RUN_DEFAULTS = {
    "example": None, "task": None, "peers": None, "model": None, "effort": None, "base": None, "cap": None,
    "brief": {"sha256": None, "source": "not recorded"}, "codex_versions": [], "launcher": None, "tokens": None,
    "drafts": [], "score": None, "facts": [], "token_series": {}, "receipts": [], "receipts_note": None,
    "warnings": [],
}
_EVENT_DEFAULTS = {"end": None, "exit": None, "check": None, "sha": None}
_AGENT_DEFAULTS = {"role": "peer", "calls": {}, "posts": 0, "changes_on_main": 0, "turns": []}


def complete(run: dict) -> dict:
    """A run with every field the views read, or ReplayError when it lacks what cannot be defaulted."""
    def number(value) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool)

    try:
        if not all(key in run for key in _RUN_KEYS) or not number(run["duration_s"]):
            raise KeyError
        events = [{**_EVENT_DEFAULTS, **event} for event in run["events"]]
        agents = [{**_AGENT_DEFAULTS, **agent} for agent in run["agents"]]
        sound = (all(number(event["t"]) and all(isinstance(event[key], str) for key in ("agent", "kind", "text"))
                     for event in events)
                 and all(isinstance(agent["id"], str) for agent in agents)
                 and all(key in run["outcome"] for key in ("finished", "exit_code", "delivered", "capped"))
                 and all(key in run["clock"] for key in ("kind", "label", "note"))
                 and "commits" in run["main"] and "description" in run["source"] and "files" in run["source"])
    except (KeyError, TypeError):
        sound = False
    if not sound:
        raise ReplayError("holds no complete run")
    return {**RUN_DEFAULTS, **run, "id": str(run["id"]), "events": events, "agents": agents}


def load(path: Path) -> list[dict]:
    """The runs at `path`: a workspace, or a replay document saved with `murmur replay --json`."""
    path = Path(path)
    if path.is_dir():
        try:
            return [collect_run(path)]
        except receipts.ReceiptsError as error:
            raise ReplayError(str(error)) from None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ReplayError(f"cannot read {path}: {error.strerror or error}") from None
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ReplayError(f"{path} is neither a workspace nor a replay saved with --json") from None
    if not isinstance(document, dict) or document.get("kind") != KIND:
        raise ReplayError(f"{path} is neither a workspace nor a replay saved with --json")
    if document.get("schema") != SCHEMA:
        raise ReplayError(f"{path} is a replay of schema {document.get('schema')!r}; this murmur reads {SCHEMA}")
    runs = document.get("runs")
    if not isinstance(runs, list) or not runs:
        raise ReplayError(f"{path} holds no complete run")
    try:
        return [complete(run) for run in runs]
    except ReplayError as error:
        raise ReplayError(f"{path} {error}") from None


def read_scores(path: Path) -> dict[str, dict]:
    """Scores by run id from a JSON file: `{"<id>": 7.8}` or `{"<id>": {"score": 7.8, "source": "..."}}`."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise ReplayError(f"cannot read {path}: {error.strerror or error}") from None
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise ReplayError(f"{path} is not JSON: {error}") from None
    if not isinstance(data, dict):
        raise ReplayError(f"{path} must be a JSON object of scores by run id")
    scores = {}
    for run_id, entry in data.items():
        value = entry.get("score") if isinstance(entry, dict) else entry
        source = entry.get("source") if isinstance(entry, dict) else None
        scores[run_id] = score(value, f"{source} ({Path(path).name})" if isinstance(source, str) and source
                               else f"supplied in {Path(path).name}", f"the score of {run_id!r} in {path}")
    return scores


def score(value, source: str, what: str = "a score") -> dict:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ReplayError(f"{what} must be a number")
    return {"value": value, "source": source}


def clock(seconds: float | None) -> str:
    """Seconds as m:ss, or h:mm:ss from an hour on."""
    if seconds is None:
        return "?"
    whole = int(seconds)
    hours, rest = divmod(whole, 3600)
    return f"{hours}:{rest // 60:02d}:{rest % 60:02d}" if hours else f"{rest // 60}:{rest % 60:02d}"


def _shape(run: dict) -> str:
    return "solo" if run["mode"] == "solo" else f"{run['mode']}, {run['peers']} peers"


def _delivered(run: dict) -> bool:
    outcome = run["outcome"]
    return bool(outcome["finished"]) and outcome["exit_code"] == 0 and outcome["delivered"] is not False


def _exit(run: dict) -> str:
    outcome = run["outcome"]
    if not outcome["finished"]:
        return "not finished"
    delivered = {True: "delivered", False: "nothing delivered"}.get(outcome["delivered"], "delivery unknown")
    return f"{outcome['exit_code']}, {delivered}" + (", capped" if outcome["capped"] else "")


def _number(value) -> str:
    return "not recorded" if value is None else f"{value:,}"


def _token(run: dict, field: str) -> int | None:
    return run["tokens"]["total"].get(field) if run.get("tokens") else None


def _uncached(run: dict) -> int | None:
    recorded = _token(run, "uncached_input_tokens")
    if recorded is not None:
        return recorded
    total, cached = _token(run, "input_tokens"), _token(run, "cached_input_tokens")
    return None if total is None or cached is None else total - cached


def _lines(main: dict) -> str:
    if main.get("files") is None:
        return f"+{main['insertions']:,}" if main.get("insertions") is not None else "not recorded"
    return f"{main['files']} file{'' if main['files'] == 1 else 's'}, +{main['insertions']} -{main['deletions']}"


def _launcher(run: dict) -> str:
    clocks = run.get("launcher")
    if not clocks or clocks.get("seconds") is None:
        return "not recorded"
    return (f"{clocks['seconds']:g} s = {_or_unknown(clocks.get('active_seconds'))} active + "
            f"{_or_unknown(clocks.get('stalled_seconds'))} stalled")


def _or_unknown(value) -> str:
    return "?" if value is None else f"{value:g}"


def _compatibility(first: dict, second: dict) -> list[str]:
    """Why two runs are not the same task under the same conditions, as far as the runs record."""
    found = []
    one, two = first["brief"]["sha256"], second["brief"]["sha256"]
    if one and two and one != two:
        found.append(f"the briefs differ (sha256 {one[:12]} and {two[:12]}): the runs did not get the same task")
    elif not (one and two):
        missing = " and ".join(run["label"] for run in (first, second) if not run["brief"]["sha256"])
        tasks = [run.get("task") for run in (first, second)]
        named = (f"; both are labelled task {tasks[0]} in their source" if tasks[0] and tasks[0] == tasks[1]
                 else "")
        found.append(f"the brief of {missing} has no recorded hash, so it is not confirmed that both runs "
                     f"got the same task{named}")
    if first.get("task") and second.get("task") and first["task"] != second["task"]:
        found.append(f"the runs are labelled as different tasks: A {first['task']}, B {second['task']}")
    for key, name in (("model", "model"), ("effort", "reasoning effort"), ("base", "base commit"),
                      ("cap", "time cap")):
        values = [run.get(key) for run in (first, second)]
        if None in values:
            missing = " and ".join(run["label"] for run in (first, second) if run.get(key) is None)
            found.append(f"the {name} of {missing} is not recorded")
        elif values[0] != values[1]:
            shown = [str(value)[:10] if key == "base" else str(value) for value in values]
            found.append(f"the {name} differs: A {shown[0]}, B {shown[1]}")
    if first["clock"]["kind"] != second["clock"]["kind"]:
        found.append("the runs are on different clocks, so their times do not compare")
    versions = [run.get("codex_versions") or [] for run in (first, second)]
    if all(versions) and versions[0] != versions[1]:
        found.append(f"the Codex CLI version differs: A {', '.join(versions[0])}, B {', '.join(versions[1])}")
    return found


def _lower(runs: list[dict], values: list, did: str, more: str, shown) -> tuple[str, str, int | None]:
    """Which run has the lower value: (a short note, what that run did, its index)."""
    if None in values:
        return "", "", None
    if values[0] == values[1]:
        return "equal", "", None
    winner = 0 if values[0] < values[1] else 1
    low, high = values[winner], values[1 - winner]
    if low > 0:
        note = f"{runs[1 - winner]['label']} " + more.format(f"{high / low:.2f}x" if high / low < 1.1
                                                             else f"{high / low:.1f}x")
    else:
        note = f"{runs[winner]['label']} had none"
    return note, f"{did} ({shown(low)} against {shown(high)})", winner


def build(runs: list[dict], scores: dict[str, dict] | None = None) -> dict:
    """The replay document for one run, or for two side by side.

      schema, kind, generated_at, title, example, clock_note, runs,
      compatibility   for two runs: what makes them unequal (another brief, model, effort, base...)
      comparison      rows of {label, values [one per run], note}
      ahead           for two runs: {"A": [...], "B": [...], "not_compared": [...]}
      notes           scores nobody asked for, and the like

    `scores` maps run ids to `score()` values. A run without one says so; nothing is derived.
    """
    if len(runs) not in (1, 2):
        raise ReplayError(f"a replay shows one run, or two side by side (got {len(runs)})")
    runs = [{**complete(run), "label": label} for run, label in zip(runs, "AB", strict=False)]
    notes = []
    for run in runs:
        if scores and run["id"] in scores:
            run["score"] = scores[run["id"]]
    if scores and (unused := sorted(set(scores) - {run["id"] for run in runs})):
        notes.append(f"scores were supplied for {', '.join(unused)}, which is not a run shown here")
    kinds = {run["clock"]["kind"] for run in runs}

    def row(key: str, label: str, shown, note: str = "") -> dict:
        return {"key": key, "label": label, "values": [shown(run) for run in runs], "note": note}

    pair = len(runs) == 2
    ahead: dict[str, list[str]] = {"A": [], "B": [], "not_compared": []}
    notes_by_row = {}
    if pair:
        fair = all(_delivered(run) for run in runs)
        measures = (
            ("time", [run["duration_s"] for run in runs], "finished sooner", "took {} as long", clock),
            ("input", [_token(run, "input_tokens") for run in runs], "used fewer input tokens",
             "used {} as many", _number),
            ("output", [_token(run, "output_tokens") for run in runs], "used fewer output tokens",
             "used {} as many", _number),
        )
        for key, values, did, more, shown in measures:
            notes_by_row[key], won, winner = _lower(runs, values, did, more, shown)
            if winner is not None and fair and (key != "time" or len(kinds) == 1):
                ahead[runs[winner]["label"]].append(won)
        if not fair:
            failed = [run for run in runs if not _delivered(run)]
            ahead["not_compared"].append(
                "time and tokens: " + " and ".join(f"{run['label']} ({_exit(run)})" for run in failed)
                + " did not finish with a delivered result, so being sooner or cheaper says nothing")
            for run in runs:
                if _delivered(run) and len(failed) == 1:
                    ahead[run["label"]].append("delivered a result; the other run did not")
        # A score is somebody else's judgement: it is shown, and never counted as a win here.
        supplied = [run["score"]["value"] if run["score"] else None for run in runs]
        if None in supplied:
            ahead["not_compared"].append(f"quality: {NO_SCORE}"
                                         + (" for both runs" if supplied == [None, None] else " for one run"))
        else:
            if supplied[0] != supplied[1]:
                higher = runs[0 if supplied[0] > supplied[1] else 1]["label"]
                notes_by_row["score"] = f"{higher} is higher by {abs(supplied[0] - supplied[1]):.3g}"
            else:
                notes_by_row["score"] = "equal"
            ahead["not_compared"].append(
                f"quality: the scores supplied are {supplied[0]:g} for A and {supplied[1]:g} for B; murmur did "
                "not assess quality and cannot tell whether a difference between two scores means anything")
        notes.append("This compares one run with one run. Runs of the same task vary, so it shows what happened "
                     "here, not what usually happens.")

    clocks = " / ".join(dict.fromkeys(run["clock"]["label"] for run in runs))
    comparison = [
        row("run", "run", lambda run: f"{run['label']} {run['id']}"),
        row("mode", "mode", _shape),
        row("model", "model / effort", lambda run: f"{run['model']} / {run['effort']}"
            if run["model"] and run["effort"] else "not recorded"),
        row("time", f"finished after ({clocks})", lambda run: clock(run["duration_s"]), notes_by_row.get("time", "")),
        row("last_main", "last change on main", lambda run: clock(run["main"]["last_change_s"])
            if run["main"].get("last_change_s") is not None
            else "none" if run["main"]["commits"] == 0 else "not recorded"),
        row("launcher", "launcher clock", _launcher),
        row("input", "input tokens", lambda run: _number(_token(run, "input_tokens")), notes_by_row.get("input", "")),
        row("cached", "  of them cached", lambda run: _number(_token(run, "cached_input_tokens"))),
        row("uncached", "  not cached", lambda run: _number(_uncached(run))),
        row("output", "output tokens", lambda run: _number(_token(run, "output_tokens")),
            notes_by_row.get("output", "")),
        row("commits", "commits on main", lambda run: _number(run["main"]["commits"])),
        row("lines", "lines on main", lambda run: _lines(run["main"])),
        row("drafts", "draft branches left", lambda run: ", ".join(run["drafts"]) if run["drafts"] else "none"),
        row("exit", "exit", _exit),
        row("score", "quality score", lambda run: f"{run['score']['value']:g}" if run["score"] else NO_SCORE,
            notes_by_row.get("score", "")),
    ]
    if all(run["launcher"] is None for run in runs):
        comparison = [item for item in comparison if item["key"] != "launcher"]
    return {
        "schema": SCHEMA,
        "kind": KIND,
        "generated_at": receipts._iso(datetime.now(timezone.utc).timestamp()),
        "title": " vs ".join(run["id"] for run in runs),
        "example": next((run["example"] for run in runs if run.get("example")), None),
        "clock_note": " / ".join(dict.fromkeys(run["clock"]["note"] for run in runs)),
        "runs": runs,
        "compatibility": _compatibility(*runs) if pair else [],
        "comparison": comparison,
        "ahead": ahead if pair else None,
        "notes": notes,
    }


def to_json(document: dict) -> str:
    return json.dumps(document, indent=1, ensure_ascii=False) + "\n"


# --- text ------------------------------------------------------------------------------

_LANE_MARKS = {"main": "M", "draft": "D", "commit": "C", "turn_end": "]", "turn_start": "[", "post": "p",
               "test": "t", "edit": "e", "git": "g", "coord": "c", "run": "x", "read": "r"}
_LANE_ORDER = {mark: rank for rank, mark in enumerate(_LANE_MARKS.values())}
LEGEND = ("r read  e edit  t test/lint/build  g git  c board and agents  x other command  . in a turn, between "
          "tool calls\n  p board post  D pushed to a draft branch  M landed on main  C commit (push time "
          "unknown)  [ ] turn start and end")


def _lane(run: dict, agent: dict, scale: float, width: int) -> str:
    cells = [" "] * width

    def column(seconds: float) -> int:
        return min(width - 1, int(seconds / scale))

    def put(index: int, mark: str) -> None:
        if cells[index] in " ." or _LANE_ORDER[mark] < _LANE_ORDER[cells[index]]:
            cells[index] = mark

    for start, end in agent["turns"]:
        for index in range(column(start), column(end) + 1):
            cells[index] = "."
    for event in run["events"]:
        mark = _LANE_MARKS.get(event["kind"])
        if event["agent"] != agent["id"] or not mark:
            continue
        last = event["end"] if event["end"] is not None and event["kind"] in TOOL_KINDS else event["t"]
        for index in range(column(event["t"]), column(last) + 1):
            put(index, mark)
    return "".join(cells).rstrip()


def _short(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[:limit].rstrip()}..."


def _usage(usage: dict) -> str:
    cached = usage.get("cached_input_tokens")
    return (f"{_number(usage.get('input_tokens'))} input"
            + (f" ({cached:,} cached)" if cached is not None else "")
            + f", {_number(usage.get('output_tokens'))} output")


def exit_note(event: dict) -> str:
    """What to say about a command's exit status: a check's verdict, or a status that is not 0."""
    if event["exit"] is None:
        return ""
    if event["check"] == "unclear":
        return f" (exit {event['exit']}, not the check's own)"
    if event["check"]:
        return f" (check {'passed' if event['check'] == 'passed' else 'FAILED'}, exit {event['exit']})"
    return f" (exit {event['exit']})" if event["exit"] else ""


def event_line(run: dict, event: dict, width: int, limit: int = 96) -> str:
    kind = KIND_NAMES.get(event["kind"], event["kind"])
    text = _short(event["text"], limit) + exit_note(event)
    return f"{clock(event['t']):>8}  {run['label']} {event['agent']:<{width}} {kind:<10} {text}".rstrip()


def _table(rows: list[dict]) -> list[str]:
    columns = len(rows[0]["values"])
    label = max(len(row["label"]) for row in rows)
    widths = [max(len(row["values"][index]) for row in rows) for index in range(columns)]
    lines = []
    for row in rows:
        cells = "  ".join(f"{value:<{width}}" for value, width in zip(row["values"], widths, strict=True))
        lines.append(f"  {row['label']:<{label}}  {cells}{'  ' + row['note'] if row['note'] else ''}".rstrip())
    return lines


def _wrapped(first: str, text: str, indent: str = "    ") -> list[str]:
    return textwrap.wrap(text, width=TEXT_WIDTH, initial_indent=first, subsequent_indent=indent,
                         break_long_words=False, break_on_hyphens=False) or [first.rstrip()]


def summary_lines(document: dict) -> list[str]:
    """The head of the text view: what is shown, on which clock, the facts and who is ahead where."""
    runs = document["runs"]
    lines = [f"murmur replay: {document['title']}"]
    if document["example"]:
        lines += _wrapped("EXAMPLE DATA: ", document["example"])
    for run in runs:
        lines += _wrapped(f"{run['label']} {run['id']}: ", run["source"]["description"])
    lines += _wrapped("clock: ", document["clock_note"])
    if len(runs) == 2:
        lines.append("")
        if document["compatibility"]:
            lines.append("NOT A LIKE-FOR-LIKE PAIR:")
            for warning in document["compatibility"]:
                lines += _wrapped("  - ", warning)
        else:
            first = runs[0]
            lines.append(f"same task and settings: brief sha256 {first['brief']['sha256'][:12]}, "
                         f"{first['model']}/{first['effort']}, base {str(first['base'])[:7]}, cap {first['cap']}")
    lines += ["", *_table(document["comparison"])]
    for run in runs:
        if run["score"]:
            lines += _wrapped(f"  score of {run['label']}: ", f"{run['score']['value']:g}, {run['score']['source']}; "
                              "murmur did not assess quality")
    if any(run["facts"] for run in runs):
        lines += ["", "other figures in the source files:"]
        for run in runs:
            for fact in run["facts"]:
                lines += _wrapped(f"  {run['label']} {fact['label']}: ", f"{fact['value']} [{fact['source']}]")
    if document["ahead"]:
        lines += ["", "where each run comes out ahead (only on what is measured above):"]
        for run in runs:
            lines += _wrapped(f"  {run['label']} {run['id']}: ",
                              "; ".join(document["ahead"][run["label"]]) or "nothing")
        for reason in document["ahead"]["not_compared"]:
            lines += _wrapped("  not compared: ", reason)
    return lines


def render_text(document: dict, every: bool = False) -> str:
    """The replay as plain text: summary, lanes, agents, events and receipts."""
    runs = document["runs"]
    lines = summary_lines(document)
    longest = max(run["duration_s"] for run in runs) or 1.0
    scale = longest / LANE_WIDTH
    name = max(len(agent["id"]) for run in runs for agent in run["agents"]) if any(
        run["agents"] for run in runs) else 4
    lines += ["", f"lanes (one column is {scale:.1f} s on the clock above)", f"  {LEGEND}"]
    for run in runs:
        lines.append(f"{run['label']} {run['id']} ({_shape(run)}), finished after {clock(run['duration_s'])}: "
                     f"exit {_exit(run)}")
        lines += [f"  {agent['id']:<{name}} |{_lane(run, agent, scale, LANE_WIDTH)}" for agent in run["agents"]]
    lines.append(f"  {'':<{name}} 0:00{clock(longest):>{LANE_WIDTH - 3}}")

    lines += ["", "agents"]
    for run in runs:
        spent = run["tokens"]["agents"] if run.get("tokens") else {}
        for agent in run["agents"]:
            calls = sum(agent["calls"].values())
            parts = [f"{calls} tool call{'' if calls == 1 else 's'}"
                     + (f" ({', '.join(f'{count} {kind}' for kind, count in agent['calls'].items())})"
                        if calls else "")]
            if agent["posts"]:
                parts.append(f"{agent['posts']} post{'' if agent['posts'] == 1 else 's'}")
            if agent["changes_on_main"]:
                parts.append(f"{agent['changes_on_main']} commit{'' if agent['changes_on_main'] == 1 else 's'} "
                             "on main")
            if agent["id"] in spent:
                parts.append(_usage(spent[agent["id"]]))
            lines += _wrapped(f"  {run['label']} {agent['id']:<{name}}  ", "; ".join(parts), " " * (name + 6))
        if not run.get("tokens"):
            lines.append(f"  {run['label']} tokens: no Codex session logs found")
        elif not spent:
            lines.append(f"  {run['label']} tokens per agent: not in the source")

    merged = sorted(((event["t"], index, run, event) for index, run in enumerate(runs) for event in run["events"]
                     if every or event["kind"] in KEY_KINDS), key=lambda item: item[:2])
    shown = merged if every else merged[:KEY_EVENT_LIMIT]
    lines += ["", "events" if every else "key events (turns, posts, commits, checks; --all lists every tool call)"]
    lines += [event_line(run, event, name) for _t, _index, run, event in shown]
    if len(shown) < len(merged):
        lines.append(f"  ... {len(merged) - len(shown)} more: --all prints them, and --html has them all")

    lines += ["", "change receipts (`murmur receipts WORKSPACE` prints each in full)"]
    for run in runs:
        if not run["receipts"]:
            lines.append(f"  {run['label']} {run['id']}: {run['receipts_note'] or 'none'}")
        for entry in run["receipts"]:
            where = "main" if entry["on_main"] else ", ".join(entry["branches"]) or "no branch"
            lines.append(f"{clock(entry['t']):>8}  {run['label']} {entry['sha']}  {entry['agent'] or 'unknown'}  "
                         f"{_short(entry['subject'], 60)}  [{where}, {entry['files']} file(s) "
                         f"+{entry['insertions']} -{entry['deletions']}]")
            lines.append(f"{'':>10}verified: {entry['status_label']}: {_short(entry['summary'], 110)}")
    notes = [*document["notes"], *(f"{run['label']} {run['id']}: {warning}" for run in runs
                                   for warning in run["warnings"])]
    if notes:
        lines.append("")
        for note in notes:
            lines += _wrapped("note: ", note, "  ")
    return "\n".join(lines) + "\n"


def _spent_at(run: dict, seconds: float) -> int | None:
    """Input tokens the run had used by `seconds`, or None when the source has no counts over time."""
    if not run.get("token_series"):
        return None
    total = 0
    for points in run["token_series"].values():
        reached = [point for point in points if point[0] <= seconds]
        total += reached[-1][1] if reached else 0
    return total


def play(document: dict, out, speed: float = DEFAULT_SPEED, animate: bool = False, sleep=time.sleep) -> None:
    """Print every event in clock order, both runs on one clock, then the summary.

    With `animate`, a second of waiting is `speed` seconds of the run, all the way through:
    quiet stretches are not shortened. Without it (no terminal) the same lines come at once.
    """
    runs = document["runs"]
    name = max((len(agent["id"]) for run in runs for agent in run["agents"]), default=4)
    steps = [(event["t"], index, run, event) for index, run in enumerate(runs) for event in run["events"]]
    steps += [(run["duration_s"], index, run, None) for index, run in enumerate(runs)]
    steps.sort(key=lambda item: (item[0], item[1], item[3] is None))
    how = (f"at {speed:g}x: one second here is {speed:g} s of the run, quiet stretches included" if animate
           else "without delays, because this is not a terminal")
    out.write(f"murmur replay: {document['title']}, played {how}\n")
    if document["example"]:
        out.write(f"EXAMPLE DATA: {document['example']}\n")
    out.write("\n".join(_wrapped("clock: ", document["clock_note"])) + "\n\n")
    now = 0.0
    for at, _index, run, event in steps:
        if animate and at > now:
            sleep((at - now) / speed)
        now = max(now, at)
        if event is None:
            line = (f"{clock(at):>8}  {run['label']} FINISH {run['id']}: exit {_exit(run)}"
                    + (f"; {_usage(run['tokens']['total'])}" if run.get("tokens") else ""))
        else:
            spent = _spent_at(run, at)
            line = event_line(run, event, name, 80) + (f"  [{spent:,} in]" if spent is not None else "")
        out.write(line + "\n")
        out.flush()
    out.write("\n" + "\n".join(summary_lines(document)) + "\n")


# --- html ------------------------------------------------------------------------------

_DATA_MARK = "/*MURMUR_REPLAY_DATA*/null"
# Inside a <script> element only `</` and `<!--` end or confuse the block; escaping these
# three characters and the two line separators JSON allows raw rules both out.
_JSON_ESCAPES = {"<": "\\u003c", ">": "\\u003e", "&": "\\u0026", "\u2028": "\\u2028", "\u2029": "\\u2029"}


def render_html(document: dict) -> str:
    """The replay as one HTML file: styles, script and data inline, nothing fetched.

    The data is embedded as JSON and the page builds itself from it with `textContent`, so
    log text never becomes markup.
    """
    template = files("murmur").joinpath("replay.html").read_text(encoding="utf-8")
    data = json.dumps(document, ensure_ascii=False, separators=(",", ":"))
    data = re.sub("[<>&\u2028\u2029]", lambda match: _JSON_ESCAPES[match[0]], data)
    if template.count(_DATA_MARK) != 1:
        raise ReplayError("the replay page template is damaged")
    return template.replace(_DATA_MARK, data)
