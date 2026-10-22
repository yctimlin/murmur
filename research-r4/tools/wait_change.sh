#!/bin/bash
# Exit when the count of finished E4 results or E4 scores changes, or after $1 seconds.
c() { echo $(ls /workspace/r4/lab/results/E4-*/result.json 2>/dev/null | wc -l) $(ls /workspace/r4/judge/E4/*.score.json 2>/dev/null | wc -l) $(ls /workspace/r4/judge/E1/*.score.json | wc -l); }
s=$(c); end=$((SECONDS+$1)); while [ $SECONDS -lt $end ]; do sleep 60; [ "$(c)" != "$s" ] && break; done; echo "before: $s now: $(c)"
