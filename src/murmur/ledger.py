"""Requirements ledger for a swarm: rows taken from the brief, each closed only by its assigned verifier.

murmur writes `ledger.json` next to a copy of this file when it sets up a swarm. The agents run the
copy (`python3 <ws>/ledger.py`) to see which rows are still open. Status is computed from the posts in
the `verify` channel of the message board, whose author field is set by Codex, not by the agents.
"""

from __future__ import annotations

import json
import re
import sqlite3
import sys
from pathlib import Path

CHANNEL = "verify"
CLOSED = ("VERIFIED", "N/A", "DESCOPED")
VERBS = (*CLOSED, "FAIL", "HANDOFF")
_POST = re.compile(r"^\s*(VERIFIED|FAIL|N/A|DESCOPED|HANDOFF)\s+((?:R\d+\s*,\s*)*R\d+)\b(.*)", re.S)
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9`\"'(\[*_])")


def brief_rows(brief: str) -> list[str]:
    """Split a brief into rows: one per bullet item and one per prose sentence; headings and code are skipped."""
    rows: list[str] = []
    paragraph: list[str] = []
    in_code = False

    def flush() -> None:
        text = " ".join(paragraph).strip()
        paragraph.clear()
        rows.extend(s.strip() for s in _SENTENCE_END.split(text) if s.strip())

    for line in brief.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            flush()
            in_code = not in_code
            continue
        if in_code:
            continue
        if not stripped or stripped.startswith("#"):
            flush()
        elif re.match(r"([-*+]|\d+[.)])\s+", stripped):
            flush()
            paragraph.append(re.sub(r"^([-*+]|\d+[.)])\s+", "", stripped))
        else:
            paragraph.append(stripped)
    flush()
    return rows


def build(brief: str, ids: list[str]) -> dict:
    """Rows with their verifier: row k goes to ids[k % n], so the work is spread by rotation."""
    rows = brief_rows(brief)
    return {"rows": [{"id": f"R{k}", "text": text, "verifier": ids[k % len(ids)]} for k, text in enumerate(rows, 1)]}


def parse(text: str) -> tuple[str, list[str], str] | None:
    match = _POST.match(text)
    if not match:
        return None
    return match[1], re.findall(r"R\d+", match[2]), match[3].strip()


def status(ledger: dict, posts: list[tuple[str, str]], ids: list[str]) -> dict[str, dict]:
    """Replay (author, text) posts in order. Only the current verifier of a row can close or fail it;
    HANDOFF moves a row to another peer and may come from its verifier or, if that peer stopped, anyone."""
    state = {r["id"]: {"verifier": r["verifier"], "status": "OPEN", "note": ""} for r in ledger["rows"]}
    for author, text in posts:
        parsed = parse(text)
        if not parsed:
            continue
        verb, row_ids, rest = parsed
        for rid in row_ids:
            row = state.get(rid)
            if row is None:
                continue
            if verb == "HANDOFF":
                target = rest.split()[0] if rest.split() else ""
                if target in ids and target != row["verifier"]:
                    row.update(verifier=target, status="OPEN", note=f"handed off by {author}")
            elif author == row["verifier"]:
                row.update(status=verb, note=rest[:120])
    return state


def _board_posts(home: Path) -> list[tuple[str, str]]:
    posts: list[tuple[str, str]] = []
    for db in sorted(home.glob("agent_message_board_*.sqlite")):
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        try:
            rows = con.execute("select author, payload from posts where channel = ? order by seq", (CHANNEL,))
            for author, payload in rows:
                try:
                    text = json.loads(payload).get("text", "")
                except (ValueError, AttributeError):
                    text = str(payload)
                posts.append((author.rsplit("/", 1)[-1], text))
        finally:
            con.close()
    return posts


def main() -> None:
    here = Path(__file__).resolve().parent
    ledger = json.loads((here / "ledger.json").read_text())
    ids = ledger["ids"]
    state = status(ledger, _board_posts(Path(ledger["codex_home"])), ids)
    who = sys.argv[1] if len(sys.argv) > 1 else None
    open_rows = [r for r in ledger["rows"] if state[r["id"]]["status"] not in CLOSED]
    for r in ledger["rows"]:
        s = state[r["id"]]
        if who and s["verifier"] != who:
            continue
        print(f"{r['id']:>5} {s['status']:<9} {s['verifier']:<4} {r['text'][:110]}")
    counts = {v: sum(1 for s in state.values() if s["status"] == v) for v in ("OPEN", "FAIL", *CLOSED)}
    print(f"\n{len(open_rows)} of {len(state)} rows not closed: " + ", ".join(f"{k} {v}" for k, v in counts.items()))


if __name__ == "__main__":
    main()
