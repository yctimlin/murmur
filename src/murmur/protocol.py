"""Completion protocol.

Peers stay equal. Each one writes an attestation for one commit. The launcher,
not an agent, decides whether every expected peer attested the current
`origin/main` with passing acceptance checks. A later push makes an older
attestation fail. Missing files mean the peer never started (`spawn-failed`).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from murmur.atomic import atomic_write_json
from murmur.errors import fail
from murmur.util import now

SPAWN_RETRY_LIMIT = 2
ATTEST_STATES = ("started", "blocked", "failed", "completed")
_AGENT_ID = re.compile(r"[A-Za-z0-9._-]+")


def evaluate_protocol(ws: Path, meta: dict, attempt_id: str) -> dict:
    if meta.get("mode") != "swarm":
        return {"version": 1, "complete": True, "mode": meta.get("mode"), "outcomes": {}}
    expected = [agent["id"] for agent in meta.get("agents", [])]
    head = read_head(ws)
    outcomes = {
        agent_id: classify_attestation(ws, agent_id, attempt_id, head) for agent_id in expected
    }
    complete = bool(expected) and all(item["status"] == "completed" for item in outcomes.values())
    return {
        "version": 1,
        "complete": complete,
        "head": head,
        "expected": expected,
        "outcomes": outcomes,
        "spawn_retry_limit": SPAWN_RETRY_LIMIT,
    }


def classify_attestation(ws: Path, agent_id: str, attempt_id: str, head: str | None) -> dict:
    path = ws / "protocol" / f"{agent_id}.json"
    if not path.is_file():
        return {"status": "spawn-failed"}
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return {"status": "failed", "reason": "unreadable attestation"}
    if data.get("attempt_id") != attempt_id:
        return {"status": "spawn-failed", "reason": "attestation is from another attempt"}
    state = data.get("state")
    if state in {"started", "blocked"}:
        return {"status": "blocked", "detail": state, "reason": data.get("reason") or ""}
    if state == "failed":
        return {"status": "failed", "reason": data.get("reason") or "peer failed"}
    if state != "completed":
        return {"status": "blocked", "detail": state or "missing", "reason": "no terminal state"}
    commit = data.get("commit")
    checks = data.get("checks") or []
    if not head:
        return {"status": "failed", "reason": "origin/main is unreadable", "commit": commit}
    if commit != head:
        return {
            "status": "failed",
            "reason": "attestation invalidated by a later push",
            "commit": commit,
            "head": head,
        }
    if not checks:
        return {"status": "failed", "reason": "no acceptance checks recorded", "commit": commit}
    failed = [item.get("name", "?") for item in checks if item.get("result") != "pass"]
    if failed:
        return {
            "status": "failed",
            "reason": "acceptance checks failed: " + ", ".join(failed),
            "commit": commit,
            "checks": checks,
        }
    return {"status": "completed", "commit": commit, "checks": checks}


def read_head(ws: Path) -> str | None:
    origin = ws / "work" / "origin.git"
    if not origin.exists():
        return None
    result = subprocess.run(
        ["git", "rev-parse", "main"],
        cwd=origin,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def format_outcomes(protocol: dict | None) -> str:
    if not protocol:
        return "completion protocol was not satisfied"
    if protocol.get("error"):
        return f"completion protocol was not satisfied: {protocol['error']}"
    parts = []
    for agent, item in protocol.get("outcomes", {}).items():
        status = item.get("status", "unknown")
        reason = item.get("reason")
        if reason and status != "completed":
            parts.append(f"{agent} {status} ({reason})")
        else:
            parts.append(f"{agent} {status}")
    head = protocol.get("head") or "unknown"
    return "incomplete at " + head + ": " + ", ".join(parts)


def attest(args: argparse.Namespace) -> None:
    ws = Path(args.workspace).expanduser().resolve()
    agent = args.agent
    if not _AGENT_ID.fullmatch(agent):
        fail(f"invalid agent id {agent!r}")
    state = args.state
    checks = [_parse_check(item) for item in args.check]
    if state != "completed" and (args.commit or checks):
        fail("--commit and --check are only for completed")
    if state == "completed":
        if not args.commit:
            fail("completed attestations need --commit")
        if not checks:
            fail("completed attestations need at least one --check name=pass|fail")
    attempt_path = ws / "protocol" / "attempt"
    if not attempt_path.is_file():
        fail("no active attempt; attestations are recorded during murmur run")
    attempt_id = attempt_path.read_text().strip()
    if not attempt_id:
        fail("active attempt id is empty")
    payload = {
        "version": 1,
        "agent": agent,
        "state": state,
        "commit": args.commit,
        "reason": args.reason or "",
        "checks": checks,
        "attempt_id": attempt_id,
        "updated_at": now(),
    }
    path = ws / "protocol" / f"{agent}.json"
    atomic_write_json(path, payload)
    history = ws / "protocol" / f"{agent}.history.jsonl"
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def _parse_check(item: str) -> dict:
    name, sep, result = item.partition("=")
    if not sep or not name or result not in {"pass", "fail"}:
        fail(f"bad --check {item!r} (use name=pass or name=fail)")
    return {"name": name, "result": result}


def add_attest_parser(commands) -> None:
    parser = commands.add_parser("attest", help="record one peer's completion attestation")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--agent", required=True)
    parser.add_argument("state", choices=ATTEST_STATES)
    parser.add_argument("--commit")
    parser.add_argument("--check", action="append", default=[])
    parser.add_argument("--reason", default="")
    parser.set_defaults(func=attest)
