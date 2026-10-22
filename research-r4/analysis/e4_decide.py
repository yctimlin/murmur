#!/usr/bin/env python3
"""E4 decision rules D1-D3 + safety stop (prereg/E4.md), mechanical. Reads judge/E4 scores via r4eval.rows and
analysis/E4-signatures.json (run tools/signatures.py E4 first). S1 counts must be hand-checked (regex false positives)."""
import json, math, statistics as st, sys
sys.path.insert(0, "/workspace/r4/tools"); import r4eval as ev
T = ["T1b", "T2", "T3b", "T4b"]
rs = ev.rows("E4"); sig = {s["run"]: s for s in json.load(open("/workspace/r4/analysis/E4-signatures.json"))}
def get(t, a, k=None): return [r for r in rs if r["task"] == t and r["arm"] == a and (k is None or r["rep"] == k)]
def q(rr): v = [r["overall"] for r in rr if r["overall"] is not None]; return st.mean(v) if v else None
coll = lambda a: sum(1 for r in rs if r["arm"] == a and r["collapse"]); judged = lambda a: sum(1 for r in rs if r["arm"] == a and r["overall"] is not None)
out = {"n_rows": len(rs), "judged": {a: judged(a) for a in ("base4", "K0", "K1", "solo")}}
kr = [r["run"] for r in rs if r["arm"] in ("K0", "K1")]
out["D1"] = {"k_runs": len(kr), "premature_end_runs": [n for n in kr if sig.get(n, {}).get("premature_end")],
             "early_quit_runs": [n for n in kr if sig.get(n, {}).get("early_quits")], "to_root": {n: sig.get(n, {}).get("to_root") for n in kr}}
out["D1"]["pass"] = len(out["D1"]["premature_end_runs"]) <= 2 and not out["D1"]["early_quit_runs"]
d2 = [q(get(t, "K0")) - q(get(t, "base4")) for t in T if q(get(t, "K0")) is not None and q(get(t, "base4")) is not None]
rate = lambda a: coll(a) / max(1, judged(a))
out["D2"] = {"tasks": len(d2), "mean_diff": st.mean(d2) if d2 else None, "collapse_rate_K0": rate("K0"), "collapse_rate_base4": rate("base4")}
out["D2"]["pass"] = bool(d2) and out["D2"]["mean_diff"] >= -0.3 and rate("K0") <= rate("base4")
pairs = [(get(t, "K1", k), get(t, "K0", k)) for t in T for k in (1, 2)]
d3 = [q(a) - q(b) for a, b in pairs if a and b and q(a) is not None and q(b) is not None]
nc = lambda rr: [r["active_nf"] for r in rr if r["active_nf"]]
rat = [st.mean(nc(get(t, "K1"))) / st.mean(nc(get(t, "K0"))) for t in T if nc(get(t, "K1")) and nc(get(t, "K0"))]
gm = math.exp(st.mean(math.log(x) for x in rat)) if rat else None
out["D3"] = {"pairs": len(d3), "mean_diff": st.mean(d3) if d3 else None, "ci90": ev.tint(d3), "collapses_K1": coll("K1"), "collapses_K0": coll("K0"), "geo_active_ratio": gm}
out["D3"]["keep"] = len(d3) == 8 and out["D3"]["mean_diff"] >= 0.3 and coll("K1") <= coll("K0") and gm is not None and gm <= 1.25
b1 = [r for r in rs if r["arm"] == "K1" and r["rep"] == 1]
out["safety_stop"] = {"block1_K1_judged": sum(1 for r in b1 if r["overall"] is not None), "collapses": sum(1 for r in b1 if r["collapse"])}
out["safety_stop"]["trigger"] = out["safety_stop"]["collapses"] >= 3
out["per_task"] = {t: {a: {"q": q(get(t, a)), "active_nf": st.mean(nc(get(t, a))) if nc(get(t, a)) else None,
                           "input_M": st.mean([r["input"] / 1e6 for r in get(t, a) if r["input"]]) if get(t, a) else None} for a in ("base4", "K0", "K1", "solo")} for t in T}
json.dump(out, open("/workspace/r4/analysis/E4-decision.json", "w"), indent=1, default=str)
print(json.dumps({k: v for k, v in out.items() if k != "per_task"}, indent=1, default=str))
for t in T: print(t, {a: {k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items()} for a, d in out["per_task"][t].items()})
