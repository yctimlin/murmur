Updated: 2026-10-20 10:38 (Asia/Taipei)
Phase: 2 — E1 (C1 consensus termination vs base4) + E2 (C2 spine + acceptance checks), now on an ADAPTIVE schedule
(prereg/AMENDMENT-2.md, committed+pushed b71f72d before use, per the 10:27 supervisor directive).
Adaptive rule: Bayesian two-part model (collapse rate + quality with task effects; log tokens/time) -> P_keep for the
pre-registered E1/E2 KEEP rules; stop KEEP >=0.90 / REJECT <=0.10 after >=3 judged runs on >=2 paired tasks; cap
3 runs/arm/task; uncertainty-sampling allocation with comparator pairing; r3 collapse-heavy tasks (T4b, then T3b) first;
1 solo per task after every 4 swarm runs. The 21 fixed-schedule jobs were withdrawn.
Latest (judged quality): T3b C1 7.0 / base4 7.8 / C2 7.55; T1b C1 7.7 / base4 7.6 (C2 pending). No collapse in 5 judged
runs. Interim P_keep: C1 0.32 (quality diff -0.10, tokens x1.08 vs base4); C2 not yet judged enough (tokens x1.13 vs C1;
its KEEP needs <=0.85 or a +0.5 quality gain). Swarm input still ~13-18M vs r3 solo 4.4M (3-4x).
Running: held-out author (6 authored, 4 calibrations done; wrapper restarting session 4); runner PAR 1 (E1-T4b-base4-r1; next E1-T3b-solo-r1,
then likely T4b C1/C2 and T2); heartbeat; judge loop; adapt loop (pid 1846605).
Next: let the adaptive loop run; PAR 3 once the author finishes; plan C3 targeting token cost.
Blockers: box freezes (~90 min per run, runs take ~2 h wall for ~25-35 active min); Claude daily limit (lifted for now).
