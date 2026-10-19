#!/usr/bin/env python3
"""Round-4 eval tool: freeze-excluded active time, blind Claude judging, per-experiment aggregation.
usage: r4eval.py judge EXP [--par N]     judge every finished, delivered run named EXP-* in the lab (resumable)
       r4eval.py agg EXP                 aggregate EXP-* runs -> /workspace/r4/results/EXP.json
       r4eval.py freeze                  print freeze windows (heartbeat gaps)
Lab via R4_LAB (default /workspace/r4/lab). Rubric = prereg/RUBRIC.md (frozen). Anonymization per prereg/FAIRNESS.md F3."""
import json, os, re, sys, glob, time, random, hashlib, shutil, subprocess, statistics as stt, datetime as dt, concurrent.futures as cf
R = "/workspace/r4"; L = os.environ.get("R4_LAB", f"{R}/lab"); J = f"{R}/judge"; CLAUDE = "/home/box/.local/bin/claude"
RUB = open(f"{R}/prereg/RUBRIC.md").read()
def log(m): open(f"{R}/LOG.md", "a").write(f"- {time.strftime('%m-%d %H:%M')} [r4eval] {m}\n"); print(m, flush=True)
def res(n): return json.load(open(f"{L}/results/{n}/result.json"))

# ---------- freeze-excluded active time ----------
def freeze_windows():
    """Heartbeat (10 s period) gaps > 60 s are VM suspensions."""
    hb = [int(x) for x in open(f"{L}/heartbeat.log").read().split() if x.isdigit()] if os.path.exists(f"{L}/heartbeat.log") else []
    return [(dt.datetime.fromtimestamp(a, dt.timezone.utc), dt.datetime.fromtimestamp(b, dt.timezone.utc)) for a, b in zip(hb, hb[1:]) if b - a > 60]
def stamps(ws):
    ts = []
    for f in glob.glob(ws + "/**/sessions/**/*.jsonl", recursive=True):
        for l in open(f, errors="replace"):
            try: d = json.loads(l)
            except Exception: continue
            if d.get("timestamp"): ts.append(dt.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")))
    return sorted(ts)
def active(ts, fw):
    """runner2 definition (gaps between consecutive events capped at 120 s), each gap first reduced by freeze overlap."""
    s = s_raw = 0
    for a, b in zip(ts, ts[1:]):
        g = (b - a).total_seconds(); s_raw += min(g, 120)
        g -= sum(max(0, (min(b, fb) - max(a, fa)).total_seconds()) for fa, fb in fw)
        s += min(max(g, 0), 120)
    return round(s / 60, 2), round(s_raw / 60, 2)

# ---------- anonymization + judging ----------
SCRUB_DIRS = {".venv", "venv", "__pycache__", ".pytest_cache", ".git", "logs", ".murmur", "node_modules", ".work"}
# AMENDMENT-1: delivered = `git archive main`, so every file was committed on purpose: keep data files (r3 dropped
# *.db/*.sqlite*/*.log, which deleted committed fixtures), and scrub identity words only in prose docs, never in code/data.
SCRUB_FILES = re.compile(r"(?i)(^|/)(PR|TASKS|PLAN|NOTES|HANDOFF|AGENTS)\.md$|murmur|swarm|orchestrat")
SCRUB_TXT = re.compile(r"(?i)\b(murmur|peers?|swarm|drafts?|orchestrator|handoff|codex|claude|agent [a-z0-9]|a[1-9]:|END vote|quorum)\b")
TEXT_EXT = (".md", ".txt", ".rst")
def anonymize(n, rid):
    src = f"{L}/results/{n}/delivered"; dst = f"/tmp/r4judge/{rid}"; shutil.rmtree(dst, ignore_errors=True); os.makedirs(dst)
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SCRUB_DIRS]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), src)
            if SCRUB_FILES.search(rel): continue
            o = os.path.join(dst, rel); os.makedirs(os.path.dirname(o), exist_ok=True)
            b = open(os.path.join(root, f), "rb").read()
            if f.endswith(TEXT_EXT) and len(b) < 2_000_000:
                try: b = SCRUB_TXT.sub("x", b.decode()).encode()
                except UnicodeDecodeError: pass
            open(o, "wb").write(b); os.utime(o, (1.7e9, 1.7e9))
    return dst
PROTECT = {"T1b": [""], "T2": [], "T3b": [], "T4b": ["exports/"]}   # r3 AMENDMENT-5; held-out tasks: whole input unless amended
def originals_ok(t, n):
    base = f"{L}/tasks/{t}/input"; bad = tot = 0; prot = PROTECT.get(t, [""])
    for root, _, files in os.walk(base):
        for f in files:
            p = os.path.join(root, f); rel = os.path.relpath(p, base)
            if rel == "README.md" or not any(rel.startswith(x) for x in prot): continue
            q = f"{L}/results/{n}/delivered/{rel}"; tot += 1
            if not os.path.exists(q) or open(q, "rb").read() != open(p, "rb").read(): bad += 1
    return {"protected_paths": prot or "none (brief permits changing all input)", "originals_total": tot, "originals_changed_or_missing": bad}
def task_of(n): return res(n)["job"]["task"]
def judge_one(exp, n, k):
    t = task_of(n); D = f"{J}/{exp}"; os.makedirs(D, exist_ok=True); out = f"{D}/{n}.j{k}.json"
    if os.path.exists(out): return json.load(open(out))
    rid = hashlib.sha256(f"{n}:{k}:{random.random()}".encode()).hexdigest()[:10]; d = anonymize(n, rid); oc = originals_ok(t, n)
    brief = open(f"{L}/tasks/{t}/brief.md").read()
    p = f"""You are an independent senior reviewer judging ONE anonymous submission for the task below, using the fixed rubric.
The submission is in the current directory ({d}). Install it, run it, exercise it, read the code. Work only inside this directory and /tmp.
Operator mechanical check of original input files: {json.dumps(oc)} (originals_changed_or_missing > 0 means the original data was modified or removed).

# TASK BRIEF
{brief}

# RUBRIC
{RUB}

End your answer with the single final JSON line exactly as the rubric specifies (include "guess")."""
    for att in range(4):
        try:
            r = subprocess.run([CLAUDE, "-p", p, "--permission-mode", "bypassPermissions"], cwd=d, capture_output=True, text=True, timeout=2700, stdin=subprocess.DEVNULL)
            lines = [l for l in r.stdout.strip().splitlines() if l.strip().strip("`").startswith("{") and "overall" in l]
            j = json.loads(lines[-1].strip().strip("`")); j["_rid"] = rid; j["_originals"] = oc
            g = re.findall(r'"guess"\s*:\s*"(single|team)"', r.stdout)
            if "guess" not in j and g: j["guess"] = g[-1]
            open(f"{D}/{n}.j{k}.md", "w").write(r.stdout); json.dump(j, open(out, "w")); shutil.rmtree(d, ignore_errors=True); return j
        except Exception as e:
            log(f"judge {n} j{k} attempt {att} failed: {repr(e)[:100]} stdout={r.stdout[-160:]!r}" if 'r' in dir() else f"judge {n} j{k} attempt {att} failed: {repr(e)[:100]}")
            time.sleep(300 if "limit" in (locals().get('r') and r.stdout or "") else 90)
    shutil.rmtree(d, ignore_errors=True); return None
def score_run(exp, n):
    r = res(n)
    if is_infra(r): return None
    if not r.get("delivered"): return {"overall": 0.0, "nondelivery": True, "judgments": []}
    js = [judge_one(exp, n, 1), judge_one(exp, n, 2)]
    if all(js) and abs(js[0]["overall"] - js[1]["overall"]) > 1.5: js.append(judge_one(exp, n, 3))
    js = [j for j in js if j]
    if not js: return None
    ov = stt.median([j["overall"] for j in js]) if len(js) == 3 else stt.mean([j["overall"] for j in js])
    return {"overall": ov, "judgments": js}
def is_infra(r): return bool(r.get("infra")) or ("CalledProcessError" in str(r.get("error") or "") and not r.get("delivered"))
def finished(exp): return sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob(f"{L}/results/{exp}-*/result.json"))
def judge(exp, par=2):
    todo = [n for n in finished(exp) if not os.path.exists(f"{J}/{exp}/{n}.score.json")]
    def one(n):
        s = score_run(exp, n)
        if s is not None: os.makedirs(f"{J}/{exp}", exist_ok=True); json.dump(s, open(f"{J}/{exp}/{n}.score.json", "w"), indent=1); log(f"judged {n}: {s['overall']}")
    with cf.ThreadPoolExecutor(par) as ex: list(ex.map(one, todo))

# ---------- run diagnostics ----------
def diag(n):
    r = res(n); ws = r.get("ws") or ""; out = {}
    o = f"{ws}/work/origin.git"
    if os.path.isdir(o):
        refs = subprocess.run(["git", "-C", o, "for-each-ref", "--format=%(refname:short)", "refs/heads/"], capture_output=True, text=True).stdout.split()
        unmerged = [x for x in refs if x != "main" and subprocess.run(["git", "-C", o, "merge-base", "--is-ancestor", x, "main"]).returncode != 0]
        out["unmerged_branches"] = len(unmerged)
        out["main_added_lines"] = sum(int(a) for a, *_ in (l.split("\t") for l in subprocess.run(["git", "-C", o, "diff", "--numstat", f"{r.get('base') or json.load(open(ws + '/murmur.json'))['base']}", "main"], capture_output=True, text=True).stdout.splitlines()) if a.isdigit())
    ends = 0
    for f in glob.glob(ws + "/**/sessions/**/*.jsonl", recursive=True):
        for l in open(f, errors="replace"):
            if "collaboration__post" in l and re.search(r"text:\s*\\?[\"'`]END\b", l): ends += 1
    out["end_posts"] = ends
    return out

# ---------- aggregate ----------
def tint(xs):
    xs = [x for x in xs if x is not None]
    if not xs: return (None, None, None)
    m = stt.mean(xs)
    if len(xs) < 2: return (round(m, 3), None, None)
    tq = {1: 6.314, 2: 2.920, 3: 2.353, 4: 2.132, 5: 2.015, 6: 1.943, 7: 1.895, 8: 1.860, 9: 1.833}.get(len(xs) - 1, 1.8)
    h = tq * stt.stdev(xs) / len(xs) ** .5; return (round(m, 3), round(m - h, 3), round(m + h, 3))
def rows(exp):
    fw = freeze_windows(); out = []
    for n in finished(exp):
        r = res(n); m = re.match(rf"{exp}-(\w+?)-(\w+)-r(\d+)$", n)
        if not m or is_infra(r): continue
        sc = json.load(open(f"{J}/{exp}/{n}.score.json")) if os.path.exists(f"{J}/{exp}/{n}.score.json") else {}
        anf, araw = active(stamps(r["ws"]), fw) if r.get("ws") else (None, None)
        q = sc.get("overall")
        out.append({"run": n, "task": m[1], "arm": m[2], "rep": int(m[3]), "delivered": bool(r.get("delivered")), "overall": q,
                    "collapse": None if q is None else (q < 3.0), "active_nf": anf, "active_raw": araw, "runner_active": r.get("active_min"),
                    "wall_min": r.get("wall_min"), "input": r.get("input"), "uncached": r.get("uncached"), "output": r.get("output"),
                    "guesses": [j.get("guess") for j in sc.get("judgments", [])], "run_exit": r.get("run_exit"), **(diag(n) if r.get("ws") else {})})
    return out
def agg(exp, arms=("C1", "base4"), cand="C1", base="base4"):
    rs = rows(exp); tasks = sorted({r["task"] for r in rs})
    def m(t, a, k): v = [r[k] for r in rs if r["task"] == t and r["arm"] == a and r[k] is not None]; return stt.mean(v) if v else None
    out = {"exp": exp, "n_runs": len(rs), "freeze_windows": [(a.isoformat(), round((b - a).total_seconds() / 60, 1)) for a, b in freeze_windows()], "rows": rs}
    out["per_task"] = {t: {a: {k: m(t, a, k) for k in ("overall", "active_nf", "active_raw", "wall_min", "input")} for a in (*arms, "solo")} for t in tasks}
    pairs = [(next((r for r in rs if r["task"] == t and r["arm"] == cand and r["rep"] == k), None), next((r for r in rs if r["task"] == t and r["arm"] == base and r["rep"] == k), None)) for t in tasks for k in (1, 2, 3)]
    pairs = [(a, b) for a, b in pairs if a and b and a["overall"] is not None and b["overall"] is not None]
    out["quality_diff_pairs"] = tint([a["overall"] - b["overall"] for a, b in pairs]); out["n_pairs"] = len(pairs)
    out["quality_diff_tasks"] = tint([m(t, cand, "overall") - m(t, base, "overall") for t in tasks if m(t, cand, "overall") is not None and m(t, base, "overall") is not None])
    for a in arms:
        out[f"collapses_{a}"] = sum(1 for r in rs if r["arm"] == a and r["collapse"])
        out[f"mean_quality_{a}"] = tint([r["overall"] for r in rs if r["arm"] == a])
        for k in ("active_nf", "input"):
            out[f"{a}_{k}_ratio_vs_solo"] = tint([m(t, a, k) / m(t, "solo", k) for t in tasks if m(t, a, k) and m(t, "solo", k)])
    out["mean_quality_solo"] = tint([r["overall"] for r in rs if r["arm"] == "solo"])
    out[f"{cand}_input_ratio_vs_{base}"] = tint([m(t, cand, "input") / m(t, base, "input") for t in tasks if m(t, cand, "input") and m(t, base, "input")])
    out[f"{cand}_active_ratio_vs_{base}"] = tint([m(t, cand, "active_nf") / m(t, base, "active_nf") for t in tasks if m(t, cand, "active_nf") and m(t, base, "active_nf")])
    g = [(r["arm"], x) for r in rs for x in r["guesses"] if x]; out["arm_guess_accuracy"] = (sum((a == "solo") == (x == "single") for a, x in g) / len(g)) if g else None
    os.makedirs(f"{R}/results", exist_ok=True); json.dump(out, open(f"{R}/results/{exp}.json", "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in out.items() if k not in ("rows", "per_task", "freeze_windows")}, indent=1))
    for r in rs: print({k: r.get(k) for k in ("run", "overall", "active_nf", "wall_min", "input", "unmerged_branches", "main_added_lines", "end_posts", "run_exit")})
    return out
if __name__ == "__main__":
    c = sys.argv[1]
    if c == "judge": judge(sys.argv[2], int(sys.argv[sys.argv.index("--par") + 1]) if "--par" in sys.argv else 2)
    elif c == "agg": agg(sys.argv[2], *([tuple(sys.argv[3].split(","))] if len(sys.argv) > 3 else []))
    elif c == "freeze": print([(a.isoformat(), round((b - a).total_seconds() / 60, 1)) for a, b in freeze_windows()])
