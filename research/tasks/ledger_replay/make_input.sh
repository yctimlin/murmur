#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 - <<'PY'
from pathlib import Path
root=Path('input')
if root.exists():
    raise SystemExit('input already exists; remove it explicitly before regenerating')
(root/'ledger').mkdir(parents=True)
(root/'tests').mkdir()
(root/'ledger'/'__init__.py').write_text('from .core import Ledger, LedgerError\n')
(root/'ledger'/'core.py').write_text('''"""In-memory event ledger; replay support is incomplete."""
from .money import parse_amount, format_amount

class LedgerError(ValueError):
    pass

class Ledger:
    def __init__(self):
        self.accounts = {}
        self.events = []
        self.last_seq = 0

    def apply(self, event):
        kind = event["type"]
        account = event.get("account")
        if kind == "open":
            self.accounts[account] = {"currency": event["currency"], "balance": 0.0, "closed": False}
        elif kind == "deposit":
            self.accounts[account]["balance"] += parse_amount(event["amount"])
        elif kind == "withdraw":
            self.accounts[account]["balance"] -= parse_amount(event["amount"])
        else:
            raise LedgerError("unsupported event type")
        self.events.append(event)
        self.last_seq = event["seq"]
        return True

    def apply_many(self, events):
        return sum(self.apply(event) for event in events)

    def balance(self, account_id):
        return format_amount(self.accounts[account_id]["balance"])

    def snapshot(self):
        return {"version": 1, "last_seq": self.last_seq, "accounts": self.accounts, "events": self.events}

    @classmethod
    def from_events(cls, events):
        ledger = cls()
        ledger.apply_many(events)
        return ledger

    @classmethod
    def from_snapshot(cls, snapshot):
        return cls.from_events(snapshot["events"])
''')
(root/'ledger'/'money.py').write_text('''def parse_amount(value):
    return float(value)

def format_amount(value):
    return f"{value:.2f}"
''')
(root/'ledger'/'__main__.py').write_text('''import argparse
import json
from pathlib import Path
from . import Ledger

parser = argparse.ArgumentParser()
parser.add_argument("command", choices=["replay"])
parser.add_argument("events")
parser.add_argument("--snapshot")
args = parser.parse_args()
ledger = Ledger.from_events(json.loads(line) for line in Path(args.events).read_text().splitlines())
result = json.dumps(ledger.snapshot(), sort_keys=True)
if args.snapshot:
    Path(args.snapshot).write_text(result + "\\n")
print(result)
''')
(root/'tests'/'test_smoke.py').write_text('''import unittest
from ledger import Ledger

class Smoke(unittest.TestCase):
    def test_open_and_deposit(self):
        ledger=Ledger()
        ledger.apply({"id":"a","seq":1,"type":"open","account":"cash","currency":"USD"})
        ledger.apply({"id":"b","seq":2,"type":"deposit","account":"cash","amount":"12.50"})
        self.assertEqual(ledger.balance("cash"),"12.50")
''')
(root/'pyproject.toml').write_text('''[project]
name = "offline-ledger"
version = "0.1.0"
requires-python = ">=3.11"
''')
(root/'README.md').write_text('''# Offline event ledger
A minimal event ledger with a replay command. The initial implementation only supports
basic open/deposit/withdraw flows. Complete the public contract in the task brief.

Run the local suite with `python -m unittest discover -s tests`.
Run `python -m ledger replay examples.jsonl` from this folder. No dependencies are needed.
''')
(root/'examples.jsonl').write_text('{"id":"a","seq":1,"type":"open","account":"cash","currency":"USD"}\n{"id":"b","seq":2,"type":"deposit","account":"cash","amount":"12.50"}\n')
(root/'.gitignore').write_text('__pycache__/\n*.pyc\n')
PY
cd input
git init -q -b main
git config user.name 'Task Fixture'
git config user.email 'fixture@example.invalid'
git add .
GIT_AUTHOR_DATE='2025-01-01T00:00:00Z' GIT_COMMITTER_DATE='2025-01-01T00:00:00Z' git commit -qm 'Initial ledger implementation'
