#!/usr/bin/env python3
"""Where does the active time go? Per-agent, per-activity active minutes for every judged E1 run (forensics, 10-21).
Each gap between consecutive events of one agent (freeze-excluded, capped at 120 s as in r4eval.active) is charged to
the activity of the tool call it belongs to: the gap before a call (model deliberation) and the gap until its output
(execution) both go to that call's kind. Kinds:
  coord   board/mail/wait/list/spawn calls with no shell command
  others  git fetch/show/diff/log/checkout/merge/rebase/cherry-pick (reading or integrating others' work)
  test    pytest/unittest/npm test/etc.
  smoke   starting the app / curl / browser checks
  edit    apply_patch, heredoc writes
  gitw    commit/push/add/status
  read    other shell (cat, sed, rg, ls, python one-offs)
  final   text after the last call (final message)
Also per run: main lines added over time and the share of active time after the last commit that added >50 lines
to main ('tail').
usage: time_accounting.py [RID ...] -> analysis/forensics/time_accounting.json + table on stdout"""
import json, sys, glob, os, re, subprocess, collections, datetime as dt
sys.path.insert(0, '/workspace/r4/tools')
from r4eval import freeze_windows
R = '/workspace/r4'; L = f'{R}/lab'; FW = freeze_windows()
COORD = re.compile(r'collaboration__|send_message|wait_agent|followup_task|list_agents|spawn_agent|board|clock|\bwait\b')


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))


def gap(a, b):
    g = (b - a).total_seconds() - sum(max(0, (min(b, fb) - max(a, fa)).total_seconds()) for fa, fb in FW)
    return min(max(g, 0), 120) / 60


def kind(name, inp):
    shell = 'exec_command' in inp or name in ('exec_command', 'shell')
    if not shell and (COORD.search(name) or COORD.search(inp)): return 'coord'
    if re.search(r'git (fetch|pull|merge|rebase|log|diff|show|checkout|switch|reset|cherry|worktree)', inp) and not re.search(r'pytest|unittest', inp): return 'others'
    if re.search(r'pytest|unittest|npm (run )?test|cargo test|go test|make test|node --test', inp): return 'test'
    if re.search(r'curl |playwright|chromium|wget |http://(localhost|127)|serve|uvicorn|flask run|app\.py', inp): return 'smoke'
    if name == 'apply_patch' or re.search(r'apply_patch|cat >|<<', inp): return 'edit'
    if re.search(r'git (add|commit|push|status)', inp): return 'gitw'
    return 'read'


def agent(path):
    who = '?'; ev = []
    for l in open(path, errors='replace'):
        try: r = json.loads(l)
        except Exception: continue
        p = r.get('payload') or {}; pt = p.get('type')
        if r['type'] == 'session_meta' and who == '?':
            m = re.search(r'"agent_path":"([^"]+)"', l); who = m[1].replace('/root/', '') if m else 'root'
        if not r.get('timestamp'): continue
        t = ts(r['timestamp'])
        if pt in ('function_call', 'custom_tool_call'):
            ev.append((t, 'call', kind(p.get('name', ''), str(p.get('input', '')) + str(p.get('arguments', '')))))
        elif pt in ('function_call_output', 'custom_tool_call_output', 'reasoning', 'message', 'task_complete', 'task_started'):
            ev.append((t, pt, None))
    ev.sort(key=lambda e: e[0])
    acc = collections.Counter(); cur = None
    # charge each gap to the next call's kind if it ends at a call, else to the pending call's kind
    for (a, _, _), (b, typ, k) in zip(ev, ev[1:]):
        if typ == 'call': cur = k
        acc[cur or 'final'] += gap(a, b)
        if typ == 'task_complete': cur = None
    return who, acc, (ev[0][0], ev[-1][0]) if ev else (None, None)


def main_growth(ws):
    gd = f'{ws}/work/origin.git'
    if not os.path.exists(gd): gd = f'{ws}/repo/.git'
    if not os.path.exists(gd): return []
    out = subprocess.run(['git', f'--git-dir={gd}', 'log', '--first-parent', 'main' if 'origin.git' in gd else 'HEAD',
                          '--format=@@%aI', '--numstat'], capture_output=True, text=True).stdout
    rows = []; t = None; add = 0
    for line in out.splitlines():
        if line.startswith('@@'):
            if t: rows.append((t, add))
            t = ts(line[2:]); add = 0
        elif line.strip():
            a = line.split('\t')[0]; add += int(a) if a.isdigit() else 0
    if t: rows.append((t, add))
    return sorted(rows)


def run(rid):
    ws = f'{L}/ws/{rid}'
    agents = [agent(f) for f in glob.glob(f'{ws}/**/sessions/**/rollout-*.jsonl', recursive=True)]
    t0 = min(a[2][0] for a in agents if a[2][0]); t1 = max(a[2][1] for a in agents if a[2][1])
    span = gap(t0, t0)  # 0
    stamps = sorted([a[2][0] for a in agents] + [a[2][1] for a in agents])
    per = {w: {k: round(v, 1) for k, v in acc.items()} for w, acc, _ in agents}
    tot = collections.Counter()
    for w, acc, _ in agents:
        if w != 'root' or len(agents) == 1: tot.update(acc)
    g = main_growth(ws)
    # active minutes on a run clock: integrate gaps over all event stamps of the run
    allst = sorted(set(e for w in [] for e in w))
    big = [t for t, add in g if add > 50 and t0 <= t <= t1 + dt.timedelta(minutes=5)]
    ev_all = []
    for f in glob.glob(f'{ws}/**/sessions/**/rollout-*.jsonl', recursive=True):
        for l in open(f, errors='replace'):
            m = re.search(r'"timestamp":"([^"]+)"', l)
            if m: ev_all.append(ts(m[1]))
    ev_all.sort()
    def A(t):
        s = 0
        for a, b in zip(ev_all, ev_all[1:]):
            if b > t: break
            s += gap(a, b)
        return s
    run_act = A(ev_all[-1])
    last_big = A(big[-1]) if big else None
    return {'run': rid, 'run_active': round(run_act, 1), 'per_agent': per,
            'peer_total': {k: round(v, 1) for k, v in tot.items()},
            'main_commits': len([1 for t, _ in g if t >= t0]), 'main_added': sum(a for t, a in g if t >= t0),
            'last_big_main_commit_A': None if last_big is None else round(last_big, 1),
            'tail_share': None if last_big is None else round(1 - last_big / run_act, 2)}


if __name__ == '__main__':
    ids = sys.argv[1:] or sorted(os.path.basename(p)[:-11] for p in glob.glob(f'{R}/judge/E1/*.score.json'))
    out = []
    K = ['edit', 'read', 'test', 'smoke', 'others', 'coord', 'gitw', 'final']
    print(f"{'run':22} {'q':>5} {'act':>5} " + ' '.join(f'{k:>6}' for k in K) + '  mainL  lastBig tail')
    for rid in ids:
        try: d = run(rid)
        except Exception as e: print(rid, 'ERR', repr(e)); continue
        sc = json.load(open(f'{R}/judge/E1/{rid}.score.json')).get('overall') if os.path.exists(f'{R}/judge/E1/{rid}.score.json') else None
        d['q'] = sc; out.append(d)
        pt = d['peer_total']; s = sum(pt.values()) or 1
        print(f"{rid:22} {sc or 0:5.2f} {d['run_active']:5.1f} " + ' '.join(f'{100*pt.get(k,0)/s:5.0f}%' for k in K) +
              f"  {d['main_added']:5d}  {d['last_big_main_commit_A']}  {d['tail_share']}")
    json.dump(out, open(f'{R}/analysis/forensics/time_accounting.json', 'w'), indent=1)
