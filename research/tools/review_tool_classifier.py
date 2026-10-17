#!/usr/bin/env python3
"""Reproduce a fixed-seed, independently annotated 40-call classifier spot audit."""
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import random

ROOT=Path(__file__).resolve().parents[1]
# Manual labels assess the actual operations under documented category precedence.
# Mixed wrappers/fixture writes are ambiguous rather than silently treated as errors.
ORIGINAL_LABELS='board edit other file_read edit edit git_read git_sync wait verify other wait verify wait edit other board board verify git_read wait git_read edit other edit verify git_read git_read verify edit verify wait verify edit git_read edit wait other board other'.split()

ANNOTATIONS={
  6:('verify','ambiguous','Inline assertion audit plus git inspection and board post; mechanical git_read priority misses semantic verification.'),
  9:('git_sync','clear','git fetch/log/list/sed plus board post; reading a test filename is not executing tests.'),
  12:('file_read','clear','Only cat/sed/rg reads, including test_registry.py and test_storage.py.'),
  14:('verify','ambiguous','Crash-recovery experiment writes temporary fixture files; mechanical edit classification is declared but semantically verification.'),
  16:('file_read','clear','Tool-metadata filtering mentions collaboration names; actual tool execution is pwd/rg/head file discovery.'),
  25:('board','clear','File reads plus a board post; test_plugins.py is read, not executed; board outranks file_read under declared rule.'),
  28:('board','clear','Board post mentions pytest, followed by HTTP server startup and board reads; no test invocation.'),
  32:('file_read','clear','Only rg/sed reads of test_storage.py/test_priority.py/test_api.py/test_sql_huey.py.'),
  34:('verify','ambiguous','Application --help and build smoke commands plus git inspection and board post; no recognized test runner token.'),
}

def main():
    definition=importlib.util.spec_from_file_location('reviewed_index',ROOT/'tools/index_runs.py')
    module=importlib.util.module_from_spec(definition);definition.loader.exec_module(module)
    calls=[]
    for row in csv.DictReader((ROOT/'data/sessions.csv').open()):
        for line in Path(row['path']).open():
            try: event=json.loads(line)
            except ValueError: continue
            payload=event.get('payload') or {}
            if payload.get('type') in ('function_call','custom_tool_call'):
                text=str(payload.get('name',''))+' '+str(payload.get('input') or payload.get('arguments') or '')
                calls.append({'run_id':row['run_id'],'session_id':row['session_id'],'call_id':payload.get('call_id'),'raw_path':row['path'],'text':text,'payload':payload})
    population=len(calls);random.Random(17).shuffle(calls)
    result=[]
    for index,row in enumerate(calls[:40]):
        text=row.pop('text');assigned=module.kind(text,row.pop('payload'))
        expected,status,note=ANNOTATIONS.get(index,(ORIGINAL_LABELS[index],'consistent','No clear disagreement with original documented operational category.'))
        # Avoid copying opaque peer-message payloads into derived artifacts.
        excerpt='send_message [opaque message payload omitted]' if text.startswith('send_message ') else text[:1200]
        result.append(dict(sample_index=index,**row,raw_sha256=hashlib.sha256(text.encode()).hexdigest(),automatic_category=assigned,audited_category=expected,audit_type=status,disagrees=expected!=assigned,rationale=note,excerpt=excerpt))
    summary={'population_calls':population,'sample_calls':40,'seed':17,'clear_disagreements':sum(r['audit_type']=='clear' and r['disagrees'] for r in result),'ambiguous_disagreements':sum(r['audit_type']=='ambiguous' and r['disagrees'] for r in result),'new_disagreements':sum(r['audit_type']=='consistent' and r['disagrees'] for r in result),'cases':result}
    print(json.dumps(summary,indent=2,sort_keys=True))

if __name__=='__main__':main()
