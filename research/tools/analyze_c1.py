#!/usr/bin/env python3
"""Reproduce C1 preregistered descriptive estimates; never modifies frozen inputs.

Run from any directory: python3 research/tools/analyze_c1.py
Outputs research/data/C1-analysis.{json,md}, C1-runs.csv, C1-pairs.csv,
and C1-forecast-runs.csv. Standard library only. Sample SD uses ddof=1.
"""
import csv
import json
import math
import statistics as st
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / 'research/data'
RAW = DATA / 'raw/C1'
PREREG = json.loads((ROOT / 'research/prereg/C1.json').read_text())
METRICS = ['score', 'delivered', 'active_min', 'input', 'uncached', 'wall_min',
           'output', 'mutation', 'commits', 'lines_429', 'leak_hits']
POSITIVE = ['active_min', 'input', 'uncached']
T95 = 4.302653
TONE = 2.919986


def summary(values):
    v = [x for x in values if x is not None]
    mean = st.mean(v) if v else None
    sd = st.stdev(v) if len(v) > 1 else None
    return {'n': len(v), 'missing': len(values)-len(v), 'mean': mean, 'sd': sd,
            'cv': sd / mean if sd is not None and mean else None}


def contrast(values, log=False):
    result = summary(values)
    result.pop('cv')  # CV is not meaningful for signed differences or log ratios.
    n = result['n']
    if n == 3:
        se = result['sd'] / math.sqrt(n)
        low, high = result['mean'] - T95 * se, result['mean'] + T95 * se
        result.update(ci95=[low, high], lower95_one=result['mean'] - TONE * se,
                      upper95_one=result['mean'] + TONE * se)
        if log:
            result.update(geomean_ratio=math.exp(result['mean']),
                          ratio_ci95=[math.exp(low), math.exp(high)],
                          ratio_upper95_one=math.exp(result['upper95_one']))
    return result


def csv_write(path, rows):
    with path.open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def f(value, digits=4):
    if value is None:
        return 'NA'
    if isinstance(value, str):
        return value
    return f'{value:.{digits}f}'


def table(headers, rows):
    return '\n'.join(['| ' + ' | '.join(headers) + ' |',
                      '| ' + ' | '.join(['---'] * len(headers)) + ' |'] +
                     ['| ' + ' | '.join(str(x) for x in row) + ' |' for row in rows])


def main():
    jobs = json.loads((RAW / 'jobs.json').read_text())
    assert len(jobs) == len(PREREG['jobs']) == 18
    runs = []
    for index, job in enumerate(jobs):
        assert job['i'] == index and job['prereg'] == PREREG['jobs'][index]
        path = RAW / (job['name'] + '.json')
        raw = json.loads(path.read_text())
        design = job['prereg']
        for field in ('task', 'peers', 'cap'):
            assert raw['job'][field] == design[field], (job['name'], field)
        if design['peers'] != 'exec':
            assert raw['job']['rev'] == design['rev']
            assert raw['murmur_sha'] == design['rev']
        score = (raw.get('score') or {}).get('rate')
        mutation = raw.get('mutation') or {}
        row = {'name': job['name'], 'task': design['task'], 'arm': design['arm'],
               'block': design['block'], 'peers': design['peers'], 'cap': design['cap'],
               'score': score, 'delivered': int(raw['delivered']) if raw.get('delivered') is not None else None}
        row.update({m: raw.get(m) for m in METRICS if m not in ('score', 'delivered', 'mutation')})
        row.update(mutation=mutation.get('score'), mutation_baseline_green=mutation.get('baseline_green'),
                   mutation_timeouts=mutation.get('timeouts'), run_exit=raw.get('run_exit'),
                   setup_exit=raw.get('setup_exit'), raw_path=str(path.relative_to(ROOT)), ws=raw['ws'])
        # No C1 record is censored. Do not infer future timeout semantics from this batch.
        row['censored_or_failed'] = raw.get('run_exit') != 0 or raw.get('delivered') is not True
        row['uncached_fraction'] = row['uncached'] / row['input'] if row['input'] and row['uncached'] is not None else None
        runs.append(row)
    calibrations = {}
    for r in runs:
        if r['arm'] != 'exec_calibration':
            continue
        valid = r['score'] is not None and r['leak_hits'] == 0 and r['run_exit'] == 0
        calibrations[r['task']] = {'run': r['name'], 'score': r['score'], 'active_min': r['active_min'],
                                  'valid': valid, 'C1_confirmatory_eligible': valid and r['score'] <= .95,
                                  'new_swarm_gate_eligible': valid and r['score'] <= .85 and r['active_min'] >= 30}
    for r in runs:
        r['confirmatory_eligible'] = calibrations[r['task']]['C1_confirmatory_eligible'] and r['leak_hits'] == 0
    groups = defaultdict(list)
    for r in runs:
        groups[(r['task'], r['arm'])].append(r)
        if r['arm'] in ('base3_A', 'base3_B'):
            groups[(r['task'], 'base3_pooled')].append(r)
    group_stats = []
    for (task, arm), rows in sorted(groups.items()):
        group_stats.append({'task': task, 'arm': arm, 'scheduled_n': len(rows),
                            'eligible_n': sum(r['confirmatory_eligible'] for r in rows),
                            'metrics': {m: summary([r[m] for r in rows]) for m in METRICS},
                            'uncached_fraction_median': st.median(r['uncached_fraction'] for r in rows),
                            'run_names': [r['name'] for r in rows]})
    blocks = defaultdict(dict)
    for r in runs:
        if r['arm'] != 'exec_calibration':
            blocks[r['block']][r['arm']] = r
    pair_rows, contrast_sets = [], defaultdict(list)
    for block, arms in sorted(blocks.items()):
        a = arms['base3_A']
        for label, other in [('AA', 'base3_B'), ('bug_fix', 'orig')]:
            if other not in arms:
                continue
            b = arms[other]
            p = {'task': a['task'], 'comparison': label, 'block': block,
                 'a': a['name'], 'b': b['name'], 'score_difference': a['score']-b['score'],
                 'delivery_difference': a['delivered']-b['delivered'],
                 'delivery_a': a['delivered'], 'delivery_b': b['delivered'],
                 'eligible': a['confirmatory_eligible'] and b['confirmatory_eligible'],
                 'clean_block': all(r['lines_429'] == 0 for r in arms.values())}
            for metric in POSITIVE:
                p[metric+'_difference'] = a[metric] - b[metric]
                p[metric+'_ratio'] = a[metric] / b[metric]
                p[metric+'_log_ratio'] = math.log(a[metric] / b[metric])
            pair_rows.append(p)
            contrast_sets[(a['task'], label)].append(p)
    contrast_stats = []
    for (task, label), pairs in sorted(contrast_sets.items()):
        s = {'task': task, 'comparison': label, 'scheduled_n': len(pairs),
             'eligible_n': sum(p['eligible'] for p in pairs),
             'score_difference': contrast([p['score_difference'] for p in pairs]),
             'delivery_difference': contrast([p['delivery_difference'] for p in pairs]),
             'clean_block_n': sum(p['clean_block'] for p in pairs)}
        for m in POSITIVE:
            s[m+'_log_ratio'] = contrast([p[m+'_log_ratio'] for p in pairs], log=True)
            s[m+'_difference'] = summary([p[m+'_difference'] for p in pairs])
        if label == 'bug_fix':
            s['nominal_score_margin_pass_ignoring_saturation'] = s['score_difference']['lower95_one'] > -.05
            s['nominal_cost_margin_pass_ignoring_saturation'] = {
                m: s[m+'_log_ratio']['ratio_upper95_one'] < 1.25 for m in POSITIVE}
            s['gross_regression_observed_triggers'] = {
                'base_only_nondelivery': any(p['delivery_a'] == 0 and p['delivery_b'] == 1 for p in pairs),
                'score_mean_below_minus_05': s['score_difference']['mean'] < -.05,
                **{m+'_geomean_above_125': s[m+'_log_ratio']['geomean_ratio'] > 1.25 for m in POSITIVE}}
            s['formal_decision'] = 'inconclusive: zero eligible pairs after preregistered calibration exclusion'
        contrast_stats.append(s)
    forecasts = []
    for r in runs:
        forecast = PREREG['predictions']['run_mean_forecasts'][r['task']][r['arm']]
        for metric in ('score', *POSITIVE):
            point = forecast[metric]
            low, high = {'score': (max(0, point-.25), min(1, point+.25)),
                         'active_min': (.5*point, min(1.45*point, float(r['cap'][:-1]))),
                         'input': (.4*point, 2.2*point),
                         'uncached': (.25*point, 3*point)}[metric]
            value = r[metric]
            forecasts.append({'name': r['name'], 'task': r['task'], 'arm': r['arm'], 'metric': metric,
                              'point': point, 'low': low, 'high': high, 'observed': value,
                              'error': value-point if metric == 'score' else math.log(value/point),
                              'covered': low <= value <= high, 'confirmatory_eligible': r['confirmatory_eligible']})
    forecast_stats = []
    for (task, arm), rows in sorted(groups.items()):
        names = {r['name'] for r in rows}
        for metric in ('score', *POSITIVE):
            items = [x for x in forecasts if x['name'] in names and x['metric'] == metric]
            observed_mean = st.mean(x['observed'] for x in items)
            forecast_stats.append({'task': task, 'arm': arm, 'metric': metric, 'n': len(items),
                                   'point': items[0]['point'], 'low': items[0]['low'], 'high': items[0]['high'],
                                   'observed_mean': observed_mean, 'mean_error': st.mean(x['error'] for x in items),
                                   'mae': st.mean(abs(x['error']) for x in items),
                                   'covered': sum(x['covered'] for x in items),
                                   'mean_within_band': items[0]['low'] <= observed_mean <= items[0]['high']})
    result = {'batch': 'C1', 'analysis_kind': 'preregistered descriptive estimates; confirmatory tasks all excluded',
              'calibrations': calibrations, 'runs': runs, 'groups': group_stats, 'pairs': pair_rows,
              'contrasts': contrast_stats, 'forecast_runs': forecasts, 'forecast_groups': forecast_stats,
              'budget': {'jobs': len(runs), 'input': sum(r['input'] for r in runs),
                         'uncached': sum(r['uncached'] for r in runs), 'remaining_jobs': 36-len(runs),
                         'remaining_input': 450000000-sum(r['input'] for r in runs)},
              'notes': ['No capped/failed deliveries, leaks or lines_429 observed; scheduled and clean-block sensitivity sets coincide.',
                        'Sample SD uses n-1; n=1 SD is missing, not zero.',
                        'Null mutation (C1-06) remains missing because baseline_green=false.',
                        'Mutation scores are scorer-reported; C1-11 excludes one timed-out mutant from denominator (20/29).',
                        't intervals use preregistered df2 multipliers 4.302653 two-sided and 2.919986 one-sided; strong normal/log-normal assumptions and n=3.',
                        'No exact two-sided sign-flip .05 significance is possible (minimum nonzero-contrast p=.25).',
                        'Nominal score zero-width t interval is mechanical ceiling arithmetic, not informative quality equivalence.',
                        'P0 status is not a raw endpoint; no runnable new P0 has been established in this analysis.']}
    (DATA/'C1-analysis.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    csv_write(DATA/'C1-runs.csv', runs)
    csv_write(DATA/'C1-pairs.csv', pair_rows)
    csv_write(DATA/'C1-forecast-runs.csv', forecasts)
    md = ['# C1 reproducible descriptive analysis', '',
          'Generated by `python3 research/tools/analyze_c1.py` from the immutable [preregistration](../prereg/C1.json) and [raw job mapping](raw/C1/jobs.json). All 18 scheduled runs are reported. No task passes the C1 calibration saturation rule; no task passes the newer <=.85 score and >=30 active-minute swarm gate. These tables therefore support descriptive time/token/delivery noise measurement, not confirmatory quality/effect claims.', '',
          'Sample SD uses n−1. `NA` means unavailable; n=1 SD is not zero. Input/uncached/output are token counts. Mutation means exclude the single missing value and explicitly report denominator. The [run CSV](C1-runs.csv), [pair CSV](C1-pairs.csv), [per-run forecast CSV](C1-forecast-runs.csv), and [complete JSON](C1-analysis.json) preserve full precision.', '',
          '## Every scheduled run', '',
          table(['Run / raw', 'Task','Arm','Block','Score','Delivery','Active min','Wall min','Input','Uncached','Output','Mutation','Commits','429','Leaks'],
                [[f'[{r["name"]}](raw/C1/{r["name"]}.json)',r['task'],r['arm'],r['block'],f(r['score']),r['delivered'],f(r['active_min'],2),f(r['wall_min'],2),r['input'],r['uncached'],r['output'],f(r['mutation']),r['commits'],r['lines_429'],r['leak_hits']] for r in runs]), '',
          'C1-06-base3A mutation is missing because the mutation runner marked its own-test baseline nongreen; it is not zero. C1-11-base3B has 20 kills / 29 non-timeout mutants = .6897 (one timeout). All run exits and all reported swarm setup exits are zero; exec records omit setup_exit; every run delivers, so no time-to-delivery censoring was detected. No leak or rate-limit exclusion changes any descriptive analysis. No confirmed new P0 is established here; test-harness failure is investigated separately.', '',
          '## Task/arm mean and sample SD', '']
    for section, metrics in [('Primary endpoints', METRICS[:5]), ('Secondary endpoints', METRICS[5:])]:
        md += ['### '+section, '',table(['Task','Arm','Scheduled n','Eligible n',*metrics],
                [[g['task'],g['arm'],g['scheduled_n'],g['eligible_n'],
                  *[f'{f(g["metrics"][m]["mean"])} ± {f(g["metrics"][m]["sd"])} (n={g["metrics"][m]["n"]})' for m in metrics]] for g in group_stats]),'']
    md += ['## Every paired contrast', '',
           'A/A is base3_A minus/divided by base3_B. Bug-fix is base3_A minus/divided by orig in ledger blocks only. B is never a second original comparator. Raw arithmetic differences and log ratios are retained in CSV/JSON.', '',
           table(['Task','Comparison','Block','Score Δ','Delivery A/B','Active Δ','Active A/B','Input Δ','Input A/B','Uncached Δ','Uncached A/B'],
                 [[p['task'],p['comparison'],p['block'],f(p['score_difference']),f'{p["delivery_a"]}/{p["delivery_b"]}',
                   *[f(p[m+s]) for m in POSITIVE for s in ('_difference','_ratio')]] for p in pair_rows]), '',
           '### Paired summary and assumption-dependent intervals', '',
           'All rows have three scheduled pairs and zero confirmatory eligible pairs. Two-sided 95% t intervals use df=2 and multiplier 4.302653; one-sided bounds use 2.919986. Log-ratio intervals assume approximately normal paired logs. Exact two-sided sign-flip minimum p=.25 with three nonzero pairs; no .05 significance claim is possible. The bounds below are descriptive, with no saturation exclusion bypass.', '',
           table(['Task','Comparison','Endpoint','Mean log ratio / Δ','Sample SD','Geomean ratio','95% interval (ratio or Δ)','One-sided upper ratio / lower score'],
                 [[s['task'],s['comparison'],m,f(v['mean']),f(v['sd']),f(v.get('geomean_ratio')),
                   '['+', '.join(f(x) for x in v.get('ratio_ci95',v['ci95']))+']',f(v.get('ratio_upper95_one',v['lower95_one']))]
                  for s in contrast_stats for m,v in [('score_difference',s['score_difference'])]+[(m,s[m+'_log_ratio']) for m in POSITIVE]]), '',
           '### Paired raw arithmetic differences', '',
           table(['Task','Comparison','Endpoint','Mean A−B / A−orig','Sample SD'],
                 [[s['task'],s['comparison'],m,f(s[m+'_difference']['mean']),f(s[m+'_difference']['sd'])]
                  for s in contrast_stats for m in POSITIVE]), '',
           '### Same-treatment dispersion and cache fractions', '',
           table(['Task','n','Score SD','Active CV','Input CV','Uncached CV','Median U/I'],
                 [[g['task'],g['scheduled_n'],f(g['metrics']['score']['sd']),*[f(g['metrics'][m]['cv']) for m in POSITIVE],f(g['uncached_fraction_median'])] for g in group_stats if g['arm']=='base3_pooled']), '',
           '## Frozen forecast diagnostics', '',
           'All rows are descriptive because calibration excluded every task. Errors are observed−forecast for score and ln(observed/forecast) for positive costs; MAE is absolute score error (absolute log error for costs). Coverage is of the frozen marginal nominal 80% run band, not a confidence interval. A mean outside a run band is the preregistered conservative forecast-failure screen. No cross-task score/noise pooling occurs.', '',
           table(['Task','Arm','Metric','Point','Band','Observed mean','Mean error','MAE','Coverage','Mean inside band'],
                 [[g['task'],g['arm'],g['metric'],f(g['point']),f'[{f(g["low"])}, {f(g["high"])}]',f(g['observed_mean']),f(g['mean_error']),f(g['mae']),f'{g["covered"]}/{g["n"]}',str(g['mean_within_band'])] for g in forecast_stats]), '',
           '## Decision and limits', '',
           'The nominal zero score difference and zero-width t interval arise from all scores equaling 1.0; they cannot establish quality noninferiority on saturated tasks. The preregistration requires three complete eligible pairs for noninferiority and supplies none. Report bug-fix safety as inconclusive. The descriptive gross-regression screen finds no base-only nondelivery, mean score loss below −.05, or geometric mean active/input/uncached ratio above 1.25. No mechanism or default peer-count change follows. A/A labels are identical treatments; their differences are noise/position diagnostics.', '',
           f'Observed input = {result["budget"]["input"]:,}; uncached = {result["budget"]["uncached"]:,}. Under 36 jobs / 450M input, {result["budget"]["remaining_jobs"]} jobs and {result["budget"]["remaining_input"]:,} input remain. This is observed accounting, separate from scheduler admission estimates.', '',
           'The primary scheduled analysis includes rate limits; all blocks have zero reported lines_429, so the clean complete-block sensitivity is identical. All 18 runs have valid available primary endpoints, no leaks, and successful delivery. The sole missing secondary mutation value is retained as NA; no outcomes are replaced. C1 includes no solo/protocol-1/protocol-2 arms and cannot identify protocol-versus-parallelism or fit a peer-count curve.', '']
    (DATA/'C1-analysis.md').write_text('\n'.join(md))
    print(json.dumps({'budget':result['budget'], 'contrasts':contrast_stats,
                      'pooled_base3':[g for g in group_stats if g['arm']=='base3_pooled']},indent=2))


if __name__ == '__main__':
    main()
