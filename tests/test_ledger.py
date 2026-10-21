"""The requirements ledger: rows from the brief, closed only by their verifier."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from murmur import ledger
from support import setup_workspace

BRIEF = """# Title

Intro sentence. We need two things! Python 3.12, offline.

- export to `ics`
- import CSV files

```
code that is skipped.
```
1. Numbered item. With two sentences.
"""


def test_rows_follow_sentences_and_bullets():
    assert ledger.brief_rows(BRIEF) == [
        "Intro sentence.", "We need two things!", "Python 3.12, offline.",
        "export to `ics`", "import CSV files", "Numbered item.", "With two sentences.",
    ]
    rows = ledger.build(BRIEF, ["a1", "a2", "a3"])["rows"]
    assert [r["verifier"] for r in rows[:4]] == ["a2", "a3", "a1", "a2"]


def test_only_the_verifier_closes_and_handoff_moves_a_row():
    led = ledger.build("One. Two. Three.", ["a1", "a2"])  # R1 a2, R2 a1, R3 a2
    posts = [
        ("a1", "VERIFIED R1 ran it"),          # not R1's verifier: ignored
        ("a2", "VERIFIED R1, R3 ran `x` -> ok"),
        ("a2", "FAIL R3 crashes on empty input"),
        ("a1", "HANDOFF R2 a2"),
        ("a2", "N/A R2 context only"),
        ("a1", "unrelated post"),
    ]
    state = ledger.status(led, posts, ["a1", "a2"])
    assert {k: v["status"] for k, v in state.items()} == {"R1": "VERIFIED", "R2": "N/A", "R3": "FAIL"}
    assert state["R2"]["verifier"] == "a2"


def test_setup_writes_ledger_and_script_reads_the_board(tmp_path: Path):
    ws = setup_workspace(tmp_path, "--peers", "2")
    data = json.loads((ws / "ledger.json").read_text())
    assert data["ids"] == ["a1", "a2"] and data["rows"][0]["text"] == "Do the thing."
    assert "python3 " + str(ws / "ledger.py") in (ws / "prompts" / "a1.md").read_text()
    db = ws / "codex-home" / "agent_message_board_1.sqlite"
    con = sqlite3.connect(db)
    con.execute("create table posts (seq integer primary key, channel text, author text, payload text)")
    con.execute("insert into posts (channel, author, payload) values ('verify', '/root/a2', ?)",
                (json.dumps({"text": "VERIFIED R1 ran it"}),))
    con.commit()
    con.close()
    out = subprocess.run([sys.executable, str(ws / "ledger.py")], capture_output=True, text=True, check=True).stdout
    assert "VERIFIED" in out and "0 of 1 rows not closed" in out
