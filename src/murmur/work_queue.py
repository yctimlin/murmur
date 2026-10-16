"""Experimental peer work queue; copied into runs and executable without murmur installed.

This schedules declared work, not arbitrary repository changes. Claims fence ledger writes,
not filesystem writes. A peer recovering an expired task must inspect the previous work.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import sqlite3
import sys
import time

LEASE_SECONDS = 900
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")


class QueueError(ValueError):
    pass


def _bounded(value: str, name: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise QueueError(f"{name} must be nonempty and at most {limit} characters")
    return value


def initialize(path: Path, agents: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE peers (id TEXT PRIMARY KEY, clone TEXT NOT NULL);
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY, title TEXT NOT NULL, detail TEXT NOT NULL,
                creator TEXT NOT NULL, state TEXT NOT NULL DEFAULT 'ready',
                owner TEXT, token TEXT, expires REAL, previous_owner TEXT,
                result TEXT, created REAL NOT NULL
            );
            CREATE TABLE dependencies (task TEXT NOT NULL, dependency TEXT NOT NULL,
                PRIMARY KEY(task, dependency));
            CREATE TABLE events (seq INTEGER PRIMARY KEY, at REAL NOT NULL,
                actor TEXT NOT NULL, kind TEXT NOT NULL, task TEXT, data TEXT NOT NULL);
        """)
        db.executemany("INSERT INTO peers VALUES (?, ?)",
                       [(a["id"], str(Path(a["clone"]).resolve())) for a in agents])


@contextmanager
def transaction(path: Path):
    # mode=rw avoids silently creating an empty queue after accidental deletion.
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=rw", uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    try:
        db.execute("BEGIN IMMEDIATE")
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def _event(db, actor, kind, task=None, **data):
    db.execute("INSERT INTO events(at, actor, kind, task, data) VALUES (?, ?, ?, ?, ?)",
               (time.time(), actor, kind, task, json.dumps(data, sort_keys=True)))


def _expire(db, now):
    rows = db.execute("SELECT id, owner FROM tasks WHERE state='running' AND expires<=?", (now,)).fetchall()
    for row in rows:
        _event(db, row["owner"], "expired", row["id"])
    db.execute("UPDATE tasks SET state='ready', previous_owner=owner, owner=NULL, "
               "token=NULL, expires=NULL WHERE state='running' AND expires<=?", (now,))


def _peer(db, actor):
    if not db.execute("SELECT 1 FROM peers WHERE id=?", (actor,)).fetchone():
        raise QueueError("unknown peer")


def add(path: Path, actor: str, task: str, title: str, detail: str, dependencies=()):
    if not ID.fullmatch(task):
        raise QueueError("task id must be 1-80 letters, digits, dots, dashes or underscores")
    _bounded(title, "title", 160)
    _bounded(detail, "detail", 1800)
    dependencies = sorted(set(dependencies))
    if len(dependencies) > 20:
        raise QueueError("at most 20 dependencies per task")
    with transaction(path) as db:
        _peer(db, actor)
        # Only older tasks can be dependencies, making cycles impossible.
        for dep in dependencies:
            if not db.execute("SELECT 1 FROM tasks WHERE id=?", (dep,)).fetchone():
                raise QueueError(f"dependency does not exist: {dep}")
        existing = db.execute("SELECT * FROM tasks WHERE id=?", (task,)).fetchone()
        if existing:
            old_deps = [r[0] for r in db.execute("SELECT dependency FROM dependencies WHERE task=? ORDER BY dependency", (task,))]
            if (existing["creator"], existing["title"], existing["detail"], old_deps) == (actor, title, detail, dependencies):
                return {"task": task, "state": existing["state"], "created": False}
            raise QueueError("task id already exists with different content or creator")
        db.execute("INSERT INTO tasks(id, title, detail, creator, created) VALUES (?, ?, ?, ?, ?)",
                   (task, title, detail, actor, time.time()))
        db.executemany("INSERT INTO dependencies VALUES (?, ?)", [(task, dep) for dep in dependencies])
        _event(db, actor, "added", task, dependencies=dependencies)
        return {"task": task, "state": "ready", "created": True}


def _summary(db):
    counts = {"ready": 0, "running": 0, "done": 0}
    counts.update({r[0]: r[1] for r in db.execute("SELECT state, COUNT(*) FROM tasks GROUP BY state")})
    total = sum(counts.values())
    ready = db.execute("SELECT COUNT(*) FROM tasks t WHERE t.state='ready' AND NOT EXISTS "
                       "(SELECT 1 FROM dependencies d JOIN tasks p ON p.id=d.dependency "
                       "WHERE d.task=t.id AND p.state!='done')").fetchone()[0]
    return {"status": "unused" if not total else "complete" if counts["done"] == total else "incomplete",
            "total": total, "done": counts["done"], "running": counts["running"],
            "ready": ready, "waiting": counts["ready"] - ready}


def claim(path: Path, actor: str, *, lease_seconds: float = LEASE_SECONDS):
    if not 0 < lease_seconds <= 3600:
        raise QueueError("lease must be positive and at most one hour")
    with transaction(path) as db:
        _peer(db, actor)
        now = time.time()
        _expire(db, now)
        row = db.execute("SELECT * FROM tasks WHERE state='running' AND owner=?", (actor,)).fetchone()
        if row:
            # Retrying next is idempotent and does not silently extend the lease.
            return {"task": dict(row), "existing_claim": True, **_summary(db)}
        row = db.execute("SELECT t.* FROM tasks t WHERE t.state='ready' AND NOT EXISTS "
                         "(SELECT 1 FROM dependencies d JOIN tasks p ON p.id=d.dependency "
                         "WHERE d.task=t.id AND p.state!='done') ORDER BY t.created, t.id LIMIT 1").fetchone()
        if not row:
            return {"task": None, **_summary(db)}
        token = secrets.token_hex(16)
        db.execute("UPDATE tasks SET state='running', owner=?, token=?, expires=? WHERE id=?",
                   (actor, token, now + lease_seconds, row["id"]))
        _event(db, actor, "claimed", row["id"], stolen=actor != row["creator"],
               recovered_from=row["previous_owner"])
        task = dict(db.execute("SELECT * FROM tasks WHERE id=?", (row["id"],)).fetchone())
        return {"task": task, "existing_claim": False, **_summary(db)}


def update(path: Path, actor: str, task: str, token: str, action: str, note: str = ""):
    if action not in {"renew", "release", "finish"}:
        raise QueueError("unknown claim action")
    if action in {"release", "finish"}:
        _bounded(note, "result or handoff note", 1000)
    with transaction(path) as db:
        _peer(db, actor)
        now = time.time()
        row = db.execute("SELECT * FROM tasks WHERE id=?", (task,)).fetchone()
        if not row or row["state"] != "running" or row["owner"] != actor or row["token"] != token or row["expires"] <= now:
            raise QueueError("claim is absent, expired, or superseded; inspect status and claim again")
        if action == "renew":
            db.execute("UPDATE tasks SET expires=? WHERE id=?", (now + LEASE_SECONDS, task))
        elif action == "release":
            db.execute("UPDATE tasks SET state='ready', previous_owner=owner, owner=NULL, token=NULL, "
                       "expires=NULL, result=? WHERE id=?", (note, task))
        else:
            db.execute("UPDATE tasks SET state='done', token=NULL, expires=NULL, result=? WHERE id=?", (note, task))
        _event(db, actor, action, task, note=note)
        return {"task": task, "action": action, **_summary(db)}


def inspect(path: Path, *, offset: int = 0):
    try:
        with transaction(path) as db:
            _expire(db, time.time())
            summary = _summary(db)
            # Never expose other peers' fencing tokens or dump the entire ledger.
            summary["tasks"] = [dict(r) for r in db.execute(
                "SELECT id, title, state, owner, expires FROM tasks ORDER BY created, id LIMIT 20 OFFSET ?", (max(0, offset),))]
            summary["next_offset"] = offset + 20 if summary["total"] > offset + 20 else None
            summary["events"] = dict(db.execute("SELECT kind, COUNT(*) FROM events GROUP BY kind"))
            return summary
    except (OSError, sqlite3.Error) as error:
        return {"status": "unavailable", "error": str(error)}


def install(ws: Path, agents: list[dict]) -> Path:
    directory = ws / "work" / ".murmur"
    directory.mkdir(parents=True, exist_ok=True)
    helper = directory / "work_queue.py"
    shutil.copyfile(__file__, helper)
    initialize(directory / "work_queue.sqlite3", agents)
    return helper


def instructions(helper: Path) -> str:
    command = f"{shlex.quote(sys.executable)} {shlex.quote(str(helper))}"
    return f"""Experimental work stealing is enabled. The shared queue is the authoritative task claim table.
Use `{command} add ID TITLE DETAIL [--after EXISTING_ID]` to publish bounded units of unfinished work;
any peer can publish, including units another peer can take. Use `{command} next` before taking a unit
and again before finishing your turn. It atomically assigns one ready unit, with a fencing token.
Work only on your active unit; if recovering another peer's expired/released unit, first inspect their
pushed work and handoff note. Claims fence queue updates, not git/filesystem writes.
Use `{command} renew ID TOKEN` before the 15-minute lease expires while working.
After integrating the result, use `{command} finish ID TOKEN RESULT` with a brief evidence pointer;
use `release ID TOKEN HANDOFF` to make unfinished work immediately claimable by another peer.
`next` returns task=null only if no work is currently ready; read running/waiting counts, and remain
available while unfinished work exists. Use `{command} status` for a bounded queue summary.
The run cannot report successful completion with an unused or unfinished queue. Queue completion
records declared work, not independent proof that the user's entire objective is correct."""


def main():
    parser = argparse.ArgumentParser(description="Internal murmur work queue")
    sub = parser.add_subparsers(dest="action", required=True)
    p = sub.add_parser("add")
    p.add_argument("id")
    p.add_argument("title")
    p.add_argument("detail")
    p.add_argument("--after", action="append", default=[])
    sub.add_parser("next")
    p = sub.add_parser("status")
    p.add_argument("--offset", type=int, default=0)
    for action in ("renew", "release", "finish"):
        p = sub.add_parser(action)
        p.add_argument("id")
        p.add_argument("token")
        if action != "renew":
            p.add_argument("note")
    args = parser.parse_args()
    path = Path(__file__).with_name("work_queue.sqlite3")
    try:
        if args.action == "status":
            result = inspect(path, offset=args.offset)
        else:
            with transaction(path) as db:
                cwd = Path.cwd().resolve()
                peer = next((r["id"] for r in db.execute("SELECT * FROM peers")
                             if cwd.is_relative_to(Path(r["clone"]))), None)
            if peer is None:
                raise QueueError("run this helper inside your own peer clone")
            if args.action == "add":
                result = add(path, peer, args.id, args.title, args.detail, args.after)
            elif args.action == "next":
                result = claim(path, peer)
            else:
                result = update(path, peer, args.id, args.token, args.action, getattr(args, "note", ""))
        print(json.dumps(result, sort_keys=True))
        return 1 if result.get("status") == "unavailable" else 0
    except (QueueError, OSError, sqlite3.Error) as error:
        print(json.dumps({"error": str(error)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
