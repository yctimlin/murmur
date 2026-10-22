#!/usr/bin/env python3
"""murmur lab runner v2 (round 3). Runs real murmur experiments for sandboxed peers, OUTSIDE the
Codex sandbox. The Codex Linux sandbox masks /tmp/codex-daemon-$UID on purpose
(codex-rs/uds/src/daemon_directory.rs, linux-sandbox/src/bwrap.rs), so nested `murmur run` inside a
peer fails; we do NOT unmask it. Peers drop declarative job files; this runner validates and runs them.

Job file QUEUE/<name>.json:
 {"murmur_repo": abs git repo under the lab dir, "rev": commit/branch,
  "task": name of a FROZEN task under /tmp/murmur-lab/tasks (gives brief, input, setup, scorer)
     -- or "brief"+"input" (+ optional "setup" key) for ad-hoc runs (no scorer),
  "peers": 1-3 | "solo" (murmur --solo) | "exec" (plain codex exec, round-2 solo prompt),
  "cap": "<=100m", "env": {"MURMUR_*": "..."}, "config": {toml keys}, "tag": free text}
Result: RESULTS/<name>/result.json. Budget: at most MURMUR_LAB_BUDGET jobs accepted per lab.
"""
import json, os, re, shutil, subprocess, sys, time, glob, datetime as dt
LAB = os.environ.get("MURMUR_LAB", "/workspace/self3/labdata")  # outside /tmp: not writable from peer sandboxes
HIDDEN_ROOT = os.environ.get("MURMUR_LAB_HIDDEN", "/srv/murmur-lab-hidden")  # root-owned; copied in only while scoring
TOKEN_CAP = int(os.environ.get("MURMUR_LAB_TOKEN_CAP", "450000000"))
Q, RES, BUILDS, WS, TASKS = (os.path.join(LAB, d) for d in ("queue", "results", "builds", "ws", "tasks"))
LEDGER = os.path.join(LAB, "ledger.jsonl")
MAX_PAR = int(os.environ.get("MURMUR_LAB_PAR", "3"))
MAX_CAP_MIN = int(os.environ.get("MURMUR_LAB_MAX_CAP_MIN", "100"))
BUDGET = int(os.environ.get("MURMUR_LAB_BUDGET", "36"))
NAME_RE = re.compile(os.environ.get("MURMUR_LAB_NAME_RE", r"^C\d+-\d\d-"))
ALLOWED_ROOTS = [LAB]
ALLOWED_SETUP = {"py": "python3 -m venv .venv && .venv/bin/pip install -q pytest",
                 "py-e": "python3 -m venv .venv && .venv/bin/pip install -q -e . pytest"}
MODEL = os.environ.get("MURMUR_LAB_MODEL", "gpt-6-astra")   # murmur eec78f8 default, recorded
EFFORT = os.environ.get("MURMUR_LAB_EFFORT", "high")

class ActiveClock:
    """Same rule as murmur's cap clock (experiment/r4-base4f, r4-k1f): a 1 s ticker leaves out any tick that arrives
    more than 10 s late, i.e. host-side VM freezes during which CLOCK_MONOTONIC keeps advancing (AMENDMENT-10)."""
    def __init__(self, tick=1.0, stall=10.0):
        import threading
        self.tick, self.stall, self.t0 = tick, stall, time.monotonic(); self.last = self.t0; self.stalled = 0.0
        self.lock = threading.Lock(); self.done = threading.Event()
        threading.Thread(target=lambda: [self.sample() for _ in iter(lambda: self.done.wait(self.tick), True)], daemon=True).start()
    def sample(self):
        with self.lock:
            n = time.monotonic(); g = n - self.last
            if g > self.tick + self.stall: self.stalled += g - self.tick
            self.last = n
    def active(self): self.sample(); return self.last - self.t0 - self.stalled

def run_active(cmd, timeout, r=None, key=None, **kw):
    """subprocess.run with a timeout counted in running (freeze-excluded) seconds; hard wall ceiling 16 h."""
    c = ActiveClock(); w0 = time.time(); p = subprocess.Popen(cmd, **kw)
    try:
        while True:
            try: rc = p.wait(timeout=5); break
            except subprocess.TimeoutExpired:
                if c.active() >= timeout or time.time() - w0 > 16 * 3600:
                    p.kill(); p.wait(); raise subprocess.TimeoutExpired(cmd, timeout)
    finally:
        c.done.set()
        if r is not None and key: r[key] = dict(active_min=round(c.active() / 60, 2), stalled_min=round(c.stalled / 60, 2))
    return rc

PR_SENTENCE = ("Record what you changed, the decisions you made, how you verified the work and how to see it "
               "in `PR.md` at the repository root.")
def under_roots(p):
    rp = os.path.realpath(p)
    return any(rp == r or rp.startswith(r.rstrip("/") + "/") for r in map(os.path.realpath, ALLOWED_ROOTS))

def load_task(j):
    if not j.get("task"): return j
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,60}", j["task"]): raise ValueError("bad task name")
    d = os.path.join(TASKS, j["task"])
    if not os.path.isfile(os.path.join(d, "TASK.json")): raise ValueError("task not frozen/unknown")
    t = json.load(open(os.path.join(d, "TASK.json")))
    j = dict(j); j["brief"] = os.path.join(d, "brief.md"); j["input"] = os.path.join(d, "input")
    j.setdefault("setup", t.get("setup"))
    if os.path.isfile(os.path.join(d, "score.sh")): j["_scorer"] = os.path.join(d, "score.sh")  # open tasks have no hidden tests
    return j

def validate(j):
    if j["peers"] != "exec":
        if not isinstance(j.get("murmur_repo"), str) or not under_roots(j["murmur_repo"]): raise ValueError("murmur_repo outside the lab dir")
        if not re.fullmatch(r"[A-Za-z0-9._/-]{1,100}", str(j.get("rev", ""))): raise ValueError("bad rev")
    for k in ("brief", "input"):
        if not isinstance(j.get(k), str) or not under_roots(j[k]) or not os.path.exists(j[k]):
            raise ValueError(f"{k} missing or outside the lab dir")
    p = j.get("peers")
    if not (p in ("solo", "exec") or (isinstance(p, int) and not isinstance(p, bool) and 1 <= p <= 3)): raise ValueError("peers must be 1-3, solo or exec")
    m = re.fullmatch(r"(\d+)m", str(j.get("cap", "30m")))
    if not m or int(m.group(1)) > MAX_CAP_MIN: raise ValueError(f"cap must be <= {MAX_CAP_MIN}m")
    if j.get("setup") not in (None, *ALLOWED_SETUP): raise ValueError("setup not in allowlist")
    for k in (j.get("env") or {}):
        if not re.fullmatch(r"MURMUR_[A-Z0-9_]+", k): raise ValueError("env keys must be MURMUR_*")

def build(repo, rev):
    import fcntl
    sha = subprocess.check_output(["git", "-C", repo, "rev-parse", "--verify", rev + "^{commit}"], text=True).strip()
    d = os.path.join(BUILDS, sha); os.makedirs(BUILDS, exist_ok=True)
    with open(d + ".lock", "w") as lk:
        fcntl.flock(lk, fcntl.LOCK_EX)
        if not os.path.exists(os.path.join(d, "venv/bin/murmur")):
            t = d + ".tmp"; shutil.rmtree(t, ignore_errors=True); shutil.rmtree(d, ignore_errors=True); os.makedirs(f"{t}/src")
            # research/ (incl. screening hidden tests) is not part of the product build
            subprocess.run(f"git -C {repo} archive {sha} | tar -x -C {t}/src && rm -rf {t}/src/research", shell=True, check=True)
            subprocess.run([sys.executable, "-m", "venv", f"{d}/venv"], check=True)   # venv at final path (scripts embed it)
            subprocess.run([f"{d}/venv/bin/pip", "install", "-q", f"{t}/src"], check=True)
            os.rename(f"{t}/src", f"{d}/src"); shutil.rmtree(t, ignore_errors=True)
    return sha, f"{d}/venv/bin/murmur"

def tokens(home):
    i = c = o = 0; ts = []; n429 = 0; files = glob.glob(home + "/sessions/**/*.jsonl", recursive=True)
    for f in files:
        last = {}
        for l in open(f, errors="replace"):
            if "429" in l and ("Too Many" in l or "rate limit" in l.lower()): n429 += 1
            try: d = json.loads(l)
            except Exception: continue
            if d.get("timestamp"): ts.append(dt.datetime.fromisoformat(d["timestamp"].replace("Z", "+00:00")))
            p = d.get("payload") or {}
            if p.get("type") == "token_count" and p.get("info"): last = p["info"]["total_token_usage"]
        i += last.get("input_tokens", 0); c += last.get("cached_input_tokens", 0); o += last.get("output_tokens", 0)
    ts.sort(); act = sum(min((b - a).total_seconds(), 120) for a, b in zip(ts, ts[1:])) / 60
    return dict(active_min=round(act, 2), input=i, uncached=i - c, output=o, sessions=len(files), lines_429=n429)

def private_codex_home(home):
    os.makedirs(home, exist_ok=True); src = os.path.expanduser(os.environ.get("CODEX_HOME", "~/.codex"))
    if os.path.exists(f"{src}/config.toml"): shutil.copy(f"{src}/config.toml", f"{home}/config.toml")
    if os.path.exists(f"{src}/auth.json") and not os.path.exists(f"{home}/auth.json"): os.symlink(f"{src}/auth.json", f"{home}/auth.json")

def run_exec(name, j, out, r):
    ws = os.path.join(WS, name); repo = os.path.join(ws, "repo"); os.makedirs(ws)
    src = j["input"]
    if os.path.isdir(os.path.join(src, ".git")): subprocess.run(["git", "clone", "-q", src, repo], check=True)
    else:
        shutil.copytree(src, repo, symlinks=True); subprocess.run(["chmod", "-R", "u+w", repo], check=True)
        subprocess.run("git init -q -b main && printf '.venv/\\n' >> .gitignore && git add -A && git -c user.name=op -c user.email=op@x commit -qm 'Initial import'", shell=True, cwd=repo, check=True)
    r["base"] = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"], text=True).strip()
    if j.get("setup"): subprocess.run(ALLOWED_SETUP[j["setup"]], shell=True, cwd=repo, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    cap = int(re.match(r"\d+", j.get("cap", "30m")).group())
    with open(os.path.join(ws, "prompt.md"), "w") as f:
        f.write(open(j["brief"]).read().rstrip() + f"\n\nThe work folder is ./repo (a git repository); commit your work to its main branch (do not push). You have up to {cap} minutes.\n\n" + PR_SENTENCE + "\n")
    home = os.path.join(ws, "codex-home"); private_codex_home(home)
    env = dict(os.environ, CODEX_HOME=home)
    t0 = time.time()
    with open(os.path.join(ws, "prompt.md")) as pi, open(os.path.join(ws, "session.jsonl"), "w") as so, open(os.path.join(ws, "err.log"), "w") as se:
        try:
            r["run_exit"] = run_active(["codex", "exec", "--json", "--skip-git-repo-check", "-m", MODEL, "-c", f'model_reasoning_effort="{EFFORT}"',
                                        "--sandbox", "workspace-write", "-c", 'approval_policy="never"'], cap * 60, r, "clock", stdin=pi, stdout=so, stderr=se, cwd=ws, env=env)
        except subprocess.TimeoutExpired: r["run_exit"] = "timeout"
    r["wall_min"] = round((time.time() - t0) / 60, 2); r["ws"] = ws; r.update(tokens(home))
    if subprocess.run(["git", "-C", repo, "status", "--porcelain"], capture_output=True, text=True).stdout.strip():
        r["auto_committed"] = True   # uncommitted work at the end is committed by the runner (same for every exec run)
        subprocess.run("git add -A && git -c user.name=op -c user.email=op@x commit -qm 'Uncommitted work at end of run'", shell=True, cwd=repo)
    r["commits"] = int(subprocess.check_output(["git", "-C", repo, "rev-list", "--count", f"{r['base']}..HEAD"], text=True))
    exp = os.path.join(out, "delivered"); subprocess.run(f"mkdir -p {exp} && git -C {repo} archive HEAD | tar -x -C {exp}", shell=True)
    return exp

def run_murmur(name, j, out, r, port):
    sha, M = build(j["murmur_repo"], j["rev"]); r["murmur_sha"] = sha
    env = dict(os.environ, **(j.get("env") or {}))
    args = [M, "setup", j["brief"], "--into", WS, "--id", name, "--port-base", str(port), "--cap", j.get("cap", "30m"),
            "--repo", j["input"], "--model", MODEL, "--effort", EFFORT]
    args += ["--solo"] if j["peers"] == "solo" else ["--peers", str(j["peers"])]
    if j.get("setup"): args += ["--setup", ALLOWED_SETUP[j["setup"]], "--setup-per-agent"]
    if j.get("config"):
        cfg = os.path.join(out, "config.toml")
        with open(cfg, "w") as f:
            for k, v in j["config"].items():
                if not re.fullmatch(r"[a-z_]+", k): raise ValueError("bad config key")
                f.write(f"{k} = {json.dumps(v)}\n")
        args += ["--config", cfg]
    t0 = time.time()
    with open(os.path.join(out, "setup.log"), "w") as lf:
        r["setup_exit"] = run_active(args, 1800, stdout=lf, stderr=subprocess.STDOUT, env=env)
    ws = os.path.join(WS, name); r["ws"] = ws
    if r["setup_exit"] != 0: return None
    cap = int(re.match(r"\d+", j.get("cap", "30m")).group()) + 10
    with open(os.path.join(out, "run.log"), "w") as lf:
        try: r["run_exit"] = run_active([M, "run", ws], cap * 60, r, "clock", stdout=lf, stderr=subprocess.STDOUT, env=env)
        except subprocess.TimeoutExpired: r["run_exit"] = "timeout"
    r["wall_min"] = round((time.time() - t0) / 60, 2); r.update(tokens(os.path.join(ws, "codex-home")))
    if os.path.exists(os.path.join(ws, "logs/run.json")): shutil.copy(os.path.join(ws, "logs/run.json"), out)
    origin = os.path.join(ws, "work/origin.git"); meta = json.load(open(os.path.join(ws, "murmur.json")))
    base = meta.get("base") or subprocess.check_output(["git", "-C", origin, "rev-list", "--max-parents=0", "main"], text=True).split()[0]
    r["commits"] = int(subprocess.check_output(["git", "-C", origin, "rev-list", "--count", f"{base}..main"], text=True))
    exp = os.path.join(out, "delivered"); subprocess.run(f"mkdir -p {exp} && git -C {origin} archive main | tar -x -C {exp}", shell=True)
    return exp

def run_job(name, j, port):
    out = os.path.join(RES, name); os.makedirs(out, exist_ok=True)
    r = {"job": j, "started": dt.datetime.now().isoformat(), "model": MODEL, "effort": EFFORT}
    try:
        j = load_task(j); validate(j)
        exp = run_exec(name, j, out, r) if j["peers"] == "exec" else run_murmur(name, j, out, r, port)
        r["delivered"] = bool(exp and r.get("commits", 0) > 0)
        if r.get("setup_exit") not in (None, 0): r["error"] = "setup failed (see setup.log)"
        logs = " ".join(open(f, errors="replace").read()[-200000:] for f in glob.glob(os.path.join(out, "*.log")) +
                        glob.glob(os.path.join(r.get("ws") or "/nonexistent", "logs", "*")) if os.path.isfile(f))
        if "503 Service" in logs or "empty model catalog" in logs or "must contain at least one model" in logs:
            r["infra"] = "provider unavailable (503 or empty model catalog)"
        if exp and not j.get("_scorer"): r["score_na"] = "open task: no hidden tests by design (RUBRIC.md)"
        if exp and j.get("_scorer"):
            sd = os.path.join(LAB, "scoretmp", name)
            try:
                shutil.rmtree(sd, ignore_errors=True); shutil.copytree(os.path.dirname(j["_scorer"]), sd, symlinks=True, ignore=shutil.ignore_patterns("input"))
                subprocess.run(["chmod", "-R", "u+w", sd], check=True)
                hid = os.path.join(HIDDEN_ROOT, j["task"])
                subprocess.run(f"sudo -n cp -r {hid} {sd}/hidden && sudo -n chown -R {os.getuid()} {sd}/hidden", shell=True, check=True)
                s = subprocess.run(["bash", os.path.join(sd, "score.sh"), exp], capture_output=True, text=True, timeout=1200, cwd=sd)
                open(os.path.join(out, "score.log"), "w").write(s.stdout[-20000:] + "\n--stderr--\n" + s.stderr[-20000:])
                r["score"] = json.loads(s.stdout.strip().splitlines()[-1])
            except Exception as e: r["score_error"] = repr(e)
            finally: shutil.rmtree(sd, ignore_errors=True)
        if exp:
            try:
                m = subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "mutation.py"), exp, "30", "3", ALLOWED_SETUP.get(j.get("setup") or "py")],
                                   capture_output=True, text=True, timeout=3600)
                if not m.stdout.strip(): raise RuntimeError(f"mutation.py exit {m.returncode}, no output: {m.stderr[-300:]}")
                r["mutation"] = json.loads(m.stdout.strip().splitlines()[-1])
            except Exception as e: r["mutation_error"] = repr(e)
        if r.get("ws"):
            hits = subprocess.run(["rg", "-l", "-e", "murmur-lab-hidden|research/tasks/[^ ]*/hidden|scoretmp", r["ws"]], capture_output=True, text=True).stdout.split()
            r["leak_hits"] = len(hits)
    except Exception as e:
        r["error"] = repr(e)
    r["finished"] = dt.datetime.now().isoformat()
    json.dump(r, open(os.path.join(out, "result.json.tmp"), "w"), indent=1); os.replace(os.path.join(out, "result.json.tmp"), os.path.join(out, "result.json"))

def tokens_used():
    t = 0
    for f in glob.glob(RES + "/*/result.json"):
        try: t += json.load(open(f)).get("input", 0) or 0
        except Exception: pass
    return t
def used():
    return sum(1 for _ in open(LEDGER)) if os.path.exists(LEDGER) else 0

def inflight():
    """Ledger jobs without a result.json whose `--one` child process is still alive."""
    if not os.path.exists(LEDGER): return set()
    names = {json.loads(l)["name"] for l in open(LEDGER) if l.strip()}
    names = {n for n in names if not os.path.exists(os.path.join(RES, n, "result.json"))}
    alive = subprocess.run(["pgrep", "-af", "runner.py --one"], capture_output=True, text=True).stdout
    return {n for n in names if f"--one {n} " in alive}

def main():
    for d in (Q, RES, BUILDS, WS, TASKS, os.path.join(LAB, "repos"), os.path.join(LAB, "scoretmp")): os.makedirs(d, exist_ok=True)
    running = {}; port = int(os.environ.get("MURMUR_LAB_PORT0", "47000"))
    while True:
        for n, p in list(running.items()):
            if p.poll() is not None: running.pop(n)
        # jobs started by an earlier runner parent (restart) still count toward MAX_PAR
        orphans = {n for n in inflight() if n not in running}
        if os.path.exists(os.path.join(LAB, "CLOSED")):
            for f in glob.glob(Q + "/*.json"): os.rename(f, f + ".rejected-lab-closed")
        for f in sorted(glob.glob(Q + "/*.json"), key=os.path.getmtime):
            if len(running) + len(orphans) >= MAX_PAR: break
            name = re.sub(r"[^A-Za-z0-9_-]", "_", os.path.basename(f)[:-5])[:80]
            claimed = f + ".claimed"
            try: os.rename(f, claimed)
            except FileNotFoundError: continue
            try: j = json.load(open(claimed))
            except Exception as e: j = {"_parse_error": repr(e)}
            if not NAME_RE.match(name):
                os.makedirs(os.path.join(RES, name), exist_ok=True)
                json.dump({"job": j, "error": "only scheduler-submitted, pre-registered jobs (C<k>-NN-*) are accepted"}, open(os.path.join(RES, name, "result.json"), "w")); continue
            if used() >= BUDGET or tokens_used() >= TOKEN_CAP:
                os.makedirs(os.path.join(RES, name), exist_ok=True)
                json.dump({"job": j, "error": f"lab budget exhausted ({BUDGET} runs or {TOKEN_CAP} input tokens)"}, open(os.path.join(RES, name, "result.json"), "w")); continue
            with open(LEDGER, "a") as lg: lg.write(json.dumps({"name": name, "t": dt.datetime.now().isoformat(), "job": j}) + "\n")
            p0 = int(os.environ.get("MURMUR_LAB_PORT0", "47000")); port = p0 + (port - p0 + 400) % 8000
            running[name] = subprocess.Popen([sys.executable or "/usr/bin/python3", __file__, "--one", name, json.dumps(j), str(port)])
        time.sleep(3)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--one": run_job(sys.argv[2], json.loads(sys.argv[3]), int(sys.argv[4]))
    else: main()
