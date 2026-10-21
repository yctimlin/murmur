Updated: 2026-10-21 12:57 (Asia/Taipei)
Phase: 2 — E1 (C1 consensus termination) + E2 (C2 spine + acceptance checks), adaptive (AMENDMENT-2), keep rules AMENDMENT-5 (quality + active-time speed; tokens secondary), infra rule AMENDMENT-6, throughput AMENDMENT-7.
Session 8 resumed 10:42 (all jobs alive). User directive 10:40 (speed up) -> AMENDMENT-7: runner PAR 3->4->5, judges 2->4. Freezes are host-side (frozen fraction 0.76/0.74/0.78 at 1/2/3 concurrent runs); avail memory 3-9 GB at PAR 5.
Judge backlog cleared. New judged: T2-C1-r2 2.25, T1b-C1-r2 2.45, T1b-C2-r2 2.55 (collapses: partial delivery, valid, no provider error), T2-base4-r2 7.9, T3b-C2-r2 7.4, T3b-C1-r3 7.55, T4b-C1-r4 7.45.
Infra (A6, rerun not scored): T4b-base4-r3, T2-C2-r2 (provider 'servers overloaded').
Scores: T1b C1 7.7, 2.45 / C2 7.85, 2.55 / base4 7.6, 7.65 / solo 6.95; T2 C1 7.9, 2.25 / C2 7.9 / base4 7.8, 7.9 / solo 7.9; T3b C1 7.0, 7.55 / C2 7.55, 7.4 / base4 7.8, 7.6 / solo 7.9; T4b C1 7.28, 7.4, 7.45 / C2 7.2, 6.8 / base4 1.6, 1.7 / solo 7.55.
Interim (adapt5 12:36): C1 P_keep 0.28 (dq +0.19 vs base4, active x0.97 vs base4, x0.74 vs solo); C2 P_keep 0.41 vs C1 (dq +0.29, active x0.94). Undecided.
Finding: collapse rate rose from 2/20 (before 10-20 21:00) to 3/8 valid runs since, across all arms; model and effort unchanged. Solo runs all predate it (vs-solo confound, noted for the report).
Running: runner PAR 5 + adapt5 (1 pending), judge loop par 4, heartbeat.
Next: keep polling until C1/C2 decided or cap -> FINAL candidate -> sealed held-out FINAL eval.
Blockers: VM freezes (~75% of wall time); provider overload errors (rerun per A6).
