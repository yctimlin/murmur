#!/usr/bin/env python3
"""E5 decision rule (prereg/E5.md), mechanical. usage: e5_decide.py BLOCK   (BLOCK = 1, 2 or 3 = blocks completed)
Pairs = (task, rep) with both K1F and base4F valid and judged. d_q = q(K1F) - q(base4F); r = ln(active_nf ratio).
Collapse = not delivered or q < 3.0. Writes analysis/E5-decision-b<BLOCK>.json."""
import json, math, statistics as st, sys
sys.path.insert(0, "/workspace/r4/tools"); import r4eval as ev
B = int(sys.argv[1]); T = ["T1b", "T2", "T3b", "T4b"]
rs = ev.rows("E5")
def one(t, a, k): return next((r for r in rs if r["task"] == t and r["arm"] == a and r["rep"] == k), None)
judged = lambda r: r is not None and (r["overall"] is not None or not r["delivered"])
coll = lambda r: (not r["delivered"]) or (r["overall"] is not None and r["overall"] < 3.0)
qv = lambda r: r["overall"] if r["overall"] is not None else 0.0   # undelivered = 0 (never judged)
pairs = [(t, k, one(t, "K1F", k), one(t, "base4F", k)) for t in T for k in range(1, B + 1)]
pairs = [(t, k, a, b) for t, k, a, b in pairs if judged(a) and judged(b)]
dq = [qv(a) - qv(b) for _, _, a, b in pairs]
rr = [math.log(a["active_nf"] / b["active_nf"]) for _, _, a, b in pairs if a["active_nf"] and b["active_nf"]]
cK = sum(coll(a) for _, _, a, _ in pairs); cB = sum(coll(b) for _, _, _, b in pairs)
q_ci, r_ci = ev.tint(dq), ev.tint(rr)
out = {"block": B, "n_pairs": len(pairs), "expected_pairs": 4 * B, "dq": q_ci, "r": r_ci,
       "ratio": None if r_ci[0] is None else round(math.exp(r_ci[0]), 3), "collapses_K1F": cK, "collapses_base4F": cB,
       "pairs": [{"task": t, "rep": k, "K1F": [a["overall"], a["active_nf"], a["delivered"]], "base4F": [b["overall"], b["active_nf"], b["delivered"]]} for t, k, a, b in pairs]}
reject = (q_ci[2] is not None and q_ci[2] < 0) or (r_ci[1] is not None and r_ci[1] > 0) or (cK - cB >= 2)
if B < 3:
    keep = B == 2 and q_ci[0] >= 0 and q_ci[1] is not None and q_ci[1] >= -0.5 and cK <= cB and r_ci[2] is not None and r_ci[2] <= 0
    out["decision"] = "STOP-REJECT (keep base4F)" if reject else "STOP-KEEP K1F" if keep else "CONTINUE"
else:
    keep = q_ci[0] >= 0 and q_ci[1] is not None and q_ci[1] >= -1.0 and cK <= cB and out["ratio"] is not None and out["ratio"] <= 1.0
    out["decision"] = "KEEP K1F" if keep else "keep base4F"
arms = ("base4F", "K1F", "solo")
def med(xs): xs = [x for x in xs if x is not None]; return st.median(xs) if xs else None
out["per_arm"] = {a: {"n": sum(r["arm"] == a for r in rs), "mean_q": ev.tint([r["overall"] for r in rs if r["arm"] == a]),
                      "collapses": sum(coll(r) for r in rs if r["arm"] == a and judged(r)),
                      "median_active_nf": med([r["active_nf"] for r in rs if r["arm"] == a]),
                      "median_input_M": med([(r.get("input") or 0) / 1e6 for r in rs if r["arm"] == a])} for a in arms}
json.dump(out, open(f"/workspace/r4/analysis/E5-decision-b{B}.json", "w"), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
