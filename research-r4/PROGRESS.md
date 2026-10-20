Updated: 2026-10-20 10:41 (Asia/Taipei)
Phase: 2 — E1 (C1 consensus termination) + E2 (C2 spine + acceptance checks) on the ADAPTIVE schedule (AMENDMENT-2);
E3 (C3 token economy) pre-registered, starts when E1/E2 screening ends.
Latest judged quality: T3b C1 7.0 / base4 7.8 / C2 7.55; T1b C1 7.7 / base4 7.6 (C2 pending). No collapse so far.
Interim P_keep: C1 0.32, C2 0.04 (C2 tokens x1.13 vs C1).
Token diagnosis (D5): swarm input 13.3-19.0M vs solo 4.38M; 29-44% of it is peers reading each other's work
(git fetch/show/diff) in ~85K-token contexts; C1/C2 coordination adds ~10 pp. -> C3 (experiment/r4-c3 fbda22e):
change digests + narrow reading + partitioned final review; prereg/E3.md (KEEP needs <=0.75x ref input, quality >= -0.3).
Running: runner PAR 1 (E1-T4b-base4-r1; next E1-T3b-solo-r1), adapt loop, judge loop, heartbeat,
held-out author (wrapper restarting session 4; 6 authored, 4 calibrations done).
Next: poll; PAR 3 once the author finishes; extend adapt.py for E3 when E1/E2 stop.
Blockers: box freezes (~2 h wall per ~30 active min run); Claude daily limit (lifted now).
