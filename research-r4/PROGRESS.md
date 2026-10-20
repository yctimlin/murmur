Updated: 2026-10-20 22:58 (Asia/Taipei)
Phase: 2 — E1 (C1 consensus termination) + E2 (C2 spine + acceptance checks), adaptive schedule (AMENDMENT-2), with keep rules changed by AMENDMENT-5.
Session 7 resumed 22:56; all jobs were alive, nothing relaunched.
User directive 22:56 handled: AMENDMENT-5 (commit 9719434, pushed) takes token cost out of every keep rule (tokens are now secondary). C1 KEEP = P(quality +0.5 vs base4 AND active <= 1.10x base4 AND <= 1.0x solo). C2 = non-inferior & faster (<= 0.85x) or better (+0.5) & not slower, and <= solo. The time model excludes collapsed runs (they are fast only because they skip the work). C3 (token economy) is deprioritized and will not be run. FINAL gate G4 (tokens) is now secondary.
Judged quality: T3b C1 7.0 / base4 7.8 / C2 7.55 / solo 7.9; T1b C1 7.7 / base4 7.6 / C2 7.85 / solo 6.95; T2 C1 7.9 / base4 7.8 / C2 7.9; T4b C1 7.275, 7.4 / C2 7.2 / base4 1.6, 1.7 (2/2 base4 collapses) / solo 7.55.
Interim 22:58 (A5 rule): C1 P_keep 0.52 (dq +1.84, P(dq>=0.5) 0.82, active x1.00 vs base4, x0.66 vs solo); C2 P_keep 0.24 vs C1 (dq -0.08, active x1.04). Swarms' active time is ~0.66x solo; tokens (secondary) ~4-9x solo.
Running: runner PAR 3 (E1-T3b-C1-r2, E1-T3b-base4-r2, E1-T2-solo-r1; pending E1-T1b-C1-r2); adapt5 loop pid 2347159; judge loop (par 2; E1-T4b-C2-r2 being judged); heartbeat.
Next: poll until C1/C2 are decided (KEEP >= 0.90 / REJECT <= 0.10, or the cap) -> FINAL candidate -> sealed held-out FINAL eval.
Blockers: box freezes (wall ~3x active); occasional relay 503s (rerun, never scored).
