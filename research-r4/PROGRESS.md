Updated: 2026-10-22 21:56 (Asia/Taipei)
Phase: 3. E4 is running (prereg/E4.md, committed 9828cd6). Session 17 resumed at 18:06; all jobs alive, nothing relaunched.
E1/E2 CLOSED (AMENDMENT-5 fallback, confounded by F-1): C1 REJECT (-0.20 vs base4), C2 REJECT (+0.16, active 0.88x).
E4 (K0 = base4 + truthful budget clock + clean peer roles; K1 = K0 + verifier-closed requirements ledger):
23/24 valid runs finished, 23 judged; last run E4-T4b-K0-r1 (2nd infra rerun) at budget 114/120.
Judged: base4 T1b 7.4 / T2 7.9 / T3b 7.2 / T4b 6.45; K0 T1b 7.85, 7.65 / T2 2.0, 7.85 / T3b 7.85, 1.3 / T4b 7.39;
K1 T1b 7.6, 7.0 / T2 2.85, 7.85 / T3b 7.2, 7.35 / T4b 6.6, 6.5; solo T1b 3.5 / T2 8.59 / T3b 1.9 / T4b 2.35.
Quality is bimodal (about 7-8.6 or about 1.3-3.5 with many severe defects); collapse rates reported next to means.
Safety stop: not triggered (1 of 4 block-1 K1 collapses).
Infra (never scored, rerun under the same name): 7 E4 runs, all K0/K1 (relay overload). Newest: E4-T1b-K0-r2 (15:08).
Running: runner PAR 5 (pid 2754406; in flight T4b-K0-r1 (2nd rerun)),
E4 judge loop (pid 3181402), heartbeat. Poll: python3 tools/poll_e4.py.
Next: after all 24: signatures, D1-D3 (analysis/e4_decide.py), then FINAL-CANDIDATE + held-out eval.
Blockers: none.
