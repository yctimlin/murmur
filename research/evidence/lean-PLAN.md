# Token-lean experiment on large tasks (fixed 2026-10-14 ~11:30 Taipei, before results)

## Breakdown (existing logs; large/breakdown.py, large/cmdmix.py)
Swarm vs solo on T1-T3 base: 4-6x model calls in total (46-58 per peer vs 26-39 solo), similar
context per call (60-80k vs 50-69k); uncached 2.1-4.4x solo. Board calls are 8-12% of input, the
draft phase 4-11% (7-20% of uncached), the tail after the last main commit 10-15%. Shell calls are
77-82%; within them git coordination (pull/rebase/push/commit + status/log/diff) is 41-45% of
swarm input vs 23-35% solo, and test runs are 4-5x solo's count.
## Change (branch feat/token-lean, from original main d881067)
G1 `.murmur/sync` one-call rebase+push with retry; G1b "every call resends your context: chain
related commands"; G2 post full-check results per commit, don't rerun a check already posted for
the same commit. No model/compaction settings.
## Arms (gpt-6-astra high, 3 peers; cap 75m swarm, 75m solo)
base = original main d881067; new = feat/token-lean; solo = plain codex exec (repo as subdir).
## Tasks (new, unseen, larger: solo expected ~45-70 min)
U1 peewee @ e245a01b: change history + point-in-time restore extension (real suite).
U2 greenfield: quire static site generator with incremental builds.
## Metrics and thresholds
Primary: uncached input ratio vs solo; also total input. Active time = gap-capped (120 s).
Quality: blind judge rubric (correctness, regressions, PR.md accuracy, design) + separate QA judge
(10-2*P0-P1); mean of 5. Keep G if: new uncached <= base * 0.75 (or <= 2x solo), new active time
<= base * 1.15, new mean >= base - 0.7 (one judge pass, noise ~1 point).
Side question: are recent smaller speedups (vs trials 2/3) due to task size or added rules?
Evidence used: solo duration vs speedup across runs, and A-old vs A-new (main vs batch-1 rules).
