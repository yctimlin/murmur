# Contrast: T4b C1 (7.28 / 7.40 / 7.45) vs C2 (7.20 / 6.80 / 6.65)  — written by the PI from runs/*.md
(The analyst for this group failed twice on API errors after writing the five run files; this contrast is mine.)

## Why C2 scored lower on T4b (~0.5 points)
1. **The spine delays the start of building and then compresses it.** C2's spine has to exist before parallel
   build-out starts. In C2-r3 nobody claimed it: a2 and a1 took "acceptance while spine builds" (A4.2-5.1, TL:77, 95).
   At A11.7 a1 noticed "no prior SPINE claim on board" (TL:211). The build window opened at A15.1, so each owner had
   about 11 minutes to write a whole layer once (A15-26). In C2-r2 the spine was done at A4.8, but the wall-clock rush
   at A14.0 ("~30min to 120m hard cap. Need wrap documentation", TL:350) ended building after about 8 active minutes
   per agent. C1 runs started building on a winning draft by A5-8 and built for 15-25 minutes.
2. **Acceptance checks were written from the team's reading of the data, not from the brief, so they certify what
   was built.**
   - In C2-r2, a2's "independent" oracle uses the same row identity as the importer. Its expected totals were pasted
     from the oracle's own output (A4.0, TL:158-160). That locked in the Kiwi `ref ####` double count, which j1 marked
     severe.
   - In C2-r1 and C2-r3, recurring detection was "verified" by synthetic unit tests (`COFFEE`) and 250k timing. Nobody
     ran it on the real book, and both judges found it useless or noisy on real data.
   - C1-r4 got this right only because a1 did an exhaustive data inventory at A2.9 (TL:104) and found the Kiwi trap.
3. **The ledger was batch-stamped.** C2-r3 a1 marked R02, R03, R12-R18, R21 and R33 DONE in one edit (A36.6, TL:838).
   C2-r1 posted "R02-33,35-37,39 DONE with test evidence" (A26.7). The judges' depth complaints (learning = vote
   count, a single CSS chart, recurring noise) are all on rows marked DONE with no brief-level check.

## What remains in the non-collapsed T4b swarm runs (C1 and C2 alike)
- Dense semicolon code (code 5-6 in every run, solo included). No review ever looked at readability.
- Features verified only on fixtures (recurring, FX, refunds), never on the real book.
- Strict CSV parsing that quarantines whole re-quoted files with trailing whitespace (C1-r2, C1-r4, C2-r2). Every
  test checked one variant at a time, never the combination the brief describes.
- Draft leftovers shipped (C1-r2, C1-r4), an artifact of merging the winning draft.
- Wall-clock rush in all five runs (onsets A3.6-A33.4), so no cleanup or hardening pass.
- Solo (7.55) read every row before designing (A0.2-1.8) and avoided the data traps.

## Mechanism implications
- Budget truth first: in 5/5 runs the build phase ended because of a false deadline.
- Verification must be grounded outside the builder's assumptions. A non-author should exercise each requirement on
  the real input and compare with what the brief says (e.g. "do the household's Netflix charges show as recurring?").
  Re-running the builder's tests does not do this.
- A spine that nobody claims stalls the start. If a spine is kept, its creation must not depend on a voluntary claim.
