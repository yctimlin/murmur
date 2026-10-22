#!/usr/bin/env python3
"""FINAL held-out evaluation driver (prereg/FINAL.md, FAIRNESS.md F2). Never prints task content.
usage: final_eval.py start   check preconditions, copy+verify sealed tasks, queue 32 runs, start eval runner + watcher
       final_eval.py watch   (detached, started by `start`) rerun infra failures in place until 32 scored-able runs"""
import json, os, random, re, subprocess, sys, time, glob
R = "/workspace/r4"; E = f"{R}/evallab"; Q = f"{E}/queue"; SEALED = "/srv/murmur-sealed-r4/heldout/final"
ARMS = {"base4": "146d476626b7b48928d9a44ee907571dd5f83dca", "orig": "eec78f8"}
SLOTS = ["H1", "H2", "H3", "H4"]; REPS = 2; SEED = 20261020

def log(m): open(f"{R}/LOG.md", "a").write(f"- {time.strftime('%m-%d %H:%M')} [final_eval] {m}\n"); print(m, flush=True)
def sh(c, **k): return subprocess.run(c, shell=True, capture_output=True, text=True, **k)

def candidate():
    t = open(f"{R}/prereg/FINAL-CANDIDATE.md").read(); m = re.search(r"\b([0-9a-f]{40})\b", t)
    if not m: sys.exit("FINAL-CANDIDATE.md has no 40-hex commit sha")
    w = f"{R}/research-wt"; sh(f"git -C {w} fetch -q origin experiment/self-improve-r4", timeout=300)
    pub = sh(f"git -C {w} show origin/experiment/self-improve-r4:research-r4/prereg/FINAL-CANDIDATE.md").stdout
    if pub.strip() != t.strip(): sys.exit("FINAL-CANDIDATE.md is not committed+pushed as is; commit and push it first")
    return m[1]

def start():
    if os.path.exists(E): sys.exit(f"{E} exists: the final eval was already started (use watch)")
    if subprocess.run(["pgrep", "-f", "^python3 /workspace/r4/tools/runner.py r4-lab-runner"], capture_output=True).returncode == 0: sys.exit("stop the dev lab runner first (<= 3 concurrent runs)")
    if "gpt-6-astra" not in sh("codex debug models", timeout=120).stdout: sys.exit("relay unhealthy: gpt-6-astra not listed")
    cand = candidate(); arms = {"cand": cand, **ARMS, "solo": None}
    pub = {t["slot"]: t["bundle_sha256"] for t in json.load(open(f"{R}/heldout/PUBLIC.json"))["tasks"]}
    for d in ("queue", "results", "tasks", "repos"): os.makedirs(f"{E}/{d}")
    os.symlink(f"{R}/lab/heartbeat.log", f"{E}/heartbeat.log"); os.symlink(f"{R}/lab/repos/murmur.git", f"{E}/repos/murmur.git")
    for a, rev in arms.items():
        if rev and sh(f"git -C {E}/repos/murmur.git cat-file -e {rev}^{{commit}}").returncode:
            sh(f"git -C {E}/repos/murmur.git fetch -q {R}/murmur '+refs/heads/*:refs/heads/*'")
            if sh(f"git -C {E}/repos/murmur.git cat-file -e {rev}^{{commit}}").returncode: sys.exit(f"commit for {a} missing")
    for s in SLOTS:  # tasks enter the lab only here (F2); content is never printed
        d = f"{E}/tasks/{s}"
        if sh(f"sudo -n cp -r {SEALED}/{s} {d} && sudo -n chown -R {os.getuid()} {d}").returncode: sys.exit(f"copy of {s} failed")
        h = sh("find . -type f | sort | xargs sha256sum | sha256sum", cwd=d).stdout.split()[0]
        if h != pub[s]: sys.exit(f"{s} bundle sha256 mismatch (got {h[:12]}, PUBLIC {pub[s][:12]})")
    rnd = random.Random(SEED); blocks = [(s, k) for k in range(1, REPS + 1) for s in SLOTS]; rnd.shuffle(blocks); plan = []
    for s, k in blocks:
        order = list(arms); rnd.shuffle(order)
        for a in order:
            spec = {"task": s, "peers": "exec", "cap": "120m"} if a == "solo" else \
                {"murmur_repo": f"{E}/repos/murmur.git", "rev": arms[a], "task": s, "peers": 3, "cap": "120m", "env": {}, "config": {}}
            plan.append((f"F-{s}-{a}-r{k}", spec))
    json.dump({"arms": arms, "plan": plan}, open(f"{E}/plan.json", "w"), indent=1)
    for i, (n, spec) in enumerate(plan):
        json.dump(spec, open(f"{Q}/{n}.json", "w")); os.utime(f"{Q}/{n}.json", (1.8e9 + i, 1.8e9 + i))
    env = f"MURMUR_LAB={E} MURMUR_LAB_NAME_RE='^F-' MURMUR_LAB_BUDGET=60 MURMUR_LAB_TOKEN_CAP=1500000000 MURMUR_LAB_MAX_CAP_MIN=120 MURMUR_LAB_PAR=3 MURMUR_LAB_PORT0=56000"
    sh(f"cd {E} && {env} setsid nohup python3 {R}/tools/runner.py r4-eval-runner >> {E}/runner.log 2>&1 < /dev/null &")
    sh(f"setsid nohup python3 {__file__} watch >> {E}/watch.log 2>&1 < /dev/null &")
    sh(f"cd {R} && R4_LAB={E} setsid nohup tools/judge_loop.sh F 32 1 > /dev/null 2>&1 < /dev/null &")
    log(f"started: cand {cand[:8]}, 4 tasks verified against PUBLIC.json sha256, 32 runs queued in 8 randomized blocks (seed {SEED}), eval runner PAR 3, watcher, judge loop F")

def watch():
    sys.path.insert(0, f"{R}/tools"); os.environ["R4_LAB"] = E; import r4eval as ev
    plan = dict((n, s) for n, s in json.load(open(f"{E}/plan.json"))["plan"])
    while True:
        done = 0
        for n, spec in plan.items():
            p = f"{E}/results/{n}/result.json"
            if not os.path.exists(p): continue
            if ev.is_infra(json.load(open(p))):
                k = len(glob.glob(f"{E}/results/{n}.infra*")) + 1; os.rename(f"{E}/results/{n}", f"{E}/results/{n}.infra{k}")
                for f in glob.glob(f"{Q}/{n}.json*"): os.rename(f, f"{f}.infra{k}")
                json.dump(spec, open(f"{Q}/{n}.json", "w")); log(f"{n}: infra failure #{k}, re-queued")
            else: done += 1
        if done == len(plan): log("all 32 runs finished (non-infra); judging continues in the F judge loop"); return
        time.sleep(300)

if __name__ == "__main__": {"start": start, "watch": watch}[sys.argv[1]]()
