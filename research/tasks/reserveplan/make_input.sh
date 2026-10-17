#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "$0")"
if [[ -e input ]]; then
  echo 'input already exists; refusing to replace it' >&2
  exit 1
fi
mkdir -p input/examples
cp SPEC.md input/SPEC.md
cat > input/README.md <<'DOC'
# reserveplan

New project: implement the offline planner described in SPEC.md. There is no existing application code. Start with the example in examples/jobs.json and build an installable Python package with a module command line.
DOC
cat > input/examples/jobs.json <<'JSON'
{
  "version": 1,
  "horizon": 60,
  "resources": {"mill": {"capacity": 2, "unavailable": [[10, 15]]}},
  "bookings": [{"resource": "mill", "start": 0, "end": 3, "units": 1}],
  "jobs": [
    {"id": "cut", "duration": 5, "requires": {"mill": 1}},
    {"id": "polish", "duration": 4, "after": [{"id": "cut", "lag": 2}], "requires": {"mill": 2}, "deadline": 12}
  ]
}
JSON
export GIT_CONFIG_NOSYSTEM=1 GIT_CONFIG_GLOBAL=/dev/null
export GIT_AUTHOR_NAME=screening GIT_AUTHOR_EMAIL=screening@example.invalid
export GIT_COMMITTER_NAME=screening GIT_COMMITTER_EMAIL=screening@example.invalid
export GIT_AUTHOR_DATE=2026-10-17T00:00:00Z GIT_COMMITTER_DATE=2026-10-17T00:00:00Z
git -C input init -q -b main
git -C input add README.md SPEC.md examples/jobs.json
git -C input commit -qm 'Initialize reserveplan specification and example'
