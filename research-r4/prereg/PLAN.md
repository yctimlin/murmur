# Round 4 research plan (PI) — 2026-10-19 23:20 Asia/Taipei

## Model of the problem (from analysis/DIAGNOSIS.md)
1. Quality gap = collapse, not mediocre teamwork. r3 swarm runs are bimodal: 10/16 high-mode runs (q≈7.5, at or above
   solo 6.64) and 6/16 collapsed runs (q 0-2.5). In a collapse each peer finishes a narrow piece, ends its turn, and the
   run ends when the last peer ends — with the system half-integrated (parts on draft/* or side branches).
2. Verified mechanism (Codex 0.162.1): ending a turn is irreversible for a peer (board posts / send_message are
   trigger_turn=false and never wake an idle thread; only followup_task does), and the root ends when all peers are
   idle. So termination = AND of unilateral per-peer "I'm done" decisions, each made from a local view.
   `wait_agent` (v2) DOES wake on any mailbox activity incl. board notifications => a peer can park instead of exiting.
3. The draft tournament ("build a draft of a direction in ~N min, rank, winner becomes base") seeds collapse: in
   low-mode runs drafts are narrow modules (e.g. the parser), the "winner" becomes main and other parts are
   orphaned on side branches. In high-mode runs drafts are tiny and real work happens on main.
4. Tokens: each peer costs about one solo run (50-100 calls x 100-170K context); 46% of peer tool calls are
   coordination. 3 peers => 3-4x solo. Reaching 1.5-2x needs a different allocation of parallel compute, not
   fewer words.

## Hypotheses (dev-tested on T1b/T2/T3b/T4b, then confirmed on sealed held-out H1-H4)
- H1 (collapse): replacing unilateral exit by a consensus-termination protocol (requirements ledger + park-not-exit +
  END quorum on a verified commit) removes the collapse mode and raises mean quality to ≈ solo, at active time
  still < solo.
- H2 (tokens/speed): replacing the draft tournament + 3 symmetric long-lived peers with "serial spine, parallel
  burst, parallel verification" (one peer builds the walking skeleton while the others write acceptance checks from
  the brief; then parts fan out; finishing = independent clean-room verification of the whole by peers that did not
  build that part) cuts tokens toward 2x solo without losing H1's quality.
- H3 (verification, Noam Brown): parallel compute spent on independent verification (clean-room acceptance runs
  against the brief) adds more quality per token than parallel typing.
Each mechanism is a protocol change (prompts + murmur plumbing), not a parameter/default tweak. CLI stays setup/run;
root only spawns and waits; no hardcoded Codex settings; no 429 handling.

## Experiments (one change at a time)
- E1 (H1): arms base4 (146d476) vs C1 (base4 + consensus termination). Dev tasks T1b,T2,T3b,T4b x 2 reps per arm,
  plus 1 fresh solo per task (r3 solo runs as additional reference). 20 runs. Prereg: prereg/E1.md before launch.
- E2 (H2/H3): C2 = C1 + spine/burst/verify allocation vs C1. Same design. Only if C1 is kept or informative.
- (A/A noise: r3 already measured A/A CV .16-.35 for time/tokens; E1 has 2 reps/arm/task, which gives within-arm
  variance; a dedicated A/A batch is not run unless E1 variance is uninterpretable.)
- FINAL: best candidate vs base4 vs orig (eec78f8) vs solo on sealed H1-H4 x 2 reps = 32 runs, blind judging,
  pre-registered decision rule (prereg/FINAL.md + decide.py frozen before tasks are copied in).

## Metrics
Quality: blind Claude judge, r3 open rubric (0-10), 2 judgments/run. Collapse: quality < 3.0 or not delivered.
Time: freeze-excluded active minutes (active_nf), plus raw active and wall. Tokens: total input (and uncached).
Delivery: commits on origin/main > 0 and brief's protected input intact.

## Budget and pacing
- Concurrency <= 3 runs total on the box (held-out author uses up to 2 for calibration; dev uses the rest).
- Runs: E1 20, E2 ~16-20, FINAL 32 (+ reruns for infra failures). Cap 120 min per run.
- Tokens: ~20M per swarm run, ~5M per solo => E1 ≈ 0.35B, E2 ≈ 0.35B, FINAL ≈ 0.5B input tokens.
- Judging: ~2 Claude judgments per run (~70-80 runs => ~160 judge sessions). Claude daily limit was hit once
  (10-19 22:42); judging is spread out and resumable.
- Time: E1 ~12 h, E2 ~12 h, FINAL ~16 h (+ judging). No fixed deadline.
