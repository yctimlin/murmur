Updated: 2026-10-22 22:52 (Asia/Taipei)
Phase: 4-pre. E4 closed (D1 PASS, D2 FAIL, D3 KEEP K1; cand K1 cd0d635 recorded in prereg/FINAL-CANDIDATE.md).
HELD-OUT FINAL ON HOLD per user directive 22:50: the freeze-clock problem gets fixed first, then a pre-registered
head-to-head of current murmur (base4) vs K1 (solo as reference) under the fixed clock. Only the winner goes to held-out.
E4 per arm (mean quality, collapses, median active_nf min): base4 7.24 0/4 29.0; K0 6.19 2/8 41.1; K1 6.62 1/8 32.3; solo 4.08 2/4 36.2.
Running: heartbeat; clock probe tools/clocklog.py (pid in analysis/clock/clocklog.pid) measures whether
monotonic/boottime/steal skip VM freezes. No lab runs in flight (dev runner stopped 22:35). final_eval.py never started.
Next: (1) stall-excluded cap clock (gap detection) as one identical patch on base4 and K1 + freeze-aware runner
timeouts for solo/murmur, with a test that a simulated stall uses no budget; (2) AMENDMENT-10 + E5 prereg, commit+push;
(3) run E5 adaptively; (4) report; held-out only with the winner.
Blockers: none.
