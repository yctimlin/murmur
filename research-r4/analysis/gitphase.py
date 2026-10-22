"""Timeline of ref updates in a murmur run's origin.git (reflogs) + size of drafts vs main."""
import subprocess, sys, os, glob, json, datetime as dt
ws = sys.argv[1]; o = ws + '/work/origin.git'
meta = json.load(open(ws + '/murmur.json')); base = meta['base']
def g(*a): return subprocess.run(['git', '-C', o, *a], capture_output=True, text=True).stdout
ev = []
for lf in glob.glob(o + '/logs/refs/heads/**', recursive=True):
    if os.path.isdir(lf): continue
    ref = lf.split('logs/refs/heads/')[1]
    for line in open(lf):
        head, _, msg = line.partition('\t')
        parts = head.split(); t = int(parts[-2]); ev.append((t, ref, parts[1][:7]))
ev.sort(); t0 = ev[0][0] if ev else 0
start = dt.datetime.fromisoformat(json.load(open(ws + '/logs/run.json'))['started_at']).timestamp()
def added(ref):
    s = g('diff', '--shortstat', base, ref).strip(); return s
print('events (min since start):')
for t, ref, sha in ev:
    print(f'  {(t-start)/60:6.1f} {ref:20s} {sha}')
for ref in sorted(set(r for _, r, _ in ev)):
    print(f'  {ref:20s} {added(ref)}')
