# FINAL candidate (prereg/FINAL.md as replaced by AMENDMENT-8)

Recorded 2026-10-22 22:35 Asia/Taipei, after all 24 E4 runs were judged and before tools/final_eval.py is started.

Rule (AMENDMENT-8): cand = K1 if E4 KEEPs K1; else K0 if E4 rule D2 holds; else C1.
E4 outcome (analysis/E4-RESULT.md, analysis/E4-decision.json): D1 PASS (hand-check against murmur's budget clock,
as S1 is defined; the regex proxy would fail it, see E4-RESULT.md), D2 FAIL (K0 - base4 -1.05), D3 KEEP K1
(+0.43 over 8 pairs, collapses 1 vs 2, active ratio 0.85), safety stop not triggered.

cand = K1 = cd0d635c09d994c8656d33fc1d164abe39e067e0 (experiment/r4-k1 = base4 + M0 truthful budget clock and clean
peer roles + M1 verifier-closed requirements ledger). No murmur change after this file is pushed.

Note before the eval: in dev, K1 was not better than base4 (mean task diff -0.62, 90% CI -2.14 to +0.90, collapses
1/8 vs 0/4). FINAL is the confirmation test of this candidate against base4, orig and solo under G1-G4.
