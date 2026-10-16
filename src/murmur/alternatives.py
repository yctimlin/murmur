"""Bounded, peer-authored implementation trials; internal opt-in mechanism.

This file is copied into a run, so its helper depends only on the standard library.
The shared ledger coordinates cooperative peers; it is not a security boundary.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time


def git(origin: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(origin), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


@contextlib.contextmanager
def transaction(state: Path):
    with sqlite3.connect(state, timeout=30) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN IMMEDIATE")
        yield db


def initialize(state: Path) -> None:
    with sqlite3.connect(state) as db:
        db.executescript("""
        CREATE TABLE trials (
          name TEXT PRIMARY KEY, base TEXT NOT NULL, checks TEXT NOT NULL,
          timeout REAL NOT NULL, status TEXT NOT NULL DEFAULT 'open', winner TEXT);
        CREATE TABLE candidates (
          trial TEXT NOT NULL, peer TEXT NOT NULL, revision TEXT NOT NULL,
          position INTEGER NOT NULL, PRIMARY KEY(trial,peer), UNIQUE(trial,revision));
        CREATE TABLE events (
          sequence INTEGER PRIMARY KEY, at REAL NOT NULL, trial TEXT NOT NULL,
          kind TEXT NOT NULL, detail TEXT NOT NULL);
        """)


def event(db, name: str, kind: str, detail: dict) -> None:
    db.execute("INSERT INTO events(at,trial,kind,detail) VALUES (?,?,?,?)",
               (time.time(), name, kind, json.dumps(detail)))


def open_trial(state: Path, origin: Path, name: str, checks: list, timeout: float) -> dict:
    if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name):
        raise ValueError("trial name must contain 1-64 letters, digits, underscores or dashes")
    if not isinstance(checks, list) or not 1 <= len(checks) <= 8:
        raise ValueError("checks must be a JSON list of 1-8 nonempty argv lists")
    if any(not isinstance(c, list) or not c or
           any(not isinstance(a, str) or not a or '\0' in a for a in c) for c in checks):
        raise ValueError("every check must be a nonempty argv list of strings")
    if not 0 < timeout <= 300:
        raise ValueError("timeout must be greater than zero and at most 300 seconds per check")
    base = git(origin, "rev-parse", "refs/heads/main")
    with transaction(state) as db:
        if db.execute("SELECT 1 FROM trials WHERE status IN ('open','evaluating')").fetchone():
            raise ValueError("finish the existing trial before opening another")
        db.execute("INSERT INTO trials(name,base,checks,timeout) VALUES (?,?,?,?)",
                   (name, base, json.dumps(checks), timeout))
        event(db, name, "opened", {"base": base, "checks": checks, "timeout": timeout})
    return {"trial": name, "base": base, "slots": 2}


def submit(state: Path, origin: Path, name: str, peer: str, revision: str) -> dict:
    revision = git(origin, "rev-parse", "--verify", "--end-of-options", f"{revision}^{{commit}}")
    with transaction(state) as db:
        trial = db.execute("SELECT * FROM trials WHERE name=?", (name,)).fetchone()
        if not trial or trial['status'] != 'open':
            raise ValueError("trial is not open")
        if git(origin, "merge-base", trial['base'], revision) != trial['base']:
            raise ValueError("candidate must descend from the trial base")
        count = db.execute("SELECT COUNT(*) FROM candidates WHERE trial=?", (name,)).fetchone()[0]
        if count >= 2:
            raise ValueError("both candidate slots are occupied")
        db.execute("INSERT INTO candidates VALUES (?,?,?,?)", (name, peer, revision, count))
        event(db, name, "submitted", {"peer": peer, "revision": revision})
    return {"trial": name, "peer": peer, "revision": revision, "position": count}


def _check(argv: list[str], cwd: Path, timeout: float) -> dict:
    started = time.monotonic()
    code, timed_out = None, False
    # File-backed output prevents large diagnostics from filling model context or RAM.
    with tempfile.TemporaryFile() as output:
        try:
            proc = subprocess.Popen(argv, cwd=cwd, stdout=output, stderr=subprocess.STDOUT,
                                    start_new_session=True)
        except OSError as error:
            return {"argv": argv, "exit_code": None, "error": str(error), "passed": False}
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            # Always stop descendants, including after a successful parent exit.
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait()
        output.seek(0, 2)
        size = output.tell()
        output.seek(max(0, size - 4000))
        tail = output.read().decode(errors='replace')
    return {"argv": argv, "exit_code": code, "timed_out": timed_out,
            "seconds": round(time.monotonic() - started, 4), "output_tail": tail,
            "output_truncated": size > 4000, "passed": code == 0 and not timed_out}


def evaluate(state: Path, origin: Path, name: str) -> dict:
    with transaction(state) as db:
        trial = db.execute("SELECT * FROM trials WHERE name=?", (name,)).fetchone()
        candidates = db.execute("SELECT * FROM candidates WHERE trial=? ORDER BY position", (name,)).fetchall()
        if not trial or trial['status'] != 'open' or len(candidates) != 2:
            raise ValueError("evaluation requires an open trial with two distinct peers' candidates")
        db.execute("UPDATE trials SET status='evaluating' WHERE name=?", (name,))
        event(db, name, "evaluation_started", {})
    checks = json.loads(trial['checks'])
    results = []
    try:
        for candidate in candidates:
            with tempfile.TemporaryDirectory(prefix='candidate-', dir=state.parent) as tmp:
                checkout = Path(tmp) / 'repo'
                git(origin, "clone", "--quiet", "--no-hardlinks", "--no-checkout", str(origin), str(checkout))
                git(checkout, "checkout", "--quiet", "--detach", candidate['revision'])
                check_results = [_check(argv, checkout, trial['timeout']) for argv in checks]
                # Tests may generate ignored/untracked caches, but may not change tracked inputs.
                clean = not git(checkout, "status", "--porcelain", "--untracked-files=no")
                same_head = git(checkout, "rev-parse", "HEAD") == candidate['revision']
                result = {"peer": candidate['peer'], "revision": candidate['revision'],
                          "checks": check_results, "tracked_clean": clean, "head_unchanged": same_head,
                          "passed": clean and same_head and all(c['passed'] for c in check_results)}
                results.append(result)
                with transaction(state) as db:
                    event(db, name, "candidate_checked", result)
        winner = next((c['revision'] for c in results if c['passed']), None)
        status = 'rejected'
        if winner:
            try:
                git(origin, "update-ref", "-m", f"murmur alternative {name}",
                    "refs/heads/main", winner, trial['base'])
                status = 'promoted'
            except ValueError:
                status = 'stale'
        with transaction(state) as db:
            db.execute("UPDATE trials SET status=?,winner=? WHERE name=?", (status, winner, name))
            event(db, name, status, {"winner": winner, "base": trial['base']})
        return {"trial": name, "status": status, "winner": winner, "results": results}
    except BaseException as error:
        with transaction(state) as db:
            db.execute("UPDATE trials SET status='failed' WHERE name=?", (name,))
            event(db, name, "failed", {"error": str(error)})
        raise


def inspect(state: Path) -> dict:
    with sqlite3.connect(state) as db:
        db.row_factory = sqlite3.Row
        trials = [dict(r) for r in db.execute("SELECT name,base,status,winner FROM trials ORDER BY name")]
        events = db.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    return {"trials": trials, "event_count": events,
            "complete": all(t['status'] == 'promoted' for t in trials)}


def install(ws: Path, agents: list[dict]) -> str:
    directory = ws / 'work' / 'alternatives'
    directory.mkdir()
    state = directory / 'trials.sqlite3'
    initialize(state)
    engine = directory / 'engine.py'
    shutil.copyfile(__file__, engine)
    for agent in agents:
        helper = Path(agent['clone']) / '.murmur' / 'alternatives'
        helper.parent.mkdir(exist_ok=True)
        argv = [sys.executable, str(engine), '--state', str(state), '--origin',
                str(ws / 'work' / 'origin.git'), '--peer', agent['id']]
        helper.write_text('#!/bin/sh\nexec ' + shlex.join(argv) + ' "$@"\n')
        helper.chmod(0o755)
    return """Internal alternative trials are enabled. For one risky bounded unit, agree on executable
acceptance checks before writing two independent implementations. Any peer may run
`.murmur/alternatives open NAME --checks '[["python3","check.py"]]' --timeout 60`
(use actual task-relevant argv; the example is not a prescribed language).
The helper prints the exact base. Two different peers start from it, implement independently,
commit, push their existing allowed draft branch, then each runs
`.murmur/alternatives submit NAME draft/PEER`. Any peer then runs
`.murmur/alternatives evaluate NAME`. Only a passing candidate can advance main; if both pass,
the first submitted wins deterministically. Checks run in fresh tracked-file clones without
ignored setup artifacts; choose self-contained checks or an argv that prepares dependencies.
Inspect `.murmur/alternatives status`. Avoid starting more than one bounded trial for the task.
A changed main makes the result stale; reopen at the new base only if the task warrants it.
An unresolved/rejected/stale trial makes run completion fail; it does not overwrite other work.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, required=True)
    parser.add_argument('--origin', type=Path, required=True)
    parser.add_argument('--peer', required=True)
    commands = parser.add_subparsers(dest='action', required=True)
    opened = commands.add_parser('open')
    opened.add_argument('name')
    opened.add_argument('--checks', required=True)
    opened.add_argument('--timeout', type=float, default=60)
    submitted = commands.add_parser('submit')
    submitted.add_argument('name')
    submitted.add_argument('revision')
    evaluated = commands.add_parser('evaluate')
    evaluated.add_argument('name')
    commands.add_parser('status')
    args = parser.parse_args()
    try:
        if args.action == 'open':
            result = open_trial(args.state, args.origin, args.name, json.loads(args.checks), args.timeout)
        elif args.action == 'submit':
            result = submit(args.state, args.origin, args.name, args.peer, args.revision)
        elif args.action == 'evaluate':
            result = evaluate(args.state, args.origin, args.name)
        else:
            result = inspect(args.state)
        print(json.dumps(result, indent=2))
        return 1 if result.get('status') in ('stale', 'rejected') else 0
    except (ValueError, sqlite3.Error, OSError) as error:
        print(f'alternatives: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
