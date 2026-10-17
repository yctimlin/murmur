#!/usr/bin/env python3
"""Reproduce diagnosis tables from research/data/index.csv; no model or lab calls."""
import csv
import json
import math
import statistics as st
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
rows=list(csv.DictReader((HERE/'data/index.csv').open()))
by={r['run_id']:r for r in rows}

def n(r,k):return float(r.get(k) or 0)
def total(k,rs=rows):return sum(n(r,k) for r in rs)
def pct(a,b):return 100*a/b if b else 0
def table(headers,rs):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|']+['| '+' | '.join(str(x) for x in r)+' |' for r in rs])
def num(x):return f'{x:,.0f}'

pairs=[('murmur-eval/A-old','murmur-eval/solo-A'),('explore/L1-s3','explore/L1-solo'),('explore/L2-s3','explore/L2-solo')]
for batch,tasks,arm in [('large',['T1','T2','T3'],'base'),('lean',['U1','U2'],'base'),('lean2',['V1','V2'],'base')]:
    pairs.extend((f'{batch}/{t}-{arm}',f'{batch}/{t}-solo') for t in tasks)
pairs.extend((f'val/{t}-base',f'val/solo-{t}') for t in ['W1','W2'])
pairs.append(('big3/big3','big3/solo'))
pairs.extend((f'self2/eval/{t}-orig',f'self2/eval/{t}-solo') for t in ['W1','W2','W3'])
paired=[(by[a],by[b]) for a,b in pairs]
dq=[n(a,'judge_quality')-n(b,'judge_quality') for a,b in paired]
ratios=[n(a,'input')/n(b,'input') for a,b in paired]
speeds=[n(b,'active_min')/n(a,'active_min') for a,b in paired]
geomean=lambda xs:math.exp(st.mean(math.log(x) for x in xs))
lines=['# Phase A diagnosis from existing artifacts','',
       'This is descriptive diagnosis, not a mechanism trial. All historical task/arm cells have one run (round 2 has two judges, not two run repetitions). We conducted no new lab runs. The screening tasks are designed separately and frozen by the scheduler after this phase.','',
       'Reproduce: `python3 research/tools/index_runs.py` then `python3 research/tools/diagnose.py`. Definitions, missingness, classifier rules, raw evidence paths and source limitations are in `research/data/METHODS.md`. The CSV is the numeric source for every table below.','',
       f"The index covers **{len(rows)} runs, {int(total('sessions'))} sessions, {num(total('input'))} observed input tokens, {num(total('uncached'))} uncached input and {num(total('output'))} output**. One empty-catalog failure has no session telemetry, and one peer in a failed 429 attempt has no provider usage; these missing costs are unknown, not zero. Research self-improvement runs remain in coverage but are excluded from task-pair comparisons.",'',
       '## Coverage and timing','',
       table(['Evidence batch','Runs','Sessions','Observed input','Uncached','Active minutes sum','Wall minutes sum'],[
           [b,len(rs:= [r for r in rows if r['batch']==b]),int(total('sessions',rs)),num(total('input',rs)),num(total('uncached',rs)),f"{total('active_min',rs):.2f}",f"{total('wall_min',rs):.2f}"] for b in sorted({r['batch'] for r in rows})]),'',
       'Active minutes use the 120-second capped union of event timestamps; wall uses retained launch/exit or session spans. The sum across runs is workload accounting, not elapsed experiment duration. Box pauses and hangs explain some divergence. The index retains both, the original harness seconds, source paths, commits, merges and outcomes.','',
       '## Ranked cost associations','',
       f"**Repeated prefix context is the largest measured token component: {num(total('cached'))} cached input tokens, {pct(total('cached'),total('input')):.2f}% of input.** Cached is a lower bound on reused context; it does not mean that all of this input can be eliminated. Uncached input is {pct(total('uncached'),total('input')):.2f}%. Output is reported separately and is not part of this denominator.",'',
       'The following disjoint operational categories rank the full input contexts charged to the latest tool category. These are associations with work, not newly emitted tool tokens or causal waste. A shell containing both edits and tests is classified as edit.','']
kinds=['edit','verify','git_sync','git_read','file_read','board','wait','other']
ranked=sorted(kinds,key=lambda k:total('call_'+k+'_input'),reverse=True)
lines += [table(['Rank','Last tool category','Input tokens','Share of all input','Tool calls'],[[i+1,k,num(total('call_'+k+'_input')),f"{pct(total('call_'+k+'_input'),total('input')):.2f}%",num(total('call_'+k+'_count'))] for i,k in enumerate(ranked)]),'',
          'The source question has a different denominator. Exact per-source tokenization is unavailable; the logs expose these serialized output character counts. These characters must not be added to cached input or model output tokens.','',
          table(['Tool output source','Characters','Share of tool-output characters'],[[s,num(total('source_'+s+'_chars')),f"{pct(total('source_'+s+'_chars'),sum(total('source_'+k+'_chars') for k in ['shell_output','file_reads','board_reads','other_tool_output'])):.2f}%"] for s in ['shell_output','file_reads','board_reads','other_tool_output']]),'',
          '## Time decomposition for every run','',
          'Each row in index.csv and sessions.csv contains eight additive phase columns. The table sums capped session minutes, including root. It is peer effort, so parallel sessions overlap and the sum differs from run active minutes. The classifier follows tool operations; it does not claim to observe private reasoning or prove that gaps were idle.','']
phases=['exploration','drafting','waiting_idle','board_traffic','ranking','merging','verification','polishing']
ph_total=sum(total('phase_'+p+'_peer_min') for p in phases)
lines += [table(['Phase','Peer minutes','Share of classified peer time'],[[p,f"{total('phase_'+p+'_peer_min'):.2f}",f"{pct(total('phase_'+p+'_peer_min'),ph_total):.2f}%"] for p in phases]),'',
          'Exploration is before the first detected edit except explicit coordination/verification operations. Drafting includes later implementation. Polishing is work after final main that is not an explicit wait, board, Git or test action. Waiting includes polling. `excluded_gap_min` retains excess per-session gaps separately.','',
          '## Draft-and-rank redundancy','']
drafted=[r for r in rows if n(r,'draft_branches')]
lines += [table(['Measure','Count','Share / denominator'],[
    ['Runs with retained draft refs',len(drafted),f'{len(drafted)}/{len(rows)} runs'],
    ['Draft refs',num(total('draft_branches')),'all retained refs'],
    ['Draft tips not ancestors of final main',num(total('draft_branches_not_ancestors')),f"{pct(total('draft_branches_not_ancestors'),total('draft_branches')):.2f}% of draft refs"],
    ['Draft-added text lines',num(total('draft_added_lines')),'per-branch additions versus task base'],
    ['Added lines absent at same final path',num(total('draft_absent_added_lines')),f"{pct(total('draft_absent_added_lines'),total('draft_added_lines')):.2f}% of draft-added lines"],
    ['Draft files identical to final blob',num(total('draft_exact_final_files')),f"{pct(total('draft_exact_final_files'),total('draft_changed_files')):.2f}% of {num(total('draft_changed_files'))} branch-file changes"]]),'',
    'The absent-line metric quantifies textual non-retention, not semantic waste: moved lines, adopted drafts later improved, and useful rejected alternatives all complicate interpretation. Non-ancestor refs can be copied or cherry-picked. `drafts.csv` provides each branch, revision and count. We cannot credibly equate this percentage with token/time savings.','']
swarms=[r for r in rows if r['mode']!='exec' and r['batch'] not in ('self','self2')]
lines += [f"Before the first main commit, task swarms spent {num(total('pre_main_input',swarms))} input tokens ({pct(total('pre_main_input',swarms),total('input',swarms)):.2f}% of their input); after the final main commit they spent {num(total('post_main_input',swarms))} ({pct(total('post_main_input',swarms),total('input',swarms)):.2f}%). These chronology markers include exploration, draft/rank, tests and coordination; they are not discarded-draft token counts. Zero-main runs have no first-main boundary and are excluded from these chronology counters.",'',
          '## Advisor pooled comparison, independently reconstructed','',
          f"Across the advisor's same 16 baseline swarm/solo pairs, mean quality difference is **{st.mean(dq):+.4f} points** (sample SD {st.stdev(dq):.4f}); swarm better/tied/worse: {sum(x>0 for x in dq)}/{sum(x==0 for x in dq)}/{sum(x<0 for x in dq)}. Thus the reported approximately -0.65 gap reproduces. The geometric mean input ratio is **{geomean(ratios):.3f}×**, and the uniform raw-log active-time speedup is **{geomean(speeds):.3f}×**. The advisor mixed some wall and active durations, so its speed estimate need not equal ours.",'',
          table(['Swarm run','Solo run','Swarm quality','Solo quality','Difference','Input ratio','Solo/swarm active time'],[[a['run_id'],b['run_id'],f"{n(a,'judge_quality'):.3f}",f"{n(b,'judge_quality'):.3f}",f"{n(a,'judge_quality')-n(b,'judge_quality'):+.3f}",f"{n(a,'input')/n(b,'input'):.3f}",f"{n(b,'active_min')/n(a,'active_min'):.3f}"] for a,b in paired]),'',
          'These are heterogeneous tasks, changing engine revisions, different rubrics and no within-cell replication. The pooled gap is a historical description; it cannot distinguish protocol from parallelism, establish an A/A noise level, or validate a peer-count optimum. Those need subsequent preregistered paired, repeated batches.','',
          '## Ranked quality deficits and delivery failures','']
dimdef={k:0.0 for k in ['c','r','risk','pr','d']};dim_n=0
for a,b in paired:
    aa=json.loads(a['judge_dimensions_json']);bb=json.loads(b['judge_dimensions_json'])
    if all(all(k in v for k in dimdef) for v in aa+bb):
        dim_n+=1
        for k in dimdef:dimdef[k]+=st.mean(v[k] for v in bb)-st.mean(v[k] for v in aa)
denom=sum(dimdef.values())
labels={'c':'Correctness','r':'Regressions','risk':'Judge risk-path score','pr':'PR.md accuracy','d':'Design'}
lines += [f'The {dim_n} pairs with the same five rubric dimensions give the following signed decomposition of their total net score deficit. big3 is excluded here because it uses a six-dimensional rubric. Shares sum to 100%; they are score loss, not defect counts.', '',
          table(['Rank','Quality dimension','Solo minus swarm point sum','Share of net dimension deficit'],[[i+1,labels[k],f'{v:.2f}',f'{pct(v,denom):.2f}%'] for i,(k,v) in enumerate(sorted(dimdef.items(),key=lambda x:x[1],reverse=True))]),'']
zero=[r for r in swarms if r['exit_status']=='0' and r['commits_on_main']=='0']
failed=[r for r in rows if r['run_id'].split('/')[-1].startswith('failed-')]
lines += [f"**Delivery failure is a separate severe mode:** {len(zero)}/{len(swarms)} task-swarm runs ({pct(len(zero),len(swarms)):.2f}%) exited 0 with no main commits. They consumed {num(total('input',zero))} input ({pct(total('input',zero),total('input',swarms)):.2f}% of task-swarm input), {num(total('uncached',zero))} uncached input and {total('active_min',zero):.2f} active minutes. This is an observed association; it does not prove which prompt change caused peers to stop after ranking.",'',
          table(['Run','Exit','Main commits','Draft refs','Input','Quality'],[[r['run_id'],r['exit_status'],r['commits_on_main'],r['draft_branches'],num(n(r,'input')),r.get('judge_quality','')] for r in zero]),'',
          f"Three explicitly retained failed setup/run attempts are included separately: {', '.join(r['run_id'] for r in failed)}. Their observed input totals {num(total('input',failed))}; the empty-catalog attempt has unknown token cost. In addition self2/eval/W1-orig exited 1 after delivery and a long root hang. These failures must not disappear behind successful reruns.",'',
          'Per-finding file, blame, phase and seam localization is in `research/data/quality_findings.csv`, with the extraction definitions and review notebook. Flags are retained as judge findings; cross-peer authorship alone does not prove causality. Unresolvable references and withdrawn evidence are marked explicitly instead of guessed.','',
          '## Decisions and limits','',
          '1. Measure repeated context and the number/type of model calls in the next phases; visible board text size alone is not an adequate cost model.',
          '2. Keep draft non-retention separate from avoidable effort; test any proposed simplification prospectively.',
          '3. Treat risk-path quality, PR evidence accuracy, and delivery completion as distinct endpoints. Existing successful tests did not guarantee these outcomes.',
          '4. Retain the protected baseline for controlled comparisons; do not promote a historical prototype or a peer-count change from these single-run comparisons.',
          '5. Run the frozen screening tasks only through the scheduler and preregister the noise/protocol/peer-count batches in their owning later phases. No hypothesis or mechanism is selected in phase A.','']
(HERE/'DIAGNOSIS.md').write_text('\n'.join(lines))
print('wrote',HERE/'DIAGNOSIS.md')
