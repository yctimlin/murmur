#!/usr/bin/env python3
"""Inventory retained judge P0/P1 findings and join exact-file git blame provenance.

Read-only historical evidence. No candidate code or reproducer is executed.
One row is one finding in one judge pass; repeated passes are NOT unique defects.
"""
import argparse
import collections
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess

EXT=r'(?:py|js|ts|tsx|jsx|html|css|sh|toml|yaml|yml|json|md)'
FILE=re.compile(r'(?<![\w])([/\w.-]+\.'+EXT+r')(?![\w])(?::([0-9]+(?:\s*[-–]\s*[0-9]+)?(?:\s*,\s*[0-9]+(?:\s*[-–]\s*[0-9]+)?)*)?)?')
START=re.compile(r'^(?:#{1,6}\s+.*\bP[01]\b|\d+[.)]\s+\*\*P[01]\b)')


def js(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def git(repo,*args):
    proc=subprocess.run(['git','--no-optional-locks','-C',str(repo),*args],capture_output=True)
    return proc.stdout if proc.returncode==0 else b''


def writecsv(path, rows, columns=None):
    columns=columns or list(dict.fromkeys(k for row in rows for k in row))
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=columns,lineterminator='\n');writer.writeheader();writer.writerows(rows)


def sections(path):
    lines=path.read_text(errors='replace').splitlines()
    starts=[i for i,line in enumerate(lines) if START.match(line)]
    for i in starts:
        heading=lines[i]
        level=len(heading)-len(heading.lstrip('#')) if heading.startswith('#') else 7
        end=len(lines)
        for j in range(i+1,len(lines)):
            if START.match(lines[j]): end=j;break
            h=re.match(r'^(#{1,6})\s',lines[j])
            if h and len(h[1])<=level: end=j;break
        title=re.sub(r'^(?:#{1,6}\s+|\d+[.)]\s+\*\*)','',heading)
        if not heading.startswith('#'): title=title.split('**',1)[0]
        yield i+1,title,'\n'.join(lines[i:end])


class Repo:
    def __init__(self,row):
        self.row=row; path=Path(row['path'])
        self.path=path/'work/origin.git' if row['mode']!='exec' else path/'repo'
        if row['mode']=='exec' and not (self.path/'.git').exists(): self.path=path
        self.head=row['main_head']; self.base=row['task_base']
        self.files=git(self.path,'ls-tree','-r','--name-only',self.head).decode(errors='replace').splitlines()
        self.by_base=collections.defaultdict(list)
        for f in self.files:self.by_base[Path(f).name].append(f)
        self.baseline=set(git(self.path,'rev-list',self.base).decode().splitlines()) if self.base else set()
        refs=git(self.path,'for-each-ref','--format=%(refname)','refs/heads/draft/').decode().splitlines()
        self.draft=set(git(self.path,'rev-list',*refs,'--not',self.base).decode().splitlines()) if refs and self.base else set()
        self.blames={};self.blobs={};self.commit_info={}

    def blob(self,file,revision=None):
        key=(revision or self.head,file)
        if key not in self.blobs:self.blobs[key]=git(self.path,'show',key[0]+':'+file)
        return self.blobs[key]

    def resolve(self,raw):
        if '/scratch/' in raw or raw.startswith(('scratch/','base/')):return None
        if '/result/' in raw:raw=raw.split('/result/',1)[1]
        elif raw.startswith('result/'):raw=raw[len('result/'):]
        raw=raw.removeprefix('./').rstrip('.')
        if raw.startswith('/'):return None
        if raw in self.files:return raw
        matches=[f for f in self.files if f.endswith('/'+raw)]
        if len(matches)==1:return matches[0]
        matches=self.by_base.get(raw,[])
        return matches[0] if len(matches)==1 else None

    def phase(self,commit,summary):
        if commit in self.baseline:return 'preexisting','ancestor_of_task_base'
        if commit in self.draft:return 'drafting','reachable_from_retained_draft_ref'
        if commit not in self.commit_info:
            raw=git(self.path,'show','-s','--format=%P',commit).decode().strip()
            self.commit_info[commit]=raw.split()
        if len(self.commit_info[commit])>1:return 'merging','last_change_is_merge_commit'
        if re.match(r'(?i)^(docs?\b|document\b|record\b|report\b|clarify\b|polish\b)',summary):return 'polishing','commit_subject_heuristic'
        if re.match(r'(?i)^(test\b|verify\b|review\b|add .*tests?\b|cover\b)',summary):return 'verification','commit_subject_heuristic'
        return 'drafting','implementation_commit_not_in_retained_draft_refs'

    def blame(self,file,revision=None):
        key=(file,revision or self.head)
        if key in self.blames:return self.blames[key]
        data=git(self.path,'blame','--line-porcelain',key[1],'--',file).decode(errors='replace').splitlines()
        result={};current={};line=None
        for s in data:
            m=re.match(r'^([0-9a-f]{40}) \d+ (\d+)(?: \d+)?$',s)
            if m:current={'commit':m[1]};line=int(m[2]);continue
            if s.startswith('author '):current['author']=s[7:]
            elif s.startswith('author-time '):current['author_time']=int(s[12:])
            elif s.startswith('summary '):current['summary']=s[8:]
            elif s.startswith('\t'):
                current['phase'],current['phase_basis']=self.phase(current['commit'],current.get('summary',''))
                result[line]=dict(current)
        self.blames[key]=result
        return result

    def locations(self,body,tree,manual=False):
        locations={}
        for m in FILE.finditer(body):
            raw=m[1];file=self.resolve(raw)
            if not file:continue
            # Reproduction tests and documentation references are not implementation blame.
            if file.endswith(('.md','.json','.yaml','.yml','.toml')) or any(part in ('tests','test','scratch','.venv') for part in Path(file).parts) or Path(file).name.startswith('test_'):continue
            ranges=[]
            if m[2]:
                for piece in m[2].split(','):
                    ns=re.findall(r'\d+',piece);ranges.append((int(ns[0]),int(ns[-1])))
            else:
                # Handle "file.py`, lines 3–9"; otherwise explicitly file-wide.
                nearby=body[m.end():m.end()+130]
                nums=re.search(r'^[^\n]{0,60}?\blines?\s+(\d+)(?:\s*[-–]\s*(\d+))?',nearby)
                if nums:ranges=[(int(nums[1]),int(nums[2] or nums[1]))]
                else:ranges=[(None,None)]
            for a,b in ranges:locations[(file,a,b)]={'file':file,'line_start':a,'line_end':b,'basis':('source_inspection_line' if manual else 'judge_line_citation') if a else 'judge_file_citation'}
        # If a file has line citations, don't widen it to every author just because it is also named elsewhere.
        line_files={f for f,a,b in locations if a}
        locations={k:v for k,v in locations.items() if k[1] or k[0] not in line_files}
        out=[]
        for _,loc in sorted(locations.items(),key=lambda kv:(kv[0][0],kv[0][1] or 0,kv[0][2] or 0)):
            file=loc['file'];candidate=tree/file
            blob=self.blob(file)
            match=candidate.is_file() and candidate.read_bytes()==blob
            loc['judge_file_matches_main']=match
            loc['judge_file_sha256']=hashlib.sha256(candidate.read_bytes()).hexdigest() if candidate.is_file() else ''
            if not match:
                loc.update(authors=[],blame=[],status='judge_file_missing_or_differs_from_final_main');out.append(loc);continue
            lines=self.blame(file)
            chosen=[(n,b) for n,b in lines.items() if loc['line_start'] is None or loc['line_start']<=n<=loc['line_end']]
            by_commit={}
            for n,b in chosen:
                if b['commit'] not in by_commit:by_commit[b['commit']]=dict(b,lines=[])
                by_commit[b['commit']]['lines'].append(n)
            loc.update(authors=sorted({b['author'] for _,b in chosen}),blame=[by_commit[k] for k in sorted(by_commit)],status='attributed' if chosen else 'line_out_of_range')
            out.append(loc)
        return out


def failure_mode(title,body):
    text=(title+' '+body).lower()
    # Mutually exclusive descriptive taxonomy, title-first to avoid incidental reproduction words.
    title=title.lower()
    if re.search(r'(?:cli|application|package|entrypoint).*(?:absent|missing)|required.*absent',title):return 'delivery_absent'
    if re.search(r'concurr|race|stale|delayed|overlap.*(?:poll|import|async)|external (?:save|deletion|editor)|in-flight|retarget|older.*(?:response|snapshot|import)',title):return 'concurrency_snapshot_identity'
    if re.search(r'interrupt|failed.*(?:write|regenerat|stream|editor|creation)|output.*(?:collis|publication)|hard-link|symlink.*destroy|lock.*(?:clos|replac)|commit failure',title):return 'failure_atomicity_lifecycle'
    if re.search(r'async|retry|replay|cancel|timezone|time.zone|dst|deadline|checkpoint|persistence|resume|wire format|expire|stopping',title):return 'lifecycle_serialization_time'
    if re.search(r'schema|unknown|collis|overwrite|corrupt|silently.*(?:los|discard|delet)|data.loss|enum|default|pluck|attribute',title):return 'data_integrity_schema'
    if re.search(r'sql|query|queries|aggregate|compar|csv|json|html|markdown|search|phrase|token|numeric|integer|sum |nan|literal|query|zero|field|text|column|group|alias|inline|snippet|labels|key|cache|render',title):return 'parsing_query_semantics'
    if re.search(r'crash|fail|reject|error|invalid|cannot|break|exponential|quadratic|overlong|blocked|blocks',title):return 'validation_error_handling'
    return 'other'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data-dir',type=Path,default=Path(__file__).resolve().parents[1]/'data')
    args=ap.parse_args();data=args.data_dir
    index=list(csv.DictReader((data/'index.csv').open()))
    findings=[];coverage=[]
    annotations={(v['run_id'],v['report_line']):v for v in json.loads((data/'quality_annotations.json').read_text())}
    for row in index:
        if not row['judge_source']:continue
        judge=Path(row['judge_source'])
        if judge.name=='results.json':judge=judge.parent/'judge'/row['judge_label']
        reports=sorted([p for p in [judge/'ADVERSARIAL.md',*judge.glob('*-adversarial/ADVERSARIAL.md')] if p.is_file()])
        if not reports:
            coverage.append({'run_id':row['run_id'],'report':'','findings':0,'p0':0,'p1':0,'status':'no_retained_adversarial_markdown'})
            continue
        repo=Repo(row)
        for report in reports:
            n0=n1=0
            for line,title,body in sections(report):
                severity=re.search(r'\bP[01]\b',title)[0]
                n0+=severity=='P0';n1+=severity=='P1'
                locs=repo.locations(body,report.parent/'result')
                note=annotations.get((row['run_id'],line),{})
                if note:
                    locs.extend(repo.locations(' '.join(note['locations']),report.parent/'result',manual=True))
                authors=sorted({a for loc in locs for a in loc['authors']})
                peers=sorted(a for a in authors if re.fullmatch(r'a\d+',a))
                exact_peers=sorted({a for loc in locs if loc['basis'] in ('judge_line_citation','source_inspection_line') for a in loc['authors'] if re.fullmatch(r'a\d+',a)})
                explicit=re.findall(r'SEAM\W{0,6}(yes|no)\b',body,re.I)
                claim=explicit[0].lower() if explicit and len(set(x.lower() for x in explicit))==1 else ('mixed' if explicit else 'unspecified')
                # A judge seam claim plus exact cited lines from different peers supports a peer seam.
                # File-wide authorship by itself never upgrades this conclusion.
                seam='confirmed_cross_peer' if claim=='yes' and len(exact_peers)>=2 else ('judge_claim_only' if claim=='yes' else ('judge_no' if claim=='no' else 'unknown'))
                if row['mode']=='exec':seam='not_applicable_solo'
                status='attributed' if locs and all(x['status']=='attributed' for x in locs) else ('partial' if any(x['status']=='attributed' for x in locs) else 'unresolved')
                phases=sorted({b['phase'] for loc in locs for b in loc['blame']})
                findings.append({'run_id':row['run_id'],'judge_label':row['judge_label'],'judge_pass':report.parent.name if report.parent!=judge else 'single',
                    'severity':severity,'title':title,'report':str(report),'report_line':line,
                    'failure_mode':failure_mode(title,body),'files_json':js(sorted({x['file'] for x in locs})),
                    'authors_json':js(authors),'peer_authors_json':js(peers),'phases_json':js(phases),
                    'judge_seam':claim,'peer_seam':seam,'exact_cited_peer_count':len(exact_peers),'attribution_status':status,'locations_json':js(locs),'source_inspection_note':note.get('reason',''),
                    'repro_paths_json':js(sorted(set(re.findall(r'scratch/[\w./-]+\.(?:py|sh|js)',body)))),
                    'evidence':'judge_report_only_not_rerun'})
            coverage.append({'run_id':row['run_id'],'report':str(report),'findings':n0+n1,'p0':n0,'p1':n1,'status':'parsed'})
    findings.sort(key=lambda x:(x['run_id'],x['report'],x['report_line']))
    coverage.sort(key=lambda x:(x['run_id'],x['report']))
    writecsv(data/'quality_findings.csv',findings)
    writecsv(data/'quality_coverage.csv',coverage)
    print(js({'findings':len(findings),'severity':dict(collections.Counter(r['severity'] for r in findings)),
              'attribution':dict(collections.Counter(r['attribution_status'] for r in findings)),
              'seam':dict(collections.Counter(r['peer_seam'] for r in findings))}))


if __name__=='__main__':main()
