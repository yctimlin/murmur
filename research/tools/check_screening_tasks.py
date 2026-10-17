#!/usr/bin/env python3
"""Pre-freeze setup/scorer smoke checks. Never run a candidate or a lab experiment."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile

BASE=Path(__file__).resolve().parents[1]/'tasks'

def digest(root,git=True):
    return {p.relative_to(root).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file() and (git or '.git' not in p.relative_to(root).parts)}

def main():
    rows=[]
    for source in sorted(BASE.iterdir()):
        if not (source/'TASK.json').is_file(): continue
        definition=json.loads((source/'TASK.json').read_text())
        assert definition['setup'] in ['py','py-e',None]
        assert isinstance(definition['expected_solo_min'],(int,float)) and definition['expected_solo_min']>0
        with tempfile.TemporaryDirectory(prefix='screening-check-') as directory:
            root=Path(directory)
            copies=[root/'first',root/'second']
            for task in copies:
                shutil.copytree(source,task,ignore=shutil.ignore_patterns('input','__pycache__'))
                subprocess.run([str(task/'make_input.sh')],check=True,capture_output=True,timeout=30)
            tree=copies[0]/'input'; before=digest(tree)
            assert digest(tree,git=False)==digest(copies[1]/'input',git=False),source.name+' nondeterministic generated files'
            grade=root/'relocated'; grade.mkdir(); shutil.copy2(copies[0]/'score.sh',grade/'score.sh'); shutil.copytree(copies[0]/'hidden',grade/'hidden')
            run=subprocess.run([str(grade/'score.sh'),str(tree)],cwd=root,text=True,capture_output=True,check=True,timeout=1200)
            score=json.loads(run.stdout.splitlines()[-1])
            assert isinstance(score['passed'],int) and isinstance(score['total'],int)
            assert score['total']>=30 and 0<=score['passed']<=score['total']
            assert score['rate']==score['passed']/score['total'] and score['rate']<=.3
            assert digest(tree)==before,source.name+' delivered tree changed'
            has_git=(tree/'.git').is_dir()
            if has_git:
                revisions=[subprocess.check_output(['git','--no-optional-locks','-C',str(t/'input'),'rev-parse','HEAD'],text=True).strip() for t in copies]
                assert revisions[0]==revisions[1]
            else:
                assert definition['class']=='plain-folder'
                assert len(before)>=300
                revisions=[]
            rows.append(dict(task=source.name,generated_files=len(digest(tree,git=False)),has_git=has_git,score=score,deterministic_content=True,input_unchanged=True,relocated_grader=True,fixture_commits=revisions))
    assert len(rows)>=3
    assert any(not r['has_git'] and r['generated_files']>=300 for r in rows)
    print(json.dumps(rows,indent=2,sort_keys=True))

if __name__=='__main__': main()
