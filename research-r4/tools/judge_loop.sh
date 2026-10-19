#!/bin/bash
# Judge finished runs of experiment $1 every 10 min until $2 runs have scores (or STOPJUDGE exists).
E=$1; N=$2; echo $$ > /workspace/r4/judge/$E.loop.pid
while [ ! -f /workspace/r4/judge/STOPJUDGE ]; do
  python3 /workspace/r4/tools/r4eval.py judge $E --par ${3:-1} >> /workspace/r4/judge/$E.loop.log 2>&1
  [ $(ls /workspace/r4/judge/$E/*.score.json 2>/dev/null | wc -l) -ge $N ] && break
  sleep 600
done
