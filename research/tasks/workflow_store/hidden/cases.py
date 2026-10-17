"""Behavioral grading: concrete oracles, transactional probes, process isolation.
No imports from operator reference; no reference-generated expected snapshots.
"""
import copy
import importlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


def canon(x):return json.dumps(x,sort_keys=True,ensure_ascii=False,allow_nan=False)

class Cases(unittest.TestCase):
    def setUp(self):
        m=importlib.import_module('workflow_store');self.Store=m.Store;self.Error=m.StoreError
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.db=self.root/'store.db';self.s=self.Store(self.db);self.addCleanup(self.s.close);self.n=0
    def cmd(self,op,now=0,**kw):
        self.n+=1;return dict(id=f'c{self.n}',now=now,op=op,**kw)
    def do(self,op,now=0,**kw):return self.s.apply(self.cmd(op,now,**kw))
    def submit(self,tasks=None,workflow='w',now=0):return self.do('submit',now,workflow=workflow,tasks=tasks if tasks is not None else [{'id':'a'}])
    def claim(self,now=0,worker='worker',lease=10,limit=1):return self.do('claim',now,worker=worker,lease=lease,limit=limit)['leases']
    def finish(self,tok,now=1,ok=True,result=None):return self.do('finish',now,token=tok,ok=ok,result=result)
    def tasks(self,w='w'):return {t['id']:t for v in self.s.snapshot()['workflows'] if v['id']==w for t in v['tasks']}
    def error(self,code,fn):
        before=self.s.export()
        with self.assertRaises(self.Error) as cm:fn()
        self.assertEqual(cm.exception.code,code);self.assertEqual(canon(self.s.export()),canon(before))
    def cli(self,*args,stdin=None):
        return subprocess.run([sys.executable,'-m','workflow_store',str(self.db),*map(str,args)],input=stdin,text=True,capture_output=True,timeout=12)
    def goodcli(self,*args,stdin=None):
        p=self.cli(*args,stdin=stdin);self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(p.stderr,'');return json.loads(p.stdout)
    def badcli(self,code,*args,stdin=None):
        p=self.cli(*args,stdin=stdin);self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,'');self.assertEqual(json.loads(p.stderr),{'error':code});self.assertEqual(len(p.stderr.splitlines()),1)

    def test_empty(self):
        self.assertEqual(self.s.snapshot(),{'version':1,'clock':0,'workflows':[]});self.assertEqual(self.s.history(),[])
    def test_error_class(self):self.assertTrue(issubclass(self.Error,ValueError))
    def test_defaults(self):
        self.assertEqual(self.submit(),{'workflow':'w','created':1})
        self.assertEqual(self.tasks()['a'],{'id':'a','payload':None,'priority':0,'max_attempts':1,'retry_delay':0,'after':[],'join':'all_success','state':'ready','attempts':0,'ready_at':0,'worker':None,'expires':None,'result':None})
    def test_empty_workflow(self):
        self.submit([]);self.assertEqual(self.s.snapshot()['workflows'][0]['state'],'succeeded');self.assertEqual(self.claim(),[])
    def test_canonical_sorting(self):
        self.submit([{'id':'c','after':['b','a']},{'id':'b'},{'id':'a'}],workflow='z');self.submit([],workflow='A')
        snap=self.s.snapshot();self.assertEqual([w['id'] for w in snap['workflows']],['A','z']);self.assertEqual([t['id'] for t in snap['workflows'][1]['tasks']],['a','b','c']);self.assertEqual(self.tasks('z')['c']['after'],['a','b'])
    def test_claim_shape(self):
        self.submit([{'id':'a','payload':[1,True,{'x':None}]}]);self.assertEqual(self.claim(lease=7),[{'token':{'workflow':'w','task':'a','attempt':1,'worker':'worker'},'payload':[1,True,{'x':None}],'expires':7}])
    def test_priority_global(self):
        self.submit([{'id':'z','priority':4},{'id':'a','priority':1}],workflow='b');self.submit([{'id':'c','priority':4},{'id':'b','priority':4}],workflow='a')
        toks=[v['token'] for v in self.claim(limit=4)];self.assertEqual([(t['workflow'],t['task']) for t in toks],[('a','b'),('a','c'),('b','z'),('b','a')])
    def test_negative_priority(self):
        self.submit([{'id':'a','priority':-2},{'id':'z','priority':-1}]);self.assertEqual(self.claim()[0]['token']['task'],'z')
    def test_claim_running_once(self):
        self.submit();self.claim();self.assertEqual(self.claim(),[]);self.assertEqual(self.tasks()['a']['attempts'],1)
    def test_success(self):
        self.submit();tok=self.claim()[0]['token'];self.assertEqual(self.finish(tok,result={'ok':[3]}),{'state':'succeeded','ready_at':0});t=self.tasks()['a'];self.assertEqual(t['result'],{'ok':[3]});self.assertIsNone(t['worker']);self.assertIsNone(t['expires']);self.assertEqual(self.s.snapshot()['workflows'][0]['state'],'succeeded')
    def test_failure_terminal(self):
        self.submit();tok=self.claim()[0]['token'];self.assertEqual(self.finish(tok,ok=False,result='oops'),{'state':'failed','ready_at':0});self.assertEqual(self.s.snapshot()['workflows'][0]['state'],'failed')
    def test_retry_backoff(self):
        self.submit([{'id':'a','max_attempts':3,'retry_delay':3}]);tok=self.claim()[0]['token'];self.assertEqual(self.finish(tok,now=2,ok=False,result='one'),{'state':'ready','ready_at':5});self.assertEqual(self.claim(now=4),[]);tok=self.claim(now=5)[0]['token'];self.assertEqual(tok['attempt'],2);self.assertEqual(self.tasks()['a']['result'],'one');self.assertEqual(self.finish(tok,now=6,ok=False),{'state':'ready','ready_at':12});tok=self.claim(now=12)[0]['token'];self.assertEqual(self.finish(tok,now=13,ok=False),{'state':'failed','ready_at':12})
    def test_expiry_uses_expiry_time(self):
        self.submit([{'id':'a','max_attempts':2,'retry_delay':3}]);self.claim();self.do('advance',100);t=self.tasks()['a'];self.assertEqual((t['state'],t['ready_at'],t['attempts'],t['result']),('ready',13,1,{'error':'lease_expired'}))
    def test_expiry_exhausted(self):
        self.submit();self.claim();self.do('advance',10);self.assertEqual(self.tasks()['a']['state'],'failed')
    def test_finish_at_expiry_rolls_back(self):
        self.submit();tok=self.claim()[0]['token'];self.error('stale',lambda:self.finish(tok,now=10));self.assertEqual(self.tasks()['a']['state'],'running');self.assertEqual(self.s.snapshot()['clock'],0)
    def test_renew_shortens(self):
        self.submit();tok=self.claim()[0]['token'];self.assertEqual(self.do('renew',2,token=tok,lease=1),{'expires':3});self.do('advance',3);self.assertEqual(self.tasks()['a']['state'],'failed')
    def test_renew_extends(self):
        self.submit();tok=self.claim()[0]['token'];self.do('renew',8,token=tok,lease=10);self.finish(tok,now=17);self.assertEqual(self.tasks()['a']['state'],'succeeded')
    def test_renew_at_expiry(self):
        self.submit();tok=self.claim()[0]['token'];self.error('stale',lambda:self.do('renew',10,token=tok,lease=5))
    def test_stale_attempt(self):
        self.submit([{'id':'a','max_attempts':2}]);old=self.claim()[0]['token'];new=self.claim(now=10)[0]['token'];self.error('stale',lambda:self.finish(old,now=10));self.finish(new,now=10)
    def test_wrong_worker(self):
        self.submit();tok=self.claim()[0]['token'];tok['worker']='other';self.error('stale',lambda:self.finish(tok))
    def test_unknown_token(self):self.error('stale',lambda:self.finish({'workflow':'missing','task':'a','worker':'w','attempt':1}))
    def test_finished_token(self):
        self.submit();tok=self.claim()[0]['token'];self.finish(tok);self.error('stale',lambda:self.finish(tok))
    def test_all_success(self):
        self.submit([{'id':'b','after':['a']},{'id':'a'}]);tok=self.claim(limit=2);self.assertEqual(len(tok),1);self.finish(tok[0]['token']);self.assertEqual(self.claim(now=1)[0]['token']['task'],'b')
    def test_cascade_blocking(self):
        self.submit([{'id':'c','after':['b']},{'id':'b','after':['a']},{'id':'a'}]);self.finish(self.claim()[0]['token'],ok=False);self.assertEqual([self.tasks()[n]['state'] for n in ['a','b','c']],['failed','blocked','blocked'])
    def test_all_done_after_failure(self):
        self.submit([{'id':'a'},{'id':'b','after':['a'],'join':'all_done'}]);self.finish(self.claim()[0]['token'],ok=False);self.assertEqual(self.tasks()['b']['state'],'ready');self.assertEqual(self.s.snapshot()['workflows'][0]['state'],'running')
    def test_any_success_early(self):
        self.submit([{'id':'a'},{'id':'b'},{'id':'c','after':['a','b'],'join':'any_success'}]);leases=self.claim(limit=2);self.finish(leases[0]['token']);self.assertEqual(self.tasks()['b']['state'],'running');self.assertEqual(self.tasks()['c']['state'],'ready')
    def test_any_success_blocked(self):
        self.submit([{'id':'a'},{'id':'b'},{'id':'c','after':['a','b'],'join':'any_success'}]);ls=self.claim(limit=2);self.finish(ls[0]['token'],ok=False);self.assertEqual(self.tasks()['c']['state'],'pending');self.finish(ls[1]['token'],ok=False);self.assertEqual(self.tasks()['c']['state'],'blocked')
    def test_any_success_no_deps(self):
        self.submit([{'id':'a','join':'any_success'}]);self.assertEqual(self.tasks()['a']['state'],'ready')
    def test_retry_not_terminal(self):
        self.submit([{'id':'a','max_attempts':2},{'id':'b','after':['a'],'join':'all_done'}]);self.finish(self.claim()[0]['token'],ok=False);self.assertEqual(self.tasks()['b']['state'],'pending')
    def test_expiration_settles_before_claim(self):
        self.submit([{'id':'a'},{'id':'b','after':['a'],'join':'all_done'}]);self.claim();self.assertEqual(self.claim(now=10)[0]['token']['task'],'b')
    def test_block_then_all_done(self):
        self.submit([{'id':'a'},{'id':'b','after':['a']},{'id':'c','after':['b'],'join':'all_done'}]);self.finish(self.claim()[0]['token'],ok=False);self.assertEqual(self.tasks()['c']['state'],'ready')
    def test_cancel_running_pending_ready(self):
        self.submit([{'id':'a'},{'id':'b'},{'id':'c','after':['a'],'join':'all_done'}]);self.claim();self.assertEqual(self.do('cancel',1,workflow='w'),{'cancelled':3});self.assertTrue(all(t['state']=='cancelled' for t in self.tasks().values()));self.assertEqual(self.s.snapshot()['workflows'][0]['state'],'cancelled')
    def test_cancel_preserves_terminal(self):
        self.submit([{'id':'a'},{'id':'b'}]);self.finish(self.claim()[0]['token']);self.assertEqual(self.do('cancel',1,workflow='w'),{'cancelled':1});self.assertEqual(self.tasks()['a']['state'],'succeeded')
    def test_cancel_after_expiry(self):
        self.submit();self.claim();self.assertEqual(self.do('cancel',10,workflow='w'),{'cancelled':0});self.assertEqual(self.s.snapshot()['workflows'][0]['state'],'failed')
    def test_cancel_missing(self):self.error('missing',lambda:self.do('cancel',workflow='no'))
    def test_cancel_other_workflow(self):
        self.submit();self.submit(workflow='other');self.do('cancel',workflow='w');self.assertEqual(self.tasks('other')['a']['state'],'ready')
    def test_workflow_exists(self):
        self.submit([]);self.error('exists',lambda:self.submit([]))
    def test_time_monotonic(self):
        self.do('advance',5);self.error('time',lambda:self.do('advance',4));self.assertEqual(self.do('advance',5),{'now':5})
    def test_duplicate_old_command(self):
        c=self.cmd('submit',workflow='w',tasks=[{'id':'a'}]);first=self.s.apply(c);self.do('advance',100);self.assertEqual(self.s.apply(copy.deepcopy(c)),first);self.assertEqual(len(self.s.history()),2);self.assertEqual(self.s.snapshot()['clock'],100)
    def test_duplicate_claim(self):
        self.submit();c=self.cmd('claim',worker='w',lease=10,limit=1);ls=self.s.apply(c);self.do('advance',100);self.assertEqual(self.s.apply(c),ls);self.assertEqual(self.tasks()['a']['state'],'failed')
    def test_conflict(self):
        c=self.cmd('advance',1);self.s.apply(c);c['now']=2;self.error('conflict',lambda:self.s.apply(c))
    def test_type_sensitive_conflict_bool(self):
        c=self.cmd('submit',workflow='w',tasks=[{'id':'a','payload':1}]);self.s.apply(c);c['tasks'][0]['payload']=True;self.error('conflict',lambda:self.s.apply(c))
    def test_type_sensitive_conflict_float(self):
        c=self.cmd('submit',workflow='w',tasks=[{'id':'a','payload':1}]);self.s.apply(c);c['tasks'][0]['payload']=1.0;self.error('conflict',lambda:self.s.apply(c))
    def test_history_original(self):
        c=self.cmd('submit',workflow='w',tasks=[{'id':'z','after':[]},{'id':'a','after':['z']}]);self.s.apply(c);self.assertEqual(self.s.history(),[c])
    def test_detached_inputs(self):
        c=self.cmd('submit',workflow='w',tasks=[{'id':'a','payload':{'x':[]}}]);self.s.apply(c);c['tasks'][0]['payload']['x'].append(3);self.assertEqual(self.tasks()['a']['payload'],{'x':[]});self.assertEqual(self.s.history()[0]['tasks'][0]['payload'],{'x':[]})
    def test_detached_outputs(self):
        self.submit([{'id':'a','payload':{'x':[]}}]);snap=self.s.snapshot();snap['workflows'][0]['tasks'][0]['payload']['x'].append(1);hist=self.s.history();hist[0]['tasks'].clear();self.assertEqual(self.tasks()['a']['payload'],{'x':[]});self.assertEqual(len(self.s.history()[0]['tasks']),1)
    def test_detached_claim_cache(self):
        self.submit([{'id':'a','payload':{'x':[]}}]);c=self.cmd('claim',worker='w',lease=10,limit=1);r=self.s.apply(c);r['leases'][0]['payload']['x'].append(1);self.assertEqual(self.s.apply(c)['leases'][0]['payload'],{'x':[]})
    def test_batch_atomic_error(self):
        self.error('missing',lambda:self.s.apply_many([self.cmd('submit',workflow='w',tasks=[]),self.cmd('cancel',4,workflow='absent')]))
    def test_batch_iterable_error(self):
        marker=RuntimeError('iterator broke')
        def values():
            yield self.cmd('submit',workflow='w',tasks=[])
            raise marker
        before=self.s.export()
        try:self.s.apply_many(values())
        except RuntimeError as exc:self.assertIs(exc,marker)
        else:self.fail('expected original exception')
        self.assertEqual(self.s.export(),before)
    def test_batch_duplicates(self):
        c=self.cmd('advance',1);r=self.s.apply_many(iter([c,c,self.cmd('advance',2)]));self.assertEqual(r,[{'now':1},{'now':1},{'now':2}]);self.assertEqual(len(self.s.history()),2)
    def test_batch_dependent_operations(self):
        cs=[self.cmd('submit',workflow='w',tasks=[{'id':'a'}]),self.cmd('claim',worker='w',lease=10,limit=1),self.cmd('finish',1,token={'workflow':'w','task':'a','attempt':1,'worker':'w'},ok=True,result=None)]
        self.assertEqual(self.s.apply_many(cs)[-1],{'state':'succeeded','ready_at':0})
    def test_batch_empty(self):self.assertEqual(self.s.apply_many(iter([])),[]);self.assertEqual(self.s.history(),[])
    def test_reopen(self):
        self.submit();self.claim();before=self.s.export();self.s.close();self.s=self.Store(self.db);self.addCleanup(self.s.close);self.assertEqual(self.s.export(),before)
    def test_two_connections_freshness(self):
        other=self.Store(self.db);self.addCleanup(other.close);self.submit();self.assertEqual(len(other.snapshot()['workflows']),1);other.apply({'id':'other','now':0,'op':'claim','worker':'other','lease':10,'limit':1});self.assertEqual(self.claim(),[])
    def test_context_closed(self):
        with self.Store(self.root/'context.db') as s:self.assertEqual(s.snapshot()['clock'],0)
        with self.assertRaises(self.Error) as cm:s.snapshot()
        self.assertEqual(cm.exception.code,'closed');s.close()
    def test_closed_apply(self):
        self.s.close()
        with self.assertRaises(self.Error) as cm:self.s.apply(self.cmd('advance'))
        self.assertEqual(cm.exception.code,'closed')
    def test_unrelated_database(self):
        p=self.root/'other.db'
        with sqlite3.connect(p) as db:db.execute('CREATE TABLE keep_me(value TEXT)');db.execute("INSERT INTO keep_me VALUES ('safe')")
        with self.assertRaises(self.Error) as cm:self.Store(p)
        self.assertEqual(cm.exception.code,'storage')
        with sqlite3.connect(p) as db:self.assertEqual(db.execute('SELECT * FROM keep_me').fetchall(),[('safe',)])
    def test_corrupt_database(self):
        p=self.root/'bad.db';p.write_bytes(b'not sqlite')
        with self.assertRaises(self.Error) as cm:self.Store(p)
        self.assertEqual(cm.exception.code,'storage');self.assertEqual(p.read_bytes(),b'not sqlite')
    def test_missing_parent(self):
        with self.assertRaises(self.Error) as cm:self.Store(self.root/'absent'/'db')
        self.assertEqual(cm.exception.code,'storage')
    def test_export_roundtrip(self):
        self.submit([{'id':'a','max_attempts':2},{'id':'b','after':['a']}]);c=self.cmd('claim',worker='w',lease=10,limit=1);r=self.s.apply(c);self.do('advance',15);bundle=self.s.export();other=self.Store(self.root/'loaded.db');self.addCleanup(other.close);self.assertIsNone(other.load(bundle));self.assertEqual(canon(other.export()),canon(bundle));self.assertEqual(other.apply(c),r)
    def test_load_empty(self):
        self.s.load({'version':1,'state':{'version':1,'clock':0,'workflows':[]},'commands':[]});self.assertEqual(self.s.history(),[])
    def test_load_nonempty_advance(self):
        bundle=self.s.export();self.do('advance');self.error('nonempty',lambda:self.s.load(bundle))
    def test_big_integers(self):
        big=10**50;self.submit([{'id':'a','payload':big,'retry_delay':big,'max_attempts':2}],now=big);tok=self.claim(now=big,lease=big)[0];self.assertEqual(tok['expires'],2*big);self.finish(tok['token'],now=big,ok=False,result=big);self.assertEqual(self.tasks()['a']['ready_at'],2*big)
    def test_unicode_ids(self):
        self.submit([{'id':'งาน / ~','payload':{'é':'文字'}}],workflow='工程');self.assertEqual(self.claim(worker='工人')[0]['token'],{'workflow':'工程','task':'งาน / ~','attempt':1,'worker':'工人'})
    def test_snapshot_no_expiration(self):
        self.submit();self.claim(lease=1);self.assertEqual(self.s.snapshot()['clock'],0);self.assertEqual(self.tasks()['a']['state'],'running')
    def test_long_chain_subprocess(self):
        script="""from workflow_store import Store
import sys
s=Store(sys.argv[1]);tasks=[{'id':str(i),'after':[] if i==0 else [str(i-1)]} for i in range(1500)]
s.apply({'id':'s','op':'submit','now':0,'workflow':'w','tasks':tasks})
assert len(s.snapshot()['workflows'][0]['tasks'])==1500
assert s.apply({'id':'x','op':'cancel','now':0,'workflow':'w'})=={'cancelled':1500}
s.close()
"""
        p=subprocess.run([sys.executable,'-c',script,str(self.root/'chain.db')],capture_output=True,text=True,timeout=15);self.assertEqual(p.returncode,0,p.stderr)
    def test_concurrent_claims(self):
        self.submit([{'id':f't{i:03}'} for i in range(100)])
        script="""from workflow_store import Store
import sys,json
with Store(sys.argv[1]) as s:
 print(json.dumps(s.apply({'id':'claim-'+sys.argv[2],'op':'claim','now':0,'worker':sys.argv[2],'lease':10,'limit':20})))
"""
        ps=[subprocess.Popen([sys.executable,'-c',script,str(self.db),str(i)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for i in range(5)]
        try:
            tokens=[]
            for p in ps:
                out,err=p.communicate(timeout=25);self.assertEqual(p.returncode,0,err);tokens.extend(json.loads(out)['leases'])
            self.assertEqual(len(tokens),100);self.assertEqual(len({(t['token']['workflow'],t['token']['task'],t['token']['attempt']) for t in tokens}),100);self.assertEqual(self.claim(),[])
        finally:
            for p in ps:
                if p.poll() is None:p.kill();p.wait()
    def test_batch_scale(self):
        script="""from workflow_store import Store
import sys
with Store(sys.argv[1]) as s:
 cs=[{'id':'s','op':'submit','now':0,'workflow':'w','tasks':[{'id':str(i)} for i in range(100)]}]
 for i in range(100):
  cs.append({'id':'c'+str(i),'op':'claim','now':0,'worker':'w','lease':10,'limit':1})
  cs.append({'id':'f'+str(i),'op':'finish','now':0,'token':{'workflow':'w','task':sorted(map(str,range(100)))[i],'attempt':1,'worker':'w'},'ok':True,'result':None})
 assert len(s.apply_many(cs))==201
 assert s.snapshot()['workflows'][0]['state']=='succeeded'
"""
        p=subprocess.run([sys.executable,'-c',script,str(self.root/'scale.db')],capture_output=True,text=True,timeout=15);self.assertEqual(p.returncode,0,p.stderr)
    def test_cli_apply_stdin(self):self.assertEqual(self.goodcli('apply','-',stdin=json.dumps(self.cmd('advance',3))),{'now':3})
    def test_cli_apply_file(self):
        p=self.root/'input.json';p.write_text(json.dumps(self.cmd('submit',workflow='w',tasks=[])));self.assertEqual(self.goodcli('apply',p),{'workflow':'w','created':0})
    def test_cli_batch(self):
        cs=[self.cmd('submit',workflow='w',tasks=[]),self.cmd('advance',2)];self.assertEqual(self.goodcli('batch','-',stdin=json.dumps(cs)),[{'workflow':'w','created':0},{'now':2}])
    def test_cli_batch_rollback(self):
        cs=[self.cmd('submit',workflow='w',tasks=[]),self.cmd('cancel',1,workflow='x')];self.badcli('missing','batch','-',stdin=json.dumps(cs));self.assertEqual(self.s.history(),[])
    def test_cli_snapshot(self):self.assertEqual(self.goodcli('snapshot'),self.s.snapshot())
    def test_cli_export(self):self.submit();self.assertEqual(self.goodcli('export'),self.s.export())
    def test_cli_load(self):
        bundle=self.s.export();self.assertEqual(self.goodcli('load','-',stdin=json.dumps(bundle)),{'loaded':True})
    def test_cli_output(self):
        p=self.root/'nested'/'out.json';r=self.cli('snapshot','--output',p);self.assertEqual((r.returncode,r.stdout,r.stderr),(0,'',''));self.assertEqual(json.loads(p.read_text()),self.s.snapshot());self.assertTrue(p.read_bytes().endswith(b'\n'))
    def test_cli_output_preserved(self):
        p=self.root/'out.json';p.write_text('keep');self.badcli('missing','apply','-','--output',p,stdin=json.dumps(self.cmd('cancel',workflow='x')));self.assertEqual(p.read_text(),'keep')
    def test_cli_output_error(self):
        p=self.root/'out';p.mkdir();self.badcli('output','snapshot','--output',p)
    def test_cli_input_error(self):self.badcli('input','apply',self.root/'missing')
    def test_cli_utf8_error(self):
        p=self.root/'bad';p.write_bytes(b'\xff');self.badcli('input','apply',p)
    def test_cli_json_error(self):self.badcli('json','apply','-',stdin='{')
    def test_cli_duplicate_json_key(self):self.badcli('json','apply','-',stdin='{"id":"x","id":"y","op":"advance","now":0}')
    def test_cli_nan(self):self.badcli('json','apply','-',stdin='{"id":"x","op":"submit","now":0,"workflow":"w","tasks":[{"id":"a","payload":NaN}]}')
    def test_cli_batch_not_array(self):self.badcli('schema','batch','-',stdin='{}')
    def test_cli_help_no_database(self):
        p=subprocess.run([sys.executable,'-m','workflow_store','--help'],capture_output=True,text=True,timeout=12);self.assertEqual(p.returncode,0);self.assertIn('usage',p.stdout.lower())
    def test_cli_import_quiet(self):
        p=subprocess.run([sys.executable,'-c','import workflow_store'],capture_output=True,text=True,timeout=12);self.assertEqual((p.returncode,p.stdout,p.stderr),(0,'',''))


def schema_case(label, command, code='schema'):
    def method(self):self.error(code,lambda:self.s.apply(copy.deepcopy(command)))
    method.__name__='test_schema_'+label;setattr(Cases,method.__name__,method)

BASE={'id':'x','now':0,'op':'advance'}
for label,command in [
 ('nondict',[]),('missing_id',{'now':0,'op':'advance'}),('extra',{**BASE,'extra':0}),('bool_time',{**BASE,'now':True}),('negative_time',{**BASE,'now':-1}),('float_time',{**BASE,'now':1.0}),('empty_id',{**BASE,'id':''}),('space_id',{**BASE,'id':' x'}),('unknown_op',{**BASE,'op':'what'}),('nonstr_op',{**BASE,'op':[]}),
 ('claim_lease0',{'id':'x','op':'claim','now':0,'worker':'w','lease':0,'limit':1}),('claim_limit101',{'id':'x','op':'claim','now':0,'worker':'w','lease':1,'limit':101}),('claim_bool_limit',{'id':'x','op':'claim','now':0,'worker':'w','lease':1,'limit':True}),('claim_bad_worker',{'id':'x','op':'claim','now':0,'worker':'','lease':1,'limit':1}),
 ('finish_bool_attempt',{'id':'x','op':'finish','now':0,'token':{'workflow':'w','task':'a','worker':'x','attempt':True},'ok':True,'result':None}),('finish_int_ok',{'id':'x','op':'finish','now':0,'token':{'workflow':'w','task':'a','worker':'x','attempt':1},'ok':1,'result':None}),('finish_extra_token',{'id':'x','op':'finish','now':0,'token':{'workflow':'w','task':'a','worker':'x','attempt':1,'extra':0},'ok':True,'result':None})]:schema_case(label,command)
for label,task in [('extra_task',{'id':'a','extra':0}),('bool_priority',{'id':'a','priority':False}),('zero_attempts',{'id':'a','max_attempts':0}),('too_many_attempts',{'id':'a','max_attempts':21}),('negative_delay',{'id':'a','retry_delay':-1}),('bad_join',{'id':'a','join':'maybe'}),('nonstr_after',{'id':'a','after':[1]}),('notlist_after',{'id':'a','after':'b'}),('bad_id',{'id':'a '}),('nan_payload',{'id':'a','payload':float('nan')}),('nonstring_payload_key',{'id':'a','payload':{1:'x'}})]:schema_case(label,{'id':'x','op':'submit','now':0,'workflow':'w','tasks':[task]})
for label,tasks in [('duplicate_task',[{'id':'a'},{'id':'a'}]),('unknown_dependency',[{'id':'a','after':['b']}]),('self_dependency',[{'id':'a','after':['a']}]),('duplicate_dependency',[{'id':'a'},{'id':'b','after':['a','a']}]),('cycle',[{'id':'a','after':['b']},{'id':'b','after':['a']}])]:schema_case(label,{'id':'x','op':'submit','now':0,'workflow':'w','tasks':tasks},'graph')


def tamper_case(label,change):
    def method(self):
        self.submit();self.claim();bundle=self.s.export();other=self.Store(self.root/'target.db');self.addCleanup(other.close);change(bundle)
        before=other.export()
        with self.assertRaises(self.Error) as cm:other.load(bundle)
        self.assertEqual(cm.exception.code,'snapshot');self.assertEqual(other.export(),before)
    method.__name__='test_load_tamper_'+label;setattr(Cases,method.__name__,method)
for label,change in [
 ('clock',lambda b:b['state'].__setitem__('clock',9)),('version_bool',lambda b:b.__setitem__('version',True)),('state_version_bool',lambda b:b['state'].__setitem__('version',True)),('attempt_bool',lambda b:b['state']['workflows'][0]['tasks'][0].__setitem__('attempts',True)),('payload',lambda b:b['state']['workflows'][0]['tasks'][0].__setitem__('payload','changed')),('duplicate_history',lambda b:b['commands'].append(copy.deepcopy(b['commands'][0]))),('missing_history',lambda b:b['commands'].pop()),('extra',lambda b:b.__setitem__('extra',1)),('wrong_state',lambda b:b['state']['workflows'][0].__setitem__('state','succeeded')),('lease',lambda b:b['state']['workflows'][0]['tasks'][0].__setitem__('expires',11))]:tamper_case(label,change)

def suite():return unittest.defaultTestLoader.loadTestsFromTestCase(Cases)
