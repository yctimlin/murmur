Updated: 2026-10-23 14:33 (Asia/Taipei)
Phase: 4-E5 decided -> preparing held-out FINAL with the winner (current murmur, base4F).
Clock fix (AMENDMENT-10): murmur's cap now counts only running time. On this VM, type-A freezes advance
MONOTONIC, so murmur detects them as late ticks and leaves them out. Same patch on all arms; solo uses the runner clock.
E5 RESULT (prereg rule, block-1 interim): STOP-REJECT K1F, so current murmur (base4F) stays.
  K1F is 2.09x slower in active time (90% CI 1.37-3.20x) and uses 3.4x the tokens. Its quality gain is +0.30
  (90% CI -0.06..+0.65), not significant. Collapses: 0 vs 0.
  Per arm mean quality / median active min / median input tokens:
    base4F 7.58 / 24.0 / 10.9M; K1F 7.88 / 58.1 / 37.4M; solo 7.90 / 35.4 / 3.2M.
  With the fixed clock, 0 of 12 runs collapsed (E4 under the broken clock: 5 of 24). No run reached the cap.
Details: analysis/E5-RESULT.md.
Next: implement origF (orig eec78f8 + the identical clock patch), then AMENDMENT-11. It restates FINAL as
base4F vs origF vs solo, all under the fixed clock. Commit and push, then start tools/final_eval.py.
Running: heartbeat, clock probe, E5 judge loop (finishing), dev runner (idle).
Blockers: none. Throughput is low: the VM is frozen ~80-90% of wall time, so a run takes 2-6 h wall.
