#!/usr/bin/env python3
"""E5 poll: valid/infra/unjudged/in-flight/queued counts (uses r4eval.is_infra)."""
import sys, json, glob, os
sys.argv = ['r4eval.py', 'noop']
src = open('/workspace/r4/tools/r4eval.py').read().split("# ---------- run diagnostics")[0]
exec(compile(src, 'r4eval', 'exec'))
R = '/workspace/r4/lab/results'; JD = '/workspace/r4/judge/E5'
valid, infra, unj, fl = [], [], [], []
for d in sorted(glob.glob(R + '/E5-*')):
    n = os.path.basename(d); p = d + '/result.json'
    if not os.path.exists(p): fl.append(n); continue
    r = json.load(open(p))
    if is_infra(r): infra.append(n); continue
    valid.append(n)
    if not os.path.exists(f'{JD}/{n}.score.json'): unj.append(n)
q = sorted(os.path.basename(f)[:-5] for f in glob.glob('/workspace/r4/lab/queue/E5-*.json'))
print(f'valid {len(valid)}/12, judged {len(valid)-len(unj)}; unjudged {unj}; in flight {fl}; queued {q}')
if infra: print('INFRA (needs rerun):', infra)
