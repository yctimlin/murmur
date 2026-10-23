#!/bin/bash
# Exit when the count of finished FINAL results or scores changes, or after $1 seconds. Prints counts only.
c() { echo $(ls /workspace/r4/evallab/results/F-*/result.json 2>/dev/null | wc -l) $(ls /workspace/r4/judge/F/*.score.json 2>/dev/null | wc -l); }
s=$(c); end=$((SECONDS+$1)); while [ $SECONDS -lt $end ]; do sleep 60; [ "$(c)" != "$s" ] && break; done; echo "before: $s now: $(c)"
