#!/usr/bin/env python3
"""Adaptive allocation for E1+E2 (prereg/AMENDMENT-2.md as amended by AMENDMENT-5: no token terms;
active-time terms vs ref and vs solo, time fitted on non-collapsed runs). One interim look per call:
fit the two-part Bayesian model, update arm decisions, keep exactly 1 pending job in the lab queue.
usage: adapt.py [--dry]"""
import json, os, re, sys, glob, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import r4eval as ev

R, L = ev.R, ev.L; Q = f"{L}/queue"; OUT = f"{R}/analysis/adapt"; STATEF = f"{OUT}/decisions.json"
EXP = "E1"; TASKS = ["T4b", "T3b", "T1b", "T2"]  # r3 collapse priority order
ARMS = ["base4", "C1", "C2"]; CANDS = ["C1", "C2"]
REV = json.load(open(f"{L}/E1-plan.json"))["arms"]
SIG_Q, SIG_TOK, SIG_ACT, NDRAW, MAXCELL = 1.0, 0.25, 0.35, 20000, 3
rng = np.random.default_rng(20261020)

def log(m): open(f"{R}/LOG.md", "a").write(f"- {time.strftime('%m-%d %H:%M')} [adapt] {m}\n"); print(m, flush=True)

def started():
    """(task, arm) -> names of runs started (finished non-infra + running), plus pending unclaimed jobs."""
    st, pend = {}, []
    for f in glob.glob(f"{Q}/{EXP}-*.json*"):
        b = os.path.basename(f); n = b.split(".json")[0]; m = re.match(rf"{EXP}-(\w+?)-(\w+)-r(\d+)$", n)
        if not m: continue
        if b.endswith(".json"): pend.append(n); continue
        if not b.endswith(".claimed"): continue
        rp = f"{L}/results/{n}/result.json"
        if os.path.exists(rp) and ev.is_infra(json.load(open(rp))): continue
        st.setdefault((m[1], m[2]), []).append(n)
    return st, pend

def gauss_post(obs, sig, prior_theta, sd_theta, sd_delta, cols=CANDS):
    """Bayesian linear model y = theta_task + delta_arm (delta_base4 = 0). Returns draws of delta per arm in cols."""
    P = len(TASKS) + len(cols); prec = np.zeros((P, P)); b = np.zeros(P)
    for i in range(len(TASKS)): prec[i, i] = 1 / sd_theta ** 2; b[i] = prior_theta / sd_theta ** 2
    for j in range(len(cols)): prec[len(TASKS) + j, len(TASKS) + j] = 1 / sd_delta ** 2
    for t, a, y in obs:
        x = np.zeros(P); x[TASKS.index(t)] = 1
        if a in cols: x[len(TASKS) + cols.index(a)] = 1
        prec += np.outer(x, x) / sig ** 2; b += x * y / sig ** 2
    cov = np.linalg.inv(prec); mu = cov @ b
    return rng.multivariate_normal(mu, cov, NDRAW)  # columns: thetas..., deltas...

def fit(rs):
    jr = [r for r in rs if r["arm"] in ARMS and (r["overall"] is not None or not r["delivered"])]
    coll = {a: [r for r in jr if r["arm"] == a] for a in ARMS}
    p = {a: rng.beta(1 + sum(1 for r in coll[a] if (not r["delivered"]) or r["overall"] < 3.0),
                     1 + sum(1 for r in coll[a] if r["delivered"] and r["overall"] >= 3.0), NDRAW) for a in ARMS}
    dq = gauss_post([(r["task"], r["arm"], r["overall"]) for r in jr if r["delivered"] and r["overall"] >= 3.0], SIG_Q, 7.0, 3.0, 1.0)
    th = dq[:, :len(TASKS)].mean(1); E = {}
    for a in ARMS:
        d = 0 if a == "base4" else dq[:, len(TASKS) + CANDS.index(a)]
        E[a] = (1 - p[a]) * (th + d) + p[a] * 1.0
    # AMENDMENT-5: time of collapsed runs is excluded (a run that skips the work is not "fast"); unjudged delivered
    # runs count provisionally; solo is an arm of the time model (speed-up vs solo). Tokens: reported only.
    fin = [r for r in rs if r["arm"] in ARMS + ["solo"] and r["delivered"] and not r["collapse"]]
    tok = gauss_post([(r["task"], r["arm"], np.log(r["input"])) for r in fin if r["input"]], SIG_TOK, np.log(15e6), 2.0, 1.0, CANDS + ["solo"])
    act = gauss_post([(r["task"], r["arm"], np.log(r["active_nf"])) for r in fin if r["active_nf"]], SIG_ACT, np.log(30), 2.0, 1.0, CANDS + ["solo"])
    lt = {"base4": 0, **{c: tok[:, len(TASKS) + j] for j, c in enumerate(CANDS + ["solo"])}}
    la = {"base4": 0, **{c: act[:, len(TASKS) + j] for j, c in enumerate(CANDS + ["solo"])}}
    return E, lt, la, p

def pkeep(c, ref, E, lt, la):
    dq = E[c] - E[ref]; rt = np.exp(lt[c] - lt[ref]); ra = np.exp(la[c] - la[ref]) * np.ones(NDRAW)
    rs_ = np.exp(la[c] - la["solo"])  # active time vs solo
    if c == "C1": ok = (dq >= 0.5) & (ra <= 1.10) & (rs_ <= 1.0)
    else: ok = (((dq >= -0.3) & (ra <= 0.85)) | ((dq >= 0.5) & (ra <= 1.10))) & (rs_ <= 1.0)
    return float(np.mean(ok)), {"dq_mean": float(np.mean(dq)), "P_dq>0": float(np.mean(dq > 0)), "P_dq>=0.5": float(np.mean(dq >= 0.5)),
                                "tok_ratio_med(secondary)": float(np.median(rt)), "act_ratio_med": float(np.median(ra)),
                                "act_ratio_vs_solo_med": float(np.median(rs_)), "P_act<=1.10": float(np.mean(ra <= 1.10))}

def main(dry=False):
    os.makedirs(OUT, exist_ok=True)
    dec = json.load(open(STATEF)) if os.path.exists(STATEF) else {c: "active" for c in CANDS}
    rs = ev.rows(EXP); judged = {(r["task"], r["arm"]) for r in rs if r["overall"] is not None}
    E, lt, la, p = fit(rs); look = {"t": time.strftime("%Y-%m-%d %H:%M"), "n_rows": len(rs), "p_collapse_mean": {a: float(p[a].mean()) for a in ARMS}}
    for c in CANDS:
        ref = "base4" if c == "C1" or dec.get("C1") == "REJECT" else "C1"
        pk, info = pkeep(c, ref, E, lt, la); look[c] = {"ref": ref, "P_keep": pk, **info}
        nj = sum(1 for r in rs if r["arm"] == c and r["overall"] is not None)
        tasks_ok = {t for t in TASKS if (t, c) in judged and (t, ref) in judged and (t, "base4") in judged}
        look[c].update(n_judged=nj, paired_tasks=sorted(tasks_ok))
        if dec[c] == "active" and nj >= 3 and len(tasks_ok) >= 2 and (pk >= 0.90 or pk <= 0.10):
            dec[c] = "KEEP" if pk >= 0.90 else "REJECT"; log(f"{c} {dec[c]} (P_keep={pk:.3f} vs {ref}; {info})")
    st, pend = started(); n = lambda t, a: len(st.get((t, a), []))
    for c in CANDS:
        if dec[c] == "active" and all(n(t, c) >= MAXCELL for t in TASKS):
            dec[c] = "CAP"; log(f"{c} reached the cap: apply the deterministic E1/E2 fallback rule")
    look["decisions"] = dict(dec); look["started"] = {f"{t}/{a}": n(t, a) for t in TASKS for a in ARMS + ["solo"]}
    json.dump(look, open(f"{OUT}/{time.strftime('%m%d-%H%M')}.json", "w"), indent=1)
    if not dry: json.dump(dec, open(STATEF, "w"), indent=1)
    print(json.dumps(look, indent=1))
    if pend: return  # one pending job at a time; decide again when it is claimed
    job = choose(rs, dec, look, n)
    if job is None: return
    t, a = job; k = 1 + max([int(x.rsplit("-r", 1)[1]) for x in st.get((t, a), [])] + [0])
    name = f"{EXP}-{t}-{a}-r{k}"
    while os.path.exists(f"{L}/results/{name}") or [g for g in glob.glob(f"{Q}/{name}.json*") if "withdrawn" not in g]: k += 1; name = f"{EXP}-{t}-{a}-r{k}"
    spec = {"task": t, "peers": "exec", "cap": "120m"} if a == "solo" else \
        {"murmur_repo": f"{L}/repos/murmur.git", "rev": REV[a], "task": t, "peers": 3, "cap": "120m", "env": {}, "config": {}}
    if dry: print("would queue", name); return
    json.dump(spec, open(f"{Q}/{name}.json", "w")); log(f"queued {name} (A5 P_keep C1={look['C1']['P_keep']:.2f}, C2={look['C2']['P_keep']:.2f})")

def choose(rs, dec, look, n):
    swarm = sum(n(t, a) for t in TASKS for a in ARMS); solos = sum(n(t, "solo") for t in TASKS)
    act = [c for c in CANDS if dec[c] == "active"]
    for t in TASKS:  # pairing: comparators catch up first
        for c in act:
            for comp in dict.fromkeys(["base4", look[c]["ref"]]):
                if n(t, comp) < n(t, c): return t, comp
    need_solo = [t for t in TASKS if n(t, "solo") == 0 and sum(n(t, a) for a in ARMS) > 0]
    if need_solo and swarm >= 4 * (solos + 1):
        return max(need_solo, key=lambda t: (sum(n(t, a) for a in ARMS), -TASKS.index(t))), "solo"
    if not act:
        if need_solo: return max(need_solo, key=lambda t: sum(n(t, a) for a in ARMS)), "solo"
        log("all candidates stopped: E1/E2 screening phase complete (no job queued)"); return None
    pk = lambda c: look[c]["P_keep"]
    w = lambda c: 0.25 if look[c]["n_judged"] < 3 else pk(c) * (1 - pk(c))  # no stop possible yet => max uncertainty
    c = max(act, key=lambda c: ((w(c) + 0.02) / (1 + sum(n(t, c) for t in TASKS)), -CANDS.index(c)))
    def uninformative(t):
        m = lambda a: [r["overall"] for r in rs if r["task"] == t and r["arm"] == a and r["overall"] is not None]
        if any(len(m(a)) < 2 for a in ARMS) or any(x < 3.0 for a in ARMS for x in m(a)): return False
        return all(abs(np.mean(m(x)) - np.mean(m("base4"))) < 0.3 for x in CANDS)
    open_t = [t for t in TASKS if n(t, c) < MAXCELL]
    pool = [t for t in open_t if not uninformative(t)] or open_t
    return min(pool, key=lambda t: (n(t, c), TASKS.index(t))), c

if __name__ == "__main__": main("--dry" in sys.argv)
