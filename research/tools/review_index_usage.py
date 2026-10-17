#!/usr/bin/env python3
"""Independent raw-token review using final thread counters, not response summation."""
import collections
import csv
import datetime
import json
from pathlib import Path

DATA=Path(__file__).resolve().parents[1]/'data'

def main():
    rows=list(csv.DictReader((DATA/'sessions.csv').open()))
    total=collections.Counter(); methods=collections.Counter(); missing=[]; mismatches=[]
    by_run=collections.defaultdict(collections.Counter)
    run_timestamps=collections.defaultdict(set)
    for row in rows:
        modern=[]; legacy=[]
        for line in Path(row['path']).open():
            try: event=json.loads(line)
            except ValueError: continue
            timestamp=event.get('timestamp')
            if timestamp:
                try: run_timestamps[row['run_id']].add(datetime.datetime.fromisoformat(timestamp.replace('Z','+00:00')).timestamp())
                except (ValueError,TypeError): pass
            payload=event.get('payload') or {}
            if event.get('type')=='token_usage_record': modern.append(payload)
            if payload.get('type')=='token_count' and payload.get('info') and payload['info'].get('total_token_usage'):
                legacy.append(payload['info']['total_token_usage'])
        if modern:
            # Read final provider thread counters rather than summing response_usage.
            final=modern[-1]['thread_token_usage']; methods['final_thread_usage']+=1
        elif legacy:
            # This historical corpus has no such session; reject resets if one is added.
            for old,new in zip(legacy,legacy[1:]):
                assert all(new.get(k,0)>=old.get(k,0) for k in ['input_tokens','cached_input_tokens','output_tokens'])
            final=legacy[-1]; methods['last_legacy_cumulative']+=1
        else:
            missing.append({'run_id':row['run_id'],'session_id':row['session_id'],'path':row['path']})
            methods['missing']+=1
            continue
        values={'input':final.get('input_tokens',0),'uncached':final.get('input_tokens',0)-final.get('cached_input_tokens',0),'output':final.get('output_tokens',0)}
        if any(values[key]!=int(row[key]) for key in values):
            mismatches.append({'run_id':row['run_id'],'session_id':row['session_id'],'raw':values,'index':{key:row[key] for key in values}})
        total.update(values); by_run[row['run_id']].update(values)
    index=list(csv.DictReader((DATA/'index.csv').open()))
    active_mismatches=[]
    for row in index:
        values=by_run[row['run_id']]
        for key in ['input','uncached','output']:
            if row[key] and values[key]!=int(row[key]): mismatches.append({'run_id':row['run_id'],'key':key,'raw':values[key],'index':row[key]})
        timestamps=sorted(run_timestamps[row['run_id']])
        if timestamps:
            active=round(sum(min(120,b-a) for a,b in zip(timestamps,timestamps[1:]))/60,6)
            if abs(active-float(row['active_min']))>0.000001: active_mismatches.append({'run_id':row['run_id'],'raw':active,'index':row['active_min']})
    result={'raw_session_count':len(rows),'index_run_count':len(index),'token_totals':dict(total),'methods':dict(methods),'missing_usage_sessions':missing,'token_mismatches':mismatches,'active_min_mismatches':active_mismatches}
    print(json.dumps(result,indent=2,sort_keys=True))
    if mismatches or active_mismatches: raise SystemExit(1)

if __name__=='__main__': main()
