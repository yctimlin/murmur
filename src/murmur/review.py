"""Independent review receipts for changed paths (experimental, opt-in).

This file is also copied into a run so peers need no installed murmur package.
The ledger is coordination state, not a security boundary against hostile peers.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import sqlite3
import subprocess
import sys
import time


class ReviewError(Exception):
    pass


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(["git", *args], cwd=repo, capture_output=True)
    if result.returncode:
        raise ReviewError(result.stderr.decode(errors="replace").strip())
    return result.stdout


def connect(directory: Path, *, create: bool = False) -> sqlite3.Connection:
    path = directory / "reviews.sqlite"
    db = sqlite3.connect(path if create else path.resolve().as_uri() + "?mode=rw",
                         uri=not create, timeout=20)
    db.execute("PRAGMA busy_timeout=20000")
    if not create:
        return db
    db.execute("""CREATE TABLE IF NOT EXISTS receipts (
        fingerprint TEXT NOT NULL, reviewer TEXT NOT NULL, revision TEXT NOT NULL,
        path TEXT NOT NULL, note TEXT NOT NULL, created REAL NOT NULL,
        PRIMARY KEY(fingerprint, reviewer))""")
    db.execute("""CREATE TABLE IF NOT EXISTS events (
        created REAL NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL)""")
    return db


def inventory(directory: Path) -> dict:
    config = json.loads((directory / "config.json").read_text())
    origin = Path(config["origin"])
    head = git(origin, "rev-parse", "refs/heads/main").decode().strip()
    base = config["base"]
    # A force-rewritten baseline must never silently waive the gate.
    git(origin, "merge-base", "--is-ancestor", base, head)
    changed = set(filter(None, git(origin, "diff", "--name-only", "--no-renames", "-z", base, head).split(b"\0")))
    writers: dict[bytes, set[str]] = {path: set() for path in changed}
    commits = git(origin, "log", "--topo-order", "--format=%H %ae", f"{base}..{head}").decode().splitlines()
    for commit in commits:
        sha, email = commit.split(" ", 1)
        # Compare merge commits to each parent, conservatively counting the merger.
        touched = git(origin, "diff-tree", "-m", "--root", "--no-commit-id", "--name-only", "--no-renames", "-r", "-z", sha)
        for path in touched.split(b"\0"):
            if path in writers:
                writers[path].add(email)
    tree = {}
    for entry in git(origin, "ls-tree", "-r", "-z", head).split(b"\0"):
        if entry:
            info, path = entry.split(b"\t", 1)
            tree[path] = info.decode()
    obligations = []
    for path in sorted(changed):
        authors = sorted(writers[path])
        name = os.fsdecode(path)
        # Default path-history simplification follows a TREESAME parent through
        # ordinary merges. A merger who merely imported a peer's content must not
        # replace that content's author and let its actual author self-sign.
        writer = git(origin, "log", "-1", "--format=%ae", "--no-renames",
                     f"{base}..{head}", "--", name).decode().strip()
        if not writer:
            raise ReviewError("cannot identify latest author for changed path")
        content = tree.get(path, "deleted")
        fingerprint = hashlib.sha256(json.dumps([base, name, content, writer], ensure_ascii=True).encode()).hexdigest()
        obligations.append({"path": name, "writer": writer, "authors": authors, "content": content, "fingerprint": fingerprint})
    return {"head": head, "changed_paths": len(changed), "required": obligations,
            "multi_author_paths": sum(len(authors) > 1 for authors in writers.values())}


def status(directory: Path) -> dict:
    snapshot = inventory(directory)
    with connect(directory) as db:
        receipts = {(key, reviewer) for key, reviewer in db.execute("SELECT fingerprint, reviewer FROM receipts")}
    config = json.loads((directory / "config.json").read_text())
    for item in snapshot["required"]:
        item["reviewers"] = sorted(agent["id"] for agent in config["agents"]
            if agent["email"] != item["writer"] and (item["fingerprint"], agent["id"]) in receipts)
    snapshot["pending"] = [item["path"] for item in snapshot["required"] if not item["reviewers"]]
    snapshot["complete"] = not snapshot["pending"]
    return snapshot


def attest(directory: Path, clone: Path, revision: str, paths: list[str], note: str) -> dict:
    config = json.loads((directory / "config.json").read_text())
    clone = Path(git(clone, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    agent = next((agent for agent in config["agents"] if Path(agent["clone"]).resolve() == clone), None)
    if agent is None:
        raise ReviewError("review must run from a configured peer clone")
    if not note.strip() or len(note) > 4000:
        raise ReviewError("give a nonempty review note of at most 4000 characters")
    snapshot = inventory(directory)
    if revision != snapshot["head"] or git(clone, "rev-parse", "HEAD").decode().strip() != revision:
        raise ReviewError("stale review: pull main and inspect the current revision before signing")
    if git(clone, "status", "--porcelain", "--untracked-files=no").strip():
        raise ReviewError("review requires a clean tracked worktree and index")
    by_path = {item["path"]: item for item in snapshot["required"]}
    if not paths:
        raise ReviewError("name at least one reviewed path")
    chosen = []
    for path in dict.fromkeys(paths):
        if path not in by_path:
            raise ReviewError(f"no review obligation for {path!r}")
        item = by_path[path]
        if item["writer"] == agent["email"]:
            raise ReviewError(f"self-review rejected for {path!r}; another peer must inspect it")
        chosen.append(item)
    # Receipts are content-bound, so an origin update after this snapshot cannot
    # approve a changed path accidentally. Final status computes fresh fingerprints.
    with connect(directory) as db:
        for item in chosen:
            db.execute("INSERT OR REPLACE INTO receipts VALUES (?, ?, ?, ?, ?, ?)",
                (item["fingerprint"], agent["id"], revision, item["path"], note.strip(), time.time()))
        db.execute("INSERT INTO events VALUES (?, ?, ?)", (time.time(), "attested",
            json.dumps({"reviewer": agent["id"], "revision": revision, "paths": paths})))
    return {"reviewer": agent["id"], "revision": revision, "reviewed": [item["path"] for item in chosen]}


def install(ws: Path, agents: list[dict], base: str) -> str:
    directory = ws / "work" / ".murmur-review"
    directory.mkdir()
    shutil.copyfile(__file__, directory / "review.py")
    (directory / "config.json").write_text(json.dumps({
        "origin": str(ws / "work" / "origin.git"), "base": base,
        "agents": [dict(agent, email=f"{agent['id']}@murmur.local") for agent in agents],
    }, indent=2) + "\n")
    with connect(directory, create=True) as db:
        db.execute("INSERT INTO events VALUES (?, ?, ?)", (time.time(), "installed", "{}"))
    for agent in agents:
        helper = Path(agent["clone"]) / ".murmur" / "review"
        helper.parent.mkdir(exist_ok=True)
        helper.write_text("#!/bin/sh\nexec " + shlex.quote(sys.executable) + " " +
            shlex.quote(str(directory / "review.py")) + " --directory " + shlex.quote(str(directory)) + ' "$@"\n')
        helper.chmod(0o755)
    return """Independent review is enforced for this run. Run `.murmur/review status` after
integrating and before finishing. Every changed path requires review by a peer other than its latest
change author, including paths edited by several peers. Ask another peer on the board to inspect the diff and behavior; any
peer may take the duty. Pull accepted main into a clean tracked checkout, inspect the
requested paths, then record the exact revision you inspected with:
`.murmur/review attest --revision FULL_HEAD_SHA --note 'what you checked and found' -- PATH...`
Self-review and stale or dirty checkout receipts are rejected. An unchanged path keeps its
receipt across unrelated commits; editing its contents, type, or mode invalidates it.
Use `.murmur/review check` before finishing; pending receipts make the run exit nonzero.
Review claims are coordination evidence, not proof of correctness. Fix findings and have
another peer review the resulting content before finishing. Wake a finished peer if needed.
"""


def inspect(ws: Path) -> dict:
    try:
        return status(ws / "work" / ".murmur-review")
    except (ReviewError, OSError, ValueError, TypeError, KeyError, sqlite3.Error) as error:
        return {"complete": False, "error": str(error)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    sub.add_parser("check")
    approve = sub.add_parser("attest")
    approve.add_argument("--revision", required=True)
    approve.add_argument("--note", required=True)
    approve.add_argument("paths", nargs="+")
    args = parser.parse_args()
    try:
        if args.action == "attest":
            result = attest(args.directory, Path.cwd(), args.revision, args.paths, args.note)
        else:
            result = status(args.directory)
        print(json.dumps(result, ensure_ascii=True))
        return int(args.action == "check" and not result["complete"])
    except (ReviewError, OSError, ValueError, TypeError, KeyError, sqlite3.Error) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
