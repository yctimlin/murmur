#!/usr/bin/env python3
"""Independent raw-Git review of the quality localization CSV (no candidate code)."""
import collections
import csv
import hashlib
import json
import re
import subprocess
from pathlib import Path

DATA=Path(__file__).resolve().parents[1]/'data'

def main():
    runs={r['run_id']:r for r in csv.DictReader((DATA/'index.csv').open())}
    rows=list(csv.DictReader((DATA/'quality_findings.csv').open()))
    checked_blame={};checked_blobs=set();errors=[];counts=collections.Counter()
    def git(repo,*args):
        p=subprocess.run(['git','--no-optional-locks','-C',str(repo),*args],capture_output=True)
        if p.returncode: raise RuntimeError(p.stderr.decode(errors='replace'))
        return p.stdout
    for row in rows:
        r=runs[row['run_id']];folder=Path(r['path'])
        repo=folder/'work/origin.git' if r['mode']!='exec' else folder/'repo'
        if r['mode']=='exec' and not (repo/'.git').exists():repo=folder
        report=Path(row['report']);lines=report.read_text().splitlines();start=int(row['report_line'])-1
        if row['severity'] not in lines[start]:errors.append(['heading',row['run_id'],start+1])
        actual_peers=set()
        for loc in json.loads(row['locations_json']):
            f=loc['file'];blobkey=(str(repo),r['main_head'],f,str(report.parent/'result'/f))
            if blobkey not in checked_blobs:
                original=git(repo,'show',r['main_head']+':'+f)
                snapshot=(report.parent/'result'/f).read_bytes()
                if original!=snapshot or hashlib.sha256(snapshot).hexdigest()!=loc['judge_file_sha256']:
                    errors.append(['snapshot',blobkey])
                checked_blobs.add(blobkey)
            key=(str(repo),r['main_head'],f,loc['line_start'],loc['line_end'])
            if key not in checked_blame:
                args=['blame','--line-porcelain']
                if loc['line_start'] is not None:args+=['-L',f"{loc['line_start']},{loc['line_end']}"]
                text=git(repo,*args,r['main_head'],'--',f).decode(errors='replace')
                author='';commit='';actual=collections.defaultdict(set)
                for line in text.splitlines():
                    head=re.match(r'^([a-f0-9]{40}) \d+ (\d+)(?: \d+)?$',line)
                    if head:commit=head[1];number=int(head[2])
                    elif line.startswith('author '):author=line[7:]
                    elif line.startswith('\t'):actual[(commit,author)].add(number)
                checked_blame[key]=actual
            actual=checked_blame[key]
            stored={(b['commit'],b['author']):set(b['lines']) for b in loc['blame']}
            if dict(actual)!=stored:errors.append(['blame',key])
            if loc['basis'] in ('judge_line_citation','source_inspection_line'):
                actual_peers.update(a for _,a in actual if re.fullmatch('a[0-9]+',a))
            for b in loc['blame']:
                if b['phase']=='preexisting':
                    p=subprocess.run(['git','--no-optional-locks','-C',str(repo),'merge-base','--is-ancestor',b['commit'],r['task_base']],capture_output=True)
                    if p.returncode:errors.append(['preexisting',row['run_id'],b['commit']])
        if row['peer_seam']=='confirmed_cross_peer':
            if row['judge_seam']!='yes' or len(actual_peers)<2:errors.append(['seam',row['run_id'],start+1])
            counts['confirmed_seams']+=1
        counts[row['severity']]+=1
    reports=collections.defaultdict(set)
    for c in csv.DictReader((DATA/'quality_coverage.csv').open()):
        if c['report']:reports[c['run_id']].add(c['report'])
    for run,source_reports in reports.items():
        p0=sum(r['run_id']==run and r['severity']=='P0' for r in rows)/len(source_reports)
        if runs[run]['judge_p0'] and p0!=float(runs[run]['judge_p0']):errors.append(['count',run,p0,runs[run]['judge_p0']])
    result=dict(findings=len(rows),severity_and_seams=dict(counts),unique_blame_queries=len(checked_blame),unique_snapshot_checks=len(checked_blobs),errors=errors)
    print(json.dumps(result,indent=2,sort_keys=True))
    if errors:raise SystemExit(1)

if __name__=='__main__':main()
