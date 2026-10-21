Updated: 2026-10-21 23:02 (Asia/Taipei)
Phase: 3 — E4 RUNNING (prereg committed+pushed 9828cd6 before any E4 run).
Done since 17:08:
- FORENSICS.md (F-1 wallclock rush 19/27 swarm runs, F-2 role inheritance, F-3 self-referential verification).
- K0 = base4 + M0 (budget-clock file from murmur's monotonic cap clock + closing.md pointer; peers spawned with
  fork_turns "none"; peer note that the launcher never answers): experiment/r4-k0 708d5fa, 41 tests pass.
- K1 = K0 + M1 (murmur splits the brief into rows — T1b 84, T2 9, T3b 129, T4b 171 — assigns each a verifier by
  rotation; ledger.py computes status from `verify` board posts, only the assigned verifier can close; peers finish
  only with no OPEN/FAIL row): experiment/r4-k1 cd0d635, 44 tests pass.
- K0 smoke (toy repo, 12 min): peers start clean (no launcher prompt), gpt-6-astra/high, read the clock. K1 smoke running.
- Drafted prereg/AMENDMENT-8.md (E1/E2 closed, confounded by F-1; FINAL candidate -> K1/K0) and prereg/E4.md
  (base4 x1, K0 x2, K1 x2, solo x1 per task = 24 runs; D1 mechanism check, D2 K0 non-regression, D3 K1 KEEP).
E1/E2 latest: 37 judged; healthy swarm 6.65-7.9, 5 collapses (1.6-2.55); solo 6.95-7.9 at 31-47 active min;
swarm active 17-45 (truncated by F-1). Judge blinding: arm-guess accuracy 0.57 (r3: 0.82).
Running: runner PAR 5 (E1-T2-C1-r3 + first 4 E4 runs), judge loops E1 + E4 (par 4), heartbeat; adapt5 stopped.
Next: poll E4; E1/E2 fallback report once E1-T2-C1-r3 is judged; mechanism signatures S1-S3; D1-D3; then FINAL.
Blockers: none (VM freezes ~75% of wall time).
