Updated: 2026-10-20 02:41 (Asia/Taipei)
Phase: 2 — E1 (C1 consensus termination vs base4, dev tasks) running, 1/20 runs done.
Latest: E1-T3b-C1-r1 delivered; END quorum worked (all 3 peers approved the same commit at 26.5 active min); runner
active 34.4 min, 18.3M input. First judging used a faulty anonymizer (deleted committed sqlite fixtures) ->
AMENDMENT-1, re-judging. Box freezes heavy (~94 min during that 2-h run; heartbeat-based freeze exclusion in place);
peers read wall time and rushed toward the cap (confound noted in DIAGNOSIS D4).
Running: held-out author (calibrations, 1 done, 1 enlargement pending); E1 runner PAR 1 (E1-T3b-base4-r1); E1 judge loop.
Next: finish E1 (PAR 3 once calibration ends), aggregate + pre-registered decision; design C2 (token mechanism).
Blockers: throughput (freezes + 1 dev slot while author calibrates).
