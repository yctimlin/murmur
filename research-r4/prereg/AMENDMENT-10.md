# AMENDMENT-10 — freeze-excluded cap clock for every arm; FINAL held until E5 decides

Written 2026-10-23 00:45 Asia/Taipei, before any run under the fixed clock and before any held-out task is used.
Trigger: user directive 2026-10-22 22:50 (SUPERVISOR-DIRECTIVES.md). Disclosure: written with full knowledge of the E1,
E2 and E4 judgments (analysis/E4-RESULT.md). Judging stays blind.

## Problem (measured)
murmur enforces its cap with `proc.wait(timeout=cap)` (time.monotonic); K0/K1 also publish that clock in
budget-clock.txt. tools/clocklog.py (analysis/clock/clocklog.txt, 5 s samples of REALTIME, MONOTONIC, MONOTONIC_RAW,
BOOTTIME and /proc/stat steal) shows two kinds of host-side freezes on this VM, about alternating:
- type A: REALTIME and MONOTONIC (also RAW and BOOTTIME) jump together by the whole freeze (332, 678, 645, 651 s);
- type B: REALTIME jumps (708, 247, 891, 1088 s) but MONOTONIC advances only 8-13 s.
Steal time stays ~0 in both. So no kernel clock excludes type-A freezes, and BOOTTIME == MONOTONIC (no suspend).
In 77 wall minutes (22:51-00:08) the VM was frozen ~69 minutes. The cap therefore spent budget on type-A freezes
(E4: murmur clock 116-124/120 at ~35-55 freeze-excluded minutes). The lab runner's subprocess timeouts (setup 30 min,
murmur cap+10 min, exec cap) are monotonic too.

## Fix (identical clock in every arm)
- murmur: `_ActiveClock` — a 1 s ticker on MONOTONIC; any tick that arrives > 10 s late counts as a stall and is
  left out; the cap wait loops until active time reaches the cap; run.json gains active_seconds/stalled_seconds.
  Type-B freezes are already absent from MONOTONIC; type-A freezes show up as late ticks. Applied as one patch,
  without other changes:
  - base4F = experiment/r4-base4f a331d54c01bcc15193e3a66930f60dd82de9eab9 (= base4 146d476 + clock)
  - K1F = experiment/r4-k1f a50d5474fb2099eb8b5b9554c9d7a790fa42c5d4 (= K1 cd0d635 + clock; budget-clock.txt now
    reports the same active clock)
  Tests (both branches): fake-clock unit test (a 600 s gap counts as 599 s of stall); a cap wait with a 1-hour jump
  in the middle caps only after 60 active s; end-to-end: the launcher is SIGSTOPped 15 s in a 4 s cap and is not capped
  early (stalled_seconds >= 10). base4F 44 passed, K1F 47 passed.
- lab runner (tools/runner.py sha256 0051240b4fa3468828a0f85019cdb5d85d430438982ee8104cfe79ae690b6c83; previous version
  kept in analysis/clock/runner.pre-A10.py): `run_active` applies the same rule to the setup timeout (1800 s), the
  murmur run timeout (cap + 10 min) and the solo `codex exec` timeout (cap), with a 16-h wall ceiling; result.json
  gains clock.active_min / clock.stalled_min. Tested by SIGSTOPping a waiter 20 s (stall 0.33 min excluded).
- Lab budget raised from 80 to 130 accepted jobs (tooling; 74 used).

Not changed: freeze-excluded active time (active_nf from heartbeat gaps, r4eval.py) stays the speed metric; rubric,
judge, anonymizer, infra rules (AMENDMENT-6, -9), PAR limit (AMENDMENT-7).

## Consequences
1. The held-out FINAL (prereg/FINAL.md, FINAL-CANDIDATE.md) is ON HOLD. E5 (prereg/E5.md) decides between current
   murmur (base4F) and the candidate (K1F) under the fixed clock. Only the E5 winner goes to the held-out eval.
2. Every arm of any later run (dev or held-out) uses the fixed clock: murmur arms with the identical clock patch
   (orig eec78f8 would get the same patch, origF, if FINAL keeps it), solo through the runner. The FINAL arm list and
   rule are re-stated in a further amendment after E5 and before any held-out run.
3. E1/E2/E4 results stay as reported, labelled "confounded by type-A freezes eating the cap".
