import copy
import importlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TREE = Path(sys.argv.pop(1))
sys.path.insert(0,str(TREE))

def opened(identity='a',seq=1,account='alice',currency='USD'):
    return dict(id=identity,seq=seq,type='open',account=account,currency=currency)

def money(kind='deposit',identity='b',seq=2,account='alice',amount='10'):
    return dict(id=identity,seq=seq,type=kind,account=account,amount=amount)

def transfer(identity='d',seq=4,source='alice',target='bob',amount='3'):
    return {'id':identity,'seq':seq,'type':'transfer','from':source,'to':target,'amount':amount}

def closed(identity='z',seq=10,account='alice'):
    return dict(id=identity,seq=seq,type='close',account=account)

class LedgerCases(unittest.TestCase):
    def setUp(self):
        api=importlib.import_module('ledger')
        self.Ledger,self.Error=api.Ledger,api.LedgerError
        self.ledger=self.Ledger()
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)

    def funded(self,amount='10'):
        self.ledger.apply(opened())
        self.ledger.apply(money(amount=amount))
        return self.ledger

    def reject(self,event):
        before=copy.deepcopy(self.ledger.snapshot())
        with self.assertRaises(self.Error): self.ledger.apply(event)
        self.assertEqual(self.ledger.snapshot(),before)

    def test_01_exception_contract(self):
        self.assertTrue(issubclass(self.Error,ValueError))

    def test_02_empty_snapshot(self):
        self.assertEqual(self.ledger.snapshot(),{'version':1,'last_seq':0,'accounts':[],'events':[]})

    def test_03_open_zero(self):
        self.assertIs(self.ledger.apply(opened()),True)
        self.assertEqual(self.ledger.balance('alice'),'0.00')

    def test_04_deposit_spelling(self):
        self.ledger.apply(opened())
        self.ledger.apply(money(amount='00012.3'))
        self.assertEqual(self.ledger.balance('alice'),'12.30')
        self.assertEqual(self.ledger.snapshot()['events'][-1]['amount'],'00012.3')

    def test_05_large_exact(self):
        self.funded('9999999999999999999999999999999999.99')
        self.ledger.apply(money(identity='c',seq=3,amount='0.01'))
        self.assertEqual(self.ledger.balance('alice'),'10000000000000000000000000000000000.00')

    def test_06_withdraw(self):
        self.funded('10.25')
        self.ledger.apply(money('withdraw','c',3,amount='3.05'))
        self.assertEqual(self.ledger.balance('alice'),'7.20')

    def test_07_overdraft_atomic(self):
        self.funded('1')
        self.reject(money('withdraw','c',3,amount='1.01'))

    def test_08_transfer(self):
        self.funded(); self.ledger.apply(opened('c',3,'bob'))
        self.ledger.apply(transfer())
        self.assertEqual((self.ledger.balance('alice'),self.ledger.balance('bob')),('7.00','3.00'))

    def test_09_transfer_currency(self):
        self.funded(); self.ledger.apply(opened('c',3,'bob','EUR'))
        self.reject(transfer())

    def test_10_transfer_self(self):
        self.funded(); self.reject(transfer(target='alice'))

    def test_11_transfer_missing_target(self):
        self.funded(); self.reject(transfer())

    def test_12_transfer_overdraft(self):
        self.funded(); self.ledger.apply(opened('c',3,'bob'))
        self.reject(transfer(amount='10.01'))

    def test_13_close_zero(self):
        self.ledger.apply(opened()); self.ledger.apply(closed())
        self.assertEqual(self.ledger.balance('alice'),'0.00')
        self.assertEqual(self.ledger.snapshot()['accounts'],[{'id':'alice','currency':'USD','balance':'0.00','closed':True}])

    def test_14_close_nonzero(self):
        self.funded(); self.reject(closed())

    def test_15_closed_deposit(self):
        self.ledger.apply(opened()); self.ledger.apply(closed(seq=2))
        self.reject(money(identity='c',seq=3))

    def test_16_closed_transfer(self):
        self.funded(); self.ledger.apply(opened('c',3,'bob')); self.ledger.apply(closed('d',4,'bob'))
        self.reject(transfer('e',5))

    def test_17_reopen_forbidden(self):
        self.ledger.apply(opened()); self.ledger.apply(closed(seq=2))
        self.reject(opened('c',3))

    def test_18_open_existing(self):
        self.funded(); self.reject(opened('c',3))

    def test_19_duplicate_is_false(self):
        event=opened(); self.ledger.apply(event); self.ledger.apply(money())
        before=copy.deepcopy(self.ledger.snapshot())
        self.assertIs(self.ledger.apply(dict(reversed(list(event.items())))),False)
        self.assertEqual(self.ledger.snapshot(),before)

    def test_20_conflicting_event_id(self):
        self.funded(); self.reject(money(amount='20'))

    def test_21_duplicate_amount_spelling_conflict(self):
        self.funded('10.00'); self.reject(money(amount='10'))

    def test_22_seq_gaps_allowed(self):
        self.ledger.apply(opened(seq=7)); self.ledger.apply(money(seq=99))
        self.assertEqual(self.ledger.snapshot()['last_seq'],99)

    def test_23_seq_not_increasing(self):
        self.funded()
        for seq in [1,2]:
            with self.subTest(seq=seq): self.reject(money(identity='x',seq=seq))

    def test_24_invalid_seq_types(self):
        for seq in [True,False,0,-1,1.0,'1',None]:
            with self.subTest(seq=seq): self.reject(opened(seq=seq))

    def test_25_invalid_identifiers(self):
        for field in ['id','account']:
            for value in ['', ' leading','trailing ',7,None]:
                event=opened(); event[field]=value
                with self.subTest(field=field,value=value): self.reject(event)

    def test_26_invalid_currency(self):
        for currency in ['usd','US','USDD','UＳD','U1D',None]:
            with self.subTest(currency=currency): self.reject(opened(currency=currency))

    def test_27_invalid_amount_forms(self):
        self.ledger.apply(opened())
        for amount in ['0','0.00','-1','+1',' 1','1 ','1e2','NaN','Infinity','.5','1.','1.001',1,1.5,True,None,'١']:
            with self.subTest(amount=amount): self.reject(money(amount=amount))

    def test_28_exact_event_shape(self):
        for event in [[],None,{'id':'a'},dict(opened(),extra=1),dict(opened(),type='unknown')]:
            with self.subTest(event=event): self.reject(event)

    def test_29_unknown_account(self):
        self.reject(money())
        with self.assertRaises(self.Error): self.ledger.balance('absent')

    def test_30_case_sensitive_accounts(self):
        self.ledger.apply(opened(account='Alice')); self.ledger.apply(opened('b',2,'alice'))
        self.ledger.apply(money(identity='c',seq=3,account='Alice',amount='1'))
        self.assertEqual((self.ledger.balance('Alice'),self.ledger.balance('alice')),('1.00','0.00'))

    def test_31_batch_count_duplicates(self):
        events=[opened(),money(),opened(),money()]
        self.assertEqual(self.ledger.apply_many(iter(events)),2)
        self.assertEqual(self.ledger.balance('alice'),'10.00')
        self.assertEqual(len(self.ledger.snapshot()['events']),2)

    def test_32_batch_rollback(self):
        self.funded(); before=copy.deepcopy(self.ledger.snapshot())
        with self.assertRaises(self.Error): self.ledger.apply_many([money(identity='c',seq=3),money('withdraw','d',4,amount='100')])
        self.assertEqual(self.ledger.snapshot(),before)
        self.assertIs(self.ledger.apply(money(identity='c',seq=3)),True)

    def test_33_iterator_failure_rollback(self):
        self.funded(); before=copy.deepcopy(self.ledger.snapshot())
        sentinel=RuntimeError('iteration broke')
        def events():
            yield money(identity='c',seq=3)
            raise sentinel
        with self.assertRaises(RuntimeError) as caught: self.ledger.apply_many(events())
        self.assertIs(caught.exception,sentinel)
        self.assertEqual(self.ledger.snapshot(),before)

    def test_34_input_event_detached(self):
        event=opened(); original=copy.deepcopy(event); self.ledger.apply(event)
        self.assertEqual(event,original)
        event['currency']='EUR'
        self.assertEqual(self.ledger.snapshot()['events'][0]['currency'],'USD')

    def test_35_snapshot_detached(self):
        self.funded(); snap=self.ledger.snapshot(); snap['events'][0]['currency']='EUR'; snap['accounts'].clear()
        self.assertEqual(self.ledger.snapshot()['events'][0]['currency'],'USD')
        self.assertEqual(self.ledger.balance('alice'),'10.00')

    def test_36_snapshot_canonical(self):
        events=[opened(account='z'),opened('b',2,'a','EUR')]
        self.ledger.apply_many(events)
        self.assertEqual(self.ledger.snapshot(),{'version':1,'last_seq':2,'accounts':[{'id':'a','currency':'EUR','balance':'0.00','closed':False},{'id':'z','currency':'USD','balance':'0.00','closed':False}],'events':events})

    def test_37_from_events(self):
        restored=self.Ledger.from_events(iter([opened(),money(),money()]))
        self.assertEqual((restored.balance('alice'),len(restored.snapshot()['events'])),('10.00',2))

    def test_38_snapshot_roundtrip(self):
        self.funded(); snap=self.ledger.snapshot(); restored=self.Ledger.from_snapshot(snap)
        self.assertEqual(restored.snapshot(),snap)
        restored.apply(money(identity='c',seq=3,amount='1'))
        self.assertEqual(self.ledger.balance('alice'),'10.00')
        self.assertEqual(restored.balance('alice'),'11.00')

    def test_39_snapshot_tampered_balance(self):
        self.funded(); snap=self.ledger.snapshot(); snap['accounts'][0]['balance']='99.00'
        with self.assertRaises(self.Error): self.Ledger.from_snapshot(snap)

    def test_40_snapshot_wrong_seq(self):
        self.funded(); snap=self.ledger.snapshot(); snap['last_seq']=99
        with self.assertRaises(self.Error): self.Ledger.from_snapshot(snap)

    def test_41_snapshot_shape_and_version(self):
        base={'version':1,'last_seq':0,'accounts':[],'events':[]}
        for snap in [None,[],dict(base,version=True),dict(base,version=2),dict(base,extra=1),{'version':1},dict(base,last_seq=False)]:
            with self.subTest(snap=snap),self.assertRaises(self.Error): self.Ledger.from_snapshot(snap)

    def test_42_snapshot_account_order_and_types(self):
        self.ledger.apply_many([opened(),opened('b',2,'bob')]); snap=self.ledger.snapshot()
        variants=[]
        wrong=copy.deepcopy(snap); wrong['accounts'].reverse(); variants.append(wrong)
        wrong=copy.deepcopy(snap); wrong['accounts'][0]['closed']=0; variants.append(wrong)
        wrong=copy.deepcopy(snap); wrong['accounts'][0]['balance']='0'; variants.append(wrong)
        for wrong in variants:
            with self.subTest(wrong=wrong),self.assertRaises(self.Error): self.Ledger.from_snapshot(wrong)

    def test_43_snapshot_duplicate_history(self):
        self.funded(); snap=self.ledger.snapshot(); snap['events'].append(copy.deepcopy(snap['events'][0]))
        with self.assertRaises(self.Error): self.Ledger.from_snapshot(snap)

    def test_44_restore_detached_input(self):
        self.funded(); snap=self.ledger.snapshot(); restored=self.Ledger.from_snapshot(snap)
        snap['events'][0]['currency']='EUR'; snap['accounts'].clear()
        self.assertEqual(restored.snapshot()['events'][0]['currency'],'USD')
        self.assertEqual(restored.balance('alice'),'10.00')

    def cli(self,text,*args):
        src=self.root/'events.jsonl'; src.write_text(text,encoding='utf-8')
        return subprocess.run([sys.executable,'-m','ledger','replay',str(src),*map(str,args)],cwd=TREE,text=True,capture_output=True,timeout=10)

    def test_45_cli_valid(self):
        run=self.cli('\n'.join(map(json.dumps,[opened(),money()])))
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(run.stdout)['accounts'],[{'id':'alice','currency':'USD','balance':'10.00','closed':False}])

    def test_46_cli_blank_lines(self):
        run=self.cli('\n '+ '\n'+json.dumps(opened())+'\n\n')
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(run.stdout)['last_seq'],1)

    def test_47_cli_snapshot_output(self):
        out=self.root/'snapshot.json'; out.write_text('old')
        before_inode=out.stat().st_ino
        run=self.cli(json.dumps(opened()),'--snapshot',out)
        self.assertEqual(run.returncode,0,run.stderr)
        self.assertEqual(json.loads(out.read_text()),json.loads(run.stdout))
        self.assertNotEqual(out.stat().st_ino,before_inode,'snapshot must be replaced atomically, not truncated in place')
        self.assertIsInstance(json.loads(run.stdout)['accounts'],list)

    def test_48_cli_invalid_keeps_existing(self):
        out=self.root/'snapshot.json'; out.write_text('preserve exactly\n')
        run=self.cli(json.dumps(opened())+'\n{bad','--snapshot',out)
        self.assertEqual(run.returncode,2)
        self.assertEqual(out.read_text(),'preserve exactly\n')
        self.assertTrue(run.stderr.strip()); self.assertNotIn('Traceback',run.stderr)

    def test_49_cli_invalid_no_creation(self):
        out=self.root/'snapshot.json'
        run=self.cli(json.dumps(money()),'--snapshot',out)
        self.assertEqual(run.returncode,2)
        self.assertFalse(out.exists()); self.assertNotIn('Traceback',run.stderr)
        self.assertEqual(run.stdout,'')

    def test_50_cli_non_event(self):
        run=self.cli('null\n')
        self.assertEqual(run.returncode,2)
        self.assertTrue(run.stderr.strip()); self.assertNotIn('Traceback',run.stderr)

if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(LedgerCases)
    result=unittest.TextTestRunner(stream=sys.stderr,verbosity=1).run(suite)
    total=result.testsRun
    failed={getattr(test,'test_case',test).id() for test,_ in result.failures+result.errors+result.skipped}
    passed=total-len(failed)
    print(json.dumps({'passed':passed,'total':total,'rate':passed/total}))
