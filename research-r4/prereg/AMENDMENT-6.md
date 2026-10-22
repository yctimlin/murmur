# AMENDMENT-6 — mechanical detection of provider-killed sessions as infra failures (tooling, F5)

Written 2026-10-21 ~06:50 Asia/Taipei.

## Trigger (disclosed)
E1-T3b-C1-r2 ran 67.2 active min (raw 87.2, wall 536), hit the 120-min cap (exit 124), added 225 lines to main
(siblings ~3,700) and posted no END. Its rollouts show that peer a1 was ended at 23:08 by codex itself:
task_complete with error "stream disconnected before completion: Our servers are currently overloaded. Please try
again later." after 5/5 reconnects failed. The root also logged 29 "overloaded" reconnects. This is a relay/API
outage in the sense of FAIRNESS.md F5. The current r4eval.is_infra only reads result.json, so it cannot see this.

The PI saw this run's unjudged time and tokens before writing this. Withdrawing it raises C1's P_keep, which creates
a bias risk. The rule below is therefore purely mechanical and arm-blind, it applies to every past and future run
(dev and FINAL, swarm and solo), and the PI checked that it changes the classification of no other E1 run. In
particular, the two base4 T4b collapses contain no provider-killed session, so they stay valid.

## Rule
A run is an infra failure (F5: withdrawn, rerun, never scored) if any codex session in the run (root, peer or solo;
<ws>/codex-home/sessions/**/rollout*.jsonl) has a task_complete event whose error message begins with
"stream disconnected", i.e. codex gave up after exhausting its reconnects on a provider error. Reconnects that
succeed are not infra. Implemented in tools/r4eval.py provider_killed(), called by is_infra(). The adapt loop,
the judge and final_eval.py all use is_infra.

## Effect at writing time
E1 runs flagged: E1-T3b-C1-r2 (new) and E1-T4b-C1-r1 (already infra: setup 503). The adaptive allocator re-queues
the cell as usual (started counts exclude infra).
