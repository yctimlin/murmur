# Round-3 open-task judging rubric (AMENDMENT-3; fixed before any run)
Judge: Claude CLI, independent reviewer, blind. Each submission is a copy of the delivered folder with arm/run identity removed
(folder renamed to a random id; git history squashed to one anonymous commit; logs, session files, .murmur*, AGENTS/peer/draft
artifacts removed; words murmur/peer/swarm/draft scrubbed from file names). The judge gets: the task brief, the anonymized folder
(it may read files and RUN the code: install, start servers, use CLI, run its tests) and this rubric. It never sees time/tokens.

Rules against bias: credit only behaviour you actually ran or verified in code; claims in DESIGN.md/README not found in the
code are penalised under design; document or code LENGTH earns nothing by itself. Anchors for every criterion: 0 absent/broken,
3 partial, 6 works on the main path, 8 works plus edge cases, 10 nothing missing found. Coverage = feature present and reachable;
correctness = behaves correctly when exercised (do not double count). Caps: does not start/install -> correctness <= 2 and
overall <= 3; destroys or modifies original input data -> robustness <= 2.
Procedure: first install and start per README (time-box 10 min of your effort), exercise the 5-8 most important flows from the
brief, then explore freely (time-box). Originals-untouched is checked mechanically (checksum) by the operator and given to you.
Finally state your guess of whether this was produced by a single agent or a team, as {"guess": "single"|"team"} (reported only).
Score each criterion 0-10 (integers), with 2-4 sentences of evidence each, citing files/commands it ran:
1. Requirement coverage (weight 3): how much of what the brief asks for (explicit and clearly implied) actually works.
2. Correctness, verified by running (weight 3): does it install and run per README; do the main flows work when exercised; bugs found.
3. Design quality (weight 2): architecture fit for the problem, data model, separation of concerns, sensible trade-offs, DESIGN.md honest and accurate.
4. Robustness (weight 2): edge cases, bad input, failure/restart behaviour named in the brief, data safety (originals untouched).
5. Code quality and tests (weight 1): readability, structure, meaningful tests that pass.
6. UX and docs (weight 1): CLI/web usability, README clarity, demo data.
Overall = weighted mean (0-10). Also list up to 3 severe defects (crash on main flow, data loss, does not start).
Output a final JSON line: {"coverage":..,"correctness":..,"design":..,"robustness":..,"code":..,"ux":..,"overall":..,"severe":[..]}

Consistency: every submission is judged twice in independent sessions (different random ids and task-order). If the two
overall scores differ by > 1.5, a third judgment is made and the median used; otherwise the mean. Per-task submissions are
also ranked pairwise once with order swapped (A/B then B/A) for base3 vs orig rep-matched pairs; the pairwise preference is
reported as a co-primary signal (base3 preferred rate with 90% CI; consistency = agreement between the two orders).

Analysis (pre-registered): per task, mean overall per arm (solo, orig, base3; 2 runs each). Primary: base3 - orig overall
difference (paired by task, mean over reps), with a paired t interval over tasks; secondary: each swarm arm vs solo; time
(active min) and input tokens ratios vs solo. Hidden tests: none (open tasks); the agent's own test pass and mutation score
are reported as secondary sanity only. Decision: base3 replaces orig as the baseline if base3-orig overall >= -0.5 (lower 90%
bound) and active time ratio <= 1.10; "better" is claimed only if the lower 90% bound > 0. Infra failures rerun; murmur
failures (crash, no delivery) score 0 overall and are never rerun.

Crash/no-delivery is defined identically for all arms incl. solo (no commit with work, or run exit != 0 without delivered tree). Limitation (pre-stated): 5 tasks x 2 reps gives df=4; the interval will be wide; reported as such.
