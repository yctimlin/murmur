"""Codex `PreToolUse` hook for a swarm: the launcher's peers start without its conversation.

`spawn_agent` copies the caller's whole conversation into the new agent unless the call sets
`fork_turns` to "none", and Codex has no setting that changes this default. A peer that
inherits the launcher's conversation carries the launcher's instructions on every request
and can take them for its own. The launcher's prompt asks for "none"; this hook makes it so
whatever the model sends.

Codex runs this file before every `spawn_agent` call, with the call as JSON on stdin. For a
call from the launcher it answers with the same arguments and `fork_turns` set to "none".
It leaves every other call alone: a peer that spawns helpers of its own keeps Codex's
default. It never blocks a call. Given input it does not understand it prints nothing, and
Codex then runs the call unchanged.

`murmur setup` copies this file into the workspace and Codex runs the copy, so it uses only
the standard library.
"""

from __future__ import annotations

import json
import sys


def rewrite(event) -> dict | None:
    """The hook's answer to one `PreToolUse` event, or None to leave the call as it is."""
    if not isinstance(event, dict):
        return None
    # Codex adds `agent_id` to the events of a spawned agent. The launcher's have none.
    if event.get("agent_id"):
        return None
    # The name carries the tool's namespace as a prefix, e.g. `collaborationspawn_agent`.
    if not str(event.get("tool_name") or "").endswith("spawn_agent"):
        return None
    arguments = event.get("tool_input")
    if not isinstance(arguments, dict) or arguments.get("fork_turns") == "none":
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {**arguments, "fork_turns": "none"},
        }
    }


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except ValueError:
        return 0
    answer = rewrite(event)
    if answer is not None:
        json.dump(answer, sys.stdout)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
