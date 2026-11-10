"""Token usage per agent, summed from the Codex rollouts of one run.

Every Codex session (the root and each peer) writes a rollout under
`<workspace>/codex-home/sessions/`. Its `token_count` events carry a running
`total_token_usage`, so the last one in a file is that session's total. Sessions are
named the way `skills/murmur/scripts/status` names them: the session that calls
`spawn_agent` is the root, and a peer is the one whose tool calls mention its
`prompts/<id>.md`. That script runs on its own, outside murmur's environment, so it
keeps its own copy of these rules.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

PROMPT_RE = re.compile(r"prompts/(\w+)\.md")
FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "total_tokens")
UNKNOWN = "root?"


def _events(rollout: Path):
    # A session that was stopped mid-write can leave a partial last line.
    with rollout.open(encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(event, dict):
                yield event


def _count(value) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def session_usage(rollout: Path) -> tuple[str, dict[str, int]]:
    """The agent a rollout belongs to and its final token totals."""
    name, usage = UNKNOWN, {}
    for event in _events(rollout):
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        kind = event.get("type")
        if kind == "response_item" and payload.get("type") in ("function_call", "custom_tool_call"):
            if name == UNKNOWN and payload.get("name") == "spawn_agent":
                name = "root"
            match = PROMPT_RE.search(str(payload.get("arguments") or payload.get("input") or ""))
            if name == UNKNOWN and match:
                name = match[1]
        elif kind == "event_msg" and payload.get("type") == "token_count":
            info = payload.get("info")
            total = info.get("total_token_usage") if isinstance(info, dict) else None
            if isinstance(total, dict):
                usage = total
    return name, {field: _count(usage.get(field)) for field in FIELDS}


def run_usage(ws: Path, solo: bool = False, order: list[str] | None = None) -> dict | None:
    """Tokens per agent and in total for a workspace, or None when there are no rollouts.

    Agents are listed root first, then in `order`, then any others by name.
    """
    rollouts = sorted((ws / "codex-home" / "sessions").rglob("*.jsonl"))
    if not rollouts:
        return None
    agents: dict[str, dict[str, int]] = {}
    for rollout in rollouts:
        try:
            name, usage = session_usage(rollout)
        except OSError:
            continue  # an unreadable log must not keep run.json from being written
        if solo:
            name = "solo"
        into = agents.setdefault(name, dict.fromkeys(FIELDS, 0))
        for field in FIELDS:
            into[field] += usage[field]
    rank = {name: index for index, name in enumerate(["root", *(order or [])])}
    agents = dict(sorted(agents.items(), key=lambda item: (rank.get(item[0], len(rank)), item[0])))
    total = {field: sum(agent[field] for agent in agents.values()) for field in FIELDS}
    return {"total": total, "agents": agents}


def describe(usage: dict[str, int]) -> str:
    """One line for a usage dict. Codex counts cached input inside input_tokens."""
    return (f"{usage['input_tokens']:,} input ({usage['cached_input_tokens']:,} cached), "
            f"{usage['output_tokens']:,} output")


def summary_lines(tokens: dict | None) -> list[str]:
    if tokens is None:
        return ["tokens: no Codex session logs found"]
    names = list(tokens["agents"])
    width = max(map(len, names), default=0)
    lines = [f"tokens: {describe(tokens['total'])}"]
    if len(names) > 1:
        lines += [f"  {name:<{width}}  {describe(tokens['agents'][name])}" for name in names]
    return lines
