"""Per-agent breakdown of murmur/solo Codex rollouts for one workspace.
usage: python3 sessions.py WS [--final]"""
import json, sys, glob, re, collections, datetime as dt
def ts(s): return dt.datetime.fromisoformat(s.replace('Z','+00:00'))
def agent_stats(path):
    st = collections.Counter(); first=last=done=None; name='?'; finals=[]; ctx=[]
    for l in open(path):
        r = json.loads(l); p = r.get('payload', {}) or {}; t = ts(r['timestamp'])
        first = first or t; last = t
        if r['type'] == 'session_meta' and name == '?':
            m = re.search(r'"agent_path":"([^"]+)"', l)
            name = m[1] if m else 'root/solo'
        pt = p.get('type')
        if pt == 'token_count' and p.get('info'):
            lu = p['info']['last_token_usage']; st['calls'] += 1
            st['in'] += lu['input_tokens']; st['cached'] += lu['cached_input_tokens']; st['out'] += lu['output_tokens']
            ctx.append(lu['input_tokens'])
        if pt == 'task_complete': done = t; st['task_complete'] += 1
        if pt == 'task_started': st['task_started'] += 1
        if pt == 'function_call': st['fc.' + p['name']] += 1
        if pt == 'custom_tool_call':
            inp = p.get('input', '')
            for m in re.findall(r'tools\.(\w+)', inp): st['ct.' + m.replace('collaboration__', 'c.')] += 1
            if 'push origin HEAD:main' in inp or 'push origin main' in inp: st['push_main'] += 1
            if 'HEAD:draft/' in inp: st['push_draft'] += 1
            if re.search(r'pytest|unittest', inp): st['tests'] += 1
        if pt == 'agent_message' and p.get('author') != name:
            st['msgs_in'] += 1
        if pt == 'message' and p.get('role') == 'assistant':
            txt = ''.join(c.get('text', '') for c in p.get('content', []) if isinstance(c, dict))
            finals.append((t, txt))
    return dict(name=name, first=first, last=last, done=done, st=st, finals=finals, ctx=ctx)
if __name__ == '__main__':
    ws = sys.argv[1]
    files = sorted(glob.glob(ws + '/**/sessions/**/rollout-*.jsonl', recursive=True))
    agents = [agent_stats(f) for f in files]
    t0 = min(a['first'] for a in agents)
    for a in agents:
        s = a['st']; m = lambda t: round((t - t0).total_seconds()/60, 1) if t else None
        keys = {k: v for k, v in s.items() if k not in ('in','cached','out','calls')}
        print(f"{a['name']:10s} start {m(a['first'])} end {m(a['last'])} done {m(a['done'])} calls {s['calls']} in {s['in']/1e6:.2f}M uncached {(s['in']-s['cached'])/1e3:.0f}K out {s['out']/1e3:.0f}K ctxmax {max(a['ctx'] or [0])/1e3:.0f}K")
        print('    ', dict(sorted(keys.items())))
        if '--final' in sys.argv and a['finals']:
            t, txt = a['finals'][-1]; print('     FINAL@', m(t), txt[:600].replace('\n', ' | '))
