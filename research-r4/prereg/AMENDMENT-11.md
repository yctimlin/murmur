# AMENDMENT-11 — held-out FINAL with the E5 winner, all arms under the freeze-excluded clock

Written 2026-10-23 14:35 Asia/Taipei, after E5 (analysis/E5-RESULT.md) and before any held-out task is copied or run.
Trigger: user directive 2026-10-22 22:50: "Only proceed to held-out eval with whichever arm wins". Disclosure: written
with knowledge of all dev results (E1, E2, E4, E5). The sealed tasks have not been read.

## What changes in prereg/FINAL.md
1. Candidate: E5 STOP-REJECTed K1F, so the E5 winner is current murmur, base4F =
   a331d54c01bcc15193e3a66930f60dd82de9eab9 (base4 146d476 + freeze-excluded cap clock, AMENDMENT-10).
   prereg/FINAL-CANDIDATE.md is replaced accordingly; the K1 version is kept as analysis/clock/FINAL-CANDIDATE.pre-A11.md.
2. Arms: cand = base4F, origF = c583a63c4c27f9245efde6937dbc576e83fb9347 (orig eec78f8 + the identical clock patch,
   experiment/r4-origf; 35 tests pass), solo = plain codex exec with the runner's freeze-excluded timeout. The separate
   base4 arm is dropped: under the fixed clock it is the candidate itself. 4 tasks x 2 reps x 3 arms = 24 runs in the
   8 randomized blocks of FINAL.md (seed 20261020, same block order code).
3. Decision rule (tools/final_decide.py): G1 = no regression vs origF (lower 90% bound of the mean quality diff
   > -0.5 and collapses(cand) <= collapses(origF)); G2, G3, G4 unchanged (G4 secondary, AMENDMENT-5).
   Not delivered => quality 0 (as FINAL.md states; the code now applies it).
   Verdict: SUCCESS if G1-G3 hold; NO-REGRESSION-VS-ORIG if only G1 holds; otherwise REGRESSION-VS-ORIG.
   The old IMPROVEMENT verdict (cand beats base4) does not apply because cand is base4F. The round's mechanism
   candidates (C1, C2, K0, K1) were all rejected in dev. The clock fix is an infrastructure correction, not a
   collaboration mechanism.
4. Concurrency: eval runner PAR 4 (FINAL.md said <= 3). Under the freeze-excluded clock a run's budget no longer
   depends on freezes. E5 ran at PAR 4 with 0 infra events in 12 runs. Judge loop parallelism 4.
5. Tooling: final_eval.py's infra watcher also moves the run's work dir aside (ws -> ws-infra) before re-queueing,
   since a rerun under the same name cannot start while it exists. File sha256: final_eval.py 8ec73c59dba1e1cd0856b826f480d100bee1e8055d30cff3391b0c6188cc6429,
   final_decide.py de8a0ac72bd0ad7f9471f96c7a1603280dffa909ca58f7faa411d5aa41f90930, runner.py 0051240b4fa3468828a0f85019cdb5d85d430438982ee8104cfe79ae690b6c83.
Everything else in FINAL.md and FAIRNESS.md is unchanged: sealed copy-in only by final_eval.py, sha256 checks,
blind judging, infra rule, and unblinding only in final_decide.py after all scores exist.
