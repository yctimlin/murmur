You are an independent task author for a software-engineering evaluation. Work autonomously; nobody will answer
questions. Your output directory is SEALED=/srv/murmur-sealed-r4/heldout (already exists, writable by you).
Everything you write goes there, except one public summary file named below. Never print task content to stdout.

## What to produce
Four NEW, large, open-ended "design and build" software tasks, ids H1, H2, H3, H4, each in $SEALED/tasks/<id>/:
- TASK.json: {"class":"open","setup":null,"expected_solo_min":<your estimate>}
- brief.md: the task brief given to the implementer (a product-style brief: users, goals, required capabilities,
  constraints, what "done" means at a high level). It must be open-ended (many valid designs) but large: a strong
  engineer working alone with an AI coding agent should need well over 40 minutes. It must require several
  interacting parts (e.g. data model + ingestion + core logic + an interface (CLI and/or local web UI) + tests + docs).
- input/: the starting folder (a README.md plus realistic input data or an existing small codebase to extend).
  Generate input data deterministically with a script; keep the generator script in $SEALED/gen/, not in input/.
Constraints: Python 3.12+ standard library is available, no network access during the task (no pip installs can be
assumed), runs on Linux, offline. Pick four DIFFERENT domains, and do not reuse these existing ones: research notes
archive/hub, clinic shift planning/rota, CI platform for a monorepo, household budget/bank exports, job queue.
Do not mention AI agents, teams, swarms, parallelism or multi-agent work in any brief. Briefs should be 400-900 words.

## Calibration (required)
Each task must take a single plain `codex exec` run at least 40 active minutes. Calibrate with the lab runner:
1. mkdir -p $SEALED/lab/{queue,results,tasks}; copy each task dir to $SEALED/lab/tasks/<id>/ (TASK.json, brief.md, input/).
2. Start a runner (once, detached):
   cd $SEALED/lab && MURMUR_LAB=$SEALED/lab MURMUR_LAB_NAME_RE='^CAL-' MURMUR_LAB_BUDGET=14 MURMUR_LAB_PAR=2 \
   MURMUR_LAB_MAX_CAP_MIN=120 setsid nohup python3 /workspace/self3/lab/runner2.py > $SEALED/lab/runner.log 2>&1 &
3. Submit a job by writing $SEALED/lab/queue/CAL-<id>-v<k>.json containing
   {"task":"<id>","peers":"exec","cap":"120m"}  (write to a .tmp file then rename).
4. Results: $SEALED/lab/results/CAL-<id>-v<k>/result.json; the field active_min is the solo active time.
   Before each batch check the model relay: `codex debug models` must list gpt-6-astra; if a run failed because of
   an outage (error, no delivery, 503), rerun it (it does not count as an enlargement).
5. If active_min < 40, ENLARGE the task (more required capabilities / more data / harder constraints; keep it
   coherent and open-ended), re-copy to $SEALED/lab/tasks/<id>-v<k+1>/ with a new id like H2v2, and recalibrate.
   At most 2 enlargements per task. If a task is still < 40 min after 2 enlargements, replace it with a new task in
   a new domain (id H5, H6...) — at most 2 replacements in total.
Run at most 2 calibrations at the same time. Poll with sleeps of at most 9 minutes per command; runs take ~1-2 h.

## Finish
- The final task set = the 4 task versions that passed (>= 40 min). Copy them to $SEALED/final/<slot>/ where slot is
  H1..H4 (with TASK.json, brief.md, input/).
- For each final slot compute the bundle sha256: `cd $SEALED/final/<slot> && find . -type f | sort | xargs sha256sum | sha256sum`.
- Write the ONLY public file /workspace/r4/heldout/PUBLIC.json:
  {"status":"done","finished_at":"<time>","tasks":[{"slot":"H1","version_id":"...","bundle_sha256":"...",
  "calib_active_min":<n>,"enlargements":<n>}, ...],"notes":"<no task content, no domains>"}
  While working, keep PUBLIC.json updated with {"status":"working", ...} (no content, no domains, numbers only).
- Stop the runner you started (kill its pid). Then run: sudo chown -R root:root /srv/murmur-sealed-r4 && sudo chmod -R go-rwx /srv/murmur-sealed-r4
Never reveal task domains or content in PUBLIC.json or any file outside $SEALED.

## Resumability
You may be interrupted and restarted with this same prompt. Keep $SEALED/AUTHOR-STATE.md up to date (what is
authored, which calibration jobs are queued/running/done, next step). On start, if it exists, read it, check
`pgrep -af runner2.py` for your runner (MURMUR_LAB=$SEALED/lab) and existing results, and continue without
redoing finished work or resubmitting jobs that already have a result or a .claimed file.
