Updated: 2026-10-22 02:17 (Asia/Taipei)
Phase: 3 — E4 RUNNING (prereg/E4.md committed+pushed 9828cd6 before any E4 run). Session 11 resumed 02:08.
E1/E2 CLOSED (AMENDMENT-5 deterministic fallback, reported only, confounded by F-1 wallclock rush):
- C1 vs base4: quality -0.20, active 0.87x base4, 0.76x solo -> REJECT. C2 vs base4: +0.16, 0.88x, 0.77x -> REJECT.
- Mean quality base4/C1/C2/solo: T4b 3.53/7.38/6.88/7.55, T3b 7.72/7.42/7.47/7.90, T1b 7.37/5.80/5.20/6.95,
  T2 7.85/5.08/7.54/7.90. 36 valid runs; E1-T2-C1-r3 = infra (provider-killed, AMENDMENT-6), not rerun.
E4 (K0 = base4 + truthful budget clock + clean peer roles; K1 = K0 + verifier-closed requirements ledger):
0/24 finished; in flight: T1b-K1-r1, T2-K0-r1 (budget minute 30/120), T1b-base4-r1, T4b-base4-r1, T4b-solo-r1.
Running: runner PAR 5 (pid 2754406), E4 judge loop (par 4), heartbeat. E1 judge loop and adapt loop stopped.
Next: poll E4; signatures S1-S3 per finished run; safety stop if >=3/4 block-1 K1 runs collapse; D1-D3; then FINAL.
Blockers: none (VM freezes ~75% of wall time, so E4 will take many wall hours).
