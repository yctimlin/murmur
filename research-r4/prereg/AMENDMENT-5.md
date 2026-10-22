# AMENDMENT-5 — token cost removed from the keep/drop rules (user directive 2026-10-20 22:56)

Written 2026-10-20 ~23:00 Asia/Taipei. The adaptive loop was paused (STOPADAPT) before any decision analysis under the
new rule. Disclosure: the decision here is NOT blind to the interim data. Interim looks up to 22:51 (all logged) were
seen, and the user's directive was itself a response to them: C1 looked better on quality and was blocked only by the
1.5x token cap. The directive comes from the user, not from the PI. All E1/E2 judgments are still blind, and the sealed
held-out FINAL is untouched.

## Change 1 — keep rules (posterior versions, used by tools/adapt5.py)
Tokens leave every keep/drop rule. Input tokens (and uncached) stay a reported secondary metric.
Speed is now active_nf (freeze-excluded active minutes), compared against the comparator and against solo:
- P_keep(C1) = P(E_C1 - E_base4 >= +0.5 AND active C1/base4 <= 1.10 AND active C1/solo <= 1.0)
  (E1 rules a and c as pre-registered; the token rule b is replaced by "not slower than base4"; collapse is part of
  E through the two-part model, as before)
- P_keep(C2) = P([(E_C2 - E_ref >= -0.3 AND active C2/ref <= 0.85) OR (E_C2 - E_ref >= +0.5 AND active C2/ref <= 1.10)]
  AND active C2/solo <= 1.0)
  (The E2 rule had a non-inferior-and-cheaper branch. It becomes non-inferior-and-faster, with the same 0.85
  threshold. The better-quality branch loses its token term. ref is as before: C1 unless C1 is REJECTED.)
- The deterministic fallback at the cap uses the same criteria, as plain means: mean paired quality diff, mean
  per-task active ratios vs ref and vs solo.
- Thresholds 0.90 (KEEP) / 0.10 (REJECT), the >= 3 judged runs on >= 2 paired tasks requirement, the cap of 3 runs
  per arm per task and the whole allocation rule of AMENDMENT-2 are unchanged.

## Change 2 — time model fitted on non-collapsed runs only, with solo as an arm
log(active_nf) ~ N(psi_task + alpha_arm, 0.35^2) with arms base4 (=0), C1, C2 and solo. It is fitted on delivered
runs that are not judged collapsed (unjudged runs count provisionally). Reason, logged at 16:31 before this
directive: collapsed base4 runs are fast and cheap only because they skip most of the work (T4b base4: 16.8/26.9 min
and 5.3/7.3M at quality 1.6/1.7). Counting them would reward collapse in a speed comparison. Collapse is already
penalized in the quality term. The token model (secondary, reported only) uses the same subset.

## Change 3 — C3 (E3) deprioritized
C3 was a token-economy candidate: its E3 KEEP rule needs input ratio <= 0.75, and its mechanisms (change digests,
narrow reading, partitioned final review) target cost, not quality or speed. Per the directive, C3 is not run after
E1/E2 screening. E3 stays on file as registered-but-not-run. A different candidate aimed at quality or speed may get
its own pre-registration later. If none does, the FINAL candidate is chosen as in prereg/FINAL.md (last KEPT link
C2 > C1, else C1 as a confirmation test).

## Change 4 — FINAL gate G4
In prereg/FINAL.md, G4 (input <= 2.0x solo) becomes a reported secondary metric. It no longer gates the verdict.
G1-G3 are unchanged. tools/final_decide.py still computes G4 and reports it, but it is excluded from the verdict.
That code edit will be committed with its own sha256 before any held-out run.

Implementation: tools/adapt5.py (= tools/adapt.py with only pkeep() and the cost-model subset/arms changed);
tools/adapt_loop.sh now calls adapt5.py. sha256 values are in LOG.md.
