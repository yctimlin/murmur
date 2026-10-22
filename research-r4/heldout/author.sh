#!/bin/bash
# Launches the held-out task author (restarts it until PUBLIC.json says done). All its output stays in the sealed dir.
S=/srv/murmur-sealed-r4/heldout; cd $S || exit 1; echo $$ > /workspace/r4/heldout/author.pid
for i in $(seq 1 30); do
  /home/box/.local/bin/claude -p "$(cat /workspace/r4/heldout/AUTHOR-PROMPT.md)" --dangerously-skip-permissions --max-turns 400 \
    --output-format stream-json --verbose < /dev/null > $S/author-session-$i.jsonl 2> $S/author-session-$i.err
  echo "session $i exit $? $(date '+%F %T')" >> /workspace/r4/heldout/author.exit
  grep -q '"status": *"done"' /workspace/r4/heldout/PUBLIC.json 2>/dev/null && break
  [ -d $S ] || break; sleep 600
done
