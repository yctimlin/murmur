#!/usr/bin/env python3
"""Deterministic mutation score of a deliverable's own test suite (round-3 sealed scorer).
usage: mutation.py ARTIFACT_DIR [n=30] [seed=3] [SETUP_CMD] -> prints {"mutants","killed","score","baseline_green","deselected"}
The artifact is copied to a temp dir; SETUP_CMD (the arm's setup command, e.g. creating .venv) runs there first.
The unmutated suite runs twice; tests failing in either run are deselected. If nothing passes, score is null
(missing), not 0.
Mutates non-test .py files (comparison flips, +/- swap, constant off-by-one, boolean negation,
return-None), one mutation per mutant, then runs `python -m pytest -x -q` with a 120 s timeout.
A mutant counts as killed if the suite fails or times out. If no test passes on the unmutated code, score is null."""
import ast, json, os, random, shutil, subprocess, sys, tempfile
SW = {ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE, ast.LtE: ast.Gt, ast.Eq: ast.NotEq, ast.NotEq: ast.Eq}
def sites(tree):
    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Compare) and type(n.ops[0]) in SW: out.append(("cmp", n))
        elif isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)): out.append(("arith", n))
        elif isinstance(n, ast.Constant) and type(n.value) is int: out.append(("const", n))
        elif isinstance(n, ast.If): out.append(("not", n))
        elif isinstance(n, ast.Return) and n.value is not None: out.append(("ret", n))
    return out
def apply(kind, n):
    if kind == "cmp": n.ops[0] = SW[type(n.ops[0])]()
    elif kind == "arith": n.op = ast.Sub() if isinstance(n.op, ast.Add) else ast.Add()
    elif kind == "const": n.value = n.value + 1
    elif kind == "not": n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)
    elif kind == "ret": n.value = ast.Constant(value=None)
def py_of(d):
    py = os.path.join(d, ".venv/bin/python"); return py if os.path.exists(py) else sys.executable
def failing(d):
    try: r = subprocess.run([py_of(d), "-m", "pytest", "-q", "-rfE", "-p", "no:cacheprovider", "-o", "addopts="], cwd=d, capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired: return None, None
    fails = {l.split(" - ")[0].split(" ", 1)[1] for l in r.stdout.splitlines() if l.startswith(("FAILED ", "ERROR "))}
    passed = "passed" in r.stdout.splitlines()[-1] if r.stdout.strip() else False
    return fails, passed
DESEL = []; TMO = [120]
def run_tests(d):
    """True = suite green, False = red (killed), None = timed out (mutant not scored)."""
    try: return subprocess.run([py_of(d), "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider", "-o", "addopts=", *DESEL], cwd=d, capture_output=True, timeout=TMO[0]).returncode == 0
    except subprocess.TimeoutExpired: return None
def main():
    art = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 30; rng = random.Random(int(sys.argv[3]) if len(sys.argv) > 3 else 3)
    files = sorted(os.path.relpath(os.path.join(r, f), art) for r, ds, fs in os.walk(art) for f in fs
                   if f.endswith(".py") and not f.startswith("test") and f not in ("conftest.py", "setup.py") and "/tests/" not in "/" + os.path.relpath(r, art) + "/"
                   and not any(c.startswith(".") and c != "." for c in os.path.relpath(r, art).split(os.sep)))
    pool = []
    for f in files:
        try: t = ast.parse(open(os.path.join(art, f)).read())
        except Exception: continue
        pool += [(f, i) for i in range(len(sites(t)))]
    tmp = tempfile.mkdtemp(); d = os.path.join(tmp, "a"); shutil.copytree(art, d, symlinks=True)
    if len(sys.argv) > 4 and sys.argv[4]:
        subprocess.run(sys.argv[4], shell=True, cwd=d, capture_output=True, timeout=900)
    f1, p1 = failing(d); f2, p2 = failing(d)
    if f1 is None or f2 is None or not (p1 or p2):
        print(json.dumps({"mutants": 0, "killed": 0, "score": None, "baseline_green": False})); shutil.rmtree(tmp, ignore_errors=True); return
    DESEL.extend(f"--deselect={t}" for t in sorted(f1 | f2))
    import time as _t; t0 = _t.time(); green = run_tests(d); TMO[0] = max(120, 3 * (_t.time() - t0))
    if not green or not pool:
        print(json.dumps({"mutants": 0, "killed": 0, "score": None, "baseline_green": green, "deselected": len(DESEL)})); shutil.rmtree(tmp, ignore_errors=True); return
    chosen = rng.sample(pool, min(n, len(pool))); killed = 0; timeouts = 0
    for f, i in chosen:
        p = os.path.join(d, f); orig = open(p).read(); t = ast.parse(orig); k, node = sites(t)[i]; apply(k, node)
        try: open(p, "w").write(ast.unparse(t))
        except Exception: continue
        res = run_tests(d)
        if res is None: timeouts += 1
        elif not res: killed += 1
        open(p, "w").write(orig)
    shutil.rmtree(tmp, ignore_errors=True)
    scored = len(chosen) - timeouts
    print(json.dumps({"mutants": len(chosen), "killed": killed, "timeouts": timeouts, "score": round(killed / scored, 4) if scored else None, "baseline_green": True, "deselected": len(DESEL)}))
if __name__ == "__main__": main()
