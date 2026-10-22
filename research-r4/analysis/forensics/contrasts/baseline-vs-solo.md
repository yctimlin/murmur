# Contrast: baseline swarm (base4) vs solo on T1b and T3b

Runs:
- T1b: E1-T1b-base4-r1 (7.6), E1-T1b-base4-r2 (7.65), and the T1b solo reference E1-T1b-solo-r1 (6.95). The T1b solo has no run file; only its timeline header was used.
- T3b: E1-T3b-base4-r1 (7.8), E1-T3b-base4-r2 (7.6), E1-T3b-solo-r1 (7.9).

Per-run evidence is in `runs/<RID>.md`. Unless noted, all minutes are active minutes (A); time figures are estimates of about ±0.5–2 min per cell.

## 1. Headline numbers

| Run | Score | Run span (A) | Agent-min | Build | Coord | Read others | Review/test others | Test own | Idle | Code lines delivered* |
|---|---|---|---|---|---|---|---|---|---|---|
| T1b-base4-r1 | 7.6 | 21.3 | 61.5 | 31.3 (51%) | 12.4 (20%) | 4.0 (7%) | 6.9 (11%) | 5.4 (9%) | 0 | 2,206 |
| T1b-base4-r2 | 7.65 | 24.1 | 68.7 | 33.2 (48%) | 13.3 (19%) | 2.9 (4%) | 7.4 (11%) | 9.8 (14%) | 0 | 2,246 |
| T1b-solo-r1 | 6.95 | 32.0 (result.json 43.1) | 32–43 | n/a | 0 | 0 | 0 | n/a | 0 | 1,907 |
| T3b-base4-r1 | 7.8 | 25.4 | 73.7 | 36.0 (49%) | 11.0 (15%) | 6.5 (9%) | 6.7 (9%) | 12.0 (16%) | 1.5 | 3,353 |
| T3b-base4-r2 | 7.6 | 38.9 | 113.0 | 65.2 (58%) | 25.4 (22%) | 6.8 (6%) | 9.3 (8%) | 4.8 (4%, undercounted) | <1 | 3,261 |
| T3b-solo-r1 | 7.9 | 39.4 | 39.4 | 17.9 (13.1 product + 4.8 tests, 45%) | 0 | 0 | 0 | 11.5 (29%) + self-review 2.5 + docs 6.3 | 0 | 2,686 |

\* Lines of py/js/html/css in `delivered/`, excluding sample-repo. This is a rough size proxy.

The team-overhead share is coordination + reading others' work + reviewing others' work:

| Run | Team overhead (agent-min) | Share of agent time |
|---|---|---|
| T1b-r1 | 23.3 | 38% |
| T1b-r2 | 23.6 | 34% |
| T3b-r1 | 24.2 | 33% |
| T3b-r2 | 41.5 | 37% |

T3b-r2's overhead alone (41.5 agent-min) is more than the entire T3b solo run (39.4).

## 2. Where the swarm's time goes compared with solo

1. **Building is roughly half of swarm time, and in absolute terms it is 2–5x the solo's.**
   - Swarm product building was 31–65 agent-min; the T3b solo spent 13.1 min writing product code, plus 4.8 min of tests.
   - The extra building produced only 15–25% more code: T3b 3.3k vs 2.7k lines; T1b 2.2k vs 1.9k.
   - The judges scored all of it the same way. Code is 6/10 in every run, and the main penalty everywhere is "dense, one-shot code".
   - So the parallel building went into more surface, not into a better product.
2. **Coordination is a fixed tax of about 11–25 agent-min per run, most of it in the first 5–7 minutes.**
   - The base4 draft → cross-review → rank → contract ritual costs about 15 agent-min in each run (T1b-r2 §8, T3b-r2 §8).
   - In T3b-r2 the ritual decided nothing. a1 proposed the final ownership split at A1.1, before any draft existed (TL:66). The "winning" a1 draft was dropped from the plan at A6.7 and its 88 lines deleted at A26.8.
   - The ritual also shipped dead code: the winning draft was merged as-is into main and never cleaned up.
     - T1b-r1: `fieldnotes/drafts/a2`, A5.5, TL:225.
     - T1b-r2: same pattern.
     - T3b-r1: `draft_demo.py` and `DRAFT-a1.md`, TL:159.
   - Both judges penalised the leftovers in 3 of 4 runs (DRAFT_LEFTOVER).
   - The solo has no such phase. It settled its architecture at A0.7 and was writing full-scope modules by A2.7.
3. **First product code reaches main later in the swarm.**

   | Run | Product code on main | First runnable end-to-end |
   |---|---|---|
   | T1b-r1 | A6.1 | A11.3 |
   | T1b-r2 | A9.1 | ~A13.9 |
   | T3b-r1 | A6.3 (A3.6 if the draft counts) | A9.9 |
   | T3b-r2 | A7.5 | A13.4 |

   The T3b solo had the whole product written (all six modules) by A11.1, when it first ran it end-to-end.
4. **Reading others' work is small: 3–7 agent-min (4–9%).**
   - Contracts posted early on the board kept builders mostly file-disjoint.
   - T1b-r2: a3 built the API against a1's posted contract "awaiting core" and it fit on the first test (TL:283, 333).
   - Merge conflicts were trivial, mostly on PR.md (1–4 per run, about 3 agent-min).
   - Reading is not where the time goes.
5. **Reviewing and testing others' work is the swarm's real added value, but it is partly duplicated.**
   - It took 7–9 agent-min (8–11%).
   - It found real seam bugs a single builder would miss:
     - T3b-r1 a2's HTTP scenario vs a1's cache key: TL:404, ebb34f6.
     - T3b-r2: secret redaction across steps, GC over-deletion, cold-cache prerequisites, import atomicity (A17.6–35.9).
     - T1b-r2: asset paths, findings truncation.
   - This probably explains robustness 8 vs the T1b solo's 7.
   - The same seams were often found 2–3 times. T1b-r2 had three separate browser harnesses and found the asset-path and 1,000-findings seams more than once. T3b-r1 had a duplicate browser review and a duplicate EOF fix.
6. **Own testing is a smaller share in the swarm than in the solo.**
   - T3b solo: 29% running and debugging, plus 12% writing tests, with an acceptance suite that copies the brief's 20 numbered scenarios (A16.0, TL:49).
   - The solo also had 16% docs and 6% self-review, and ran 5 red-to-green cycles before committing at green 59/59 (A38.2).
   - Swarm peers tested their own modules for 4–16% of agent time. Brief-level checks were spread across owners, and each peer declared "no remaining findings" for its own scope.
     - T3b-r2 TL:875.
     - T3b-r1 A24.4–25.0: "within delivered scope".
   - Gaps no one owned were never checked. Examples: T3b-r1's definition-change trigger and CLI raw JSON; T1b's XLSX and dedicated jobs (SCOPE_SHRINK, no board decision).
7. **Idle time is about 0.** No peer waited for another inside its turn. Long gaps in the timelines were single big file generations. Root spawned and waited at no token cost. Idle time is not the problem.

## 3. Why the swarm is not faster or better despite 3x the agents

### A. The swarm stops itself on wall time (WALLCLOCK_RUSH)

This is the dominant cause in 3 of 4 runs. Peers read wall timestamps (`date`, board `created_at`) and posted countdowns, while VM freezes made wall time far exceed active time.

| Run | Posts / TL | Active min actually used (of 120) |
|---|---|---|
| T1b-r1 | a1: "remaining ~33m of cap" (A15.8, TL:470); "Hard cap in ~4m (start21:08, now23:04)" (A19.8, TL:614) | about 20 |
| T1b-r2 | a1 "Hard cap elapsed" (A22.4, TL:608); a3 "Hard cap reached" (A22.5, TL:614), after a 30-wall-min freeze | about 22.5 |
| T3b-r1 | "~24min wall-clock left" (A17.2, TL:439); "Hard cap ~2min left" (A22.7, TL:624) | 25 |
| T3b-r2 | "~55m remain by wall clock" (A13.3, TL:329); "~35min cap remains" (A22.7, TL:509); a1 "finish... within cap" (A37.3, TL:834) | about 39 |

- **Peers end within about 1 active minute of each other.** The countdown is broadcast, and one agent's belief becomes everyone's.
  - T1b-r1: A20.4–21.0.
  - T1b-r2: A22.4–23.8.
  - T3b-r1: A24.7–25.0.
  - T3b-r2: A37.3–38.7.
- **What the rush cost:**
  - T3b-r1 "fixed" a redaction bug by narrowing input to secrets of 16+ characters: "More invasive schema-aware redaction risky at deadline" (TL:624). The judge called it a "slightly odd restriction" (SHORTCUT_FIX).
  - T1b-r2 a1 dropped planned work: the threshold CLI option and dossier docs (TL:563 vs TL:608).
  - No run did a cleanup or refactor pass. That is why DRAFT_LEFTOVER and the code-6 penalties remain.
- **The solo saw the same clock and did not rush.**
  - It checked `date -u` at A33.3 (TL:100), when wall time was past its "120 minutes" (prompt line 92).
  - It still ran 2 more fix/verify cycles and committed only at green (A38.2).
  - With no peers posting countdowns there was no shared deadline belief, and it ended because its plan was done.
- **Net effect:** the swarm's shorter spans (21–25 vs 32–39 active min) are not efficiency. The swarm ended early with about 95 of 120 cap-minutes unused, not because the work was complete.

### B. The draft-and-vote ritual adds fixed cost and leftovers, but no quality

- The ritual costs about 15 agent-min and delays product code by 4–7 active minutes.
- Its drafts were thrown away (T3b-r2, T1b) or shipped as dead code (T1b-r1, T1b-r2, T3b-r1).
- In T3b-r1 it worked best: claims diverged into complementary layers (A1.6, TL:89) and two of three drafts were reused.

### C. Parallel building splits the brief by module, so nobody owns brief-level coverage

- The solo's checklist was the brief itself: its 20-scenario acceptance suite was written at A16.0.
- Swarm peers verified their own modules plus the seams they happened to probe.
- Brief items outside any module were never claimed. Examples: T3b path-filtered rebuild on definition change; T1b CLI annotate/state (T1b-r1 a1 scoped the CLI down at A4.9, with no PR.md note).
- Coverage ends up equal to the solo's, not higher, despite about 2–3x the building minutes.

### D. Same model, same style failure

Every peer writes the same dense one-shot code as the solo. Three agents produce three times the code-6 surface. Nobody in any run reviewed readability. Review targeted only behaviour.

### E. Review value is real but small and partly duplicated

Cross-owner review (8–11% of agent time) is the one place the swarm beats solo (robustness 8). Without a split of review targets, about a third of it found the same seams again.

## 4. Mechanisms that would change the outcome, and the predicted log signature

1. **Monotonic budget given to peers.** Inject active or elapsed-monotonic minutes into each turn, and forbid wall-time arithmetic in prompts.
   - Expected signature: no "remaining ~Nm" or "hard cap" posts before about A100; turn ends not clustered in a 1-minute window at A20–25.
   - Spans would grow to at least 40–60 A.
   - A cleanup/refactor phase would appear: commits deleting `drafts/` and `DRAFT-*`, followed by fewer DRAFT_LEFTOVER penalties.
   - No SHORTCUT_FIX-style "risky at deadline" posts.
   - This is the highest-leverage fix.
2. **Drop or shrink the draft vote when ownership is already agreed** (T3b-r2 A1.1, T1b-r2 A2.9).
   - Expected signature: first product commit on main at A2–4 instead of A6–9.
   - About 15 fewer coordination agent-min.
   - No `drafts/` tree on main.
3. **A brief-level acceptance owner.** One peer converts the brief's numbered scenarios into a suite early, as the solo did at A16.0, and the others build against it. C2's "acceptance checks" target this.
   - Expected signature: a commit mapping all scenarios to tests before about A15.
   - Board findings would cite scenario numbers.
   - Coverage complaints such as "definition change does not trigger" or "XLSX missing" would turn into red tests and assigned fixes before any END.
4. **Partitioned review plus a readability pass.** Assign each reviewer distinct seams or scenario ranges, and run one explicit "refactor dense files" task after the features freeze.
   - Expected signature: no duplicate harnesses or re-found seams (DUPLICATE_WORK goes to 0).
   - Commits that split large modules.
   - The judge "code" score rises above 6, which no run here achieved.

Without fix 1, fixes 2–4 mostly reshuffle the same about 20–25 active minutes. With fix 1, the swarm's extra agent-minutes could buy the cleanup and brief-coverage work that the solo does serially. That is the only plausible route for 3x the agents to beat solo on quality.
