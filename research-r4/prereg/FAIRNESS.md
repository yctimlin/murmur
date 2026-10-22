# Round 4 fairness scheme (written 2026-10-19 23:05 Asia/Taipei, before any r4 development run)

Problem: the PI (this Claude session chain) both develops murmur changes and runs the final evaluation.
Goal: the final held-out evaluation must not be tunable by the developer.

## F1. Held-out tasks are authored by a separate process the PI never reads
- A separate `claude -p` process (prompt: heldout/AUTHOR-PROMPT.md, constrains FORM only: size, offline Python,
  open-ended design+build, domain diversity, no murmur/swarm hints) authors 4 NEW tasks directly into
  /srv/murmur-sealed-r4/heldout/ (mode 700). Its session log and calibration workspaces also live there.
- It calibrates each task with plain solo `codex exec` (runner2 "exec" arm, gpt-6-astra/high, its own lab dir inside
  the sealed dir) and enlarges a task (max 2 times) if solo active time < 40 min.
- It publishes ONLY heldout/PUBLIC.json: task ids (H1..H4), sha256 of each task bundle, calibration active minutes,
  status. When done, `sudo chown -R root:root /srv/murmur-sealed-r4` (author does it; PI verifies ownership only).
- The PI commits: never cat/ls/grep/find inside /srv/murmur-sealed-r4, never read the author's output beyond
  PUBLIC.json, never tail its stdout (it is redirected into the sealed dir). Process liveness checked by pid only.
- The calibration runs are NOT scored (separate from eval reps).

## F2. Frozen evaluation before the held-out runs
- Rubric (prereg/RUBRIC.md, based on r3 open-rubric), judge prompt, anonymizer, decision code (prereg/decide.py) and
  arm commits are frozen, sha256'd and committed BEFORE the held-out tasks are copied in. Amendments only as dated
  files prereg/AMENDMENT-*.md before unblinding.
- The final eval script copies the sealed tasks into the eval lab (via sudo) only at eval time, then runs all arms
  in randomized interleaved blocks (each block = one rep of every arm on one task) so time-of-day/relay drift is
  balanced.
- The candidate is frozen (commit sha recorded in prereg) before the eval script starts; no murmur change after.

## F3. Blind judging
- Separate `claude -p` judges with no access to arm names; random ids per judgment; 2 judgments per run, 3rd if gap > 1.5.
- Anonymization (strengthened vs r3, where the judge guessed solo vs team 82%): delivered tree only, no git history,
  PR.md removed and replaced by nothing for all arms (solo writes PR.md too), drop `.work/`, draft/planning notes,
  scrub identity words, normalize mtimes. The judge is asked to guess solo vs team at the end; the guess rate is
  reported as a blinding check (target: closer to 50%).
- Judge prompts never mention murmur, swarms or which arms exist.

## F4. Development tasks
- r3 tasks T1b/T2/T3b/T4b (and new dev tasks the PI may write) are development tasks: all mechanism screening uses
  only them. Held-out tasks are used exactly once, in the final evaluation.

## F5. Infrastructure failures
- Relay/API outages (503, empty catalog, CalledProcessError without delivery, Claude 403/limit) are withdrawn and
  rerun, never scored, with the same rule for all arms (r3 open_eval.is_infra rule).
