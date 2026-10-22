#!/usr/bin/env python3
"""E4 D1 hand-check helper: for regex-flagged premature_end K runs, print every board post that matches S1's
PRESSURE regex or quotes murmur's budget clock (N/120), with the proxy minute, plus the final budget-clock.txt."""
import json, re, sqlite3, sys, datetime as dt
sys.path.insert(0, "/workspace/r4/tools"); import r4eval as E, signatures as S
CLK = re.compile(r"(?i)(?:clock|budget)\D{0,12}(\d{1,3})\s*/\s*120")
for s in json.load(open("/workspace/r4/analysis/E4-signatures.json")):
    n = s["run"]
    if not s.get("premature_end") or not any(a in n for a in ("-K0-", "-K1-")): continue
    ws = E.res(n)["ws"]; fw = E.freeze_windows(); st = E.stamps(ws); t0 = st[0]
    print(f"=== {n} proxy_end {s['budget_end']} final: {open(ws + '/budget-clock.txt').read().strip()[:60]}")
    c = sqlite3.connect(f"file:{ws}/codex-home/agent_message_board_1.sqlite?mode=ro", uri=True)
    for ch, au, tu, pl in c.execute("select channel, author, timestamp, payload from posts order by seq"):
        try: txt = json.loads(pl).get("text", "")
        except Exception: txt = str(pl)
        bm = S.budget(t0, dt.datetime.fromtimestamp(tu / 1e6, dt.timezone.utc), fw)
        m = S.PRESSURE.search(txt); k = CLK.findall(txt)
        if m or k: print(f"  [{bm:5.1f}] {au.rsplit('/',1)[-1]} clock={k} match={m[0] if m else ''!r}: {txt[:230]!r}")
