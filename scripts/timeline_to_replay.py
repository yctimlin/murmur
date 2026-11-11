#!/usr/bin/env python3
"""Turn published round-4 forensics timelines into a replay that `murmur replay` can show.

  scripts/timeline_to_replay.py TIMELINE.md [TIMELINE_B.md] [--results E1.json]
                                [--clock active|wall] [--html FILE] [--json FILE] [--all]

The timelines are on the `experiment/self-improve-r4` branch, one per run, in
`research-r4/analysis/forensics/timelines/`. Each has a header (the run's `result.json`, the
judges' scores, the git refs at the end, the run's span) and an event stream, one line per event:

  A <active min> | <wall time> | <agent> | <kind> | <content>

`--results` adds what `research-r4/results/E1.json` records for the same run (task, output and
uncached tokens, the other active-time estimates). To get the files:

  git archive origin/experiment/self-improve-r4 research-r4/analysis/forensics/timelines \\
      research-r4/results/E1.json | tar -x -C /tmp/r4

Only what those files say is shown, each number with the file it came from. What they do not
record (the model, the brief, per-agent tokens, which commits are on main, exit statuses of
most commands, change receipts) is reported as not recorded. A timeline has two clocks; the
replay uses one and says which: `active` is the timeline's own estimate in active minutes,
`wall` is its wall-clock time of day, which includes the time the host was frozen.

Without --html or --json the text view is printed. `murmur replay FILE` reads a --json file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    from murmur import receipts, replay
except ImportError:  # run from a checkout without installing
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
    from murmur import receipts, replay

EVENT = re.compile(r"^A\s*(\d+(?:\.\d+)?) \| (\d\d):(\d\d):(\d\d) \| (\S+)\s* \| (\S+)\s* \| ?(.*)$")
SPAN = re.compile(r"^- run span: active ([\d.]+) min, wall ([\d.]+) min")
REF = re.compile(r"^(\S+) ([0-9a-f]{7,40})$")
CUT = re.compile(r" …\[\+\d+\]$")  # how the timeline marks text it shortened
EXIT = re.compile(r"Process exited with code (\d+)|\"exit_code\"\s*:\s*(\d+)")
DROPPED = {"THINK": "reasoning summaries", "MAIL": "deliveries of messages to an agent"}
CLOCKS = {
    "active": {
        "kind": "active",
        "label": "active minutes, the timeline's estimate",
        "note": "the timeline's own clock: active minutes since the run's first event, in steps of 0.1 min. It "
                "is an estimate made by the research tooling (tools/forensics_extract.py on the same branch: "
                "host freezes left out, and no gap between two events counted as more than 120 s), not a "
                "measured duration. The other time figures the files give are listed with the facts.",
    },
    "wall": {
        "kind": "wall",
        "label": "wall clock",
        "note": "wall-clock time since the run's first event, from the timeline's time-of-day column (whole "
                "seconds, Asia/Taipei). It includes the time the host machine was frozen. The other time "
                "figures the files give are listed with the facts.",
    },
}


class TimelineError(Exception):
    pass


def _cited(path: Path) -> str:
    """The path from `research-r4` on, which is how the branch names the file."""
    parts = path.resolve().parts
    return "/".join(parts[parts.index("research-r4"):]) if "research-r4" in parts else path.name


def parse(path: Path) -> dict:
    """A timeline file as {"id", "result", "score", "judges", "refs", "span", "rows"}."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as error:
        raise TimelineError(f"cannot read {path}: {error}") from None
    found = {"id": None, "result": None, "score": None, "judges": [], "refs": {}, "span": None, "rows": []}
    in_refs = False
    for number, line in enumerate(lines, start=1):
        if match := EVENT.match(line):
            active, hours, minutes, seconds, who, kind, content = match.groups()
            found["rows"].append({"line": number, "active": float(active), "who": who, "kind": kind,
                                  "wall": int(hours) * 3600 + int(minutes) * 60 + int(seconds), "text": content})
        elif line.startswith("# Timeline ") and found["id"] is None:
            found["id"] = line.removeprefix("# Timeline ").strip()
        elif line.startswith("result.json: "):
            found["result"] = _json(line.removeprefix("result.json: "))
        elif line.startswith("score overall "):
            found["score"] = _float(line.removeprefix("score overall "))
        elif line.startswith("- judge: "):
            found["judges"].append(_json(line.removeprefix("- judge: ")) or {})
        elif line.startswith("```"):
            in_refs = not in_refs and bool(lines[number - 2].startswith("git refs at end"))
        elif in_refs and (match := REF.match(line.strip())):
            found["refs"][match[1]] = match[2]
        elif match := SPAN.match(line):
            found["span"] = {"active_min": float(match[1]), "wall_min": float(match[2])}
    if not found["id"] or not found["rows"] or not isinstance(found["result"], dict):
        raise TimelineError(f"{path} is not a forensics timeline (no title, result.json line or event stream)")
    return found


def _json(text: str):
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


def _float(text: str) -> float | None:
    try:
        return float(text)
    except ValueError:
        return None


def _wall_seconds(rows: list[dict]) -> list[int]:
    """Seconds since the first row. The column is a time of day, so a step back is midnight."""
    days, previous, out = 0, rows[0]["wall"], []
    for row in rows:
        if row["wall"] < previous - 12 * 3600:
            days += 1
        previous = row["wall"]
        out.append(days * 86400 + row["wall"] - rows[0]["wall"])
    return out


def to_run(path: Path, results: Path | None = None, clock: str = "active") -> dict:
    """One timeline file as a run of a replay document."""
    timeline = parse(path)
    rows, result, run_id = timeline["rows"], timeline["result"], timeline["id"]
    cited = _cited(path)
    row = None
    if results:
        try:
            listed = json.loads(results.read_text(encoding="utf-8")).get("rows")
        except (OSError, ValueError, AttributeError) as error:
            raise TimelineError(f"cannot read {results}: {error}") from None
        row = next((item for item in listed or [] if isinstance(item, dict) and item.get("run") == run_id), None)
        if row is None:
            raise TimelineError(f"{results} has no row for {run_id}")
    cited_results = _cited(results) if results else None
    wall = _wall_seconds(rows)
    times = [round(row_["active"] * 60, 1) for row_ in rows] if clock == "active" else wall
    redact = receipts.Redactor(path.resolve().parent)

    callers = sorted({item["who"] for item in rows if item["kind"] in ("CALL", "FCALL", "TURN_START", "TURN_END")})
    first_turn = next((index for index, item in enumerate(rows) if item["kind"] == "TURN_START"), 0)
    events, dropped, pending, base = [], {}, {}, None
    for index, (item, at) in enumerate(zip(rows, times, strict=True)):
        who, kind, text = item["who"], item["kind"], item["text"]
        if kind in DROPPED:
            dropped[kind] = dropped.get(kind, 0) + 1
        elif kind == "OUT":
            code = EXIT.search(text)
            for event in pending.pop(who, []):
                event["end"] = at
                if code and event.get("_only"):
                    event["exit"] = int(code[1] or code[2])
                    event["check"] = replay.check_of(event["script"], event["exit"])
        elif kind in ("CALL", "FCALL"):
            name, _, arguments = text.partition(" ") if kind == "FCALL" else ("exec", "", text)
            made = [{**event, "t": at, "end": None, "sha": None}
                    for event in replay.call_events(who, name, CUT.sub("", arguments))]
            if made and CUT.search(arguments):
                made[-1]["text"] += " [cut short in the timeline]"
            scripts = [event for event in made if "script" in event]
            for event in made:
                event["_only"] = len(scripts) == 1 and event is scripts[0]
            pending[who] = made
            events += made
        elif kind == "COMMIT":
            sha = text.split(" ", 1)[0]
            if index < first_turn and who not in callers:
                base = {"sha": sha, "text": text, "who": who}  # what the run started from, not its work
                continue
            author = who
            if who not in callers:
                # Git names the commit's author; the agent is the one whose command printed its SHA.
                printed = re.compile(rf"\[[^\]]*\b{re.escape(sha)}\]")
                author = next((other["who"] for other in rows if other["kind"] == "OUT"
                               and printed.search(other["text"])), who)
                text += f" (git author {who})"
            events.append({"t": at, "end": None, "agent": author, "kind": "commit", "text": text, "exit": None,
                           "check": None, "sha": sha})
        else:
            mapped = {"TURN_START": "turn_start", "TURN_END": "turn_end", "SAY": "say", "ERROR": "error"}.get(kind)
            if kind == "TURN_START" and index and (rows[index - 1]["who"], rows[index - 1]["kind"]) == (who, kind):
                dropped["repeated TURN_START"] = dropped.get("repeated TURN_START", 0) + 1
                continue
            if kind.startswith("POST#"):
                mapped, text = "post", f"#{kind.removeprefix('POST#')} {text}"
            elif kind == "TURN_START":
                text = ""
            if mapped is None:
                dropped[kind] = dropped.get(kind, 0) + 1
                continue
            events.append({"t": at, "end": None, "agent": who, "kind": mapped, "text": text, "exit": None,
                           "check": None, "sha": None})
    for event in events:
        event.pop("_only", None)
        event.pop("script", None)
        event["text"] = replay.event_text(redact, event["text"])
    events.sort(key=lambda event: event["t"])  # stable: the file's order within one clock step

    duration = max(times)
    peers = sorted(name for name in callers if name != "root")
    solo = not peers
    order = [*(["root"] if "root" in callers else []), *peers]
    order += [name for name in dict.fromkeys(event["agent"] for event in events) if name not in order]
    roles = {name: "solo" if solo else "root" if name == "root" else "peer" for name in order}
    commits = [event for event in events if event["kind"] == "commit"]

    def fact(label: str, value, source: str) -> dict:
        return {"label": label, "value": value if isinstance(value, str) else json.dumps(value), "source": source}

    facts = [fact(f"result.json {key}", result[key], cited)
             for key in ("active_min", "wall_min", "murmur_sha") if key in result]
    span = timeline["span"]
    warnings = []
    if span:
        facts.append(fact("timeline run span", f"active {span['active_min']:g} min, wall {span['wall_min']:g} min",
                          cited))
        shown = span["active_min"] if clock == "active" else span["wall_min"]
        if abs(duration / 60 - shown) > 0.11:
            warnings.append(f"the event stream ends at {duration / 60:.1f} min on this clock, but the timeline's "
                            f"own summary says {shown:g}")
    for number, judge in enumerate(timeline["judges"], start=1):
        facts.append(fact(f"judge {number}", judge, cited))
    if base:
        facts.append(fact("started from", base["text"], cited))
    if row:
        facts += [fact(f"E1.json {key}", row[key], cited_results)
                  for key in ("active_nf", "active_raw", "runner_active", "main_added_lines", "unmerged_branches",
                              "guesses", "collapse") if key in row]
    if dropped:
        warnings.append("left out of the timeline: " + ", ".join(
            f"{count} {kind} line{'' if count == 1 else 's'}" + (f" ({DROPPED[kind]})" if kind in DROPPED else "")
            for kind, count in sorted(dropped.items())))
    warnings.append("tool calls are read from the timeline's call text, which is cut to a few hundred characters: "
                    "it says what was asked for, not whether each command ran, and an exit status is shown only "
                    "where the output line gives one for a single command")
    warnings.append(f"commits ({len(commits)}) are placed by their author time; the timeline does not say when "
                    "each reached a branch, so none is marked as landed on main")
    judged = [judge.get("overall") for judge in timeline["judges"] if isinstance(judge, dict)]
    score = None
    if timeline["score"] is not None:
        score = replay.score(timeline["score"], f"'score overall' in {cited}" + (
            f"; its judge lines give {' and '.join(f'{value:g}' for value in judged)}" if judged else ""))
    delivered = result.get("delivered")
    return {
        "id": run_id,
        "source": {
            "kind": "timeline",
            "description": "imported from a published research timeline (branch experiment/self-improve-r4), "
                           "not read from a run's workspace",
            "files": [cited, *([cited_results] if cited_results else [])],
        },
        "task": row.get("task") if row else None,
        "mode": "solo" if solo else "swarm",
        "peers": len(peers) or 1,
        "base": base["sha"] if base else None,
        "clock": {**CLOCKS[clock], "start": None},
        "duration_s": duration,
        "outcome": {"finished": True, "exit_code": result.get("run_exit"),
                    "delivered": delivered if isinstance(delivered, bool) else None,
                    "capped": result.get("capped"), "interrupted": None, "diagnostic": None},
        "tokens": {
            "total": {"input_tokens": result.get("input"), "cached_input_tokens": None,
                      "uncached_input_tokens": row.get("uncached") if row else None,
                      "output_tokens": row.get("output") if row else None},
            "agents": {},
            "source": f"result.json as quoted in {cited}" + (f", and {cited_results}" if row else ""),
        } if result.get("input") is not None else None,
        "main": {"commits": result.get("commits"), "files": None,
                 "insertions": row.get("main_added_lines") if row else None, "deletions": None,
                 "last_change_s": None},
        "drafts": sorted(name for name in timeline["refs"] if name != "main"),
        "score": score,
        "facts": facts,
        "agents": replay.agent_rows(order, roles, events, [], duration),
        "events": events,
        "receipts": [],
        "receipts_note": "not available: change receipts are made from a run's session logs and its origin.git, "
                         f"and the published timeline carries neither. The commits it lists ({len(commits)}) "
                         "are in the event list.",
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("timelines", nargs="+", metavar="TIMELINE.md", help="one timeline, or two to compare")
    parser.add_argument("--results", metavar="E1.json", help="research-r4/results/E1.json, for what it adds")
    parser.add_argument("--clock", choices=sorted(CLOCKS), default="active",
                        help="which of the timeline's two clocks to place events on (default: active)")
    parser.add_argument("--html", metavar="FILE", help="write the replay as one self-contained HTML page")
    parser.add_argument("--json", metavar="FILE", help="write the replay as JSON, which `murmur replay` reads")
    parser.add_argument("--all", action="store_true", help="in the text view, list every tool call")
    args = parser.parse_args(argv)
    if len(args.timelines) > 2:
        parser.error("give one timeline, or two to compare")
    try:
        runs = [to_run(Path(path), Path(args.results) if args.results else None, args.clock)
                for path in args.timelines]
        document = replay.build(runs)
    except (TimelineError, replay.ReplayError) as error:
        print(f"timeline_to_replay: {error}", file=sys.stderr)
        return 1
    for target, text in ((args.html, replay.render_html), (args.json, replay.to_json)):
        if target:
            Path(target).write_text(text(document), encoding="utf-8")
            print(f"wrote {target}", file=sys.stderr)
    if args.html or args.json:
        print("\n".join(replay.summary_lines(document)))
    else:
        sys.stdout.write(replay.render_text(document, every=args.all))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
