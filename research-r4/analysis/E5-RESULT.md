# E5 result — current murmur (base4F) vs candidate K1F under the freeze-excluded clock

Computed 2026-10-23 14:2x Asia/Taipei by analysis/e5_decide.py 1 (sha256 a8ee56aa, committed before any E5 result),
prereg/E5.md + AMENDMENT-10. Block 1: 12/12 runs valid (no infra event, no rerun), all judged (2 judgments each).

## Decision at the block-1 interim: STOP-REJECT -> keep base4F (current murmur). Blocks 2-3 not run.
Trigger: K1F is clearly slower. Mean ln(active_nf ratio K1F/base4F) = 0.737, 90% CI 0.312..1.162
(ratio 2.09x, CI 1.37x..3.20x); the rule stops when the lower bound is > 0.
Quality did not trigger: mean d_q = +0.295, 90% CI -0.059..+0.649. Collapses were 0 vs 0.

| pair | K1F q | base4F q | K1F active_nf | base4F active_nf |
|---|---|---|---|---|
| T1b | 7.97 | 7.51 | 34.6 | 23.8 |
| T2  | 8.05 | 8.20 | 49.3 | 30.6 |
| T3b | 7.80 | 7.43 | 66.9 | 24.2 |
| T4b | 7.70 | 7.20 | 70.2 | 23.9 |

Per arm (mean q [90% CI], collapses, median active_nf, median input tokens):
- base4F 7.58 [7.08, 8.09], 0/4, 24.0 min, 10.9M
- K1F    7.88 [7.69, 8.07], 0/4, 58.1 min, 37.4M
- solo   7.90 [7.59, 8.21], 0/4, 35.4 min, 3.2M (reference)

## Observations (descriptive, not gating)
- No run hit the cap. Every swarm ended on its own, and murmur's run.json reports stalled minutes excluded:
  base4F about 25-32 active minutes; K1F 35-72; solo 32-50 (runner clock).
  So the type-A freeze minutes now excluded by the clock were 6-26 per run.
- With the clock fixed, no arm collapsed (0/12). In E4, 5/24 runs collapsed under the freeze-eaten cap (K0 2/8,
  K1 1/8, solo 2/4). This is consistent with the cap truncation being a main source of E4's bimodal quality, but the
  runs were not controlled across days (relay/model drift possible).
- K1F buys about +0.3 quality (not significant) for about 2.1x active time and 3.4x tokens versus base4F.
  Under the user's rule (non-inferior AND not slower), it is rejected.
- base4F vs solo (reference only, n=4): quality -0.32 (7.58 vs 7.90), active time about 0.68x (faster),
  input tokens about 3.4x.
