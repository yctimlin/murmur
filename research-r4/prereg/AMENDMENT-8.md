# AMENDMENT-8 — E1/E2 screening closed; candidate chain replaced by forensically derived K0/K1 (E4)

Written 2026-10-21 22:50 Asia/Taipei, before any K0/K1 lab run and before the sealed held-out tasks are used.
Disclosure: NOT blind to interim data. All E1/E2 judgments (37 runs) were seen, and the forensic study
(analysis/FORENSICS.md, user directive 10-21 14:02) read every judged run's logs. Judgments themselves stayed blind.

## Why
FORENSICS F-1 (WALLCLOCK RUSH, 19/27 swarm runs, 0/4 solo): peers estimated murmur's 120-min cap from the wall clock,
which keeps running through host-side VM freezes (~75% of wall time) while murmur's cap runs on time.monotonic. Teams
broadcast false countdowns and END at 20-35 active min. The run window of every swarm arm (base4, C1, C2) was thus set
by random freeze timing; solo was not affected. The E1/E2 arm contrasts and every swarm-vs-solo comparison measured so
far are confounded by this environment artefact. F-2 (ROLE INHERITANCE): forked peers inherited the launcher prompt
(both base4 T4b collapses start with a peer quitting because of it). F-3 (self-referential verification) is present in
all 5 collapses and in C1 and C2 alike.

## Changes
1. E1/E2: adapt5 has stopped both candidates at the cap (C2 15:07, C1 16:36). The last E1 run in flight
   (E1-T2-C1-r3) is completed and judged. The AMENDMENT-5 deterministic fallback is computed and REPORTED, with the F-1
   confound stated, but it no longer selects the FINAL candidate. C1 and C2 are not carried forward. C3/E3 stay
   registered-but-not-run.
2. New experiment E4 (prereg/E4.md) with K0 = base4 + M0 (truthful budget clock, clean peer roles; bug fixes) and
   K1 = K0 + M1 (grounded requirements ledger closed only by rotating non-builder verifiers).
3. FINAL (prereg/FINAL.md) candidate rule replaced by: cand = K1 if E4 KEEPs K1; else K0 if E4 rule D2 holds;
   else the old rule's default (C1) as a confirmation test. Everything else in FINAL.md (arms base4/orig/solo, tasks,
   blocks, judge, G1-G3 verdict, G4 secondary per AMENDMENT-5) is unchanged. Note for the report: base4 and orig in
   FINAL still contain the F-1/F-2 bugs; that is what they are, and the gap to them is part of what FINAL measures.
