from pathlib import Path
import importlib.util, json, copy, hashlib, subprocess, shutil, tempfile
base=Path(__file__).resolve().parents[1]/'tasks'/'reserveplan'
spec=importlib.util.spec_from_file_location('rp_cases',base/'hidden/cases.py'); cases=importlib.util.module_from_spec(spec); spec.loader.exec_module(cases)
def peak(intervals):
    changes={}
    for a,b,u in intervals:
        if a==b: continue
        changes[a]=changes.get(a,0)+u; changes[b]=changes.get(b,0)-u
    used=high=0
    for _,delta in sorted(changes.items()): used+=delta; high=max(high,used)
    return high
def oracle(value):
    resources=value['resources']; horizon=value.get('horizon',10000)
    bookings={r:[] for r in resources}; done={}; order=[]
    for b in value.get('bookings',[]): bookings[b['resource']].append((b['start'],b['end'],b['units']))
    def deps(job): return [(d,0) if isinstance(d,str) else (d['id'],d.get('lag',0)) for d in job.get('after',[])]
    while len(done)<len(value['jobs']):
        choices=[j for j in value['jobs'] if j['id'] not in done and all(d in done for d,_ in deps(j))]
        chosen=sorted(choices,key=lambda j:(-j.get('priority',0),j['id']))[0]
        lower=max([chosen.get('release',0)]+[done[d]['end']+lag for d,lag in deps(chosen)])
        needs=chosen.get('requires',{}); duration=chosen['duration']; starts={lower}
        for r in needs:
            starts.update(b for a,b,u in bookings[r]); starts.update(b for a,b in resources[r].get('unavailable',[]))
        placed=None
        for start in sorted(x for x in starts if x>=lower):
            end=start+duration
            if end>horizon: continue
            good=True
            for r,units in needs.items():
                if duration and any(start<b and end>a for a,b in resources[r].get('unavailable',[])): good=False; break
                if peak(bookings[r]+[(start,end,units)])>resources[r]['capacity']: good=False; break
            if good: placed=(start,end); break
        if placed is None: return None
        start,end=placed
        for r,units in needs.items(): bookings[r].append((start,end,units))
        done[chosen['id']]={'id':chosen['id'],'start':start,'end':end,'tardiness':max(0,end-chosen.get('deadline',end))}; order.append(chosen['id'])
    return {'version':1,'order':order,'jobs':sorted(done.values(),key=lambda r:r['id']),'makespan':max((r['end'] for r in done.values()),default=0),'total_tardiness':sum(r['tardiness'] for r in done.values()),'resources':{r:{'peak':peak(intervals),'unit_minutes':sum((b-a)*u for a,b,u in intervals)} for r,intervals in bookings.items()}}
verified=[]
for name,fn in cases.CASES:
    captured=dict(zip(fn.__code__.co_freevars,[c.cell_contents for c in fn.__closure__ or []]))
    if 'value' in captured and ('result' in captured or name.startswith('grid_oracle_seed_')):
        value=captured['value']; expected=captured.get('result') or cases.oracle(value)
        actual=oracle(value)
        assert actual==expected,(name,actual,expected)
        verified.append(name)
def digest(root):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}
with tempfile.TemporaryDirectory(prefix='a2-reserveplan-review-') as tmp:
    root=Path(tmp)
    for name in ['first','second']:
        shutil.copytree(base,root/name,ignore=shutil.ignore_patterns('input','__pycache__'))
        subprocess.run([str(root/name/'make_input.sh')],check=True,capture_output=True)
    tree=root/'first/input'; before=digest(tree); assert before==digest(root/'second/input')
    revs=[subprocess.check_output(['git','-C',str(root/n/'input'),'rev-parse','HEAD'],text=True).strip() for n in ['first','second']]
    assert revs[0]==revs[1]
    scorer=root/'relocated'; scorer.mkdir(); shutil.copy2(base/'score.sh',scorer/'score.sh'); shutil.copytree(base/'hidden',scorer/'hidden')
    proc=subprocess.run([str(scorer/'score.sh'),str(tree)],cwd='/tmp',capture_output=True,text=True,check=True)
    score=json.loads(proc.stdout.splitlines()[-1]); assert score=={'passed':0,'total':74,'rate':0.0}
    assert digest(tree)==before
print(json.dumps({'task':'reserveplan','verified_schedule_cases':verified,'count':len(verified),'baseline':score,'deterministic_commit':revs[0],'relocated_grader':True,'input_unchanged':True},indent=2,sort_keys=True))
