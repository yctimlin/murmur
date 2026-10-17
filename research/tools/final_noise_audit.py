#!/usr/bin/env python3
"""Independent raw-result arithmetic and illustrative paired-cost sizing.

Standard library only; does not import the primary C1 analyzer. This is an
analysis of completed jobs, not a preregistration or a new lab experiment.
"""
import json
import math
from pathlib import Path
from statistics import NormalDist, mean, stdev

ROOT = Path(__file__).resolve().parents[2]
METRICS = ('active_min', 'input', 'uncached')


def summary(values):
    return dict(n=len(values), mean=mean(values), sd=stdev(values),
                min=min(values), max=max(values))


def load(batch):
    raw = ROOT / 'research/data/raw' / batch
    return [dict(json.loads((raw / (j['name'] + '.json')).read_text()),
                 name=j['name'], **j['prereg'])
            for j in json.loads((raw / 'jobs.json').read_text())]


def value(row, metric):
    return row['score']['rate'] if metric == 'score' else row[metric]


c1, c2 = load('C1'), load('C2')
zsum = NormalDist().inv_cdf(.975) + NormalDist().inv_cdf(.8)
# For df=2, chi-square CDF is 1-exp(-x/2), so its .05 quantile is -2*log(.95).
# n=3 independent normal log contrasts => a one-sided 95% upper SD multiplier.
upper_sd_multiplier = math.sqrt(2 / (-2 * math.log(.95)))
noise, sizing, bugfix = [], [], []
for task in ('ledger_replay', 'reserveplan'):
    runs = [r for r in c1 if r['task'] == task and r['arm'] in ('base3_A', 'base3_B')]
    cell = dict(task=task, treatment='base3, peers=3', runs=[r['name'] for r in runs], metrics={})
    for metric in (*METRICS, 'score', 'delivered'):
        values = [value(r, metric) for r in runs]
        cell['metrics'][metric] = dict(summary(values), values=values)
        if metric in METRICS:
            cell['metrics'][metric]['cv'] = stdev(values) / mean(values)
    cell['zero_failure_upper95_iid'] = 1 - .05 ** (1 / len(runs))
    noise.append(cell)
    pairs = [(a, next(r for r in runs if r['block'] == a['block'] and r['arm'] == 'base3_B'))
             for a in runs if a['arm'] == 'base3_A']
    for metric in METRICS:
        logs = [math.log(a[metric] / b[metric]) for a, b in pairs]
        sd = stdev(logs)
        sizing.append(dict(task=task, metric=metric, pairs=[dict(block=a['block'], a=a['name'], b=b['name'],
            difference=a[metric]-b[metric], log_ratio=lr) for (a,b),lr in zip(pairs,logs)],
            log_summary=summary(logs),
            paired_difference_summary=summary([a[metric]-b[metric] for a,b in pairs]),
            geometric_ratio=math.exp(mean(logs)),
            normal_approx_pairs=[dict(cost_reduction=effect, target_ratio=1-effect,
                delta=abs(math.log(1-effect)),
                plug_in_pairs=math.ceil((zsum * sd / math.log(1-effect)) ** 2),
                upper_sd_stress_pairs=math.ceil((zsum * sd * upper_sd_multiplier / math.log(1-effect)) ** 2))
                for effect in (.10,.20)]))
    if task == 'ledger_replay':
        pairs = [(a, next(r for r in c1 if r['block'] == a['block'] and r['arm'] == 'orig'))
                 for a in runs if a['arm'] == 'base3_A']
        for metric in METRICS:
            logs = [math.log(a[metric] / b[metric]) for a,b in pairs]
            m, s = mean(logs), stdev(logs)
            bugfix.append(dict(metric=metric, log_summary=summary(logs), geometric_ratio=math.exp(m),
                upper95=math.exp(m+2.919986*s/math.sqrt(3)),
                differences=[a[metric]-b[metric] for a,b in pairs]))

workflow = dict(task='workflow_store', treatment='plain exec', runs=[r['name'] for r in c2], metrics={})
for metric in (*METRICS,'score','delivered'):
    values=[value(r, metric) for r in c2]
    workflow['metrics'][metric]=dict(summary(values), values=values)
workflow['zero_failure_upper95_iid']=1-.05**(1/len(c2))
noise.append(workflow)
all_runs=c1+c2
out=dict(method='Independent raw-result audit. All results descriptive because no task passed calibration.',
    sizing_assumptions=dict(alpha_two_sided=.05,power=.8,zsum=zsum,
        formula='ceil(((z(.975)+z(.8))*sample_SD(log(A/B))/abs(log(1-reduction)))**2)',
        unit='Independent concurrent blocks, each containing one run per compared arm; 2N runs for N pairs.',
        upper_sd_multiplier=upper_sd_multiplier,
        limits='Normal approximation with known SD replaced by an n=3 estimate; not exact t-test power, not a minimum guaranteed sample, not validated on long tasks. Upper-SD stress assumes independent normal log contrasts. No multiple-comparison adjustment. Recalibrate on long unsaturated tasks and use task-level replication before choosing final N.'),
    noise=noise,sizing=sizing,bugfix=bugfix,
    budget=dict(jobs=len(all_runs),input=sum(r['input'] for r in all_runs),
        remaining_jobs=36-len(all_runs),remaining_input=450000000-sum(r['input'] for r in all_runs)),
    quality_sizing='Not identified: all scores are 1.0. Zero observed score SD must not become zero assumed future SD.',
    delivery_sizing='Per-task zero-failure upper bounds shown only under independent Bernoulli runs; concurrent shared-block dependence makes them optimistic.')
path=ROOT/'research/data/final-noise-audit.json'
path.write_text(json.dumps(out,indent=2)+'\n')
for row in sizing:
    print(row['task'],row['metric'],'paired log SD',round(row['log_summary']['sd'],6),
          'pairs 10%/20%',*[v['plug_in_pairs'] for v in row['normal_approx_pairs']],
          'upper-SD stress',*[v['upper_sd_stress_pairs'] for v in row['normal_approx_pairs']])
print('Budget:',out['budget'])
print('Wrote',path.relative_to(ROOT))
