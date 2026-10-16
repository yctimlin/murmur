#!/usr/bin/env python3
"""Export a screen's observed timing, tokens and mechanism evidence without model calls.

Run from a checkout: python scripts/audit_screen.py WORKSPACE --kind live --section review
`kind` is the operator's declaration, not inferred proof of a live/fake backend.
No success/quality verdict is inferred from a process exit or a populated evidence section.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from murmur.usage import summarize_usage


def _read(path: Path, errors: list[str]) -> dict:
    try:
        value = json.loads(path.read_text())
        if not isinstance(value, dict):
            raise ValueError("expected a JSON object")
        return value
    except (OSError, ValueError) as exc:
        errors.append(f"{path.name}: {exc}")
        return {}


def _fingerprint(path: Path) -> str | None:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def audit(workspace: Path, *, kind: str, sections: list[str]) -> dict:
    errors: list[str] = []
    meta_path = workspace / "murmur.json"
    record_path = workspace / "logs" / "run.json"
    meta = _read(meta_path, errors)
    record = _read(record_path, errors)
    usage = summarize_usage(workspace / "codex-home")
    stored_usage = record.get("usage")
    if isinstance(stored_usage, dict):
        agree = stored_usage.get("tokens") == usage["tokens"]
        if not agree:
            errors.append("run.json usage differs from current rollout observations")
    else:
        agree = None
    evidence = {key: record.get(key) for key in sections}
    for key, value in evidence.items():
        if value is None:
            errors.append(f"run.json has no mechanism evidence section {key!r}")
    result = record.get("result")
    result = result if isinstance(result, dict) else {}
    return {
        "workspace": str(workspace.resolve()),
        "declared_kind": kind,
        "kind_verified": False,
        "run_id": meta.get("run_id"),
        "peers": meta.get("peers"),
        "cap": meta.get("cap"),
        "base": meta.get("base"),
        "delivered_head": result.get("head"),
        "started_at": record.get("started_at"),
        "ended_at": record.get("ended_at"),
        "wall_seconds": record.get("seconds"),
        "exit_code": record.get("exit_code"),
        "codex_exit_code": record.get("codex_exit_code"),
        "capped": record.get("capped"),
        "interrupted": record.get("interrupted"),
        "usage": usage,
        "usage_matches_run_record": agree,
        "mechanism_evidence": evidence,
        "source_sha256": {"murmur.json": _fingerprint(meta_path),
                          "logs/run.json": _fingerprint(record_path)},
        "errors": errors,
        "limits": "Observed telemetry only. Missing tokens stay unknown, including fixtures. "
                  "No model quality, causal speedup, mechanism activation, or complete billing inferred.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--kind", choices=("live", "fixture"), required=True)
    parser.add_argument("--section", action="append", default=[], help="run.json mechanism evidence key")
    args = parser.parse_args()
    report = audit(args.workspace, kind=args.kind, sections=args.section)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
