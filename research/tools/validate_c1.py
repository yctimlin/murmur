#!/usr/bin/env python3
"""Read-only validation of the preregistered C1 design; never submit a lab job."""
import collections
import itertools
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
BARE = Path('/workspace/self3/labdata/repos/r3.git')
BASE = 'f95eaa169f1cd1741d1fbf02d7d939f8e77ba156'
ORIG = 'eec78f846a8c373f4c351f03f9fd89cbe01cb7a7'

def require(condition, message):
    if not condition:
        raise ValueError(message)

def main():
    data = json.loads((ROOT / 'research/prereg/C1.json').read_text())
    jobs = data['jobs']
    require(data['batch'] == 'C1', 'batch mismatch')
    require((ROOT / data['notebook']).is_file(), 'notebook missing')
    require(len(jobs) == 18, 'C1 must have exactly 18 jobs')
    tasks = {'document_catalog', 'ledger_replay', 'reserveplan'}
    require({j['task'] for j in jobs[:3]} == tasks, 'first block must calibrate all tasks')
    require(all(j['peers'] == 'exec' and j['block'] == 'b00-calibration' for j in jobs[:3]), 'calibration must come first')
    for job in jobs:
        require(job['task'] in tasks, 'unknown task')
        require(job['peers'] in (3, 'exec'), 'C1 has only three-peer and exec jobs')
        require(bool(re.fullmatch(r'\d+m', job['cap'])) and 0 < int(job['cap'][:-1]) <= 100, 'invalid cap')
        require(job['cap'] == ('90m' if job['task'] == 'reserveplan' else '60m'), 'unequal task caps')
        require(not job.get('env') and not job.get('config'), 'C1 has no treatment switches')
        require(job['rev'] == (ORIG if job['arm'] == 'orig' else BASE), 'revision differs from frozen design')
    for rev in {j['rev'] for j in jobs}:
        subprocess.run(['git', f'--git-dir={BARE}', 'rev-parse', '--verify', f'{rev}^{{commit}}'], check=True, stdout=subprocess.DEVNULL)
    blocks = [(key, list(group)) for key, group in itertools.groupby(jobs, key=lambda j:j['block'])]
    require(len(blocks) == 7 and len({b[0] for b in blocks}) == 7, 'noncontiguous/repeated blocks')
    require(all(1 <= len(group) <= 3 for _, group in blocks), 'block exceeds concurrency')
    for task in ('ledger_replay', 'reserveplan'):
        subset = [j for j in jobs if j['task'] == task and j['peers'] == 3]
        counts = collections.Counter(j['arm'] for j in subset)
        require(counts['base3_A'] == counts['base3_B'] == 3, 'need three A/A pairs per task')
        require(counts['orig'] == (3 if task == 'ledger_replay' else 0), 'bug-fix replication mismatch')
        for _, group in blocks[1:]:
            if group[0]['task'] != task:
                continue
            require(len({j['task'] for j in group}) == 1, 'comparison block mixes tasks')
            aa = [j for j in group if j['arm'].startswith('base3_')]
            require(len(aa) == 2, 'A/A pair missing')
            require({j['arm'] for j in aa} == {'base3_A', 'base3_B'}, 'A/A labels invalid')
            stripped = [{k:v for k,v in j.items() if k != 'arm'} for j in aa]
            require(stripped[0] == stripped[1], 'A/A differs in treatment')
    estimate = sum(3000000 if j['peers'] == 'exec' else 12000000 for j in jobs)
    means = data['predictions']['run_mean_forecasts']
    forecast = sum(means[j['task']][j['arm']]['input'] for j in jobs)
    require(estimate == 189000000, 'scheduler budget estimate mismatch')
    require(forecast == data['predictions']['budget']['model_expected_input_tokens'] == 203779200, 'model cost forecast mismatch')
    require(estimate < 450000000 and len(jobs) < 36, 'initial round budget exceeded')
    print(json.dumps({'valid':True,'jobs':len(jobs),'blocks':[{'block':k,'jobs':len(g)} for k,g in blocks],
        'aa_pairs_per_task':3,'base3_replicates_per_task':6,'bug_fix_pairs':3,'scheduler_estimate_input':estimate,
        'model_forecast_input':forecast,'remaining_jobs':36-len(jobs),'revisions_verified_in':str(BARE)}, indent=2))

if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, subprocess.CalledProcessError) as error:
        print(f'C1 validation failed: {error}', file=sys.stderr)
        sys.exit(1)
