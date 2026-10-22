# FINAL held-out evaluation — pre-registration

Written 2026-10-20 (time in LOG.md / git commit), BEFORE the held-out tasks are copied anywhere, before the candidate
is chosen, and before any E1/E2/E3 decision. Governs the single use of the sealed tasks H1-H4
(heldout/PUBLIC.json bundle sha256: H1 b872e7b4..., H2 28e5bc5d..., H3 c03aab10..., H4 5d91dae2...).
FAIRNESS.md F1-F5 apply unchanged.

## Candidate (fixed by rule, recorded before the eval starts)
cand = the last KEPT link of the dev chain: C3 if E3 KEEPs it, else C2 if E2 KEEPs it, else C1 if E1 KEEPs it.
If no candidate is kept, cand = C1 (the collapse mechanism, the main hypothesis) and the final eval is reported as a
confirmation test of a not-kept candidate. Its commit sha is written to prereg/FINAL-CANDIDATE.md, committed and
pushed before tools/final_eval.py is started; no murmur change after that.

## Arms, design
- cand (3 peers), base4 = 146d476 (3 peers), orig = eec78f8 (3 peers), solo = plain `codex exec` (runner "exec" arm,
  round-2 solo prompt). gpt-6-astra / high for every arm (runner defaults; no per-arm Codex settings). Cap 120 min.
- Tasks H1-H4 x 2 reps x 4 arms = 32 runs, in 8 blocks (block = one rep of every arm on one task); block order and
  arm order inside blocks randomized with seed 20261020; <= 3 concurrent runs; separate lab /workspace/r4/evallab.
- Tasks enter the lab only via tools/final_eval.py (sudo copy of /srv/murmur-sealed-r4/heldout/final/<slot>, bundle
  sha256 checked against PUBLIC.json; the PI never prints task content).
- Infra failures (F5 rule, r4eval.is_infra) are moved aside (results/<name>.infra<k>) and re-queued at the front of
  the queue under the same name; never scored.

## Metrics
- Quality: blind Claude judges, prereg/RUBRIC.md, judge prompt and anonymizer of tools/r4eval.py at the commit that
  freezes this file (AMENDMENT-1 version); 2 judgments/run, 3rd if gap > 1.5 (median of 3). Not delivered => 0.
  Collapse: quality < 3.0 or not delivered.
- Active time: freeze-excluded active minutes (active_nf, r4eval.active with the heartbeat freeze windows). Raw active
  and wall are reported too.
- Tokens: total input tokens (uncached and output reported too).
- Blinding check: share of judgments whose solo/team guess is correct.

## Decision rule (tools/final_decide.py, frozen with this file)
Block pairing: diff_b = cand(b) - X(b) for each of the 8 blocks; 90% two-sided t interval over blocks.
- G1 no regression vs baselines: for X in {base4, orig}: lower 90% bound of mean quality diff > -0.5, and
  collapses(cand) <= collapses(X).
- G2 quality on par with solo: lower 90% bound of mean quality diff (cand - solo) > -0.75.
- G3 faster than solo: geometric mean of active_nf ratio cand/solo over blocks < 1.0 and its upper 90% bound < 1.10.
- G4 token budget: geometric mean of input ratio cand/solo over blocks <= 2.0 (point estimate; 90% interval reported).
Verdict: SUCCESS if G1-G4 all hold; IMPROVEMENT if G1 holds and cand beats base4 on mean quality (point) or
tokens (ratio < 0.9) without failing G1; otherwise NO-IMPROVEMENT. Every G is reported separately with its numbers;
secondary comparisons (base4 vs orig, base4 vs solo) are descriptive.
Unblinding = the first time arm labels are joined with judge scores; it happens only in final_decide.py after all
32 scores exist.
