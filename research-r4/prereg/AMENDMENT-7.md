# AMENDMENT-7 (tooling / throughput only) — 2026-10-21 10:44 Asia/Taipei

Trigger: user directive 10:40 (via supervisor): speed up by running more sessions in parallel.

Changes (no rule, metric, arm, task, threshold or stopping change):
1. Dev lab runner parallelism raised PAR 3 -> 4 (restart-safe parent restart; in-flight runs untouched).
2. Judge loop parallelism raised 2 -> 4. Failed judgments from the Claude 429 DAILY_LIMIT window (10-21 07:49-10:07)
   are retried automatically (judge_one is resumable; no verdict was recorded for them). One in-flight judge
   (~5 min old) was killed by the restart and will be redone from scratch with a fresh anonymized copy.
3. Adaptive allocation (adapt5.py, 1 pending job) is unchanged; with PAR 4 the runner simply fills a 4th slot.

Validity: active time is freeze-excluded (active_nf, heartbeat gaps > 60 s), so extra concurrency cannot inflate the
primary speed metric via VM freezes. Risk = CPU/memory contention slowing runs inside non-frozen time; this affects all
arms concurrently (arms interleaved by the adaptive queue). Measured before the change: 8 cores, 15 GB RAM, ~7-8 GB
available, load 1-min 2.9 / 15-min 11.4. Guard: if available memory drops below 2 GB or 1-min load stays > 16 while not
frozen, PAR goes back to 3 (logged). PAR 5 is considered only if memory stays > 4 GB available at PAR 4.

## Addendum 11:12 — PAR 5
Measured (heartbeat x run start/finish times, all lab history): minutes frozen fraction = 0.76 at 1 concurrent run,
0.74 at 2, 0.78 at 3 -> VM freezes are host-side and independent of our concurrency. At PAR 4 + 4 judges available
memory stayed 6.6-8.7 GB. Runner raised to PAR 5. Known confound: CPU contention inside non-frozen time may slow
higher-concurrency runs; most solo runs ran at PAR <= 3. Mitigation: the final analysis reports, as a sensitivity
check, each run's mean concurrency (from result.json start/finish) and the active-time ratios restricted to runs at
<= 3 concurrent. Same guard (avail < 2 GB or sustained load > 16 while not frozen -> lower PAR).
