Updated: 2026-10-23 18:41 (Asia/Taipei)
Phase: 5 — held-out FINAL running (E5 winner only, per user directive).
E5 (fixed clock): K1F STOP-REJECTed at the block-1 interim. Current murmur (base4F) stays.
  K1F was 2.09x slower (90% CI 1.37-3.20x) and used 3.4x the tokens, for +0.30 quality (90% CI -0.06..+0.65).
  Per arm mean quality / median active min: base4F 7.58 / 24.0; K1F 7.88 / 58.1; solo 7.90 / 35.4.
  0/12 collapses.
FINAL (AMENDMENT-11, pushed 664c435 before any held-out copy): base4F (a331d54) vs origF (c583a63, orig + same clock)
vs solo, all under the freeze-excluded clock. H1-H4 x 2 reps = 24 runs, PAR 4, blind judging.
G1 = no regression vs origF; G2 = quality on par with solo; G3 = faster than solo; G4 = tokens (secondary).
Started 14:36. A tooling fault (repo symlink) failed 8 murmur jobs instantly; nothing ran. Fixed and re-queued 14:4x.
Running: eval runner pid 77075 (4 solo runs in flight), watcher 77077, judge loop F, heartbeat, clock probe.
Next: wait for all 24 runs to be judged (likely 1-2 days at ~80-90% VM freeze), then final_decide.py and FINAL-REPORT.md.
Blockers: none. 18:42 blinding deviation fixed: the judge loop had logged one labelled held-out score (solo); scores for F are no longer logged (see LOG).
