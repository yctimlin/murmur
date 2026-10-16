"""Claimable, revision-bound final integration checks (internal experiment).

The generated helper is a frozen copy of this standard-library-only module. The
ledger is coordination among trusted peers, not an authorization boundary.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import shlex
import signal
import sqlite3
import subprocess
import sys
import time


class BarrierError(Exception):
    pass


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise BarrierError((result.stderr or result.stdout).strip())
    return result.stdout.strip()


def _clean(clone: Path) -> bool:
    # Scratch is documented as non-deliverable throughout murmur.
    return not _git(clone, "status", "--porcelain", "--untracked-files=all", "--", ".", ":(exclude).work")


def install(ws: Path, agents: list[dict], cap_seconds: int) -> str:
    folder = ws / "work" / ".murmur-integration"
    folder.mkdir()
    config = {"origin": str(ws / "work" / "origin.git"),
              "agents": {agent["id"]: agent["clone"] for agent in agents},
              "check_timeout": max(1, min(cap_seconds, 600))}
    (folder / "config.json").write_text(json.dumps(config))
    (folder / "integration.py").write_text(Path(__file__).read_text())
    with sqlite3.connect(folder / "ledger.sqlite3") as db:
        db.execute("CREATE TABLE state (id INTEGER PRIMARY KEY CHECK (id=1), data TEXT NOT NULL)")
        db.execute("CREATE TABLE events (id INTEGER PRIMARY KEY, at REAL NOT NULL, data TEXT NOT NULL)")
        state = {"head": _git(Path(config["origin"]), "rev-parse", "main"),
                 "ready": {agent["id"]: False for agent in agents}, "claim": None, "receipt": None}
        db.execute("INSERT INTO state VALUES (1, ?)", (json.dumps(state),))
    for agent in agents:
        helper = Path(agent["clone"]) / ".murmur" / "integration"
        helper.parent.mkdir(exist_ok=True)
        command = [sys.executable, str(folder / "integration.py"), "--ledger", str(folder), "--peer", agent["id"]]
        helper.write_text("#!/bin/sh\nexec " + shlex.join(command) + ' "$@"\n')
        helper.chmod(0o755)
    return """
Integration barrier is enabled. After pushing your work and pulling current main,
run `.murmur/integration ready`. It records your implementation as ready; do not
finish until `.murmur/integration status` reports complete. Any peer can run
`.murmur/integration check -- <command> <args...>` once every peer is ready. Choose
a meaningful end-to-end check for the objective, exercising the assembled result.
The helper exclusively claims that duty and executes the command on clean current
main; it records the revision, exit, duration and log. A failed check or later main
push invalidates completion. Fix failures, push, pull and check again. Use
`.murmur/integration active` before starting more implementation after readiness.
Only one peer needs to check; others can review or use a long collaboration wait.
The final runner rejects missing or stale integration evidence even on Codex exit 0.
""".strip()


class Ledger:
    def __init__(self, folder: Path):
        self.folder = folder
        self.config = json.loads((folder / "config.json").read_text())
        self.origin = Path(self.config["origin"])

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.folder / "ledger.sqlite3", timeout=10)
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT data FROM state WHERE id=1").fetchone()
            state = json.loads(row[0])
            head = _git(self.origin, "rev-parse", "main")
            if state["head"] != head:
                state.update(head=head, claim=None, receipt=None)
                self.event(db, "head_changed", revision=head)
            yield db, state
            db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(state),))
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def event(db, kind: str, **data):
        db.execute("INSERT INTO events (at,data) VALUES (?,?)", (time.time(), json.dumps({"event": kind, **data})))

    def clone(self, peer: str) -> Path:
        if peer not in self.config["agents"]:
            raise BarrierError("unknown peer")
        return Path(self.config["agents"][peer])

    def ready(self, peer: str, ready: bool) -> dict:
        clone = self.clone(peer)
        with self.transaction() as (db, state):
            if ready and (_git(clone, "rev-parse", "HEAD") != state["head"] or not _clean(clone)):
                raise BarrierError("ready requires a clean clone at current main; push/pull first")
            if state["ready"][peer] != ready:
                state["ready"][peer] = ready
                state["receipt"] = None
                state["claim"] = None
                self.event(db, "ready" if ready else "active", peer=peer)
        return self.status()

    @staticmethod
    def describe(state: dict) -> dict:
        pending = [peer for peer, ready in state["ready"].items() if not ready]
        receipt = state["receipt"]
        complete = not pending and receipt is not None and receipt["passed"] and receipt["revision"] == state["head"]
        return {"complete": bool(complete), "revision": state["head"], "pending_peers": pending,
                "claim": state["claim"], "receipt": receipt}

    def status(self) -> dict:
        with self.transaction() as (_, state):
            return self.describe(state)

    def claim(self, peer: str, argv: list[str]) -> dict:
        clone = self.clone(peer)
        if not argv:
            raise BarrierError("check needs an executable and arguments after --")
        with self.transaction() as (db, state):
            if not all(state["ready"].values()):
                raise BarrierError("implementation still active: " + ", ".join(p for p, ready in state["ready"].items() if not ready))
            if _git(clone, "rev-parse", "HEAD") != state["head"] or not _clean(clone):
                raise BarrierError("check requires a clean clone at current main; pull first")
            previous = state["claim"]
            if previous and previous["expires"] > time.time():
                raise BarrierError("integration duty claimed by " + previous["peer"])
            claim = {"peer": peer, "revision": state["head"], "token": secrets.token_hex(12),
                     "expires": time.time() + self.config["check_timeout"] + 30,
                     "argv": argv}
            state["claim"] = claim
            state["receipt"] = None
            self.event(db, "claimed", **claim)
        return claim

    def check(self, peer: str, argv: list[str]) -> dict:
        claim = self.claim(peer, argv)
        clone = self.clone(peer)
        started = time.monotonic()
        log_path = self.folder / (claim["token"] + ".log")
        returncode = None
        error = None
        proc = None
        handlers = {}
        def interrupted(signum, frame):
            raise InterruptedError(f"signal {signum}")
        try:
            for signum in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP):
                handlers[signum] = signal.signal(signum, interrupted)
            with log_path.open("wb") as log:
                proc = subprocess.Popen(argv, cwd=clone, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
                returncode = proc.wait(timeout=self.config["check_timeout"])
        except (OSError, subprocess.TimeoutExpired, InterruptedError) as exc:
            error = str(exc)
        finally:
            if proc is not None:
                # This process group was created above and belongs only to this check.
                for sig in (signal.SIGTERM, signal.SIGKILL):
                    try:
                        os.killpg(proc.pid, sig)
                    except ProcessLookupError:
                        break
                proc.wait()
            for signum, handler in handlers.items():
                signal.signal(signum, handler)
        clean = _clean(clone)
        clone_head = _git(clone, "rev-parse", "HEAD")
        with self.transaction() as (db, state):
            same_claim = state["claim"] and state["claim"]["token"] == claim["token"]
            passed = (returncode == 0 and error is None and clean and clone_head == claim["revision"]
                      and state["head"] == claim["revision"] and bool(same_claim) and all(state["ready"].values()))
            receipt = {"peer": peer, "revision": claim["revision"], "argv": argv, "exit_code": returncode,
                       "seconds": round(time.monotonic() - started, 3), "clean_after": clean,
                       "passed": passed, "error": error, "log": str(log_path)}
            if same_claim:
                state["claim"] = None
                state["receipt"] = receipt
            self.event(db, "checked", **receipt)
        return receipt


def inspect(ws: Path) -> dict:
    try:
        return Ledger(ws / "work" / ".murmur-integration").status()
    except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, BarrierError) as exc:
        return {"complete": False, "error": str(exc)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ledger", type=Path, required=True)
    parser.add_argument("--peer", required=True)
    parser.add_argument("action", choices=["ready", "active", "status", "check"])
    parser.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    try:
        ledger = Ledger(args.ledger)
        if args.action == "check":
            argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            result = ledger.check(args.peer, argv)
            code = 0 if result["passed"] else 2
        elif args.action in ("ready", "active"):
            result = ledger.ready(args.peer, args.action == "ready")
            code = 0
        else:
            result = ledger.status()
            code = 0
        print(json.dumps(result, sort_keys=True))
        raise SystemExit(code)
    except (BarrierError, OSError, sqlite3.Error, ValueError) as exc:
        print(json.dumps({"error": str(exc)}))
        raise SystemExit(2) from None


if __name__ == "__main__":
    main()
