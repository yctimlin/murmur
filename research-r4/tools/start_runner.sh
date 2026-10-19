#!/bin/bash
# r4 dev lab runner. PAR from $1 (default 1).
pgrep -f "r4-lab-runner" >/dev/null && { echo already running; exit 0; }
cd /workspace/r4/lab && MURMUR_LAB=/workspace/r4/lab MURMUR_LAB_NAME_RE='^E\d-' MURMUR_LAB_BUDGET=80 MURMUR_LAB_TOKEN_CAP=1500000000 \
MURMUR_LAB_MAX_CAP_MIN=120 MURMUR_LAB_PAR=${1:-1} MURMUR_LAB_PORT0=52000 \
  setsid nohup python3 /workspace/r4/tools/runner.py r4-lab-runner >> /workspace/r4/lab/runner.log 2>&1 < /dev/null &
echo started
