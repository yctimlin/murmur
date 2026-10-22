#!/bin/bash
# One-shot status: alive jobs, finished/judged counts, latest adapt look.
cd /workspace/r4; date +'%m-%d %H:%M'
for p in $(pgrep -f '^python3 /workspace/r4/tools/runner.py r4-lab-runner') $(cat judge/E1.loop.pid analysis/adapt/loop.pid analysis/mutation_backfill.pid 2>/dev/null); do ps -p $p -o pid=,args= >/dev/null && ps -p $p -o pid=,args= | cut -c1-70 || echo "DEAD $p"; done
pgrep -af 'runner.py --one' | grep -o 'E1-[A-Za-z0-9-]*' | sort -u | tr '\n' ' '; echo; ls lab/queue/*.json 2>/dev/null
echo "finished $(ls lab/results/*/result.json | wc -l), judged $(ls judge/E1/*.score.json 2>/dev/null | wc -l)"
f=$(ls analysis/adapt/1020-*.json analysis/adapt/10*-*.json 2>/dev/null | sort | tail -1); python3 -c "
import json,sys;d=json.load(open('$f'));print('$f', d['decisions'], {k:{x:round(d[k][x],2) if isinstance(d[k][x],float) else d[k][x] for x in ('P_keep','dq_mean','tok_ratio_med','act_ratio_med','n_judged')} for k in ('C1','C2') if k in d})"
tail -2 analysis/mutation_backfill.log | cut -c1-100
