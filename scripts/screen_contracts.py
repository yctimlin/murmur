#!/usr/bin/env python3
"""Deterministic two-peer contract screen through real murmur setup/run.

Usage: python scripts/screen_contracts.py NEW_DIRECTORY
The fake model driver performs scripted peer operations; no model tokens are spent.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def command(argv, cwd=None, env=None, expected=0):
    result = subprocess.run(list(map(str, argv)), cwd=cwd, env=env,
                            capture_output=True, text=True, timeout=60)
    if result.returncode != expected:
        raise RuntimeError(f"{argv}: {result.returncode}: {result.stderr}")
    return result


def peer_driver():
    if sys.argv[1:3] == ["debug", "models"]:
        print('{"models":[]}')
        return
    ws = Path(sys.argv[sys.argv.index("-C") + 1]).parent
    first = ws / "work" / "peers" / "a1"
    second = ws / "work" / "peers" / "a2"
    probe = first / ".murmur" / "probe.py"
    probe.write_text('import json\np=json.load(open("packet.json"))\nassert p["kind"]=="note"\nassert p["payload"]=="hello"\n')
    frozen = command([first / ".murmur" / "contract", "add", "packet-shape", "--probe", probe,
                      "--", sys.executable, "{probe}"], cwd=first)
    path = second / "packet.json"
    path.write_text('{"kind":"note","body":"hello"}\n')
    command(["git", "add", "packet.json"], cwd=second)
    command(["git", "commit", "-qm", "deliberate seam violation"], cwd=second)
    rejected = subprocess.run(["git", "push", "origin", "HEAD:main"], cwd=second,
                              capture_output=True, text=True, timeout=60)
    assert rejected.returncode != 0 and "contract rejected" in rejected.stderr, rejected.stderr
    path.write_text('{"kind":"note","payload":"hello","label":"screen"}\n')
    command(["git", "add", "packet.json"], cwd=second)
    command(["git", "commit", "-qm", "preserve contract and add label"], cwd=second)
    accepted = command(["git", "push", "origin", "HEAD:main"], cwd=second)
    evidence = {"driver": "scripted; zero model calls", "activation": json.loads(frozen.stdout),
                "rejected_exit": rejected.returncode, "rejection": rejected.stderr,
                "accepted_exit": accepted.returncode,
                "events": [json.loads(line) for line in (ws / "work" / ".murmur-contracts" / "events.jsonl").read_text().splitlines()]}
    (ws / "logs" / "contract-screen.json").write_text(json.dumps(evidence, indent=2)+"\n")
    Path(sys.argv[sys.argv.index("-o") + 1]).write_text("scripted screen completed\n")
    print(json.dumps({"type":"event_msg","payload":{"type":"task_complete"}}))


def capture(destination):
    destination.mkdir(parents=True, exist_ok=False)
    source = destination / "source"
    source.mkdir()
    command(["git", "init", "-qb", "main", source])
    (source / "packet.json").write_text('{"kind":"note","payload":"hello"}\n')
    command(["git", "add", "packet.json"], cwd=source)
    command(["git", "-c", "user.name=screen", "-c", "user.email=screen@local", "commit", "-qm", "base"], cwd=source)
    brief = destination / "brief.md"
    brief.write_text("Extend note packet with a label while preserving kind/payload contract.\n")
    executable = destination / "bin"
    executable.mkdir()
    (executable / "codex").symlink_to(Path(__file__).resolve())
    env = {**os.environ, "PATH": str(executable)+os.pathsep+os.environ["PATH"],
           "PYTHONPATH": str(ROOT / "src"), "MURMUR_CONTRACTS": "1"}
    started = time.monotonic()
    setup = command([sys.executable, "-m", "murmur", "setup", brief, "--repo", source,
                     "--into", destination, "--id", "run", "--peers", "2", "--cap", "25m"], env=env)
    run = command([sys.executable, "-m", "murmur", "run", destination / "run"], env=env)
    (destination / "transcript.txt").write_text(setup.stdout + setup.stderr + run.stdout + run.stderr)
    summary = {"mode":"scripted-real-git", "model_calls":0, "model_tokens":0,
               "seconds":round(time.monotonic()-started, 4), "run_exit":run.returncode,
               "evidence":"run/logs/contract-screen.json", "run_record":"run/logs/run.json"}
    (destination / "screen.json").write_text(json.dumps(summary, indent=2)+"\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    if Path(sys.argv[0]).name == "codex":
        peer_driver()
    elif len(sys.argv) == 2:
        capture(Path(sys.argv[1]).resolve())
    else:
        raise SystemExit("usage: python scripts/screen_contracts.py NEW_DIRECTORY")
