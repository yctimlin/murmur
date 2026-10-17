#!/usr/bin/env python3
"""Reproduce task controls without running a model or changing a frozen input.
Outputs JSON on stdout; preserves scorer stderr and results under --output.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

TASK=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    output=Path(args.output).resolve();output.mkdir(parents=True,exist_ok=True)
    reference=(TASK/'controls/reference.py').read_text();cli=(TASK/'controls/reference_cli.py').read_text()
    mutations={
      'expiry_strict':("t['expires']<=self.clock", "t['expires']<self.clock"),
      'retry_from_observation':("{'error':'lease_expired'},t['expires'])", "{'error':'lease_expired'},self.clock)"),
      'no_fencing_attempt':(" or t['attempts']!=tok['attempt']", ""),
      'weak_typed_equality':("dump(a)==dump(b)", "a==b"),
      'priority_ascending':("(-t['priority'],w,t['id'])", "(t['priority'],w,t['id'])"),
      'retry_linear':("2**(t['attempts']-1)", "1"),
      'batch_partial_commit':("except BaseException:\n            self.db.rollback();raise", "except BaseException:\n            if 'e' in locals():self._save(e);self.db.commit()\n            else:self.db.rollback()\n            raise"),
      'load_without_state_check':("if not equal(e.export(),bundle):fail('snapshot')", "if False:fail('snapshot')"),
    }
    report={}
    with tempfile.TemporaryDirectory(prefix='workflow-controls-') as temp:
        root=Path(temp)
        # make_input only receives its public source files. The gate uses the same script.
        public=root/'public';public.mkdir()
        for name in ('make_input.sh','SPEC.md'):shutil.copy2(TASK/name,public/name)
        subprocess.run(['bash',str(public/'make_input.sh')],check=True,capture_output=True,text=True)
        trees={'baseline':public/'input'}
        for name,code in [('positive',reference)]+[(n,reference.replace(a,b)) for n,(a,b) in mutations.items()]:
            if name in mutations and mutations[name][0] not in reference:raise RuntimeError('mutation anchor absent: '+name)
            tree=root/name;pkg=tree/'workflow_store';pkg.mkdir(parents=True);(pkg/'__init__.py').write_text(code);(pkg/'__main__.py').write_text(cli);trees[name]=tree
        for name,tree in trees.items():
            proc=subprocess.run(['bash',str(TASK/'score.sh'),str(tree)],capture_output=True,text=True,timeout=620)
            (output/f'{name}.log').write_text(proc.stderr)
            (output/f'{name}.json').write_text(proc.stdout)
            result=json.loads(proc.stdout.strip().splitlines()[-1]);report[name]=result
        if report['baseline']['passed']!=0:raise RuntimeError('baseline should be zero')
        if report['positive']['rate']!=1:raise RuntimeError('positive control does not pass')
        if any(report[name]['rate']>=1 for name in mutations):raise RuntimeError('undetected defect control')
        # Ensure the public input has no hidden/reference code and no untracked files.
        files=subprocess.run(['git','-C',str(public/'input'),'ls-files'],capture_output=True,text=True,check=True).stdout.splitlines()
        report['public_input_files']=files
    report['control_kind']='deterministic local authored controls; not model calibration or runner mutation score'
    report['sha256']={str(p.relative_to(TASK)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(TASK.rglob('*')) if p.is_file() and '__pycache__' not in p.parts}
    (output/'summary.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report,indent=2,sort_keys=True))

if __name__=='__main__':main()
