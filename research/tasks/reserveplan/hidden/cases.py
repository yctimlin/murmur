"""Independent examples, validation cases, and a minute-grid schedule oracle."""
import copy
import csv
import importlib
import io
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest

CASES = []


def case(name):
    def register(fn):
        CASES.append((name, fn))
        return fn
    return register


def api():
    return importlib.import_module('reserveplan')


def spec(jobs=None, resources=None, bookings=None, horizon=30):
    return {'version': 1, 'horizon': horizon, 'resources': resources or {},
            'jobs': jobs or [], 'bookings': bookings or []}


def job(id, duration, **fields):
    return dict(id=id, duration=duration, **fields)


def expected(rows, order=None, resources=None):
    rows = [dict(id=r[0], start=r[1], end=r[2], tardiness=r[3] if len(r)>3 else 0) for r in rows]
    return {'version': 1, 'jobs': sorted(rows, key=lambda x: x['id']),
            'order': order if order is not None else [r['id'] for r in rows],
            'makespan': max((r['end'] for r in rows), default=0),
            'total_tardiness': sum(r['tardiness'] for r in rows), 'resources': resources or {}}


def plan_case(name, value, result):
    @case(name)
    def run(t):
        t.assertEqual(api().plan(copy.deepcopy(value)), result)


plan_case('empty', spec(), expected([]))
plan_case('one_unconstrained', spec([job('a', 7)]), expected([('a', 0, 7)]))
plan_case('lexical_selection', spec([job('z', 3), job('A', 5), job('a', 1)]),
          expected([('A', 0, 5), ('a', 0, 1), ('z', 0, 3)]))
plan_case('priority_selection', spec([job('a', 2, priority=-1), job('z', 3, priority=8), job('b', 1)]),
          expected([('z', 0, 3), ('b', 0, 1), ('a', 0, 2)]))
plan_case('dependency_and_lag', spec([job('b', 4, after=[{'id':'a','lag':3}]), job('a', 2)]),
          expected([('a', 0, 2), ('b', 5, 9)]))
plan_case('diamond_and_release', spec([job('a', 2), job('b', 4, after=['a']), job('c', 2, after=['a'], release=9), job('d', 3, after=['b', {'id':'c','lag':2}])]),
          expected([('a',0,2),('b',2,6),('c',9,11),('d',13,16)]))
plan_case('serial_future_ready', spec([job('a', 2, priority=10, release=10), job('b', 2, after=['a'], priority=9), job('c', 3, priority=1)]),
          expected([('a',10,12),('b',12,14),('c',0,3)]))
plan_case('unit_capacity', spec([job('b',3,requires={'r':1}),job('a',4,requires={'r':1})], {'r':{'capacity':1}}),
          expected([('a',0,4),('b',4,7)],resources={'r':{'peak':1,'unit_minutes':7}}))
plan_case('capacity_parallel', spec([job('a',4,requires={'r':1}),job('b',3,requires={'r':1}),job('c',2,requires={'r':1})], {'r':{'capacity':2}}),
          expected([('a',0,4),('b',0,3),('c',3,5)],resources={'r':{'peak':2,'unit_minutes':9}}))
plan_case('weighted_capacity', spec([job('a',4,requires={'r':2}),job('b',2,requires={'r':1}),job('c',3,requires={'r':2})], {'r':{'capacity':3}}),
          expected([('a',0,4),('b',0,2),('c',4,7)],resources={'r':{'peak':3,'unit_minutes':16}}))
plan_case('later_gap_fill', spec([job('z',4,priority=10,release=10,requires={'r':1}),job('a',5,requires={'r':1})], {'r':{'capacity':1}}),
          expected([('z',10,14),('a',0,5)],resources={'r':{'peak':1,'unit_minutes':9}}))
plan_case('half_open_booking', spec([job('a',3,requires={'r':1})], {'r':{'capacity':1}}, [{'resource':'r','start':3,'end':6,'units':1}]),
          expected([('a',0,3)],resources={'r':{'peak':1,'unit_minutes':6}}))
plan_case('booking_overlap_spans_whole_job', spec([job('a',6,requires={'r':1})], {'r':{'capacity':1}}, [{'resource':'r','start':3,'end':6,'units':1}]),
          expected([('a',6,12)],resources={'r':{'peak':1,'unit_minutes':9}}))
plan_case('partial_booking_capacity', spec([job('a',5,requires={'r':1})], {'r':{'capacity':2}}, [{'resource':'r','start':1,'end':4,'units':1}]),
          expected([('a',0,5)],resources={'r':{'peak':2,'unit_minutes':8}}))
plan_case('downtime_spanning', spec([job('a',5,requires={'r':1})], {'r':{'capacity':5,'unavailable':[[2,6]]}}),
          expected([('a',6,11)],resources={'r':{'peak':1,'unit_minutes':5}}))
plan_case('downtime_union', spec([job('a',2,release=4,requires={'r':1})], {'r':{'capacity':1,'unavailable':[[7,10],[2,5],[5,8],[3,4]]}}),
          expected([('a',10,12)],resources={'r':{'peak':1,'unit_minutes':2}}))
plan_case('two_resources', spec([job('a',4,requires={'r':1,'s':1})], {'r':{'capacity':1,'unavailable':[[0,3]]},'s':{'capacity':1,'unavailable':[[5,8]]}}),
          expected([('a',8,12)],resources={'r':{'peak':1,'unit_minutes':4},'s':{'peak':1,'unit_minutes':4}}))
plan_case('unrequested_downtime', spec([job('a',6)], {'r':{'capacity':1,'unavailable':[[0,30]]}}),
          expected([('a',0,6)],resources={'r':{'peak':0,'unit_minutes':0}}))
plan_case('zero_duration_downtime', spec([job('a',0,release=4,requires={'r':1})], {'r':{'capacity':1,'unavailable':[[0,30]]}}),
          expected([('a',4,4)],resources={'r':{'peak':0,'unit_minutes':0}}))
plan_case('zero_at_horizon', spec([job('a',30),job('b',0,after=['a'])]),expected([('a',0,30),('b',30,30)]))
plan_case('deadline_reporting', spec([job('a',4,deadline=2),job('b',1,release=5,deadline=8),job('c',2,release=8)]),
          expected([('a',0,4,2),('b',5,6),('c',8,10)]))
plan_case('bookings_usage_only', spec([],{'used':{'capacity':3},'idle':{'capacity':2}},[{'resource':'used','start':0,'end':3,'units':2},{'resource':'used','start':3,'end':8,'units':3}]),
          expected([],resources={'used':{'peak':3,'unit_minutes':21},'idle':{'peak':0,'unit_minutes':0}}))
plan_case('overlapping_booking_usage', spec([],{'r':{'capacity':4}},[{'resource':'r','start':0,'end':5,'units':2},{'resource':'r','start':2,'end':4,'units':1}]),
          expected([],resources={'r':{'peak':3,'unit_minutes':12}}))
plan_case('punctuation_identifiers',spec([job('é, a',1,requires={'gpu/0~x':1}),job('Z',2,after=['é, a'])],{'gpu/0~x':{'capacity':1}}),
          expected([('é, a',0,1),('Z',1,3)],resources={'gpu/0~x':{'peak':1,'unit_minutes':1}}))
plan_case('defaults',{'version':1,'resources':{'r':{'capacity':1}},'jobs':[job('a',1)]},expected([('a',0,1)],resources={'r':{'peak':0,'unit_minutes':0}}))
plan_case('billion_minute_horizon',spec([job('a',3,requires={'r':1})],{'r':{'capacity':1,'unavailable':[[0,999999990]]}},horizon=1000000000),
          expected([('a',999999990,999999993)],resources={'r':{'peak':1,'unit_minutes':3}}))


def bad_case(name, value, code, path, validation=True):
    @case(name)
    def run(t):
        module=api()
        t.assertTrue(issubclass(module.PlanError, ValueError))
        for method in ([module.validate,module.plan] if validation else [module.plan]):
            with t.assertRaises(module.PlanError) as caught:
                method(copy.deepcopy(value))
            t.assertEqual(caught.exception.code,code)
            t.assertEqual(caught.exception.path,path)


bad_case('schema_top', [], 'schema', '')
bad_case('schema_version_boolean', dict(spec(),version=True), 'schema','/version')
bad_case('schema_missing_resources', {'version':1,'jobs':[]},'schema','/resources')
bad_case('schema_unknown_top', dict(spec(),extra=1),'schema','/extra')
bad_case('schema_negative_duration',spec([job('a',-1)]),'schema','/jobs/0/duration')
bad_case('schema_duration_boolean',spec([job('a',True)]),'schema','/jobs/0/duration')
bad_case('schema_empty_id',spec([job('',1)]),'schema','/jobs/0/id')
bad_case('schema_resource_boolean',spec(resources={'r':{'capacity':True}}),'schema','/resources/r/capacity')
bad_case('schema_unknown_job_field',spec([job('a',1,unexpected=3)]),'schema','/jobs/0/unexpected')
bad_case('schema_interval_reversed',spec(resources={'r':{'capacity':1,'unavailable':[[4,2]]}}),'schema','/resources/r/unavailable/0')
bad_case('schema_interval_endpoint_bool',spec(resources={'r':{'capacity':1,'unavailable':[[False,2]]}}),'schema','/resources/r/unavailable/0/0')
bad_case('schema_release_outside_horizon',spec([job('a',1,release=31)]),'schema','/jobs/0/release')
bad_case('schema_dependency_lag_negative',spec([job('a',1),job('b',1,after=[{'id':'a','lag':-1}])]),'schema','/jobs/1/after/0/lag')
bad_case('schema_empty_resource_escaped_parent',spec(resources={'':{'capacity':1}}),'schema','/resources/')
bad_case('duplicate_job',spec([job('a',1),job('a',2)]),'duplicate_job','/jobs/1/id')
bad_case('unknown_resource_pointer_escape',spec([job('a',1,requires={'a/b~c':1})]),'unknown_resource','/jobs/0/requires/a~1b~0c')
bad_case('capacity_request',spec([job('a',1,requires={'r':3})],{'r':{'capacity':2}}),'capacity','/jobs/0/requires/r')
bad_case('unknown_dependency',spec([job('a',1,after=['missing'])]),'unknown_dependency','/jobs/0/after/0')
bad_case('duplicate_dependency_mixed_form',spec([job('a',1),job('b',1,after=['a',{'id':'a','lag':3}])]),'duplicate_dependency','/jobs/1/after/1')
bad_case('self_dependency',spec([job('a',1,after=['a'])]),'cycle','/jobs')
bad_case('cycle_disconnected',spec([job('a',1),job('b',1,after=['c']),job('c',1,after=['b'])]),'cycle','/jobs')
bad_case('unknown_booking_resource',spec(bookings=[{'resource':'r','start':0,'end':2,'units':1}]),'unknown_resource','/bookings/0/resource')
bad_case('booking_capacity',spec(resources={'r':{'capacity':1}},bookings=[{'resource':'r','start':0,'end':2,'units':2}]),'capacity','/bookings/0/units')
bad_case('booking_aggregate_conflict',spec(resources={'r':{'capacity':2}},bookings=[{'resource':'r','start':0,'end':3,'units':2},{'resource':'r','start':2,'end':4,'units':1}]),'booking_conflict','/bookings')
bad_case('booking_downtime_conflict',spec(resources={'r':{'capacity':2,'unavailable':[[2,5]]}},bookings=[{'resource':'r','start':0,'end':3,'units':1}]),'booking_conflict','/bookings')
bad_case('booking_empty_interval',spec(resources={'r':{'capacity':2}},bookings=[{'resource':'r','start':2,'end':2,'units':1}]),'schema','/bookings/0/end')
bad_case('unschedulable_resource',spec([job('a',4,requires={'r':1})],{'r':{'capacity':1,'unavailable':[[0,28]]}}),'unschedulable','/jobs/0',False)
bad_case('unschedulable_lag',spec([job('a',20),job('b',0,after=[{'id':'a','lag':11}])]),'unschedulable','/jobs/1',False)


@case('validation_does_not_schedule')
def run(t):
    value=spec([job('a',4,requires={'r':1})],{'r':{'capacity':1,'unavailable':[[0,30]]}})
    t.assertIsNone(api().validate(value))


@case('input_immutability_and_repeated_call')
def run(t):
    value=spec([job('b',3,after=[{'id':'a','lag':2}],requires={'r':1}),job('a',2,requires={'r':1})],{'r':{'capacity':1,'unavailable':[[12,15],[8,10]]}})
    before=copy.deepcopy(value)
    api().validate(value)
    first=api().plan(value)
    t.assertEqual(value,before)
    t.assertEqual(api().plan(value),first)
    t.assertEqual(value,before)


def oracle(value):
    """Small-horizon brute force, deliberately different from an event scheduler."""
    horizon=value['horizon']; resources=value['resources']; done={}; order=[]
    used={r:[0]*horizon for r in resources}
    closed={r:set() for r in resources}
    for r,v in resources.items():
        for a,b in v.get('unavailable',[]): closed[r].update(range(a,b))
    for b in value['bookings']:
        for minute in range(b['start'],b['end']): used[b['resource']][minute]+=b['units']
    def deps(j):
        return [(d,0) if isinstance(d,str) else (d['id'],d.get('lag',0)) for d in j.get('after',[])]
    while len(done)<len(value['jobs']):
        ready=[j for j in value['jobs'] if j['id'] not in done and all(d in done for d,_ in deps(j))]
        chosen=min(ready,key=lambda j:(-j.get('priority',0),j['id']))
        lower=max([chosen.get('release',0)]+[done[d]['end']+lag for d,lag in deps(chosen)])
        duration=chosen['duration']; needs=chosen.get('requires',{})
        for start in range(lower,horizon-duration+1):
            if all(all(m not in closed[r] and used[r][m]+units<=resources[r]['capacity'] for m in range(start,start+duration)) for r,units in needs.items()): break
        else: return None
        end=start+duration
        for r,units in needs.items():
            for m in range(start,end): used[r][m]+=units
        done[chosen['id']]={'id':chosen['id'],'start':start,'end':end,'tardiness':max(0,end-chosen.get('deadline',end))}
        order.append(chosen['id'])
    return {'version':1,'order':order,'jobs':sorted(done.values(),key=lambda j:j['id']), 'makespan':max((r['end'] for r in done.values()),default=0),'total_tardiness':sum(r['tardiness'] for r in done.values()),'resources':{r:{'peak':max(u,default=0),'unit_minutes':sum(u)} for r,u in used.items()}}


def random_case(seed):
    rng=random.Random(seed)
    resources={'r':{'capacity':3,'unavailable':[[9,12]]},'s':{'capacity':2,'unavailable':[[20,23]]}}
    jobs=[]
    for i in range(9):
        previous=rng.sample(range(i),min(i,rng.randrange(3)))
        needs={r:rng.randint(1,v['capacity']) for r,v in resources.items() if rng.random()<.65}
        jobs.append(job(str(i),rng.randrange(5),after=[{'id':str(d),'lag':rng.randrange(3)} for d in previous],requires=needs,priority=rng.randrange(-2,4),release=rng.randrange(8),deadline=rng.randrange(3,30)))
    rng.shuffle(jobs)
    value=spec(jobs,resources,[{'resource':'r','start':3,'end':6,'units':1}],horizon=60)
    @case('grid_oracle_seed_'+str(seed))
    def run(t):
        result=oracle(value)
        t.assertIsNotNone(result)
        t.assertEqual(api().plan(copy.deepcopy(value)),result)


for seed in [4,7,13,22]: random_case(seed)


def cli(args, stdin=None):
    return subprocess.run([sys.executable,'-m','reserveplan',*args],input=stdin,text=True,capture_output=True,timeout=12,env=os.environ.copy())


def assert_error(t, proc, code, path):
    t.assertEqual(proc.returncode,2,proc.stderr)
    t.assertEqual(proc.stdout,'')
    t.assertEqual(json.loads(proc.stderr),{'error':code,'path':path})
    t.assertTrue(proc.stderr.endswith('\n'))


@case('cli_json_stdin')
def run(t):
    proc=cli(['plan','-'],json.dumps(spec([job('a',2)])))
    t.assertEqual(proc.returncode,0,proc.stderr);t.assertEqual(proc.stderr,'')
    t.assertEqual(json.loads(proc.stdout),expected([('a',0,2)]));t.assertTrue(proc.stdout.endswith('\n'))


@case('cli_json_file_and_output_dirs')
def run(t):
    with tempfile.TemporaryDirectory() as temp:
        p=Path(temp);(p/'in.json').write_text(json.dumps(spec([job('a',2)])))
        out=p/'nested'/'out.json'; proc=cli(['plan',str(p/'in.json'),'--output',str(out)])
        t.assertEqual(proc.returncode,0,proc.stderr);t.assertEqual(proc.stdout,'');t.assertEqual(proc.stderr,'')
        t.assertEqual(json.loads(out.read_text()),expected([('a',0,2)]));t.assertTrue(out.read_text().endswith('\n'))


@case('cli_csv_quoting_sorted')
def run(t):
    proc=cli(['plan','-','--format','csv'],json.dumps(spec([job('z,"quoted"',2,priority=9),job('a\nline',1)])))
    t.assertEqual(proc.returncode,0,proc.stderr);t.assertEqual(proc.stderr,'')
    t.assertNotIn('\r',proc.stdout)
    t.assertEqual(list(csv.reader(io.StringIO(proc.stdout))),[['id','start','end','tardiness'],['a\nline','0','1','0'],['z,"quoted"','0','2','0']])


@case('cli_csv_empty')
def run(t):
    proc=cli(['plan','-','--format','csv'],json.dumps(spec()))
    t.assertEqual(proc.returncode,0,proc.stderr);t.assertEqual(proc.stdout,'id,start,end,tardiness\n')


@case('cli_validate_without_scheduling')
def run(t):
    value=spec([job('a',4,requires={'r':1})],{'r':{'capacity':1,'unavailable':[[0,30]]}})
    proc=cli(['validate','-'],json.dumps(value))
    t.assertEqual(proc.returncode,0,proc.stderr);t.assertEqual(proc.stderr,'');t.assertEqual(json.loads(proc.stdout),{'valid':True})


@case('cli_malformed_json')
def run(t): assert_error(t,cli(['plan','-'],'{broken'),'json','')


@case('cli_missing_input')
def run(t):
    with tempfile.TemporaryDirectory() as temp:
        assert_error(t,cli(['plan',str(Path(temp)/'missing')]),'input','')


@case('cli_invalid_utf8')
def run(t):
    with tempfile.TemporaryDirectory() as temp:
        p=Path(temp)/'bad';p.write_bytes(b'\xff')
        assert_error(t,cli(['plan',str(p)]),'input','')


@case('cli_schema_error')
def run(t): assert_error(t,cli(['plan','-'],json.dumps(spec([job('a',-1)]))),'schema','/jobs/0/duration')


@case('cli_unschedulable')
def run(t):
    value=spec([job('a',4,requires={'r':1})],{'r':{'capacity':1,'unavailable':[[0,30]]}})
    assert_error(t,cli(['plan','-'],json.dumps(value)),'unschedulable','/jobs/0')


@case('cli_preserves_output_on_invalid_input')
def run(t):
    with tempfile.TemporaryDirectory() as temp:
        p=Path(temp)/'out';p.write_text('precious\n')
        assert_error(t,cli(['plan','-','--output',str(p)],'{'),'json','')
        t.assertEqual(p.read_text(),'precious\n')


@case('cli_output_error')
def run(t):
    with tempfile.TemporaryDirectory() as temp:
        assert_error(t,cli(['plan','-','--output',temp],json.dumps(spec())),'output','')


@case('cli_help')
def run(t):
    proc=cli(['--help']);t.assertEqual(proc.returncode,0,proc.stderr)
    t.assertIn('plan',proc.stdout);t.assertIn('validate',proc.stdout)


@case('import_silent')
def run(t):
    proc=subprocess.run([sys.executable,'-c','import reserveplan'],capture_output=True,text=True,timeout=12)
    t.assertEqual(proc.returncode,0,proc.stderr);t.assertEqual(proc.stdout,'');t.assertEqual(proc.stderr,'')


def suite():
    cls=type('ReservePlanCases',(unittest.TestCase,),{})
    for name,fn in CASES:
        setattr(cls,'test_'+name,lambda self,fn=fn:fn(self))
    return unittest.defaultTestLoader.loadTestsFromTestCase(cls)
