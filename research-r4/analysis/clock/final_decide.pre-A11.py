#!/usr/bin/env python3
"""FINAL decision (prereg/FINAL.md). usage: final_decide.py  ->  /workspace/r4/results/FINAL.json
Reads the evallab runs F-<task>-<arm>-r<rep> (blocks = task x rep) and their judge scores."""
import json, math, os, sys, statistics as stt
os.environ.setdefault("R4_LAB", "/workspace/r4/evallab")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r4eval as ev

def tint(xs):
    m, lo, hi = ev.tint(xs); return {"mean": m, "lo90": lo, "hi90": hi, "n": len([x for x in xs if x is not None])}

def main():
    rs = ev.rows("F"); arms = ("cand", "base4", "orig", "solo")
    blocks = sorted({(r["task"], r["rep"]) for r in rs})
    cell = {(r["task"], r["rep"], r["arm"]): r for r in rs}
    full = [b for b in blocks if all((b[0], b[1], a) in cell and cell[(b[0], b[1], a)]["overall"] is not None for a in arms)]
    if len(full) < 8: print(f"only {len(full)}/8 complete blocks; not deciding"); return
    g = lambda b, a, k: cell[(b[0], b[1], a)][k]
    def qdiff(x): return tint([g(b, "cand", "overall") - g(b, x, "overall") for b in full])
    def lratio(k, x):
        t = tint([math.log(g(b, "cand", k) / g(b, x, k)) for b in full if g(b, "cand", k) and g(b, x, k)])
        return {kk: (round(math.exp(v), 3) if v is not None and kk != "n" else v) for kk, v in t.items()}
    coll = {a: sum(1 for b in full if g(b, a, "overall") < 3.0) for a in arms}
    out = {"blocks": full, "collapses": coll,
           "quality": {a: tint([g(b, a, "overall") for b in full]) for a in arms},
           "active_nf": {a: tint([g(b, a, "active_nf") for b in full]) for a in arms},
           "input_M": {a: tint([g(b, a, "input") / 1e6 for b in full]) for a in arms},
           "qdiff": {x: qdiff(x) for x in ("base4", "orig", "solo")},
           "active_ratio_vs_solo": lratio("active_nf", "solo"), "input_ratio_vs_solo": lratio("input", "solo"),
           "input_ratio_vs_base4": lratio("input", "base4"),
           "blinding_correct": None}
    gs = [(gu, r["arm"]) for r in rs for gu in r["guesses"] if gu]
    if gs: out["blinding_correct"] = round(sum(1 for gu, a in gs if (gu == "single") == (a == "solo")) / len(gs), 3)
    G1 = all(out["qdiff"][x]["lo90"] > -0.5 and coll["cand"] <= coll[x] for x in ("base4", "orig"))
    G2 = out["qdiff"]["solo"]["lo90"] > -0.75
    G3 = out["active_ratio_vs_solo"]["mean"] < 1.0 and out["active_ratio_vs_solo"]["hi90"] < 1.10
    G4 = out["input_ratio_vs_solo"]["mean"] <= 2.0
    better = out["qdiff"]["base4"]["mean"] > 0 or out["input_ratio_vs_base4"]["mean"] < 0.9
    out["G"] = {"G1_no_regression": G1, "G2_quality_vs_solo": G2, "G3_faster_than_solo": G3, "G4_tokens_le_2x_solo(secondary, AMENDMENT-5)": G4}
    out["verdict"] = "SUCCESS" if G1 and G2 and G3 else "IMPROVEMENT" if G1 and better else "NO-IMPROVEMENT"
    os.makedirs(f"{ev.R}/results", exist_ok=True); json.dump(out, open(f"{ev.R}/results/FINAL.json", "w"), indent=1, default=str)
    print(json.dumps({k: out[k] for k in ("G", "verdict", "qdiff", "collapses")}, indent=1, default=str))

if __name__ == "__main__": main()
