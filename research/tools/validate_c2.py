#!/usr/bin/env python3
"""Independent review of C2 registration/fixture; never launches a lab run."""
import collections
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
R = ROOT / 'research'
registration = json.loads((R / 'prereg/C2.json').read_text())
jobs = registration['jobs']
assert registration['batch'] == 'C2'
assert (ROOT / registration['notebook']).is_file()
assert len(jobs) == 3
assert len({j['arm'] for j in jobs}) == 3
assert all(j['peers'] == 'exec' and j['task'] == 'workflow_store' for j in jobs)
assert all(j['cap'] == '100m' and not j.get('env') and not j.get('config') for j in jobs)
assert max(collections.Counter(j['block'] for j in jobs).values()) <= 3
assert len({j['block'] for j in jobs}) == 1
gates = (R / 'GATES.md').read_text()
base = re.search(r'base3 \(bug-fix base\): ([0-9a-f]{40})', gates).group(1)
assert all(j['rev'] == base for j in jobs)
subprocess.run(['git', '--git-dir=/workspace/self3/labdata/repos/r3.git', 'cat-file', '-e', base+'^{commit}'],check=True)
remaining_jobs = int(re.search(r'lab budget: 36 jobs; used 18; remaining (\d+)', gates).group(1))
assert remaining_jobs == 18
raw = R / 'data/raw/C1'
consumed = sum(json.loads((raw / (j['name']+'.json')).read_text())['input']
               for j in json.loads((raw / 'jobs.json').read_text()))
b = registration['predictions']['budget']
assert b['input_used_before_C2'] == consumed == 92629793
assert b['estimated_input_tokens'] == len(jobs)*3000000 == 9000000
assert b['model_expected_input_tokens'] == len(jobs)*registration['predictions']['point_forecasts']['input'] == 8100000
assert b['input_remaining_before_C2'] == 450000000-consumed == 357370207
assert b['input_remaining_after_estimate'] == 450000000-consumed-9000000 == 348370207
assert b['jobs_remaining_after_C2'] == remaining_jobs-len(jobs) == 15
# Old task/prereg/raw data must remain immutable throughout this phase.
immutable = ['research/prereg/C1.json','research/data/raw/C1','research/tasks/document_catalog',
             'research/tasks/ledger_replay','research/tasks/reserveplan']
subprocess.run(['git','diff','--exit-code','963ae66','--',*immutable],cwd=ROOT,check=True,capture_output=True)
source = R / 'tasks/workflow_store'
source_manifest = {str(p.relative_to(source)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(source.rglob('*')) if p.is_file() and not any(x in p.parts for x in ['input','__pycache__'])}
with tempfile.TemporaryDirectory(prefix='a2-c2-fixture-') as tmp:
    generated = []
    for label in ['first','second']:
        dest = Path(tmp)/label
        shutil.copytree(source,dest,ignore=shutil.ignore_patterns('input','__pycache__'))
        subprocess.run(['bash',str(dest/'make_input.sh')],check=True,capture_output=True)
        files = {str(p.relative_to(dest/'input')):hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in sorted((dest/'input').rglob('*')) if p.is_file() and '.git' not in p.relative_to(dest/'input').parts}
        commit = subprocess.check_output(['git','-C',str(dest/'input'),'rev-parse','HEAD'],text=True).strip()
        generated.append({'files':files,'rev':commit})
    assert generated[0] == generated[1]
    assert set(generated[0]['files']) == {'SPEC.md','README.md','.gitignore','examples/batch.json'}
result = {'valid':True,'jobs':len(jobs),'blocks':1,'swarm_jobs':0,'base_revision':base,
          'jobs_remaining_after_C2':15,'input_used_before_C2':consumed,
          'input_remaining_after_estimate':348370207,'old_tasks_prereg_and_raw_unchanged':True,
          'new_task_manifest':source_manifest,'fixture_deterministic':True,
          'fixture_has_hidden_or_reference':False,'fixture':generated[0],
          'notes':['Manual review confirms all-three-run valid/delivered/leak-free/uncensored eligibility, score<=.85 and active>=30.',
                   'Calibration is one-block same-treatment description; subsequent exec/solo causal comparison is explicitly not licensed.',
                   'Task duration and quality remain unknown until scheduler calibration. No lab experiment launched by this validator.']}
(R / 'data/C2-design-independent-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
