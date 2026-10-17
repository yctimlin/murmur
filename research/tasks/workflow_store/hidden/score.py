#!/usr/bin/env python3
"""Score a fresh copy; never import from or execute inside the supplied tree."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from cases import suite


def main():
    tests=suite(); total=tests.countTestCases()
    if len(sys.argv)==4 and sys.argv[1]=='--worker':
        tree=Path(sys.argv[2]); result_path=Path(sys.argv[3])
        os.chdir(tree)
        sys.path[:0]=[str(tree),str(tree/'src')]
        result=unittest.TextTestRunner(stream=sys.stderr,verbosity=1).run(tests)
        passed=result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped)
        result_path.write_text(json.dumps({'passed':passed,'total':total,'rate':passed/total}))
        return
    passed=0
    try:
        if len(sys.argv)!=2: raise ValueError('usage: score.sh <delivered tree>')
        source=Path(sys.argv[1]).resolve()
        if not source.is_dir(): raise ValueError('delivered tree must be a directory')
        with tempfile.TemporaryDirectory(prefix='workflow-store-score-') as temp:
            root=Path(temp);tree=root/'tree'
            shutil.copytree(source,tree,symlinks=False,ignore=shutil.ignore_patterns('.git','.venv','__pycache__'))
            env=os.environ.copy();env['PYTHONPATH']=os.pathsep.join([str(tree),str(tree/'src')])
            env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONHASHSEED']='0';env['PIP_NO_INDEX']='1'
            result_file=root/'result.json'
            proc=subprocess.run([sys.executable,str(HERE/'score.py'),'--worker',str(tree),str(result_file)],cwd=tree,env=env,capture_output=True,text=True,timeout=600)
            # Keep diagnostics bounded, while preserving the final JSON line as the interface.
            if proc.stderr: print(proc.stderr[-18000:],file=sys.stderr,end='')
            if result_file.is_file(): passed=json.loads(result_file.read_text())['passed']
    except Exception as exc:
        print('scoring failed: '+str(exc),file=sys.stderr)
    print(json.dumps({'passed':passed,'total':total,'rate':passed/total},sort_keys=True))


if __name__=='__main__': main()
