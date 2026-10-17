#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 - <<'PY'
from pathlib import Path
import json
root = Path('input')
if root.exists():
    raise SystemExit('input already exists; remove it explicitly before regenerating')
(root / 'catalogue').mkdir(parents=True)
(root / 'catalogue' / '__init__.py').write_text('''"""Offline support archive catalogue."""
def build_catalog(root):
    return {"documents": [], "errors": []}

def search_catalog(catalog, query="", *, tags=None, status="published", limit=None):
    return []
''')
(root / 'catalogue' / '__main__.py').write_text('''import sys
sys.stderr.write("Catalogue command line is not implemented yet\\n")
raise SystemExit(2)
''')
for i in range(336):
    folder = root / 'archive' / ('team-%02d' % (i % 12))
    folder.mkdir(parents=True, exist_ok=True)
    key = 'article-%03d' % (i % 310)
    doc = {'id': key, 'title': 'Support guide %03d' % i,
           'body': 'Troubleshooting offline clients. Check routing and cache settings. Topic %d.' % (i % 17),
           'revision': 1 + i // 310, 'tags': ['Client' if i % 2 else 'Server', 'topic-%02d' % (i % 17)],
           'status': ['published','published','published','draft','archived'][i % 5],
           'updated': '2025-%02d-%02d' % (1 + i % 12, 1 + i % 28),
           'links': ['article-%03d' % ((i + 1) % 310)]}
    (folder / ('record-%03d.json' % i)).write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True) + '\n')
(root / 'README.md').write_text('''# Offline support archive
The `archive/` tree contains 336 article revisions from twelve support teams.
The catalogue package is a starter. Implement the API and CLI described in the task brief.
Run commands from this folder with Python 3.11 or newer. No dependency installation is needed.
''')
(root / '.gitignore').write_text('__pycache__/\n*.pyc\nindex.json\n')
PY
