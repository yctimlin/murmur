# Phase A diagnosis from existing artifacts

This is descriptive diagnosis, not a mechanism trial. All historical task/arm cells have one run (round 2 has two judges, not two run repetitions). We conducted no new lab runs. The screening tasks are designed separately and frozen by the scheduler after this phase.

Reproduce: `python3 research/tools/index_runs.py` then `python3 research/tools/diagnose.py`. Definitions, missingness, classifier rules, raw evidence paths and source limitations are in `research/data/METHODS.md`. The CSV is the numeric source for every table below.

The index covers **76 runs, 241 sessions, 668,357,819 observed input tokens, 22,209,979 uncached input and 5,016,406 output**. One empty-catalog failure has no session telemetry, and one peer in a failed 429 attempt has no provider usage; these missing costs are unknown, not zero. Research self-improvement runs remain in coverage but are excluded from task-pair comparisons.

## Coverage and timing

| Evidence batch | Runs | Sessions | Observed input | Uncached | Active minutes sum | Wall minutes sum |
|---|---|---|---|---|---|---|
| big3 | 2 | 5 | 17,436,734 | 484,670 | 65.19 | 127.45 |
| explore | 15 | 44 | 44,614,699 | 2,037,547 | 189.74 | 287.87 |
| large | 9 | 27 | 81,024,177 | 2,778,161 | 226.59 | 368.41 |
| lean | 6 | 18 | 63,330,490 | 1,779,642 | 173.42 | 185.74 |
| lean2 | 8 | 24 | 61,181,788 | 2,007,516 | 200.82 | 204.52 |
| murmur-eval | 5 | 14 | 32,062,584 | 1,061,752 | 112.74 | 114.28 |
| self | 1 | 8 | 24,535,776 | 1,263,968 | 21.32 | 21.65 |
| self2 | 1 | 7 | 37,111,029 | 886,645 | 30.91 | 31.52 |
| self2/eval | 21 | 70 | 193,356,312 | 5,222,936 | 612.45 | 868.78 |
| val | 8 | 24 | 113,704,230 | 4,687,142 | 331.75 | 343.52 |

Active minutes use the 120-second capped union of event timestamps; wall uses retained launch/exit or session spans. The sum across runs is workload accounting, not elapsed experiment duration. Box pauses and hangs explain some divergence. The index retains both, the original harness seconds, source paths, commits, merges and outcomes.

## Ranked cost associations

**Repeated prefix context is the largest measured token component: 646,147,840 cached input tokens, 96.68% of input.** Cached is a lower bound on reused context; it does not mean that all of this input can be eliminated. Uncached input is 3.32%. Output is reported separately and is not part of this denominator.

The following disjoint operational categories rank the full input contexts charged to the latest tool category. These are associations with work, not newly emitted tool tokens or causal waste. A shell containing both edits and tests is classified as edit.

| Rank | Last tool category | Input tokens | Share of all input | Tool calls |
|---|---|---|---|---|
| 1 | edit | 146,294,191 | 21.89% | 2,023 |
| 2 | other | 104,635,016 | 15.66% | 1,741 |
| 3 | git_sync | 88,859,982 | 13.30% | 1,141 |
| 4 | git_read | 86,625,131 | 12.96% | 1,213 |
| 5 | wait | 68,747,360 | 10.29% | 1,227 |
| 6 | file_read | 68,252,970 | 10.21% | 1,284 |
| 7 | verify | 53,770,361 | 8.05% | 698 |
| 8 | board | 51,172,808 | 7.66% | 684 |

The source question has a different denominator. Exact per-source tokenization is unavailable; the logs expose these serialized output character counts. These characters must not be added to cached input or model output tokens.

| Tool output source | Characters | Share of tool-output characters |
|---|---|---|
| shell_output | 33,749,874 | 36.18% |
| file_reads | 14,899,883 | 15.97% |
| board_reads | 12,358,930 | 13.25% |
| other_tool_output | 32,276,239 | 34.60% |

## Time decomposition for every run

Each row in index.csv and sessions.csv contains eight additive phase columns. The table sums capped session minutes, including root. It is peer effort, so parallel sessions overlap and the sum differs from run active minutes. The classifier follows tool operations; it does not claim to observe private reasoning or prove that gaps were idle.

| Phase | Peer minutes | Share of classified peer time |
|---|---|---|
| exploration | 447.81 | 9.15% |
| drafting | 2506.42 | 51.20% |
| waiting_idle | 734.09 | 14.99% |
| board_traffic | 254.77 | 5.20% |
| ranking | 39.45 | 0.81% |
| merging | 512.60 | 10.47% |
| verification | 321.35 | 6.56% |
| polishing | 79.23 | 1.62% |

Exploration is before the first detected edit except explicit coordination/verification operations. Drafting includes later implementation. Polishing is work after final main that is not an explicit wait, board, Git or test action. Waiting includes polling. `excluded_gap_min` retains excess per-session gaps separately.

## Draft-and-rank redundancy

| Measure | Count | Share / denominator |
|---|---|---|
| Runs with retained draft refs | 48 | 48/76 runs |
| Draft refs | 142 | all retained refs |
| Draft tips not ancestors of final main | 103 | 72.54% of draft refs |
| Draft-added text lines | 34,529 | per-branch additions versus task base |
| Added lines absent at same final path | 22,723 | 65.81% of draft-added lines |
| Draft files identical to final blob | 65 | 15.33% of 424 branch-file changes |

The absent-line metric quantifies textual non-retention, not semantic waste: moved lines, adopted drafts later improved, and useful rejected alternatives all complicate interpretation. Non-ancestor refs can be copied or cherry-picked. `drafts.csv` provides each branch, revision and count. We cannot credibly equate this percentage with token/time savings.

Before the first main commit, task swarms spent 39,070,618 input tokens (6.93% of their input); after the final main commit they spent 61,220,498 (10.86%). These chronology markers include exploration, draft/rank, tests and coordination; they are not discarded-draft token counts. Zero-main runs have no first-main boundary and are excluded from these chronology counters.

## Advisor pooled comparison, independently reconstructed

Across the advisor's same 16 baseline swarm/solo pairs, mean quality difference is **-0.6521 points** (sample SD 0.7647); swarm better/tied/worse: 2/2/12. Thus the reported approximately -0.65 gap reproduces. The geometric mean input ratio is **5.260×**, and the uniform raw-log active-time speedup is **1.145×**. The advisor mixed some wall and active durations, so its speed estimate need not equal ours.

| Swarm run | Solo run | Swarm quality | Solo quality | Difference | Input ratio | Solo/swarm active time |
|---|---|---|---|---|---|---|
| murmur-eval/A-old | murmur-eval/solo-A | 8.800 | 9.000 | -0.200 | 4.169 | 1.121 |
| explore/L1-s3 | explore/L1-solo | 8.000 | 8.800 | -0.800 | 4.928 | 1.068 |
| explore/L2-s3 | explore/L2-solo | 8.200 | 9.000 | -0.800 | 5.639 | 1.095 |
| large/T1-base | large/T1-solo | 6.600 | 8.000 | -1.400 | 5.562 | 1.104 |
| large/T2-base | large/T2-solo | 8.800 | 9.600 | -0.800 | 10.006 | 0.927 |
| large/T3-base | large/T3-solo | 9.200 | 9.200 | +0.000 | 4.811 | 1.387 |
| lean/U1-base | lean/U1-solo | 7.400 | 7.400 | +0.000 | 5.676 | 1.089 |
| lean/U2-base | lean/U2-solo | 6.400 | 6.800 | -0.400 | 7.881 | 1.099 |
| lean2/V1-base | lean2/V1-solo | 7.600 | 8.400 | -0.800 | 5.351 | 1.044 |
| lean2/V2-base | lean2/V2-solo | 6.800 | 8.800 | -2.000 | 4.276 | 1.417 |
| val/W1-base | val/solo-W1 | 6.800 | 6.400 | +0.400 | 6.458 | 1.048 |
| val/W2-base | val/solo-W2 | 8.200 | 8.400 | -0.200 | 4.670 | 1.126 |
| big3/big3 | big3/solo | 8.333 | 7.667 | +0.667 | 4.801 | 1.102 |
| self2/eval/W1-orig | self2/eval/W1-solo | 6.800 | 7.800 | -1.000 | 3.737 | 1.177 |
| self2/eval/W2-orig | self2/eval/W2-solo | 7.400 | 8.500 | -1.100 | 4.031 | 1.367 |
| self2/eval/W3-orig | self2/eval/W3-solo | 7.800 | 9.800 | -2.000 | 4.950 | 1.260 |

These are heterogeneous tasks, changing engine revisions, different rubrics and no within-cell replication. The pooled gap is a historical description; it cannot distinguish protocol from parallelism, establish an A/A noise level, or validate a peer-count optimum. Those need subsequent preregistered paired, repeated batches.

## Ranked quality deficits and delivery failures

The 15 pairs with the same five rubric dimensions give the following signed decomposition of their total net score deficit. big3 is excluded here because it uses a six-dimensional rubric. Shares sum to 100%; they are score loss, not defect counts.

| Rank | Quality dimension | Solo minus swarm point sum | Share of net dimension deficit |
|---|---|---|---|
| 1 | Judge risk-path score | 24.50 | 44.14% |
| 2 | PR.md accuracy | 15.50 | 27.93% |
| 3 | Correctness | 7.50 | 13.51% |
| 4 | Regressions | 4.50 | 8.11% |
| 5 | Design | 3.50 | 6.31% |

**Delivery failure is a separate severe mode:** 2/54 task-swarm runs (3.70%) exited 0 with no main commits. They consumed 18,058,454 input (3.20% of task-swarm input), 344,022 uncached input and 73.90 active minutes. This is an observed association; it does not prove which prompt change caused peers to stop after ranking.

| Run | Exit | Main commits | Draft refs | Input | Quality |
|---|---|---|---|---|---|
| self2/eval/W2-a2 | 0 | 0 | 3 | 10,939,146 | 1.4 |
| self2/eval/W2-base | 0 | 0 | 3 | 7,119,308 | 1.1 |

Three explicitly retained failed setup/run attempts are included separately: self2/eval/failed-W1-a1-429, self2/eval/failed-W1-a5-429, self2/eval/failed-W2-a1-emptycatalog. Their observed input totals 2,136,735; the empty-catalog attempt has unknown token cost. In addition self2/eval/W1-orig exited 1 after delivery and a long root hang. These failures must not disappear behind successful reruns.

Per-finding file, blame, phase and seam localization is in `research/data/quality_findings.csv`, with the extraction definitions and review notebook. Flags are retained as judge findings; cross-peer authorship alone does not prove causality. Unresolvable references and withdrawn evidence are marked explicitly instead of guessed.

## Defect localization and ranked finding types

The independently reviewed inventory has **230 judge-pass findings: 121 P0 and 109 P1 across 78 reports**. All 230 have retained-file attribution; each row supplies report line, file, exact or whole-file citation basis, Git authors/commits and phase evidence. These are observations per judge pass, not unique bugs: round 2 can count the same bug twice. Required-but-absent files are represented by the inherited implementation that remained, without blaming its baseline author for nondelivery.

The following mutually exclusive, title-led descriptive taxonomy ranks findings. It is exploratory and does not assign a causal mechanism.

| Rank | Finding type | Observations | Share of all judge-pass findings |
|---|---|---|---|
| 1 | parsing_query_semantics | 76 | 33.04% |
| 2 | concurrency_snapshot_identity | 35 | 15.22% |
| 3 | lifecycle_serialization_time | 34 | 14.78% |
| 4 | data_integrity_schema | 31 | 13.48% |
| 5 | other | 22 | 9.57% |
| 6 | validation_error_handling | 16 | 6.96% |
| 7 | failure_atomicity_lifecycle | 12 | 5.22% |
| 8 | delivery_absent | 4 | 1.74% |

**18 observations have an explicit judge seam claim plus exact cited lines authored by at least two peers** (14 P0, 4 P1; 9.73% of 185 swarm findings). Another 21 swarm claims lack this stronger authorship evidence. Old judges often did not label seams, and whole-file authorship cannot establish a seam, so this is not a population seam rate or proof that parallelism caused a defect.

Among 100 swarm P0 observations, 59 (59.00%) cite exact lines from one peer and 23 cite multiple peers. The remainder has no exact peer-line attribution (for example baseline/absent code or whole-file references). Single cited authorship does not rule out an interface defect.

Phase is the last blamed change of the cited lines, not proof of when a missing check or conceptual defect first arose. One finding can mention multiple phases, so the following shares overlap.

| Last-change phase mentioned | Findings mentioning phase | Share of all findings (overlapping) |
|---|---|---|
| drafting | 215 | 93.48% |
| preexisting | 32 | 13.91% |
| polishing | 9 | 3.91% |
| verification | 1 | 0.43% |

The full evidence and taxonomy definitions are in `research/data/QUALITY_METHODS.md`; `research/tools/review_quality.py` independently checks raw blame and snapshot bytes. `judge_p1` now includes direct Markdown-count means when the preserved score aggregate omitted P1; its source is explicit. In self2/eval/W3-a5, the direct P1 mean is 1.5 while the risk-formula inference is 0.5, demonstrating why the formula is not authoritative.

## Decisions and limits

1. Measure repeated context and the number/type of model calls in the next phases; visible board text size alone is not an adequate cost model.
2. Keep draft non-retention separate from avoidable effort; test any proposed simplification prospectively.
3. Treat risk-path quality, PR evidence accuracy, and delivery completion as distinct endpoints. Existing successful tests did not guarantee these outcomes.
4. Retain the protected baseline for controlled comparisons; do not promote a historical prototype or a peer-count change from these single-run comparisons.
5. Run the frozen screening tasks only through the scheduler and preregister the noise/protocol/peer-count batches in their owning later phases. No hypothesis or mechanism is selected in phase A.
