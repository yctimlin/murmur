"""Operator positive-control CLI; copied into temporary control tree only."""
import argparse
import json
import os
from pathlib import Path
import sys
import tempfile
from . import Store,StoreError

def strict_pairs(items):
    result={}
    for k,v in items:
        if k in result:raise ValueError('duplicate key')
        result[k]=v
    return result

def read_input(path):
    try:text=sys.stdin.read() if path=='-' else Path(path).read_text(encoding='utf8')
    except (OSError,UnicodeError) as exc:raise StoreError('input') from exc
    try:return json.loads(text,object_pairs_hook=strict_pairs,parse_constant=lambda v:(_ for _ in ()).throw(ValueError(v)))
    except (ValueError,TypeError) as exc:raise StoreError('json') from exc

def output(value,path):
    text=json.dumps(value,ensure_ascii=False,allow_nan=False)+'\n'
    if path is None:sys.stdout.write(text);return
    temp=None
    try:
        target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
        fd,temp=tempfile.mkstemp(dir=target.parent,prefix='.workflow-')
        with os.fdopen(fd,'w',encoding='utf8') as stream:stream.write(text)
        os.replace(temp,target);temp=None
    except (OSError,UnicodeError) as exc:raise StoreError('output') from exc
    finally:
        if temp:
            try:os.unlink(temp)
            except OSError:pass

def main():
    p=argparse.ArgumentParser();p.add_argument('db');sub=p.add_subparsers(dest='op',required=True)
    for name in ('apply','batch','snapshot','export','load'):
        s=sub.add_parser(name)
        if name in ('apply','batch','load'):s.add_argument('input')
        if name!='load':s.add_argument('--output')
    args=p.parse_args()
    try:
        data=read_input(args.input) if hasattr(args,'input') else None
        if args.op=='batch' and type(data) is not list:raise StoreError('schema')
        with Store(args.db) as s:
            if args.op=='apply':result=s.apply(data)
            elif args.op=='batch':result=s.apply_many(data)
            elif args.op=='snapshot':result=s.snapshot()
            elif args.op=='export':result=s.export()
            else:s.load(data);result={'loaded':True}
        output(result,getattr(args,'output',None))
    except StoreError as exc:
        sys.stderr.write(json.dumps({'error':exc.code})+'\n');return 2
    return 0

if __name__=='__main__':raise SystemExit(main())
