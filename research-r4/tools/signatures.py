#!/usr/bin/env python3
"""E4 mechanism signatures (prereg/E4.md S1-S3) per run, from raw rollouts + board sqlite.
usage: signatures.py RUN [RUN...]  |  signatures.py E4   (all finished E4-* runs) -> analysis/E4-signatures.json
Budget minute of an event = wall time since the first event minus heartbeat freeze overlap (proxy for murmur's
monotonic cap clock). S1: time-pressure posts before budget minute 90, and whether the team ended within 10 budget
minutes after one (premature END episode). S2: peer turns ending before 2 budget min after the peer's start; posts
or messages addressed to /root. S3 (K1): verify-channel posts, ledger.py calls, final row status."""
import json, os, re, sys, glob, sqlite3, subprocess, datetime as dt
sys.path.insert(0, os.path.dirname(__file__))
import r4eval as E

PRESSURE = re.compile(r"(?i)hard cap|min(ute)?s? (left|remaining)|time (left|remaining)|out of time|running out|hurry|before the cap|past .{0,10}cap")

def ts(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))

def budget(t0, t, fw):
    g = (t - t0).total_seconds() - sum(max(0, (min(t, b) - max(t0, a)).total_seconds()) for a, b in fw)
    return round(max(g, 0) / 60, 1)

def rollouts(ws):
    out = {}
    for f in glob.glob(f"{ws}/codex-home/sessions/**/rollout*.jsonl", recursive=True):
        first = open(f, errors="replace").readline()
        m = re.search(r'"agent_path":"([^"]+)"', first)
        out[m[1].rsplit("/", 1)[-1] if m else "root"] = f
    return out

def run_sig(n):
    r = E.res(n); ws = r.get("ws"); fw = E.freeze_windows()
    if not ws or not os.path.isdir(ws): return {"run": n, "error": "no ws"}
    stamps = E.stamps(ws); t0, tend = stamps[0], stamps[-1]
    sig = {"run": n, "budget_end": budget(t0, tend, fw), "pressure_posts": [], "early_quits": [], "to_root": 0,
           "peer_ends": {}, "ledger_calls": 0}
    for who, f in rollouts(ws).items():
        if who == "root": continue
        first = None
        for l in open(f, errors="replace"):
            try: d = json.loads(l)
            except Exception: continue
            t = d.get("timestamp"); p = d.get("payload") or {}
            if not t: continue
            t = ts(t); first = first or t
            if p.get("type") == "task_complete":
                sig["peer_ends"].setdefault(who, []).append(budget(t0, t, fw))
                if budget(first, t, fw) < 2: sig["early_quits"].append(who)
            if d.get("type") == "response_item" and p.get("type") in ("function_call", "custom_tool_call"):
                a = str(p.get("arguments") or p.get("input") or "")
                if re.search(r'"/root"|\x27/root\x27|agents_to_notify:\s*\[[^\]]*"/root"\]', a): sig["to_root"] += 1
                sig["ledger_calls"] += a.count("ledger.py")
    db = f"{ws}/codex-home/agent_message_board_1.sqlite"
    posts = []
    if os.path.exists(db):
        c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        for ch, au, tu, pl in c.execute("select channel, author, timestamp, payload from posts order by seq"):
            try: txt = json.loads(pl).get("text", "")
            except Exception: txt = str(pl)
            t = dt.datetime.fromtimestamp(tu / 1e6, dt.timezone.utc); bm = budget(t0, t, fw)
            posts.append((ch, au.rsplit("/", 1)[-1], bm, txt))
            if PRESSURE.search(txt) and bm < 90: sig["pressure_posts"].append({"by": au.rsplit("/", 1)[-1], "budget_min": bm, "text": txt[:160]})
    sig["premature_end"] = any(sig["budget_end"] - p["budget_min"] <= 10 for p in sig["pressure_posts"])
    if os.path.exists(f"{ws}/ledger.py"):
        v = [p for p in posts if p[0] == "verify"]
        sig["verify_posts"] = len(v)
        sig["verify_verbs"] = {k: sum(1 for p in v if p[3].lstrip().startswith(k)) for k in ("VERIFIED", "FAIL", "N/A", "DESCOPED", "HANDOFF")}
        out = subprocess.run([sys.executable, f"{ws}/ledger.py"], capture_output=True, text=True).stdout
        sig["ledger_final"] = out.strip().splitlines()[-1] if out.strip() else "error"
    return sig

if __name__ == "__main__":
    args = sys.argv[1:]
    if args == ["E4"]:
        res = [run_sig(n) for n in E.finished("E4")]
        json.dump(res, open(f"{E.R}/analysis/E4-signatures.json", "w"), indent=1)
        for s in res: print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in s.items() if k != "peer_ends"}))
    else:
        for n in args: print(json.dumps(run_sig(n), indent=1))
