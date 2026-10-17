"""Operator-only executable positive control; never copied into task input.

Uses one SQLite JSON state row deliberately: validates observable contract without
prescribing a relational implementation to the candidate.
"""
import copy
import json
import math
import sqlite3

class StoreError(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def fail(code): raise StoreError(code)
def ident(x): return type(x) is str and bool(x) and x.strip() == x
def integer(x, minimum=None, maximum=None):
    return type(x) is int and (minimum is None or x >= minimum) and (maximum is None or x <= maximum)
def validjson(x):
    if x is None or type(x) in (str, bool, int): return True
    if type(x) is float: return math.isfinite(x)
    if type(x) is list: return all(validjson(v) for v in x)
    if type(x) is dict: return all(type(k) is str and validjson(v) for k,v in x.items())
    return False

def dump(x): return json.dumps(x, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
def equal(a,b): return validjson(a) and validjson(b) and dump(a)==dump(b)
def keys(x, required, optional=()):
    return type(x) is dict and set(required) <= x.keys() and x.keys() <= set(required)|set(optional)
TERMINAL={'succeeded','failed','blocked','cancelled'}

class Engine:
    def __init__(self):
        self.clock=0; self.workflows={}; self.commands=[]; self.cache={}
    def settle(self):
        for tasks in self.workflows.values():
            # Iterative fixed point, including long DAGs.
            while True:
                changed=False
                for t in tasks.values():
                    if t['state']!='pending': continue
                    ds=[tasks[d]['state'] for d in t['after']]
                    state=None
                    if not ds: state='ready'
                    elif t['join']=='all_success':
                        if any(s in TERMINAL and s!='succeeded' for s in ds): state='blocked'
                        elif all(s=='succeeded' for s in ds): state='ready'
                    elif t['join']=='all_done':
                        if all(s in TERMINAL for s in ds): state='ready'
                    elif 'succeeded' in ds: state='ready'
                    elif all(s in TERMINAL for s in ds): state='blocked'
                    if state: t['state']=state; changed=True
                if not changed: break
    def outcome(self,t,ok,result,at):
        t['result']=copy.deepcopy(result)
        t['worker']=None;t['expires']=None
        if ok: t['state']='succeeded'
        elif t['attempts']<t['max_attempts']:
            t['state']='ready';t['ready_at']=at+t['retry_delay']*2**(t['attempts']-1)
        else: t['state']='failed'
    def check(self,c):
        if not keys(c,('id','now','op'),('workflow','tasks','worker','lease','limit','token','ok','result')): fail('schema')
        if not ident(c['id']) or not integer(c['now'],0): fail('schema')
        op=c['op']
        fields={'submit':('workflow','tasks'),'claim':('worker','lease','limit'),'renew':('token','lease'),'finish':('token','ok','result'),'cancel':('workflow',),'advance':()}
        if type(op) is not str or op not in fields or set(c)!=set(('id','now','op')+fields[op]): fail('schema')
        if 'workflow' in c and not ident(c['workflow']): fail('schema')
        if 'lease' in c and not integer(c['lease'],1): fail('schema')
        if op=='claim' and (not ident(c['worker']) or not integer(c['limit'],1,100)): fail('schema')
        if op in ('renew','finish'):
            t=c['token']
            if not keys(t,('workflow','task','attempt','worker')) or not all(ident(t[k]) for k in ('workflow','task','worker')) or not integer(t['attempt'],1): fail('schema')
        if op=='finish' and (type(c['ok']) is not bool or not validjson(c['result'])): fail('schema')
        if op=='submit':
            if type(c['tasks']) is not list: fail('schema')
            for t in c['tasks']:
                if not keys(t,('id',),('payload','priority','max_attempts','retry_delay','after','join')): fail('schema')
                if not ident(t['id']) or not validjson(t.get('payload')) or not integer(t.get('priority',0)) or not integer(t.get('max_attempts',1),1,20) or not integer(t.get('retry_delay',0),0): fail('schema')
                if type(t.get('after',[])) is not list or not all(ident(x) for x in t.get('after',[])) or t.get('join','all_success') not in ('all_success','all_done','any_success'): fail('schema')
            names=[t['id'] for t in c['tasks']]
            if len(set(names))!=len(names):fail('graph')
            edges={t['id']:t.get('after',[]) for t in c['tasks']}
            if any(len(set(ds))!=len(ds) or any(d not in edges or d==name for d in ds) for name,ds in edges.items()):fail('graph')
            pending=set(edges);seen=set()
            while pending:
                available={n for n in pending if set(edges[n])<=seen}
                if not available:fail('graph')
                pending-=available;seen|=available
    def apply(self,c):
        if type(c) is dict and type(c.get('id')) is str and c['id'] in self.cache:
            old,result=self.cache[c['id']]
            if not equal(c,old):fail('conflict')
            return copy.deepcopy(result)
        self.check(c)
        if c['now']<self.clock:fail('time')
        self.clock=c['now']
        for tasks in self.workflows.values():
            for t in tasks.values():
                if t['state']=='running' and t['expires']<=self.clock:
                    self.outcome(t,False,{'error':'lease_expired'},t['expires'])
        self.settle();op=c['op']
        if op=='submit':
            if c['workflow'] in self.workflows:fail('exists')
            tasks={}
            for raw in c['tasks']:
                t={'id':raw['id'],'payload':copy.deepcopy(raw.get('payload')),'priority':raw.get('priority',0),'max_attempts':raw.get('max_attempts',1),'retry_delay':raw.get('retry_delay',0),'after':sorted(raw.get('after',[])),'join':raw.get('join','all_success'),'state':'pending','attempts':0,'ready_at':self.clock,'worker':None,'expires':None,'result':None}
                tasks[t['id']]=t
            self.workflows[c['workflow']]=tasks
            result={'workflow':c['workflow'],'created':len(tasks)}
        elif op=='claim':
            ready=sorted(((-t['priority'],w,t['id']) for w,ts in self.workflows.items() for t in ts.values() if t['state']=='ready' and t['ready_at']<=self.clock))[:c['limit']]
            leases=[]
            for _,w,tid in ready:
                t=self.workflows[w][tid];t['state']='running';t['attempts']+=1;t['worker']=c['worker'];t['expires']=self.clock+c['lease']
                leases.append({'token':{'workflow':w,'task':tid,'attempt':t['attempts'],'worker':t['worker']},'payload':copy.deepcopy(t['payload']),'expires':t['expires']})
            result={'leases':leases}
        elif op in ('renew','finish'):
            tok=c['token'];t=self.workflows.get(tok['workflow'],{}).get(tok['task'])
            if not t or t['state']!='running' or t['attempts']!=tok['attempt'] or t['worker']!=tok['worker']:fail('stale')
            if op=='renew':
                t['expires']=self.clock+c['lease'];result={'expires':t['expires']}
            else:
                self.outcome(t,c['ok'],c['result'],self.clock)
                result={'state':t['state'],'ready_at':t['ready_at']}
        elif op=='cancel':
            if c['workflow'] not in self.workflows:fail('missing')
            count=0
            for t in self.workflows[c['workflow']].values():
                if t['state'] not in TERMINAL:
                    t['state']='cancelled';t['worker']=None;t['expires']=None;count+=1
            result={'cancelled':count}
        else:result={'now':self.clock}
        self.settle();self.commands.append(copy.deepcopy(c));self.cache[c['id']]=(copy.deepcopy(c),copy.deepcopy(result))
        return copy.deepcopy(result)
    def snapshot(self):
        workflows=[]
        for w,ts in sorted(self.workflows.items()):
            tasks=[copy.deepcopy(t) for _,t in sorted(ts.items())];states=[t['state'] for t in tasks]
            status='running' if any(s not in TERMINAL for s in states) else ('succeeded' if all(s=='succeeded' for s in states) else ('cancelled' if 'cancelled' in states else 'failed'))
            workflows.append({'id':w,'state':status,'tasks':tasks})
        return {'version':1,'clock':self.clock,'workflows':workflows}
    def export(self):return {'version':1,'state':self.snapshot(),'commands':copy.deepcopy(self.commands)}
    @classmethod
    def replay(cls,commands):
        e=cls()
        for c in commands:e.apply(c)
        return e

class Store:
    def __init__(self,path):
        self.db=None
        try:
            self.db=sqlite3.connect(str(path),timeout=10,isolation_level=None)
            self.db.execute('BEGIN IMMEDIATE')
            tables=self.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
            if not tables:
                self.db.execute('CREATE TABLE workflow_store_state (id INTEGER PRIMARY KEY, value TEXT NOT NULL)')
                self.db.execute('INSERT INTO workflow_store_state VALUES (1, ?)',(dump({'commands':[]}),))
            elif tables!=[('workflow_store_state',)]:fail('storage')
            self.db.execute('SELECT value FROM workflow_store_state WHERE id=1').fetchone()[0]
            self.db.commit()
        except Exception as exc:
            if self.db:self.db.close()
            self.db=None
            if isinstance(exc,StoreError):raise
            raise StoreError('storage') from exc
    def close(self):
        if self.db:self.db.close();self.db=None
    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def _engine(self):
        if self.db is None:fail('closed')
        raw=json.loads(self.db.execute('SELECT value FROM workflow_store_state WHERE id=1').fetchone()[0])
        # Persist full materialized engine as JSON to avoid replay per transaction.
        e=Engine()
        if 'workflows' in raw:
            e.clock=raw['clock'];e.workflows=raw['workflows'];e.commands=raw['commands'];e.cache=raw['cache']
        return e
    def _save(self,e):
        self.db.execute('UPDATE workflow_store_state SET value=? WHERE id=1',(dump({'clock':e.clock,'workflows':e.workflows,'commands':e.commands,'cache':e.cache}),))
    def apply_many(self,commands):
        if self.db is None:fail('closed')
        try:
            self.db.execute('BEGIN IMMEDIATE');e=self._engine()
            out=[e.apply(c) for c in commands];self._save(e);self.db.commit();return out
        except BaseException:
            self.db.rollback();raise
    def apply(self,command):return self.apply_many([command])[0]
    def snapshot(self):return self._engine().snapshot()
    def history(self):return copy.deepcopy(self._engine().commands)
    def export(self):return self._engine().export()
    def load(self,bundle):
        if self.db is None:fail('closed')
        try:
            self.db.execute('BEGIN IMMEDIATE')
            if self._engine().commands:fail('nonempty')
            try:
                if not keys(bundle,('version','state','commands')) or type(bundle['commands']) is not list:fail('snapshot')
                e=Engine.replay(bundle['commands'])
                if not equal(e.export(),bundle):fail('snapshot')
            except Exception:fail('snapshot')
            self._save(e);self.db.commit()
        except BaseException:
            self.db.rollback();raise
