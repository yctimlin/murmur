# AMENDMENT-2 — adaptive (Bayesian sequential) allocation for the rest of E1 + E2

Written 2026-10-20 ~10:45 Asia/Taipei, on the user's directive (SUPERVISOR-DIRECTIVES 10-20 10:27), BEFORE the rule is
applied and before any E1/E2 decision. State when written: 7 runs finished/running (T3b, T1b x base4/C1/C2, T4b-base4
running); judged: T3b C1 7.0 / base4 7.8, T1b C1 7.7 / base4 7.6; C2 runs unjudged. No collapse seen (0/4 judged).
Implementation: tools/adapt.py (frozen with this amendment; sha256 in LOG.md). Everything else in E1.md/E2.md
(arms, tasks, metrics, judging, anonymization, freeze handling, infra reruns) is unchanged. The sealed held-out FINAL
is untouched.

## Why
The fixed schedule (20 + 8 runs, PAR 1 while the held-out author calibrates, ~2 h wall per run because of box
freezes) needs ~30+ h. Most of its value is in cells whose decision is still uncertain; the fixed design spends equal
runs on cells already settled. C1 targets the collapse mode; collapse has not occurred yet in r4 (0/4), so the
information per run is highest on tasks where r3 collapsed most (T4b, T3b: 2 low-mode runs each; T1b, T2: 1 each)
and on tasks not yet observed (T4b, T2).

## Model (re-fit at every interim look = whenever a run finishes or a judgment lands; tools/adapt.py, every 10 min)
Arms base4, C1, C2 on dev tasks T1b, T2, T3b, T4b. Two-part model, because r3 quality is bimodal:
- Collapse (quality < 3.0 or not delivered): c ~ Bernoulli(p_arm), prior Beta(1,1) per arm, pooled over tasks.
- Quality of non-collapsed runs: q ~ N(theta_task + delta_arm, sigma^2), sigma = 1.0 (fixed: r3 high-mode spread
  + judge noise, conservative), delta_base4 = 0, delta_C ~ N(0, 1) (skeptical), theta_task ~ N(7, 3^2).
- Expected quality of an arm: E_a = mean_task[(1 - p_a)(theta_t + delta_a) + p_a * 1.0] (1.0 = mean r3 collapse score).
- Cost: log(input tokens) ~ N(phi_task + tau_arm, 0.25^2), log(active_nf) ~ N(psi_task + alpha_arm, 0.35^2)
  (r3 A/A CV 0.16-0.35), tau/alpha ~ N(0, 1), base4 = 0. Uses every finished non-infra run (judged or not).
Posterior by conjugate Gaussian algebra + 20,000 Monte Carlo draws, fixed seed.

## Keep probabilities (posterior versions of the pre-registered E1/E2 rules)
- P_keep(C1) = P(E_C1 - E_base4 >= +0.5 AND input ratio C1/base4 <= 1.5)                       (E1 rule a,b,d)
- P_keep(C2) = P([E_C2 - E_ref >= -0.3 AND input C2/ref <= 0.85 AND active C2/ref <= 1.10] OR
                 [E_C2 - E_ref >= +0.5 AND input C2/ref <= 1.10 AND active C2/ref <= 1.10])         (E2 rule)
  ref = C1 unless C1 has been REJECTED, then ref = base4 (as E2.md).
E1 rule (c) (C1 not slower than solo) is checked deterministically at the end on the fresh solo runs, as pre-registered.

## Stopping (per candidate)
- An arm may stop only after >= 3 judged runs on >= 2 tasks that also have judged runs of its comparator(s).
- KEEP (screen pass) if P_keep >= 0.90; REJECT (futility) if P_keep <= 0.10.
- Cap: 3 runs per arm per task (12 per arm = original 8 + the pre-registered one-time extension). At the cap the
  original deterministic E1/E2 rules are applied to all data (fallback; inconclusive => REJECT, base stays).
- A stopped candidate is still run when it is the comparator (ref) of an active candidate.
- When every candidate is stopped the E1/E2 screening phase ends; freed budget goes to a new candidate (C3) that
  gets its own pre-registration before its first run.

## Allocation (when the lab queue has no pending job; exactly 1 pending job is kept so new data steer the next pick)
0. Pairing first: if on some task base4 or an active candidate's ref has fewer runs than that candidate, run the
   lagging comparator there (so a candidate never leads its comparators on a task by more than 1 run).
1. Solo: 1 fresh solo run per task (needed for E1 rule c and the goal metric), scheduled after every 4 swarm runs
   started, on the task with the most swarm runs that has no solo yet.
2. Otherwise pick the active candidate X maximizing (P_keep(1 - P_keep) + 0.02) / (1 + n_X) (uncertainty sampling,
   n_X = runs started; P_keep(1 - P_keep) is replaced by its maximum 0.25 while X has < 3 judged runs, because the
   Beta(1,1) collapse prior otherwise penalizes arms that are merely unjudged; ties -> C1), then the task with the fewest X runs (< 3), ties by r3 collapse priority T4b > T3b > T1b > T2,
   skipping "uninformative" tasks unless none is left: every arm has >= 2 judged runs there, no collapse, and
   |mean(X) - mean(base4)| < 0.3 for every candidate.
Started counts include running jobs; infra failures are withdrawn and rerun (do not count).
Every interim look is written to analysis/adapt/ (timestamped JSON) and decisions/new jobs to LOG.md.
