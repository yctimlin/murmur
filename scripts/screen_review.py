#!/usr/bin/env python3
"""Deterministic two-peer review screen; zero model calls, real Git and launcher.

Run: python scripts/screen_review.py NEW_DIRECTORY
This is a mechanism screen, not evidence of model review quality or token savings.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def command(args, cwd=None, expected=0, env=None):
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, text=True)
    if result.returncode != expected:
        raise RuntimeError(f"{args}: expected {expected}, got {result.returncode}: {result.stderr}")
    return result


def git(cwd, *args):
    return command(["git", *args], cwd).stdout.strip()


def fake_peer_run(args):
    if args[:2] == ["debug", "models"]:
        os.execv(sys.executable, [sys.executable, str(ROOT / "tests/fake_codex.py"), *args])
    ws = Path(args[args.index("-C") + 1]).parent
    meta = json.loads((ws / "murmur.json").read_text())
    a1, a2 = [Path(a["clone"]) for a in meta["agents"]]
    helper1, helper2 = a1 / ".murmur/review", a2 / ".murmur/review"
    enabled = helper1.exists()
    events = []

    def commit(clone, path, text):
        (clone / path).write_text(text)
        git(clone, "add", path)
        git(clone, "commit", "-qm", "screen change")
        git(clone, "push", "origin", "HEAD:main")
        return git(clone, "rev-parse", "HEAD")

    head = commit(a1, "greeting.py", 'def greet(name):\n    return "Hello, " + name.strip() + "!"\n')
    git(a2, "pull", "--ff-only")
    check = 'from greeting import greet; assert greet("  ") == "Hello, stranger!"'
    result = command([sys.executable, "-c", check], a2, expected=1)
    events.append({"kind": "boundary-defect-detected", "exit_code": result.returncode})
    head = commit(a1, "greeting.py", 'def greet(name):\n    return "Hello, " + (name.strip() or "stranger") + "!"\n')
    if enabled:
        for helper, clone, expected_error in [(helper1, a1, "self-review"), (helper2, a2, "stale")]:
            result = command([str(helper), "attest", "--revision", head, "--note", "screen probe", "--", "greeting.py"], clone, expected=1)
            assert expected_error in result.stderr
            events.append({"kind": expected_error + "-rejected", "detail": json.loads(result.stderr)})
    git(a2, "pull", "--ff-only")
    command([sys.executable, "-c", check], a2)
    if enabled and os.environ.get("MURMUR_REVIEW_SCREEN_MISSING") != "1":
        result = command([str(helper2), "attest", "--revision", head, "--note", "Exercised blank-name boundary after fixing regression", "--", "greeting.py"], a2)
        events.append({"kind": "independent-review", "detail": json.loads(result.stdout)})
    if enabled:
        result = command([str(helper2), "status"], a2)
        events.append({"kind": "coverage", "detail": json.loads(result.stdout)})
    (ws / "logs/screen-events.json").write_text(json.dumps(events, indent=2) + "\n")
    Path(args[args.index("-o") + 1]).write_text("scripted peer screen completed\n")
    print(json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}}))


def capture(destination):
    destination.mkdir(parents=True, exist_ok=False)
    bin_dir = destination / "bin"
    bin_dir.mkdir()
    (bin_dir / "codex").symlink_to(Path(__file__).resolve())
    config_home = destination / "codex-config"
    config_home.mkdir()
    source = destination / "source"
    source.mkdir()
    git(source, "init", "-q", "-b", "main")
    git(source, "config", "user.name", "Fixture")
    git(source, "config", "user.email", "fixture@example.invalid")
    (source / "README.md").write_text("Tiny greeting utility\n")
    git(source, "add", "README.md")
    git(source, "commit", "-qm", "initial")
    brief = destination / "brief.md"
    brief.write_text("Implement a greeting utility that handles blank input; independently review it.\n")
    env = {**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ.get("PATH", ""),
           "PYTHONPATH": str(ROOT / "src"), "CODEX_HOME": str(config_home)}
    rows = []
    for arm in ["base", "enabled", "missing-review"]:
        config = destination / (arm + ".toml")
        config.write_text("independent_review = " + ("false" if arm == "base" else "true") + "\n")
        command([sys.executable, "-m", "murmur", "setup", str(brief), "--repo", str(source),
                 "--peers", "2", "--cap", "25m", "--config", str(config), "--into", str(destination), "--id", arm], env=env)
        ws = destination / arm
        started = time.monotonic()
        result = command([sys.executable, "-m", "murmur", "run", str(ws)],
                         expected=1 if arm == "missing-review" else 0,
                         env={**env, "MURMUR_REVIEW_SCREEN_MISSING": "1" if arm == "missing-review" else "0"})
        (ws / "logs/launcher.txt").write_text(result.stdout + result.stderr)
        record = json.loads((ws / "logs/run.json").read_text())
        rows.append({"arm": arm, "seconds": round(time.monotonic() - started, 3),
                     "exit_code": result.returncode, "model_tokens": 0,
                     "usage": record["usage"], "review": record.get("independent_review"),
                     "events": json.loads((ws / "logs/screen-events.json").read_text())})
    (destination / "screen.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(destination / "screen.json")


if __name__ == "__main__":
    if "exec" in sys.argv[1:] or sys.argv[1:3] == ["debug", "models"]:
        fake_peer_run(sys.argv[1:])
    elif len(sys.argv) == 2:
        capture(Path(sys.argv[1]).resolve())
    else:
        raise SystemExit("usage: python scripts/screen_review.py NEW_DIRECTORY")
