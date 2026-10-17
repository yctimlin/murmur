#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ -e input ]]; then echo 'input already exists' >&2; exit 1; fi
mkdir -p input/examples
cp SPEC.md input/SPEC.md
cat > input/README.md <<'DOC'
# workflow_store
Implement the durable workflow execution store in SPEC.md. The repository intentionally contains no implementation. The public JSON batch illustrates submission and claiming; completion tokens identify a workflow, task, attempt, and worker. Add documentation and tests alongside the package.
DOC
cat > input/examples/batch.json <<'JSON'
[
 {"id":"submit","now":0,"op":"submit","workflow":"build","tasks":[{"id":"compile","max_attempts":2,"retry_delay":3},{"id":"notify","after":["compile"],"join":"all_done"}]},
 {"id":"claim","now":0,"op":"claim","worker":"worker-1","lease":10,"limit":1},
 {"id":"finish","now":2,"op":"finish","token":{"workflow":"build","task":"compile","attempt":1,"worker":"worker-1"},"ok":true,"result":{"artifact":"out.zip"}}
]
JSON
cat > input/.gitignore <<'DOC'
__pycache__/
*.pyc
*.db
*.sqlite
DOC
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_AUTHOR_NAME=screening GIT_AUTHOR_EMAIL=screening@example.invalid
export GIT_COMMITTER_NAME=screening GIT_COMMITTER_EMAIL=screening@example.invalid
export GIT_AUTHOR_DATE=2026-10-17T00:00:00Z GIT_COMMITTER_DATE=2026-10-17T00:00:00Z
git -C input init -q -b main
git -C input add .
git -C input commit -qm 'Initialize durable workflow store contract'
