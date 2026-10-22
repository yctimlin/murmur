#!/usr/bin/env python3
"""Forensic timeline extractor (directive 10-21 14:02): raw run logs -> one chronological event stream per run.
usage: forensics_extract.py [RUN_ID ...]   (default: every judged E1 run)
Writes analysis/forensics/timelines/<rid>.md. Sources (unsummarized, only truncated):
  codex rollouts of root/peers/solo (tool calls, outputs head, reasoning headings, assistant text, inter-agent mail,
  task_started/complete), message-board posts (sqlite), git history of origin.git (or solo repo), judge verdicts.
Times: 'A' = freeze-excluded active minutes since the first event of the run (r4eval definition); 'W' = Taipei wall clock."""
import json, sys, glob, os, re, sqlite3, subprocess, datetime as dt
sys.path.insert(0, '/workspace/r4/tools')
from r4eval import freeze_windows

R = '/workspace/r4'; L = f'{R}/lab'; OUT = f'{R}/analysis/forensics/timelines'
TZ = dt.timezone(dt.timedelta(hours=8))
FW = freeze_windows()


def ts(s): return dt.datetime.fromisoformat(s.replace('Z', '+00:00'))
def cut(s, n): s = re.sub(r'\s+', ' ', s or '').strip(); return s if len(s) <= n else s[:n] + f' …[+{len(s)-n}]'


def texts(content):
    return ' '.join(c.get('text', '') for c in content or [] if isinstance(c, dict) and c.get('type') in ('input_text', 'output_text', 'text'))


def rollout_events(path):
    ev, who = [], '?'
    for l in open(path, errors='replace'):
        try: r = json.loads(l)
        except Exception: continue
        p = r.get('payload') or {}; t = r.get('timestamp'); typ, pt = r['type'], p.get('type')
        if not t: continue
        t = ts(t)
        if typ == 'session_meta' and who == '?':
            m = re.search(r'"agent_path":"([^"]+)"', l); who = m[1].replace('/root/', '') if m else 'root'
            continue
        if pt == 'task_started': ev.append((t, who, 'TURN_START', p.get('turn_attribution', {}).get('turn_trigger', '')))
        elif pt == 'task_complete': ev.append((t, who, 'TURN_END', cut(p.get('last_agent_message'), 1500)))
        elif pt == 'custom_tool_call': ev.append((t, who, 'CALL', cut(p.get('input'), 600)))
        elif pt == 'function_call': ev.append((t, who, 'FCALL', f"{p.get('name')} {cut(p.get('arguments'), 400)}"))
        elif pt in ('custom_tool_call_output', 'function_call_output'):
            o = p.get('output'); o = texts(o) if isinstance(o, list) else str(o)
            ev.append((t, who, 'OUT', cut(o, 300)))
        elif pt == 'reasoning':
            s = ' | '.join(x.get('text', '') for x in p.get('summary', []) if isinstance(x, dict))
            if s: ev.append((t, who, 'THINK', cut(s, 300)))
        elif pt == 'message' and p.get('role') == 'assistant':
            ev.append((t, who, 'SAY', cut(texts(p.get('content')), 1200)))
        elif pt == 'agent_message':
            ev.append((t, who, 'MAIL', f"{p.get('author')}->{p.get('recipient')}: {cut(texts(p.get('content')), 500)}"))
        elif pt == 'error' or (pt == 'stream_error'):
            ev.append((t, who, 'ERROR', cut(json.dumps(p), 300)))
    return ev


def board_events(db):
    ev = []
    try:
        c = sqlite3.connect(f'file:{db}?mode=ro', uri=True)
        for ch, au, tsu, pl in c.execute('select channel,author,timestamp,payload from posts order by seq'):
            try: txt = json.loads(pl).get('text', pl)
            except Exception: txt = pl
            ev.append((dt.datetime.fromtimestamp(tsu / 1e6, dt.timezone.utc), au.replace('/root/', ''), f'POST#{ch}', cut(txt, 900)))
    except Exception as e:
        ev.append((None, 'x', 'BOARD_ERR', str(e)))
    return ev


def git_events(gitdir):
    ev = []
    if not os.path.exists(gitdir): return ev
    out = subprocess.run(['git', f'--git-dir={gitdir}', 'log', '--all', '--format=@@%H|%aI|%an|%D|%s', '--shortstat'],
                         capture_output=True, text=True).stdout
    cur = None
    for line in out.splitlines():
        if line.startswith('@@'):
            h, t, an, refs, s = line[2:].split('|', 4)
            cur = [ts(t), an, 'COMMIT', f'{h[:7]} [{refs}] {cut(s, 200)}']; ev.append(cur)
        elif line.strip() and cur: cur[3] += ' (' + line.strip() + ')'
    refs = subprocess.run(['git', f'--git-dir={gitdir}', 'for-each-ref', '--format=%(refname:short) %(objectname:short)'],
                          capture_output=True, text=True).stdout
    return [tuple(e) for e in ev], refs


def active_clock(stamps):
    """map wall time -> freeze-excluded active minutes (gaps capped at 120 s, as r4eval.active)."""
    stamps = sorted(stamps); acc = [0.0]
    for a, b in zip(stamps, stamps[1:]):
        g = (b - a).total_seconds() - sum(max(0, (min(b, fb) - max(a, fa)).total_seconds()) for fa, fb in FW)
        acc.append(acc[-1] + min(max(g, 0), 120) / 60)
    import bisect
    def f(t):
        i = bisect.bisect_right(stamps, t) - 1
        return acc[max(i, 0)]
    return f


def run(rid):
    ws = f'{L}/ws/{rid}'; resd = f'{L}/results/{rid}'
    res = json.load(open(f'{resd}/result.json'))
    rolls = glob.glob(f'{ws}/**/sessions/**/*.jsonl', recursive=True)
    ev = []
    for f in rolls: ev += rollout_events(f)
    db = f'{ws}/codex-home/agent_message_board_1.sqlite'
    if os.path.exists(db): ev += [e for e in board_events(db) if e[0]]
    gd = f'{ws}/work/origin.git' if os.path.exists(f'{ws}/work/origin.git') else f'{ws}/repo/.git'
    gev, refs = git_events(gd) if os.path.exists(gd) else ([], '')
    t0 = min(e[0] for e in ev); t1 = max(e[0] for e in ev)
    ev += [e for e in gev if e[0] >= t0 - dt.timedelta(minutes=1)]
    ev.sort(key=lambda e: e[0])
    A = active_clock([e[0] for e in ev])
    o = [f'# Timeline {rid}', '']
    keep = {k: res.get(k) for k in ('run_exit', 'wall_min', 'active_min', 'input', 'commits', 'delivered', 'murmur_sha', 'capped')}
    o.append(f'result.json: {json.dumps(keep)}')
    sc = f'{R}/judge/E1/{rid}.score.json'
    if os.path.exists(sc):
        s = json.load(open(sc))
        o.append(f"score overall {s.get('overall')}")
        for j in s.get('judgments', []):
            o.append(f"- judge: {json.dumps({k: j.get(k) for k in ('coverage','correctness','design','robustness','code','ux','overall','guess')})}")
            for x in j.get('severe', []): o.append(f'  - severe: {x}')
    o.append(f'judge evidence (full text): {R}/judge/E1/{rid}.j1.md, .j2.md')
    o.append(f'git refs at end ({gd}):\n```\n{refs.strip()}\n```')
    # per-agent summary
    agents = sorted({e[1] for e in ev if e[2] in ('CALL', 'FCALL', 'TURN_END')})
    o.append('\n## Per-agent summary (A = active min)')
    for a in agents:
        ae = [e for e in ev if e[1] == a]
        calls = [e for e in ae if e[2] in ('CALL', 'FCALL')]
        ends = [f'{A(e[0]):.1f}' for e in ae if e[2] == 'TURN_END']
        starts = [f'{A(e[0]):.1f}' for e in ae if e[2] == 'TURN_START']
        gaps = [(A(x[0]), A(y[0]) - A(x[0])) for x, y in zip(calls, calls[1:]) if A(y[0]) - A(x[0]) > 3]
        o.append(f'- {a}: calls {len(calls)}, first A{A(ae[0][0]):.1f}, last A{A(ae[-1][0]):.1f}, turn starts {starts}, turn ends {ends}, '
                 f'idle gaps >3 active min between calls: {[f"A{s:.1f}+{g:.1f}" for s, g in gaps]}')
    o.append(f'- run span: active {A(t1):.1f} min, wall {(t1 - t0).total_seconds() / 60:.1f} min')
    o.append('\n## Event stream (A active-min | W Taipei | who | kind | content)')
    for t, who, k, c in ev:
        o.append(f'A{A(t):6.1f} | {t.astimezone(TZ):%H:%M:%S} | {who:5} | {k:9} | {c}')
    os.makedirs(OUT, exist_ok=True)
    open(f'{OUT}/{rid}.md', 'w').write('\n'.join(o) + '\n')
    return len(ev)


if __name__ == '__main__':
    ids = sys.argv[1:] or sorted(os.path.basename(p)[:-11] for p in glob.glob(f'{R}/judge/E1/*.score.json'))
    for rid in ids:
        try: print(rid, run(rid))
        except Exception as e: print(rid, 'ERR', repr(e))
