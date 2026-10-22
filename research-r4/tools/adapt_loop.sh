#!/bin/bash
# Interim look + queue top-up every 5 min (prereg/AMENDMENT-2.md + AMENDMENT-5) until STOPADAPT exists.
echo $$ > /workspace/r4/analysis/adapt/loop.pid
while [ ! -f /workspace/r4/analysis/adapt/STOPADAPT ]; do
  python3 /workspace/r4/tools/adapt5.py >> /workspace/r4/analysis/adapt/loop.log 2>&1
  sleep 300
done
