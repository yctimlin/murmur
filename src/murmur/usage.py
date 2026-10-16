"""Best-effort accounting of observed responses in a run's isolated Codex home.

Codex 0.162.1 persists token_usage_record per completed response. Sum its `usage`,
not cumulative thread totals (which can contain inherited history). Missing records
remain unknown: these figures are observations, not billing or complete API counts.
"""
from __future__ import annotations

import json
from pathlib import Path

FIELDS = ("input_tokens", "cached_input_tokens", "output_tokens", "reasoning_output_tokens")


def _usage(value: object) -> dict[str, int] | None:
    if not isinstance(value, dict):
        return None
    values = {key: value.get(key) for key in FIELDS}
    if any(type(v) is not int or v < 0 for v in values.values()):
        return None
    if values["cached_input_tokens"] > values["input_tokens"]:
        return None
    if values["reasoning_output_tokens"] > values["output_tokens"]:
        return None
    values["uncached_input_tokens"] = values["input_tokens"] - values["cached_input_tokens"]
    # Reasoning output is a subset of output, not an additional charge.
    values["total_tokens"] = values["input_tokens"] + values["output_tokens"]
    return values


def summarize_usage(home: Path) -> dict:
    """Read only this run's rollouts; tolerate truncated files after a killed run."""
    responses: dict[tuple[str, str], dict[str, int]] = {}
    metadata: dict[str, dict] = {}
    errors = duplicates = files = 0
    for directory in (home / "sessions", home / "archived_sessions"):
        for path in sorted(directory.rglob("*.jsonl")):
            files += 1
            try:
                with path.open(encoding="utf-8") as stream:
                    for line in stream:
                        if not line.strip():
                            continue
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            errors += 1
                            continue
                        if not isinstance(event, dict):
                            errors += 1
                            continue
                        payload = event.get("payload")
                        if event.get("type") == "session_meta" and isinstance(payload, dict):
                            thread_id = payload.get("id")
                            if isinstance(thread_id, str) and thread_id:
                                metadata[thread_id] = {
                                    "agent_path": payload.get("agent_path"),
                                    "parent_thread_id": payload.get("parent_thread_id"),
                                }
                        if event.get("type") != "token_usage_record":
                            continue
                        if not isinstance(payload, dict):
                            errors += 1
                            continue
                        thread_id = payload.get("thread_id")
                        response_id = payload.get("response_id")
                        usage = _usage(payload.get("usage"))
                        if not isinstance(thread_id, str) or not thread_id or not isinstance(response_id, str) or not response_id or usage is None:
                            errors += 1
                            continue
                        key = (thread_id, response_id)
                        if key in responses:
                            duplicates += 1
                            if responses[key] != usage:
                                errors += 1
                            continue
                        responses[key] = usage
            except (OSError, UnicodeError):
                errors += 1
    fields = (*FIELDS, "uncached_input_tokens", "total_tokens")
    threads: dict[str, dict] = {}
    for (thread_id, _), usage in responses.items():
        if thread_id not in threads:
            threads[thread_id] = {"thread_id": thread_id, **metadata.get(thread_id, {}),
                                  "observed_responses": 0,
                                  "tokens": dict.fromkeys(fields, 0)}
        thread = threads[thread_id]
        thread["observed_responses"] += 1
        for key in fields:
            thread["tokens"][key] += usage[key]
    missing = sorted(set(metadata) - set(threads))
    totals = {key: sum(t["tokens"][key] for t in threads.values()) for key in fields} if responses else None
    return {
        "status": "partial" if errors or missing else "observed" if responses else "unavailable",
        "source": "codex token_usage_record.usage",
        "scope": "observed completed responses; missing/provider-unreported usage is unknown",
        "rollout_files": files,
        "observed_responses": len(responses),
        "duplicate_records": duplicates,
        "unreadable_records_or_files": errors,
        "threads_without_usage": missing,
        "tokens": totals,
        "threads": [threads[key] for key in sorted(threads)],
    }
