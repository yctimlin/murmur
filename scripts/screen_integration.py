#!/usr/bin/env python3
"""Deterministic integration-barrier screen; real Git, fake Codex, zero model calls.

Run: python scripts/screen_integration.py NEW_DIRECTORY
Also runnable with --driver WORKSPACE by the generated fake Codex executable.
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
    result = subprocess.run(argv, cwd=cwd, env=env, capture_output=True, text=True, timeout=30)
    if result.returncode != expected:
        raise RuntimeError(f"{argv!r}: {result.returncode}: {result.stdout} {result.stderr}")
    return result


def driver(ws: Path):
    meta = json.loads((ws / "murmur.json").read_text())
    peers = [Path(peer["clone"]) for peer in meta["agents"]]
    def git(peer, *args):
        return command(["git", *args], cwd=peer)
    def commit(peer, file, text):
        (peer / file).write_text(text)
        git(peer, "add", file)
        git(peer, "commit", "-qm", file)
        git(peer, "push", "origin", "HEAD:main")
    def helper(peer, *args, expected=0):
        return json.loads(command([str(peer / ".murmur/integration"), *args], expected=expected).stdout)
    a1, a2 = peers
    commit(a1, "producer.py", "def value(): return {'amount': 3}\n")
    git(a2, "pull", "--ff-only")
    commit(a2, "check.py", "from producer import value\nassert value()['total'] == 3\n")
    git(a1, "pull", "--ff-only")
    transcript = []
    if meta.get("integration_barrier"):
        transcript += [helper(a1, "ready"), helper(a2, "ready")]
        failure = helper(a2, "check", "--", sys.executable, "-B", "check.py", expected=2)
        assert failure["exit_code"] == 1 and not failure["passed"]
        transcript.append(failure)
        helper(a1, "active")
        commit(a1, "producer.py", "def value(): return {'total': 3}\n")
        git(a2, "pull", "--ff-only")
        helper(a1, "ready")
        success = helper(a2, "check", "--", sys.executable, "-B", "check.py")
        assert success["passed"]
        transcript.append(success)
        # A late docs commit also invalidates the exact-revision receipt.
        commit(a1, "PR.md", "Tiny producer-consumer seam repaired and checked.\n")
        stale = helper(a1, "status")
        assert not stale["complete"]
        transcript.append(stale)
        git(a2, "pull", "--ff-only")
        transcript.append(helper(a2, "check", "--", sys.executable, "-B", "check.py"))
    (ws / "logs" / "screen-events.json").write_text(json.dumps(transcript, indent=2) + "\n")
    print(json.dumps({"type": "event_msg", "payload": {"type": "task_complete"}}))


def screen(destination: Path):
    destination.mkdir(parents=True, exist_ok=False)
    bin_dir = destination / "bin"
    bin_dir.mkdir()
    fake = bin_dir / "codex"
    fake.write_text("#!/usr/bin/env python3\nimport json, pathlib, subprocess, sys\n"
                    "if sys.argv[1:3] == ['debug', 'models']:\n"
                    " print(json.dumps({'models': []})); raise SystemExit(0)\n"
                    "ws=pathlib.Path(sys.argv[sys.argv.index('-C')+1]).parent\n"
                    f"raise SystemExit(subprocess.call([{sys.executable!r}, {str(Path(__file__).resolve())!r}, '--driver', str(ws)]))\n")
    fake.chmod(0o755)
    empty_home = destination / "codex-config"
    empty_home.mkdir()
    env = {**os.environ, "PATH": str(bin_dir) + os.pathsep + os.environ["PATH"],
           "PYTHONPATH": str(ROOT / "src"), "CODEX_HOME": str(empty_home)}
    fixture = destination / "fixture"
    fixture.mkdir()
    # Explicit repository boundary, even if the destination sits inside this checkout.
    command(["git", "init", "-qb", "main"], cwd=fixture)
    command(["git", "config", "user.name", "screen"], cwd=fixture)
    command(["git", "config", "user.email", "screen@example.invalid"], cwd=fixture)
    (fixture / "README.md").write_text("Producer/consumer protocol screen.\n")
    command(["git", "add", "."], cwd=fixture)
    command(["git", "commit", "-qm", "fixture"], cwd=fixture)
    brief = destination / "brief.md"
    brief.write_text("Make a tiny producer and consumer agree on a value.\n")
    rows = []
    for enabled in (False, True):
        arm = "enabled" if enabled else "base"
        config = destination / (arm + ".toml")
        config.write_text("integration_barrier = " + str(enabled).lower() + "\n")
        started = time.monotonic()
        command([sys.executable, "-m", "murmur", "setup", str(brief), "--repo", str(fixture),
                 "--config", str(config), "--peers", "2", "--cap", "25m", "--into", str(destination), "--id", arm], env=env)
        ws = destination / arm
        result = command([sys.executable, "-m", "murmur", "run", str(ws)], env=env)
        (ws / "logs/screen.stdout").write_text(result.stdout)
        record = json.loads((ws / "logs/run.json").read_text())
        rows.append({"arm": arm, "wall_seconds": round(time.monotonic()-started, 3),
                     "exit_code": record["exit_code"], "model_calls": 0, "model_tokens": 0,
                     "usage_status": record["usage"]["status"],
                     "integration": record.get("integration"),
                     "screen_events": json.loads((ws / "logs/screen-events.json").read_text())})
    output = {"kind": "scripted-mechanism-screen", "task": "producer-consumer key mismatch",
              "quality_or_cost_claim": False, "rows": rows}
    (destination / "screen.json").write_text(json.dumps(output, indent=2) + "\n")
    print(destination / "screen.json")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--driver"]:
        driver(Path(sys.argv[2]))
    elif len(sys.argv) == 2:
        screen(Path(sys.argv[1]).resolve())
    else:
        raise SystemExit(__doc__)
