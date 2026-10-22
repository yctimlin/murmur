# E4 result (prereg/E4.md, AMENDMENT-8/9) — written 2026-10-22 22:30 Asia/Taipei

24/24 valid runs, all judged (2 judgments each, 3rd if gap > 1.5). Infra events (never scored, rerun under the same
name, AMENDMENT-6/9): 8, all K0/K1 (E4-T1b-K1-r1, E4-T4b-K1-r2 setup relay, E4-T2-K0-r2, E4-T1b-K0-r1, E4-T4b-K0-r1 x2,
E4-T1b-K0-r2). Decision output: analysis/E4-decision.json (analysis/e4_decide.py), signatures analysis/E4-signatures.json,
hand-check analysis/s1_handcheck.py.

## Per run (quality, freeze-excluded active min, input tokens M)
| task | base4 | K0 r1 / r2 | K1 r1 / r2 | solo |
|---|---|---|---|---|
| T1b | 7.40 / 31.0 / 7.3 | 7.85 / 35.1 / 20.7 ; 7.65 / 35.1 / 13.6 | 7.60 / 38.3 / 14.0 ; 7.00 / 32.2 / 20.6 | 3.50 / 36.3 / 3.4 |
| T2 | 7.90 / 28.8 / 19.6 | 2.00 / 53.7 / 9.6 ; 7.85 / 29.0 / 10.6 | 2.85 / 45.0 / 16.5 ; 7.85 / 24.9 / 13.2 | 8.59 / 36.1 / 2.3 |
| T3b | 7.20 / 23.4 / 12.5 | 7.85 / 42.0 / 28.0 ; 1.30 / 40.3 / 12.7 | 7.20 / 30.7 / 14.5 ; 7.35 / 42.8 / 33.3 | 1.90 / 30.5 / 2.4 |
| T4b | 6.45 / 29.1 / 7.3 | 7.60 / 48.1 / 26.1 ; 7.39 / 43.8 / 32.3 | 6.60 / 32.3 / 9.3 ; 6.50 / 31.9 / 15.5 | 2.35 / 55.9 / 6.7 |

Per arm: base4 mean 7.24, 0/4 collapses, median active 29.0, median input 9.9M; K0 6.19, 2/8, 41.1, 17.1M;
K1 6.62, 1/8, 32.3, 15.0M; solo 4.08, 2/4 (T3b 1.9, T4b 2.35), 36.2, 2.9M.

## Decision rules
- D1 (M0 executes): PASS. Regex (signatures.py) flags 6/16 K runs, but it measures "budget minute" with a proxy
  (wall minus heartbeat freeze windows), whereas prereg S1 names the budget clock, i.e. murmur's enforced clock that
  M0 publishes. Every flagged K post is a truthful clock report quoting murmur's clock at >= 84/120, and every team
  kept working until murmur's clock read 116-124/120 (no voluntary early END). S1 episodes 0/16, S2 early quits 0/16.
  Sensitivity: if the proxy were taken literally, D1 would FAIL (6 > 2) and no K arm could be a FINAL candidate.
  base4: F-1 false "hard cap" posts and team END at proxy minute 23-31 in 3/4 runs, as in E1.
- D2 (K0 non-regression vs base4): FAIL. Mean task diff -1.05 (90% t-interval -3.46 to +1.35), collapse rate 0.25 vs 0.
- D3 (KEEP K1 over K0): KEEP. Mean over 8 pairs +0.43 (90% CI -1.14 to +2.01; point-estimate rule), collapses 1 <= 2,
  geometric active ratio K1/K0 0.85 <= 1.25.
- Safety stop: not triggered (1/4 block-1 K1 collapses).
=> AMENDMENT-8 candidate rule: cand = K1 (cd0d635c09d994c8656d33fc1d164abe39e067e0).

## Descriptive (not gating)
- K1 - base4 per task: -0.10, -2.55, +0.08, +0.10 (mean -0.62, 90% CI -2.14 to +0.90); the difference is the single
  T2 K1 collapse. K1 active median 32 vs base4 29; tokens ~1.5x base4.
- K1 - solo: mean +2.53 (CI -2.06 to +7.13); E4 solos collapsed on T3b/T4b and scored 3.5 on T1b (E1 solos 0/4
  collapses: drift or solo variance; solo n = 1 per task).
- Quality is bimodal (about 6.5-8.6, or 1.3-3.5 with many severe defects); with n = 1-2 per cell the decisive events
  are collapses, and E4 cannot separate K1 from base4.
- Mechanism check M1 (S3): ledger closed fully in 5/8 K1 runs; T3b-K1-r1 left 19/129 open, T4b-K1-r1 75/171, T4b-K1-r2 2/171.

## Limitations
- Freeze-clock confound: murmur's cap clock (cli.py _BudgetClock, time.monotonic) advances during the host's VM
  freezes ("clock ... (jumped)", "tool suspension advanced 22min"), so swarm runs got ~25-55 freeze-excluded active
  minutes of a 120-min cap, varying with freezes. Same mechanism in base4/orig; solo's runner timeout is wall-clock
  too but solo rarely reaches it. Biases speed/quality against swarm arms and adds noise.
- All 8 infra reruns were K runs (longer runs, more relay exposure); reruns were outcome-blind, residual selection risk.
- Base4 n = 1 per task; D2/D3 intervals are wide.
