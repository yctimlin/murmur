#!/usr/bin/env python3
"""Deterministically index historical murmur evidence. Read-only; stdlib only.

Run from any cwd; outputs default to research/data beside this script.
No inference fills missing outcomes, engine revisions, or token telemetry.
See research/data/METHODS.md for attribution definitions and limitations.
"""
import argparse
import collections
import csv
import datetime as dt
import json
import re
import subprocess
from pathlib import Path

ROOTS = ('murmur-eval', 'explore', 'large', 'lean', 'lean2', 'val', 'big3', 'self', 'self2', 'self2/eval')
PHASES = ('exploration', 'drafting', 'waiting_idle', 'board_traffic', 'ranking', 'merging', 'verification', 'polishing')
SOURCES = ('shell_output', 'file_reads', 'board_reads', 'other_tool_output')
KINDS = ('edit', 'verify', 'git_sync', 'git_read', 'file_read', 'board', 'wait', 'other')

def js(x):
    return json.dumps(x, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def stamp(s):
    try:
        return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
    except (ValueError, TypeError, AttributeError):
        return None

def readjson(p):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}

def git(repo, *args, strip=True):
    if not repo or not Path(repo).exists():
        return ''
    p = subprocess.run(['git', '--no-optional-locks', '-C', str(repo), *args], capture_output=True, text=True, errors='replace')
    return (p.stdout.strip() if strip else p.stdout) if p.returncode == 0 else ''

def kind(text):
    # Priority is explicit: mixed edit/test shells count as edits; all output follows the same category.
    if re.search(r'apply_patch|write_text\(|write_bytes\(|\bcat\s*>|\btee\s|open\([^\n]+[\'"]w[ab]?[\'"]', text):
        return 'edit'
    if re.search(r'pytest|unittest|runtests|npm (?:run )?test|node --test|coverage run|\btest_[\w]+\.py|compileall|py_compile', text):
        return 'verify'
    if re.search(r'git (?:-[^\s]+\s+[^\s]+\s+)*(?:pull|push|rebase|fetch|merge|commit|add|cherry-pick)\b|\.murmur/sync', text):
        return 'git_sync'
    if re.search(r'git (?:-[^\s]+\s+[^\s]+\s+)*(?:log|show|diff|status|blame)\b', text):
        return 'git_read'
    if re.search(r'wait_agent|list_agents|wait_for|write_stdin|tools\.wait\(', text):
        return 'wait'
    if re.search(r'collaboration.*(?:read|search|list|post|channel|subscribe)|message_board', text):
        return 'board'
    if re.search(r'\b(?:cat|sed|head|tail|rg|grep|ls|find|wc|read_file)\b|read_text\(|read_bytes\(', text):
        return 'file_read'
    return 'other'

def phase(k, text, edited, t, last_main):
    if re.search(r'(?:ranking|ranked|ranks|rank|vote|ballot)\b', text, re.I) and k == 'board':
        return 'ranking'
    if k == 'wait': return 'waiting_idle'
    if k == 'board': return 'board_traffic'
    if k == 'git_sync': return 'merging'
    if k == 'verify': return 'verification'
    if not edited and k != 'edit': return 'exploration'
    if last_main and t >= last_main: return 'polishing'
    return 'drafting'

def records(path):
    with path.open(errors='replace') as f:
        for line in f:
            try:
                yield json.loads(line)
            except ValueError:
                continue

def first_meta(path):
    try:
        with path.open(errors='replace') as f:
            return json.loads(f.readline()).get('payload', {})
    except (OSError, ValueError):
        return {}

def session(path, run_id, last_main, first_main):
    ds = list(records(path))
    meta = next((x['payload'] for x in ds if x.get('type') == 'session_meta'), {})
    ts = sorted(set(t for x in ds if (t := stamp(x.get('timestamp'))) is not None))
    # Newer logs offer response IDs; older logs only cumulative token_count snapshots.
    modern = any(x.get('type') == 'token_usage_record' for x in ds)
    previous = collections.Counter()
    seen = set()
    totals = collections.Counter()
    charges = collections.Counter()
    phase_secs = collections.Counter()
    source_chars = collections.Counter()
    pending_calls = {}
    count_calls = collections.Counter()
    current_kind, current_phase = 'other', 'exploration'
    edited = False
    first_edit = None
    prev_t = None
    gap_excess = 0.0
    before_first_input = 0
    after_last_input = 0
    response_count = 0
    malformed_cumulative = 0
    for d in ds:
        t = stamp(d.get('timestamp'))
        p = d.get('payload') or {}
        typ = p.get('type')
        if t is not None and prev_t is not None and t >= prev_t:
            delta = t-prev_t
            phase_secs[current_phase] += min(delta, 120)
            gap_excess += max(0, delta-120)
        if t is not None: prev_t = t
        if typ in ('function_call', 'custom_tool_call'):
            txt = str(p.get('name', ''))+' '+str(p.get('input') or p.get('arguments') or '')
            current_kind = kind(txt)
            current_phase = phase(current_kind, txt, edited, t or 0, last_main)
            if current_kind == 'edit':
                edited = True
                first_edit = first_edit or t
            pending_calls[p.get('call_id', '')] = current_kind
            count_calls[current_kind] += 1
        if typ in ('function_call_output', 'custom_tool_call_output'):
            k = pending_calls.get(p.get('call_id', ''), 'other')
            source = {'file_read': 'file_reads', 'board': 'board_reads'}.get(k)
            if source is None:
                source = 'other_tool_output' if k in ('wait', 'other') else 'shell_output'
            out = p.get('output', '')
            source_chars[source] += len(out if isinstance(out, str) else js(out))
        usage = None
        if modern and d.get('type') == 'token_usage_record':
            key = p.get('response_id') or (p.get('thread_id'), p.get('turn_id'), js(p.get('usage')))
            if key not in seen:
                seen.add(key)
                usage = p.get('usage') or {}
        elif not modern and typ == 'token_count' and p.get('info'):
            cumulative = p['info'].get('total_token_usage') or {}
            if cumulative and cumulative != previous:
                if any(cumulative.get(k,0) < previous.get(k,0) for k in ('input_tokens','output_tokens')):
                    malformed_cumulative += 1
                usage = {k:max(0,v-previous.get(k,0)) for k,v in cumulative.items() if isinstance(v,(int,float))}
                previous = collections.Counter(cumulative)
        if usage is not None:
            response_count += 1
            totals.update(usage)
            inp = usage.get('input_tokens', 0)
            charges[current_kind] += inp
            if first_main and t and t < first_main: before_first_input += inp
            if last_main and t and t > last_main: after_last_input += inp
    sid = meta.get('id') or meta.get('session_id') or path.stem
    cwd = meta.get('cwd', '')
    cwd_agent = re.search(r'/peers/([^/]+)', cwd)
    agent_path = meta.get('agent_path') or ('/root/'+cwd_agent.group(1) if cwd_agent else ('/root' if cwd.endswith('/work') else '/solo'))
    agent = agent_path.removeprefix('/root/').removeprefix('/')
    observed_usage = response_count > 0
    row = dict(run_id=run_id, session_id=sid, agent=agent, agent_path=agent_path,
               usage_status='observed' if observed_usage else 'unknown', path=str(path), cwd=cwd,
               start=dt.datetime.fromtimestamp(ts[0],dt.timezone.utc).isoformat() if ts else '',
               end=dt.datetime.fromtimestamp(ts[-1],dt.timezone.utc).isoformat() if ts else '',
               active_min=round(sum(min(b-a,120) for a,b in zip(ts,ts[1:]))/60,6),
               wall_min=round((ts[-1]-ts[0])/60,6) if ts else '',
               excluded_gap_min=round(gap_excess/60,6), input=totals['input_tokens'] if observed_usage else None,
               uncached=totals['input_tokens']-totals['cached_input_tokens'] if observed_usage else None,
               output=totals['output_tokens'] if observed_usage else None,
               cached=totals['cached_input_tokens'] if observed_usage else None, responses=response_count,
               token_method=('response_usage_deduplicated' if modern else 'cumulative_snapshot_deltas') if observed_usage else 'unavailable',
               cumulative_resets=malformed_cumulative,
               first_edit=dt.datetime.fromtimestamp(first_edit,dt.timezone.utc).isoformat() if first_edit else '',
               pre_main_input=before_first_input, post_main_input=after_last_input)
    row.update({f'phase_{p}_peer_min':round(phase_secs[p]/60,6) for p in PHASES})
    row.update({f'source_{s}_chars':source_chars[s] for s in SOURCES})
    row.update({f'call_{k}_input':charges[k] if observed_usage else None for k in KINDS})
    row.update({f'call_{k}_count':count_calls[k] for k in KINDS})
    return row, ts

def final_text(path):
    if path.suffix == '.md':
        return path.read_text(errors='replace')
    chunks=[]
    for d in records(path):
        it=d.get('item',{})
        if it.get('type')=='agent_message': chunks.append(it.get('text',''))
    return '\n'.join(chunks)

def judge_maps(root):
    mapping={}
    for p in sorted((root/'judge').glob('map*.txt')):
        content=p.read_text()
        if root.name=='eval' or root.name=='val':
            for line in content.splitlines():
                words=line.split()
                if len(words)==3: mapping[words[1]+'-'+words[2]]=words[0]
        elif root.name=='big3':
            for label,arm in re.findall(r'(G\d+)\s+(solo|swarm)',content):mapping['solo' if arm=='solo' else 'big3']=label
        else:
            for label,run in re.findall(r'([A-Z]\d+)\s+([\w-]+)',content):mapping[run]=label
    return mapping

def judge(root, name):
    if root.name == 'eval':
        # The operator withdrew round-2 judge prompts/logs. Preserved aggregates are the
        # authoritative available score evidence; do not attempt to recover sealed logs.
        saved = readjson(root/'results.json')
        for r in saved if isinstance(saved, list) else []:
            if r['T']+'-'+r['arm'] == name:
                dims={k:r[k] for k in ('c','r','risk','pr','d')}
                return dict(judge_label=r['label'],judge_source=str(root/'results.json'),judge_passes=r['npass'],
                            judge_quality=r['q'],judge_p0=r['p0'],judge_p1='',judge_p1_inferred_from_risk=10-r['risk']-2*r['p0'],
                            judge_dimensions_json=js([dims]),judge_seam_p0=r['seam'])
        return {}
    mapped_name=name
    if root.name == 'val' and name.startswith('solo-'): mapped_name=name[5:]+'-solo'
    label=judge_maps(root).get(mapped_name)
    if not label: return {}
    p=root/'judge'/label
    groups=[p] if root.name!='eval' else [p/'A-rubric',p/'B-rubric']
    qualities=[]; p0s=[];p1s=[]; dims=[]
    for g in groups:
        if root.name=='eval':
            adversarial=p/(g.name[0]+'-adversarial')
        else: adversarial=g
        txt='\n'.join(final_text(f) for f in sorted(g.iterdir()) if f.name in ('JUDGEMENT.md','rubric.jsonl','out.jsonl','j.jsonl'))
        atxt='\n'.join(final_text(f) for f in sorted(adversarial.iterdir()) if f.name in ('ADVERSARIAL.md','adversarial.jsonl','out.jsonl'))
        score_matches=re.findall(r'SCORES:\s*([^\n]+)',txt)
        score=dict((k,float(v)) for k,v in re.findall(r'(\w+)\s*=\s*([\d.]+)',score_matches[-1])) if score_matches else {}
        if not score and root.name=='big3':
            score=dict((k,float(v)) for k,v in re.findall(r'\|\s*(c|rb|cp|d|pr)\s*[—–-][^|]+\|\s*(\d+)/10',txt))
        adv_matches=re.findall(r'ADV:\s*([^\n]+)',atxt)
        adv=dict((k,float(v)) for k,v in re.findall(r'(\w+)\s*=\s*([\d.]+)',adv_matches[-1])) if adv_matches else {}
        if 'p0' in adv:p0s.append(adv['p0'])
        if 'p1' in adv:p1s.append(adv['p1'])
        if 'score' in adv:score['risk']=adv['score']
        if score:
            dims.append(score)
            # Only full 5/6-dimension or non-code 4-dimension rubrics are complete.
            if ('c' not in score or 'risk' in score):qualities.append(sum(score.values())/len(score))
    return dict(judge_label=label,judge_source=str(p),judge_passes=len(qualities),judge_quality=round(sum(qualities)/len(qualities),6) if qualities else '',
                judge_p0=sum(p0s)/len(p0s) if p0s else '', judge_p1=sum(p1s)/len(p1s) if p1s else '',judge_dimensions_json=js(dims))

def draft_stats(repo, base, main):
    drafts=[]
    if not base or not main:return drafts
    refs=git(repo,'for-each-ref','--format=%(refname:short)','refs/heads/draft/').splitlines()
    for ref in sorted(refs):
        changes=[]
        for l in git(repo,'diff','--numstat',base,ref).splitlines():
            fields=l.split('\t',2)
            if len(fields)!=3:continue
            add,delete,path=fields
            blob=git(repo,'rev-parse',ref+':'+path)
            finalblob=git(repo,'rev-parse','main:'+path)
            patch=git(repo,'diff','--no-ext-diff','--unified=0',base,ref,'--',path)
            added_lines=collections.Counter(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
            final_lines=collections.Counter(git(repo,'show','main:'+path,strip=False).splitlines())
            absent=sum((added_lines-final_lines).values())
            changes.append(dict(path=path,added=int(add) if add.isdigit() else 0,deleted=int(delete) if delete.isdigit() else 0,
                                exact_final_blob=bool(blob and blob==finalblob),absent_added=absent))
        merged=subprocess.run(['git','--no-optional-locks','-C',str(repo),'merge-base','--is-ancestor',ref,'main'],capture_output=True).returncode==0
        drafts.append(dict(ref=ref,head=git(repo,'rev-parse',ref),ancestor_of_main=merged,files=len(changes),added=sum(x['added'] for x in changes),
                           deleted=sum(x['deleted'] for x in changes),exact_final_files=sum(x['exact_final_blob'] for x in changes),
                           nonfinal_added=sum(x['added'] for x in changes if not x['exact_final_blob']),
                           absent_added=sum(x['absent_added'] for x in changes)))
    return drafts

def arm_info(batch,name):
    # Historical engine revisions come from preregistered plans, NOT task repository bases.
    arm=name.split('-',1)[1] if '-' in name else name
    if name.startswith('solo-'):arm='solo'
    if batch=='big3':return ('solo','plain-codex-exec','') if name=='solo' else ('swarm','90d8501','/workspace/big3/PLAN.md')
    if batch=='self2/eval':
        clean=name.removeprefix('failed-')
        arm=clean.split('-')[1]
        if arm=='orig':return arm,'eec78f8','/workspace/self2/eval-plan.md'
        if arm=='base':return arm,'658d82a','/workspace/self2/eval-plan.md'
        if arm in ('a1','a2','a5'):
            folder={'a1':'a1-integration-barrier','a2':'a2-cross-review','a5':'a5-contracts'}[arm]
            source=Path('/workspace/self2/arms')/folder/'src'
            return arm,git(source,'rev-parse','HEAD'),str(source)
    if batch in ('lean','lean2','val'):
        if arm=='base':return arm,'d881067',f'/workspace/{batch}/PLAN.md'
        if arm in ('lean2','lean3'):return arm,'231cab2',f'/workspace/{batch}/PLAN.md'
        if arm=='new':return arm,'feat/token-lean',f'/workspace/{batch}/PLAN.md'
    if batch=='large':return arm,{'base':'research/large-base','new':'feat/integration-quality','solo':'plain-codex-exec'}.get(arm,''),'/workspace/large/PLAN.md'
    if batch=='murmur-eval':return arm,{'new':'feat/verification-batch1','old':'main-at-run-unpinned','solo':'plain-codex-exec'}.get(arm,''),'/workspace/murmur-eval/PLAN.md'
    if batch=='explore':return arm, 'plain-codex-exec' if arm=='solo' else 'explore-with-'+arm, '/workspace/explore/PLAN.md'
    if batch=='self':return 'self6p','eec78f8','/workspace/self/brief.md'
    if batch=='self2':return 'r2','658d82a','/workspace/self2/brief.md'
    return arm, 'plain-codex-exec' if arm=='solo' else '', ''

def writecsv(path,rows):
    cols=list(dict.fromkeys(k for r in rows for k in r))
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=cols,lineterminator='\n');w.writeheader();w.writerows(rows)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workspace',type=Path,default=Path('/workspace'))
    ap.add_argument('--solo-sessions',type=Path,default=Path('/home/box/.codex/sessions'))
    ap.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parents[1]/'data')
    args=ap.parse_args();args.output_dir.mkdir(parents=True,exist_ok=True)
    solo_files=collections.defaultdict(list)
    for f in sorted(args.solo_sessions.glob('2026/10/*/*.jsonl')):
        cwd=first_meta(f).get('cwd','')
        if cwd:solo_files[str(Path(cwd).resolve())].append(f)
    specs=[]
    for batch in ROOTS:
        root=args.workspace/batch
        for config in sorted((root/'ws').glob('*/murmur.json')):
            specs.append((batch,config.parent.name,config.parent,readjson(config),False))
        solos=[p for p in root.iterdir() if p.is_dir() and ('solo-' in p.name or p.name.endswith('-solo'))]
        if batch=='big3':solos=[root/'solo']
        if batch=='self2/eval':solos=sorted((root/'solo').glob('*'))
        for p in sorted(solos):specs.append((batch,p.name,p,{},True))
    index=[];sessions=[];draft_rows=[]
    for batch,name,path,cfg,is_solo in specs:
        run_id=batch+'/'+name
        root=args.workspace/batch
        task=name.removeprefix('failed-').replace('solo-','').split('-')[0]
        if batch=='big3':task='big3'
        runlog=readjson(path/'logs/run.json')
        repo=path/'repo' if is_solo else path/'work/origin.git'
        if is_solo and not (repo/'.git').exists():repo=path
        files=[]
        if is_solo:
            files=solo_files.get(str(repo.resolve()),[])+solo_files.get(str(path.resolve()),[])
            files=sorted(set(files))
        else:files=sorted((path/'codex-home/sessions').glob('**/*.jsonl'))
        base=cfg.get('base','')
        if is_solo:
            # Match the same task's input base in a sibling swarm; solo .git may have harness commit.
            candidates=[v[3].get('base','') for v in specs if v[0]==batch and not v[4] and v[1].removeprefix('failed-').split('-')[0]==task]
            if batch=='big3':candidates=[v[3].get('base','') for v in specs if v[0]==batch and not v[4]]
            base=next((b for b in candidates if b and git(repo,'cat-file','-t',b)=='commit'),'')
        head=git(repo,'rev-parse','main') or git(repo,'rev-parse','HEAD')
        if not base and is_solo:
            # Solo snapshots initialized independently: use first root commit as input base.
            base=git(repo,'rev-list','--max-parents=0',head).splitlines()[0] if head else ''
        mainlog=git(repo,'log','--first-parent','--format=%cI',base+'..'+head).splitlines() if base and head else []
        main_ts=sorted(t for s in mainlog if (t:=stamp(s)) is not None)
        allts=[];run_sessions=[]
        for f in files:
            s,ts=session(f,run_id,main_ts[-1] if main_ts else None,main_ts[0] if main_ts else None)
            sessions.append(s);run_sessions.append(s);allts.extend(ts)
        allts=sorted(set(allts))
        arm,rev,rev_source=arm_info(batch,name)
        observed=any(s['usage_status']=='observed' for s in run_sessions)
        row=dict(run_id=run_id,batch=batch,task=task,arm=arm,engine_revision=rev,engine_revision_source=rev_source,
                 path=str(path),mode='exec' if is_solo else cfg.get('mode','swarm'),peers=1 if is_solo else cfg.get('peers',''),
                 task_base=base,main_head=head,
                 active_min=round(sum(min(b-a,120) for a,b in zip(allts,allts[1:]))/60,6) if allts else '',
                 wall_min=round((stamp(runlog['ended_at'])-stamp(runlog['started_at']))/60,6) if runlog.get('ended_at') and runlog.get('started_at') else (round((allts[-1]-allts[0])/60,6) if allts else ''),
                 wall_source='run_log' if runlog.get('ended_at') else ('session_span' if allts else 'missing'),
                 harness_seconds=runlog.get('seconds',''), sessions=len(run_sessions),
                 input=sum(s['input'] or 0 for s in run_sessions) if observed else '',uncached=sum(s['uncached'] or 0 for s in run_sessions) if observed else '',
                 output=sum(s['output'] or 0 for s in run_sessions) if observed else '',cached=sum(s['cached'] or 0 for s in run_sessions) if observed else '',
                 responses=sum(s['responses'] for s in run_sessions),
                 token_coverage=('partial' if any(s['usage_status']=='unknown' for s in run_sessions) else 'observed') if observed else 'missing',
                 sessions_missing_usage=sum(s['usage_status']=='unknown' for s in run_sessions),
                 commits_on_main=int(git(repo,'rev-list','--count',base+'..'+head) or 0) if base and head else '',
                 merges=int(git(repo,'rev-list','--merges','--count',base+'..'+head) or 0) if base and head else '',
                 first_main=dt.datetime.fromtimestamp(main_ts[0],dt.timezone.utc).isoformat() if main_ts else '',
                 last_main=dt.datetime.fromtimestamp(main_ts[-1],dt.timezone.utc).isoformat() if main_ts else '',
                 exit_status=runlog.get('exit_code',''),exit_source=str(path/'logs/run.json') if runlog else '',
                 reported_delivery=js(runlog.get('result',{})),
                 lines_429=sum('429' in line for f in (path/'logs/session.err',path/'session.err') if f.exists() for line in f.read_text(errors='replace').splitlines()),
                 wall_minus_active_min='',
                 sessions_json=js([{k:s[k] for k in ('session_id','agent','agent_path','usage_status','input','uncached','output','active_min','wall_min','token_method')} for s in run_sessions]))
        if row['wall_min'] != '' and row['active_min'] != '':
            row['wall_minus_active_min']=round(row['wall_min']-row['active_min'],6)
        if is_solo:
            final_events=[d for d in records(path/'session.jsonl')] if (path/'session.jsonl').exists() else []
            completed=[d for d in final_events if d.get('type')=='turn.completed']
            failed=[d for d in final_events if d.get('type')=='turn.failed']
            row['exit_status']='turn_failed' if failed else ('turn_completed' if completed else 'unknown')
            row['exit_source']=str(path/'session.jsonl')
        row.update(judge(root,name))
        for field in [f'phase_{p}_peer_min' for p in PHASES]+[f'source_{s}_chars' for s in SOURCES]+[f'call_{k}_input' for k in KINDS]+[f'call_{k}_count' for k in KINDS]+['excluded_gap_min','pre_main_input','post_main_input']:
            row[field]=round(sum(s[field] or 0 for s in run_sessions),6) if observed else ''
        ds=draft_stats(repo,base,head)
        row.update(draft_branches=len(ds),draft_branches_not_ancestors=sum(not d['ancestor_of_main'] for d in ds),
                   draft_added_lines=sum(d['added'] for d in ds),draft_nonfinal_added_lines=sum(d['nonfinal_added'] for d in ds),
                   draft_changed_files=sum(d['files'] for d in ds),draft_exact_final_files=sum(d['exact_final_files'] for d in ds),
                   draft_absent_added_lines=sum(d['absent_added'] for d in ds))
        draft_rows.extend(dict(run_id=run_id,**d) for d in ds)
        index.append(row)
        print(run_id, len(files), row['input'],file=__import__('sys').stderr)
    index.sort(key=lambda r:r['run_id']);sessions.sort(key=lambda r:(r['run_id'],r['session_id']));draft_rows.sort(key=lambda r:(r['run_id'],r['ref']))
    writecsv(args.output_dir/'index.csv',index);writecsv(args.output_dir/'sessions.csv',sessions);writecsv(args.output_dir/'drafts.csv',draft_rows)
    print(f'{len(index)} runs; {len(sessions)} sessions; {len(draft_rows)} draft branches')

if __name__=='__main__':main()
