#!/usr/bin/env python3
"""Backfill the auxiliary mutation score (tools/mutation.py = r3 sealed scorer, n=30 seed=3) into result.json of
finished runs whose mutation step failed (AMENDMENT-4). Sequential, low priority. usage: backfill_mutation.py LAB"""
import glob, json, os, subprocess, sys, datetime as dt
L = sys.argv[1]; T = os.path.dirname(os.path.abspath(__file__))
SETUP = "python3 -m venv .venv && .venv/bin/pip install -q pytest"
for f in sorted(glob.glob(f"{L}/results/*/result.json")):
    r = json.load(open(f)); exp = os.path.join(os.path.dirname(f), "delivered")
    if r.get("mutation") or not os.path.isdir(exp): continue
    m = subprocess.run(["nice", "-n", "19", sys.executable, f"{T}/mutation.py", exp, "30", "3", SETUP], capture_output=True, text=True, timeout=5400)
    r = json.load(open(f))  # re-read: never clobber concurrent writers
    try: r["mutation"] = json.loads(m.stdout.strip().splitlines()[-1]); r["mutation_backfilled"] = dt.datetime.now().isoformat()
    except Exception: r["mutation_backfill_error"] = f"exit {m.returncode}: {m.stderr[-300:]}"
    json.dump(r, open(f + ".tmp", "w"), indent=1); os.replace(f + ".tmp", f)
    print(os.path.basename(os.path.dirname(f)), r.get("mutation") or r.get("mutation_backfill_error"), flush=True)
