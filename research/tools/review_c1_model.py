#!/usr/bin/env python3
"""Independent raw-result check of C1 frozen forecasts; standard library only.

Does not import primary analysis. All score/effect outputs are descriptive
because first exec calibration saturated every task.
"""
import json
import math
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'research/data/raw/C1'
PREREG = json.loads((ROOT / 'research/prereg/C1.json').read_text())
rows = []
for job in json.loads((RAW / 'jobs.json').read_text()):
    result = json.loads((RAW / (job['name'] + '.json')).read_text())
    rows.append(dict(result, name=job['name'], **job['prereg']))


def stats(values):
    return {'n': len(values), 'mean': statistics.mean(values),
            'sd': statistics.stdev(values) if len(values) > 1 else None}


def measured(row, metric):
    return row['score']['rate'] if metric == 'score' else row[metric]


def forecast(task, arm):
    return PREREG['predictions']['run_mean_forecasts'][task][
        'base3_A' if arm == 'base3_combined' else arm]


def band(mu, metric, cap):
    if metric == 'score':
        return [max(0, mu - .25), min(1, mu + .25)]
    if metric == 'active_min':
        return [.5 * mu, min(1.45 * mu, cap)]
    if metric == 'input':
        return [.4 * mu, 2.2 * mu]
    return [.25 * mu, 3 * mu]

cells = []
for task in sorted({r['task'] for r in rows}):
    arms = sorted({r['arm'] for r in rows if r['task'] == task})
    if 'base3_A' in arms:
        arms.append('base3_combined')
    for arm in arms:
        selected = [r for r in rows if r['task'] == task and
                    (r['arm'] == arm or (arm == 'base3_combined' and r['arm'].startswith('base3_')))]
        cell = {'task': task, 'arm': arm, 'n': len(selected), 'metrics': {}}
        for metric, mu in forecast(task, arm).items():
            values = [measured(r, metric) for r in selected]
            limits = band(mu, metric, int(selected[0]['cap'][:-1]))
            errors = [v - mu if metric == 'score' else math.log(v / mu) for v in values]
            cell['metrics'][metric] = dict(stats(values), forecast=mu, band=limits,
                mean_outside_band=not limits[0] <= statistics.mean(values) <= limits[1],
                coverage=sum(limits[0] <= v <= limits[1] for v in values),
                mean_error=statistics.mean(errors),
                error_kind='signed_difference' if metric == 'score' else 'log_ratio',
                mae=statistics.mean(abs(v) for v in errors) if metric == 'score' else None,
                runs=[{'name': r['name'], 'value': v, 'error': e} for r, v, e in zip(selected, values, errors)])
        cells.append(cell)

noise = {}
for task in ['ledger_replay', 'reserveplan']:
    selected = [r for r in rows if r['task'] == task and r['arm'].startswith('base3_')]
    noise[task] = {metric: dict(stats([r[metric] for r in selected]),
        cv=statistics.stdev(r[metric] for r in selected) / statistics.mean(r[metric] for r in selected))
        for metric in ['active_min', 'input', 'uncached']}
    noise[task]['median_uncached_fraction'] = statistics.median(r['uncached'] / r['input'] for r in selected)
    noise[task]['score_sd'] = statistics.stdev(r['score']['rate'] for r in selected)

contrasts = []
for comparator in ['base3_B', 'orig']:
    for task in ['ledger_replay', 'reserveplan']:
        pairs = []
        for a in rows:
            if a['task'] != task or a['arm'] != 'base3_A':
                continue
            b = next((r for r in rows if r['block'] == a['block'] and r['arm'] == comparator), None)
            if b:
                pairs.append((a, b))
        if not pairs:
            continue
        metrics = {}
        for metric in ['active_min', 'input', 'uncached']:
            logs = [math.log(a[metric] / b[metric]) for a, b in pairs]
            mean, sd = statistics.mean(logs), statistics.stdev(logs)
            metrics[metric] = {'geom_ratio': math.exp(mean), 'log_mean': mean, 'log_sd': sd,
                'nominal_upper95': math.exp(mean + 2.919986 * sd / math.sqrt(len(logs))),
                'nominal_two_sided95': [math.exp(mean + sign * 4.302653 * sd / math.sqrt(len(logs))) for sign in [-1, 1]],
                'pairs': [{'block': a['block'], 'a': a[metric], 'b': b[metric], 'log_ratio': x} for (a, b), x in zip(pairs, logs)]}
        contrasts.append({'task': task, 'contrast': 'base3_A/' + comparator, 'metrics': metrics})

out = {'method': 'Independent raw-result model reproduction; all inference descriptive after saturation exclusion.',
       'input_sum': sum(r['input'] for r in rows), 'remaining_input': 450000000 - sum(r['input'] for r in rows),
       'cells': cells, 'noise': noise, 'contrasts': contrasts}
path = ROOT / 'research/data/C1-model-independent-review.json'
path.write_text(json.dumps(out, indent=2) + '\n')
for cell in cells:
    print(cell['task'], cell['arm'], 'n=' + str(cell['n']))
    for metric, val in cell['metrics'].items():
        print(' ', metric, 'mean=', round(val['mean'], 6), 'SD=', None if val['sd'] is None else round(val['sd'], 6),
              'coverage=', str(val['coverage']) + '/' + str(cell['n']), 'mean_fail=', val['mean_outside_band'],
              'mean_error=', round(val['mean_error'], 6))
print('Written', path.relative_to(ROOT))
