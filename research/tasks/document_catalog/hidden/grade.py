"""Offline harness: run against a disposable copy, never import delivered code here."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

TOTAL = 48

def main():
    source = Path(sys.argv[1]).resolve()
    with tempfile.TemporaryDirectory(prefix='catalogue-score-') as directory:
        target = Path(directory) / 'tree'
        shutil.copytree(source, target, ignore=shutil.ignore_patterns('.git', '__pycache__', '.venv'), symlinks=False)
        env = dict(os.environ, PYTHONPATH=str(target), PYTHONDONTWRITEBYTECODE='1')
        try:
            completed = subprocess.run([sys.executable, str(Path(__file__).with_name('cases.py')), str(target)], cwd=target, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=180)
            lines = completed.stdout.splitlines()
            score = json.loads(lines[-1]) if lines else None
            if not isinstance(score, dict) or score.get('total') != TOTAL:
                raise ValueError('grader did not return expected case count')
            print(completed.stderr, file=sys.stderr, end='')
            print(json.dumps(score, sort_keys=True))
        except (subprocess.TimeoutExpired, ValueError, json.JSONDecodeError) as error:
            print(str(error), file=sys.stderr)
            print(json.dumps({'passed': 0, 'total': TOTAL, 'rate': 0.0}, sort_keys=True))

if __name__ == '__main__':
    main()
