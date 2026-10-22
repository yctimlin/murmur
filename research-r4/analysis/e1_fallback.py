#!/usr/bin/env python3
"""AMENDMENT-5 deterministic fallback for E1/E2 at the cap (reported only; AMENDMENT-8: does not select FINAL).
Plain means: quality diff = mean over tasks of (mean cand - mean ref) (all judged runs, collapses included);
active ratios = mean over tasks of mean active_nf(cand)/mean active_nf(ref|solo) on delivered non-collapsed runs."""
import json, os, sys, statistics as st
sys.path.insert(0, "/workspace/r4/tools"); import r4eval as ev
rs = ev.rows("E1"); T = ["T4b", "T3b", "T1b", "T2"]
def m(t, a, k, ok=lambda r: True):
    v = [r[k] for r in rs if r["task"] == t and r["arm"] == a and r[k] is not None and ok(r)]; return st.mean(v) if v else None
nc = lambda r: r["delivered"] and not r["collapse"]
def crit(c, ref):
    dq = [m(t, c, "overall") - m(t, ref, "overall") for t in T if m(t, c, "overall") is not None and m(t, ref, "overall") is not None]
    ra = [m(t, c, "active_nf", nc) / m(t, ref, "active_nf", nc) for t in T if m(t, c, "active_nf", nc) and m(t, ref, "active_nf", nc)]
    rsol = [m(t, c, "active_nf", nc) / m(t, "solo", "active_nf", nc) for t in T if m(t, c, "active_nf", nc) and m(t, "solo", "active_nf", nc)]
    dq, ra, rsol = st.mean(dq), st.mean(ra), st.mean(rsol)
    if c == "C1": keep = dq >= 0.5 and ra <= 1.10 and rsol <= 1.0
    else: keep = ((dq >= -0.3 and ra <= 0.85) or (dq >= 0.5 and ra <= 1.10)) and rsol <= 1.0
    return {"ref": ref, "quality_diff": round(dq, 3), "active_ratio_vs_ref": round(ra, 3), "active_ratio_vs_solo": round(rsol, 3), "fallback": "KEEP" if keep else "REJECT"}
out = {"n_rows": len(rs), "per_task": {t: {a: {"n": sum(1 for r in rs if r["task"] == t and r["arm"] == a and r["overall"] is not None),
        "quality": m(t, a, "overall"), "collapses": sum(1 for r in rs if r["task"] == t and r["arm"] == a and r["collapse"]),
        "active_nf_noncollapsed": m(t, a, "active_nf", nc)} for a in ("base4", "C1", "C2", "solo")} for t in T}}
out["C1"] = crit("C1", "base4")
out["C2"] = crit("C2", "base4" if out["C1"]["fallback"] == "REJECT" else "C1")
json.dump(out, open("/workspace/r4/analysis/e1_fallback.json", "w"), indent=1, default=str)
print(json.dumps({k: out[k] for k in ("n_rows", "C1", "C2")}, indent=1))
for t in T: print(t, {a: (v["n"], round(v["quality"], 2) if v["quality"] else None, v["collapses"], round(v["active_nf_noncollapsed"], 1) if v["active_nf_noncollapsed"] else None) for a, v in out["per_task"][t].items()})
