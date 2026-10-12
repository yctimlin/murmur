"""Small shared helpers."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from murmur.errors import fail

DURATION_RE = re.compile(r"^(\d+)([smh])$")


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def seconds(duration: str) -> int:
    match = DURATION_RE.match(duration)
    if not match:
        fail(f"bad duration {duration!r} (use e.g. 45m or 3h)")
    return int(match[1]) * {"s": 1, "m": 60, "h": 3600}[match[2]]


def toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, list):
        return "[" + ", ".join(toml_value(item) for item in value) + "]"
    if isinstance(value, dict):
        pairs = (f"{json.dumps(key)} = {toml_value(item)}" for key, item in value.items())
        return "{" + ", ".join(pairs) + "}"
    raise TypeError(f"cannot write {type(value).__name__} as TOML")
